"""Run from backend/:  pytest -q   (needs a local Postgres, see README step 3)"""
import time
import uuid

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app import auth, dbtools, foods
from app.config import settings
from app.main import app

DAY = "2030-01-07"
ALICE, BOB = str(uuid.uuid4()), str(uuid.uuid4())

PROFILE = {"name": "Alice", "age": 20, "sex": "female", "height_cm": 160, "weight_kg": 52,
           "activity": "light", "diet": "veg", "allergens": ["peanut"],
           "meals": ["dinner", "breakfast", "lunch"], "capacity": {"roti": 4}}
MENU = {"start_date": DAY, "meals": {
    "breakfast": ["idli", "sambar", "chai"],
    "lunch": ["chapati", "rice", "dal fry", "mix veg", "curd"],
    "dinner": ["roti", "rice", "chole", "salad", "buttermilk", "xyz unknown dish"]}}


def H(uid):
    return {"X-User-Id": uid}


def _reset_database(url):
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("drop schema if exists public cascade")
        c.execute("drop schema if exists auth cascade")
        c.execute("create schema public")


@pytest.fixture(scope="module")
def client():
    _reset_database(settings.database_url)
    dbtools.migrate()
    dbtools.seed_foods()
    foods.clear_cache()
    with TestClient(app) as c:
        assert c.put("/v1/me", json=PROFILE, headers=H(ALICE)).status_code == 200
        assert c.post("/v1/menus", json=MENU, headers=H(ALICE)).status_code == 200
        yield c


def day(c, uid=ALICE):
    r = c.get(f"/v1/days/{DAY}", headers=H(uid))
    assert r.status_code == 200, r.text
    return r.json()


def nutrient(d, key):
    return next(n for n in d["nutrients"] if n["key"] == key)


# ---------------- basics ----------------
def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_requires_login(client):
    assert client.get(f"/v1/days/{DAY}").status_code == 401


def test_profile_and_targets(client):
    r = client.get("/v1/me", headers=H(ALICE)).json()
    assert r["profile"]["meals"] == ["breakfast", "lunch", "dinner"]      # re-ordered
    assert 1500 < r["targets"]["kcal"] < 2200
    assert r["targets"]["iron"] == 29


def test_profile_validation(client):
    bad = {**PROFILE, "age": 16}
    assert client.put("/v1/me", json=bad, headers=H(ALICE)).status_code == 422
    bad = {**PROFILE, "meals": ["midnight_snack"]}
    assert client.put("/v1/me", json=bad, headers=H(ALICE)).status_code == 422


def test_menu_matching(client):
    r = client.post("/v1/menus", json=MENU, headers=H(ALICE)).json()
    assert [u["input"] for u in r["meals"]["dinner"]["unmatched"]] == ["xyz unknown dish"]
    lunch = [m["food_id"] for m in r["meals"]["lunch"]["matched"]]
    assert lunch == ["roti", "plain_rice", "dal_tadka", "mix_veg", "curd"]


def test_no_confident_wrong_matches(client):
    cat = foods.catalog_for(ALICE)
    assert cat.match("aloo prtha")[0]["id"] == "aloo_paratha"
    assert cat.match("veg pulav")[0]["id"] == "veg_biryani"
    food, _, suggestions = cat.match("curd rice")          # different dish -> ask the user
    assert food is None and {"food_id": "curd", "name": "Curd"} in suggestions
    assert cat.match("chicken 65")[0] is None


def test_food_search(client):
    names = [f["name"] for f in client.get("/v1/foods", params={"q": "paneer"}, headers=H(ALICE)).json()]
    assert "Palak Paneer" in names


# ---------------- the planner ----------------
def test_plan_hits_calorie_window(client):
    kcal = nutrient(day(client), "kcal")
    assert 0.9 * kcal["target"] <= kcal["expected"] <= 1.1 * kcal["target"]


def test_plan_respects_capacity_and_allergy(client):
    items = [it for m in day(client)["meals"] for it in m["items"]]
    assert sum(it["servings"] for it in items if it["food_id"] == "roti") <= 4
    assert all(it["food_id"] != "peanuts" for it in items)


def test_every_meal_has_a_staple(client):
    staples = {"roti", "plain_rice", "idli", "aloo_paratha", "poha", "upma"}
    for m in day(client)["meals"]:
        if m["status"] == "planned" and not m["menu_missing"]:
            assert any(it["food_id"] in staples for it in m["items"]), m


def test_tips_suggest_foods_that_actually_help(client):
    s = client.get(f"/v1/days/{DAY}/suggestions", headers=H(ALICE)).json()
    iron = [x for x in s if x["for"] == "Iron"]
    assert all(x["amount"] >= 0.03 * 29 for x in iron)          # no half-lemon-for-iron advice


def test_skip_with_and_without_compensation(client):
    url = f"/v1/days/{DAY}/meals/breakfast"
    d = client.post(url + "/skip", json={"compensate": True}, headers=H(ALICE)).json()
    assert d["meals"][0]["status"] == "skipped"
    kcal = nutrient(d, "kcal")
    assert kcal["expected"] >= 0.9 * kcal["target"]

    full_target = kcal["target"]
    d = client.post(url + "/skip", json={"compensate": False}, headers=H(ALICE)).json()
    assert nutrient(d, "kcal")["target"] < full_target           # day's goal shrank

    d = client.delete(url, headers=H(ALICE)).json()
    assert d["meals"][0]["status"] == "planned"


def test_eat_logs_and_replans(client):
    d = client.post(f"/v1/days/{DAY}/meals/breakfast/eat",
                    json={"items": [{"food_id": "idli", "servings": 3}]}, headers=H(ALICE)).json()
    assert nutrient(d, "kcal")["consumed"] == 174
    assert d["meals"][0]["status"] == "eaten"
    assert d["meals"][1]["status"] == "planned"


def test_eat_rejects_unknown_food(client):
    r = client.post(f"/v1/days/{DAY}/meals/lunch/eat",
                    json={"items": [{"food_id": "pizza_9000", "servings": 1}]}, headers=H(ALICE))
    assert r.status_code == 400


def test_custom_food(client):
    f = client.post("/v1/foods", json={"name": "Hostel Special Upma", "unit": "plate", "kcal": 280,
                                       "protein": 6, "carbs": 40, "fat": 10}, headers=H(ALICE)).json()
    assert f["id"].startswith("c_") and f["custom"]
    names = [x["name"] for x in client.get("/v1/foods", params={"q": "hostel special"}, headers=H(ALICE)).json()]
    assert "Hostel Special Upma" in names


def test_suggestions(client):
    s = client.get(f"/v1/days/{DAY}/suggestions", headers=H(ALICE)).json()
    assert s and all(x["food_id"] != "peanuts" for x in s)


# ---------------- privacy ----------------
def test_users_are_isolated(client):
    assert client.get("/v1/me", headers=H(BOB)).status_code == 404
    client.put("/v1/me", json={**PROFILE, "name": "Bob", "sex": "male"}, headers=H(BOB))
    bob = day(client, BOB)
    assert all(m["menu_missing"] for m in bob["meals"])          # Bob can't see Alice's menu
    names = [x["name"] for x in client.get("/v1/foods", params={"q": "hostel special"}, headers=H(BOB)).json()]
    assert "Hostel Special Upma" not in names                      # nor her custom food


def test_delete_account(client):
    assert client.delete("/v1/me", headers=H(BOB)).json()["deleted"] is True
    assert client.get("/v1/me", headers=H(BOB)).status_code == 404


# ---------------- real Supabase-style login ----------------
@pytest.fixture
def supabase_mode(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://demo.supabase.co")
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret-" + "x" * 32)


def make_claims(sub, **extra):
    return {"sub": sub, "aud": "authenticated", "iss": "https://demo.supabase.co/auth/v1",
            "exp": int(time.time()) + 600, **extra}


def test_legacy_hs256_token(client, supabase_mode):
    good = jwt.encode(make_claims(ALICE), settings.supabase_jwt_secret, algorithm="HS256")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {good}"}).status_code == 200

    expired = jwt.encode(make_claims(ALICE, exp=int(time.time()) - 10),
                         settings.supabase_jwt_secret, algorithm="HS256")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    forged = jwt.encode(make_claims(ALICE), "wrong-secret-" + "y" * 32, algorithm="HS256")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    # dev header must be ignored in supabase mode
    assert client.get("/v1/me", headers=H(ALICE)).status_code == 401


def test_asymmetric_es256_token(client, supabase_mode, monkeypatch):
    private = ec.generate_private_key(ec.SECP256R1())

    class FakeJWKS:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": private.public_key()})()

    monkeypatch.setattr(auth, "_jwks_client", FakeJWKS())
    token = jwt.encode(make_claims(ALICE), private, algorithm="ES256", headers={"kid": "k1"})
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    other = ec.generate_private_key(ec.SECP256R1())
    bad = jwt.encode(make_claims(ALICE), other, algorithm="ES256", headers={"kid": "k1"})
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


# ---------------- Supabase-only migration ----------------
def test_supabase_migration_applies(monkeypatch):
    """Simulate Supabase's auth schema and check 002_auth.supabase.sql runs cleanly."""
    url = settings.database_url.rsplit("/", 1)[0] + "/eatfit_supabase_sim"
    with psycopg.connect(settings.database_url.rsplit("/", 1)[0] + "/postgres", autocommit=True) as c:
        c.execute("drop database if exists eatfit_supabase_sim")
        c.execute("create database eatfit_supabase_sim")
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("create schema auth")
        c.execute("create table auth.users (id uuid primary key)")
        c.execute("create function auth.uid() returns uuid language sql as $$ select null::uuid $$")
        c.execute("do $$ begin create role authenticated; exception when duplicate_object then null; end $$")
    monkeypatch.setattr(settings, "database_url", url)
    dbtools.migrate()
    with psycopg.connect(url) as c:
        applied = {r[0] for r in c.execute("select name from schema_migrations")}
        rls = c.execute("select relrowsecurity from pg_class where relname = 'profiles'").fetchone()[0]
    assert "002_auth.supabase.sql" in applied and rls is True


def test_delete_account_removes_login(client, supabase_mode, monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "supabase_service_key", "service-key")
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda req, timeout: calls.append((req.get_method(), req.full_url))
                        or type("R", (), {"status": 200, "__enter__": lambda s: s,
                                          "__exit__": lambda s, *a: None})())
    carol = str(uuid.uuid4())
    token = jwt.encode(make_claims(carol), settings.supabase_jwt_secret, algorithm="HS256")
    r = client.delete("/v1/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert r == {"deleted": True, "login_deleted": True}
    assert calls == [("DELETE", f"https://demo.supabase.co/auth/v1/admin/users/{carol}")]

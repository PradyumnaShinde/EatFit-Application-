"""EatFit API.  Local:  uvicorn app.main:app --reload   ->   http://127.0.0.1:8000/docs"""
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import repo
from .auth import current_user, delete_login
from .config import settings
from .db import pool
from .foods import catalog_for
from .menu_parser import MenuScanError, scan_menu
from .planner import build_day, suggestions
from .schemas import MEALS, CustomFoodIn, EatIn, MenuIn, ProfileIn, SkipIn
from .targets import daily_targets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("eatfit")


@asynccontextmanager
async def lifespan(app):
    pool.open()
    log.info("EatFit API started (env=%s, auth=%s)", settings.env, settings.auth_mode)
    yield
    pool.close()


app = FastAPI(title="EatFit API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])


# ---------------- helpers ----------------
def need_profile(uid):
    p = repo.get_profile(uid)
    if p is None:
        raise HTTPException(404, "Profile not set up yet")
    return p


def check_meal(meal):
    if meal not in MEALS:
        raise HTTPException(400, f"Unknown meal '{meal}'")


def match_names(catalog, names):
    matched, unmatched = [], []
    for name in names:
        food, score, did_you_mean = catalog.match(name)
        if food:
            matched.append({"input": name, "food_id": food["id"], "name": food["name"], "score": score})
        else:
            unmatched.append({"input": name, "suggestions": did_you_mean})
    return matched, unmatched


# ---------------- health ----------------
@app.get("/health")
def health():
    with pool.connection() as c:
        c.execute("select 1")
    return {"ok": True}


# ---------------- me / profile ----------------
@app.get("/v1/me")
def get_me(uid: str = Depends(current_user)):
    p = need_profile(uid)
    return {"profile": p, "targets": daily_targets(p)}


@app.put("/v1/me")
def put_me(body: ProfileIn, uid: str = Depends(current_user)):
    p = body.model_dump()
    repo.upsert_profile(uid, p)
    return {"profile": p, "targets": daily_targets(p)}


@app.delete("/v1/me")
def delete_me(uid: str = Depends(current_user)):
    """Deletes all of the user's data AND their login (Play Store requires this)."""
    repo.delete_user(uid)
    try:
        login_deleted = delete_login(uid)
    except Exception:
        log.exception("could not delete auth user %s", uid)
        raise HTTPException(502, "Your data was deleted but the login could not be removed; please retry")
    return {"deleted": True, "login_deleted": login_deleted}


# ---------------- foods ----------------
@app.get("/v1/foods")
def list_foods(q: str = "", category: Optional[str] = None, uid: str = Depends(current_user)):
    return catalog_for(uid).search(q, category)


@app.post("/v1/foods", status_code=201)
def create_food(body: CustomFoodIn, uid: str = Depends(current_user)):
    return repo.add_custom_food(uid, body.model_dump())


# ---------------- menus ----------------
@app.post("/v1/menus")
def save_menu(body: MenuIn, uid: str = Depends(current_user)):
    end = body.end_date or body.start_date
    if end < body.start_date or (end - body.start_date) > timedelta(days=62):
        raise HTTPException(400, "end_date must be within 62 days after start_date")
    catalog = catalog_for(uid)
    ids, report = {}, {}
    for meal, names in body.meals.items():
        matched, unmatched = match_names(catalog, names)
        ids[meal] = list(dict.fromkeys(x["food_id"] for x in matched))   # dedupe, keep order
        report[meal] = {"matched": matched, "unmatched": unmatched}
    repo.add_menu(uid, body.start_date, end, ids)
    return {"start_date": body.start_date, "end_date": end, "meals": report}


@app.get("/v1/menus/{day}")
def get_menu(day: date, uid: str = Depends(current_user)):
    catalog = catalog_for(uid)
    menu = repo.menu_for(uid, day)
    return {meal: [{"food_id": f, "name": catalog.get(f)["name"]} for f in ids if catalog.get(f)]
            for meal, ids in menu.items()}


@app.post("/v1/menus/scan")
async def scan(file: UploadFile = File(...), uid: str = Depends(current_user)):
    """Photo -> suggested matches. The app shows them for confirmation, then calls POST /v1/menus."""
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {settings.max_upload_mb} MB")
    mime = file.content_type if (file.content_type or "").startswith("image/") else "image/jpeg"
    try:
        result = scan_menu(data, mime)
    except MenuScanError as e:
        raise HTTPException(502, str(e))

    catalog = catalog_for(uid)
    meals = {m: v for m, v in (result.get("meals") or {}).items() if v}
    if not meals:
        meals = {"all": [it["name"] for it in result.get("items", []) if it.get("name")]}
    out = {}
    for meal, names in meals.items():
        matched, unmatched = match_names(catalog, names)
        out[meal] = {"matched": matched, "unmatched": unmatched}
    return {"meals": out, "prices": result.get("items", [])}


# ---------------- the day ----------------
@app.get("/v1/days/{day}")
def get_day(day: date, uid: str = Depends(current_user)):
    return build_day(uid, day, need_profile(uid), catalog_for(uid))


@app.post("/v1/days/{day}/meals/{meal}/eat")
def eat(day: date, meal: str, body: EatIn, uid: str = Depends(current_user)):
    check_meal(meal)
    profile, catalog = need_profile(uid), catalog_for(uid)
    for it in body.items:
        if catalog.get(it.food_id) is None:
            raise HTTPException(400, f"Unknown food '{it.food_id}'")
    repo.log_meal(uid, day, meal, [it.model_dump() for it in body.items])
    return build_day(uid, day, profile, catalog)


@app.post("/v1/days/{day}/meals/{meal}/skip")
def skip(day: date, meal: str, body: SkipIn, uid: str = Depends(current_user)):
    check_meal(meal)
    profile = need_profile(uid)
    repo.skip_meal(uid, day, meal, body.compensate)
    return build_day(uid, day, profile, catalog_for(uid))


@app.delete("/v1/days/{day}/meals/{meal}")
def reset(day: date, meal: str, uid: str = Depends(current_user)):
    check_meal(meal)
    profile = need_profile(uid)
    repo.reset_meal(uid, day, meal)
    return build_day(uid, day, profile, catalog_for(uid))


@app.get("/v1/days/{day}/suggestions")
def suggest(day: date, category: Optional[str] = Query(None), uid: str = Depends(current_user)):
    return suggestions(uid, day, need_profile(uid), catalog_for(uid), category)

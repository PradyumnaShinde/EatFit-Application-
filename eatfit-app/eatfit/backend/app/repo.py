"""Every database query lives here. Nothing else in the app writes SQL."""
import uuid
from datetime import date

from psycopg.types.json import Jsonb

from .db import conn

NUTRIENTS = ["kcal", "protein", "carbs", "fat", "fibre", "iron", "calcium", "vitc"]
FOOD_COLS = ("id, name, aliases, unit, grams, step, max_per_meal, diet, allergens, category, "
             "booster, " + ", ".join(NUTRIENTS) + ", source, owner_id")


def _food(r):
    food = {k: r[k] for k in ["id", "name", "aliases", "unit", "grams", "step", "max_per_meal",
                              "diet", "allergens", "category", "booster", "source"]}
    food["nutrients"] = {n: r[n] for n in NUTRIENTS}
    food["custom"] = r["owner_id"] is not None
    return food


# ---------------- foods ----------------
def official_foods():
    with conn() as c:
        return [_food(r) for r in c.execute(f"select {FOOD_COLS} from foods where owner_id is null")]


def custom_foods(uid):
    with conn() as c:
        rows = c.execute(f"select {FOOD_COLS} from foods where owner_id = %s", (uid,))
        return [_food(r) for r in rows]


def add_custom_food(uid, f):
    fid = "c_" + uuid.uuid4().hex[:10]
    with conn() as c:
        r = c.execute(f"""
            insert into foods (id, name, aliases, unit, grams, step, max_per_meal, diet, allergens,
                               category, booster, {", ".join(NUTRIENTS)}, source, owner_id)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false,
                    {", ".join(["%s"] * len(NUTRIENTS))}, 'user', %s)
            returning {FOOD_COLS}""",
            (fid, f["name"], [f["name"].lower()], f["unit"], f["grams"], f["step"],
             f["max_per_meal"], f["diet"], f["allergens"], f["category"],
             *[f[n] for n in NUTRIENTS], uid)).fetchone()
        return _food(r)


# ---------------- profiles ----------------
PROFILE_FIELDS = ["name", "age", "sex", "height_cm", "weight_kg", "activity", "goal", "diet",
                  "allergens", "avoid", "meals", "capacity", "allow_boosters",
                  "location", "occupation"]


def get_profile(uid):
    with conn() as c:
        r = c.execute(f"select {', '.join(PROFILE_FIELDS)} from profiles where user_id = %s",
                      (uid,)).fetchone()
        return dict(r) if r else None


def upsert_profile(uid, p):
    values = {k: p[k] for k in PROFILE_FIELDS}
    values["capacity"] = Jsonb(values["capacity"])
    cols = ", ".join(PROFILE_FIELDS)
    placeholders = ", ".join(f"%({k})s" for k in PROFILE_FIELDS)
    updates = ", ".join(f"{k} = excluded.{k}" for k in PROFILE_FIELDS)
    with conn() as c:
        c.execute(f"""insert into profiles (user_id, {cols}) values (%(uid)s, {placeholders})
                      on conflict (user_id) do update set {updates}, updated_at = now()""",
                  {**values, "uid": uid})


def delete_user(uid):
    """Right to erasure: remove everything we store about this user."""
    with conn() as c:
        for table in ["meal_logs", "skipped_meals", "menus", "profiles"]:
            c.execute(f"delete from {table} where user_id = %s", (uid,))
        c.execute("delete from foods where owner_id = %s", (uid,))


# ---------------- menus ----------------
def add_menu(uid, start: date, end: date, meals: dict):
    with conn() as c:
        c.execute("insert into menus (user_id, start_date, end_date, meals) values (%s, %s, %s, %s)",
                  (uid, start, end, Jsonb(meals)))


def menu_for(uid, day: date):
    """Most recently uploaded menu that covers this day."""
    with conn() as c:
        r = c.execute("""select meals from menus
                         where user_id = %s and start_date <= %s and end_date >= %s
                         order by created_at desc, id desc limit 1""", (uid, day, day)).fetchone()
        return r["meals"] if r else {}


# ---------------- a day: eaten / skipped ----------------
def eaten(uid, day: date):
    """{meal: [{food_id, servings}, ...]}"""
    out = {}
    with conn() as c:
        rows = c.execute("""select meal, food_id, servings from meal_logs
                            where user_id = %s and day = %s order by id""", (uid, day))
        for r in rows:
            out.setdefault(r["meal"], []).append({"food_id": r["food_id"], "servings": r["servings"]})
    return out


def skipped(uid, day: date):
    """{meal: compensate}"""
    with conn() as c:
        rows = c.execute("select meal, compensate from skipped_meals where user_id = %s and day = %s",
                         (uid, day))
        return {r["meal"]: r["compensate"] for r in rows}


def log_meal(uid, day: date, meal, items):
    with conn() as c:
        c.execute("delete from skipped_meals where user_id = %s and day = %s and meal = %s",
                  (uid, day, meal))
        for it in items:
            c.execute("""insert into meal_logs (user_id, day, meal, food_id, servings)
                         values (%s, %s, %s, %s, %s)""",
                      (uid, day, meal, it["food_id"], it["servings"]))


def skip_meal(uid, day: date, meal, compensate):
    with conn() as c:
        c.execute("delete from meal_logs where user_id = %s and day = %s and meal = %s",
                  (uid, day, meal))
        c.execute("""insert into skipped_meals (user_id, day, meal, compensate) values (%s, %s, %s, %s)
                     on conflict (user_id, day, meal) do update set compensate = excluded.compensate""",
                  (uid, day, meal, compensate))


def reset_meal(uid, day: date, meal):
    with conn() as c:
        c.execute("delete from meal_logs where user_id = %s and day = %s and meal = %s", (uid, day, meal))
        c.execute("delete from skipped_meals where user_id = %s and day = %s and meal = %s",
                  (uid, day, meal))

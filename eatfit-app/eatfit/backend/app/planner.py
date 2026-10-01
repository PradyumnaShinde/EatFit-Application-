"""One user, one day: targets -> what's eaten/skipped -> what's left -> plan -> tips."""
from . import repo
from .foods import is_allowed
from .optimizer import NUTRIENTS, meal_shares, optimize
from .targets import daily_targets

LABELS = {"kcal": "Calories", "protein": "Protein", "carbs": "Carbs", "fat": "Fat",
          "fibre": "Fibre", "iron": "Iron", "calcium": "Calcium", "vitc": "Vitamin C"}
UNITS = {"kcal": "kcal", "protein": "g", "carbs": "g", "fat": "g",
         "fibre": "g", "iron": "mg", "calcium": "mg", "vitc": "mg"}


def add_up(foods, items):
    total = {k: 0.0 for k in NUTRIENTS}
    for it in items:
        f = foods.get(it["food_id"])
        if f:
            for k in NUTRIENTS:
                total[k] += f["nutrients"][k] * it["servings"]
    return total


def describe(foods, items):
    out = []
    for it in items:
        f = foods.get(it["food_id"], {"name": it["food_id"], "unit": ""})
        out.append({"food_id": it["food_id"], "name": f["name"], "unit": f["unit"],
                    "servings": it["servings"], "booster": it.get("booster", False)})
    return out


def build_day(uid, day, profile, catalog):
    foods = catalog.foods
    targets = daily_targets(profile)
    menu = repo.menu_for(uid, day)
    eaten = repo.eaten(uid, day)
    skipped = repo.skipped(uid, day)
    meals = profile["meals"]

    # 1) eaten so far
    eaten_items = [it for items in eaten.values() for it in items]
    consumed = add_up(foods, eaten_items)

    # 2) skipped without compensating -> today's target shrinks by that meal's share
    shares = meal_shares(meals)
    factor = 1.0 - sum(shares.get(m, 0) for m, comp in skipped.items() if not comp)
    effective = {k: targets[k] * factor for k in NUTRIENTS}
    remaining = {k: max(effective[k] - consumed[k], 0) for k in NUTRIENTS}

    # 3) eating capacity left today ("max 4 rotis")
    capacity_left = {
        fid: cap - sum(it["servings"] for it in eaten_items if it["food_id"] == fid)
        for fid, cap in profile["capacity"].items()
    }

    # 4) plan the meals still open
    open_meals = [m for m in meals if m not in eaten and m not in skipped]
    plan = optimize(foods, remaining, targets, menu, open_meals, profile, capacity_left)

    # 5) where the day ends up if the plan is followed
    planned_items = [it for items in plan.values() for it in items]
    expected = add_up(foods, eaten_items + planned_items)

    cards = []
    for m in meals:
        if m in skipped:
            cards.append({"meal": m, "status": "skipped", "compensate": skipped[m], "items": []})
        elif m in eaten:
            cards.append({"meal": m, "status": "eaten", "items": describe(foods, eaten[m])})
        else:
            cards.append({"meal": m, "status": "planned", "items": plan.get(m, []),
                          "menu_missing": not menu.get(m)})

    return {
        "day": day.isoformat(),
        "targets": targets,
        "meals": cards,
        "nutrients": [{"key": k, "label": LABELS[k], "unit": UNITS[k],
                       "target": round(effective[k], 1),
                       "consumed": round(consumed[k], 1),
                       "expected": round(expected[k], 1)} for k in NUTRIENTS],
        "tips": tips(foods, profile, effective, expected),
    }


def best_foods_for(foods, nutrient, profile, targets, n=3, category=None):
    """Snack/fruit/add-on foods where ONE serving covers the biggest share of today's need.
    (Ranking per calorie would recommend half a lemon for iron: tiny calories, tiny help.)"""
    need = max(targets[nutrient], 1e-9)
    pool = [f for f in foods.values()
            if is_allowed(f, profile)
            and (f["booster"] or f["category"] in ("fruit", "booster", "snack"))
            and (category is None or f["category"] == category)
            and f["nutrients"][nutrient] / need >= 0.03]          # at least 3% of the day's need
    pool.sort(key=lambda f: f["nutrients"][nutrient], reverse=True)
    return pool[:n]


def tips(foods, profile, effective, expected):
    out = []
    for k in ["protein", "fibre", "iron", "calcium", "vitc"]:
        pct = expected[k] / effective[k] if effective[k] else 1
        if pct < 0.9:
            best = best_foods_for(foods, k, profile, effective, n=2)
            if not best:
                continue
            names = " or ".join(f["name"] for f in best)
            out.append({"nutrient": k, "percent": round(pct * 100),
                        "text": f"Still short on {LABELS[k]} ({round(pct * 100)}%). "
                                f"Add {names} if you can."})
    return out


def suggestions(uid, day, profile, catalog, category=None):
    """Quick Suggest: best things to grab for the 2 nutrients you're furthest behind on."""
    d = build_day(uid, day, profile, catalog)
    behind = sorted((x for x in d["nutrients"] if x["key"] != "kcal"),
                    key=lambda x: x["expected"] / max(x["target"], 1e-9))[:2]
    out = []
    for b in behind:
        targets = {x["key"]: x["target"] for x in d["nutrients"]}
        for f in best_foods_for(catalog.foods, b["key"], profile, targets, n=3, category=category):
            out.append({"for": b["label"], "food_id": f["id"], "name": f["name"],
                        "unit": f["unit"], "amount": f["nutrients"][b["key"]], "nutrient_unit": b["unit"]})
    return out

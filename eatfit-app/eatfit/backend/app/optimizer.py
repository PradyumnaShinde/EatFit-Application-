"""The planning engine: decides how many rotis / bowls of each menu item to eat.

It is a small integer linear program (see docs/OPTIMIZER.md for the maths):
  variables   : units of each food at each remaining meal
  constraints : calorie window, sensible meal sizes, eating capacity, menu availability
  objective   : land as close as possible to every remaining nutrient target
"""
import pulp

from .foods import is_allowed

NUTRIENTS = ["kcal", "protein", "carbs", "fat", "fibre", "iron", "calcium", "vitc"]

# Usual share of the day's food at each meal
MEAL_SHARE = {"breakfast": 0.25, "brunch": 0.40, "lunch": 0.35,
              "snacks": 0.10, "dinner": 0.30, "milk": 0.05}

# Penalty for missing / overshooting each target (per 100% of the day's target)
UNDER_W = {"kcal": 3, "protein": 4, "carbs": 1, "fat": 1,
           "fibre": 1, "iron": 1.5, "calcium": 1, "vitc": 1.5}
OVER_W = {"kcal": 3, "protein": 0.3, "carbs": 1, "fat": 2,
          "fibre": 0, "iron": 0, "calcium": 0, "vitc": 0}

BOOSTER_COST = 0.05          # tiny cost so add-ons are used only when they help
MAX_BOOSTERS_PER_MEAL = 2
KCAL_WINDOW = (0.9, 1.1)     # total calories must land within this band of what's left
MEAL_SIZE = (0.6, 1.4)       # each meal stays within this band of its usual share
STAPLE_CATEGORIES = {"staple", "breakfast"}   # roti, rice, idli, poha... a meal needs one


def meal_shares(meals):
    raw = {m: MEAL_SHARE.get(m, 0.2) for m in meals}
    total = sum(raw.values())
    return {m: v / total for m, v in raw.items()}


def _solver():
    highs = pulp.HiGHS(msg=False, timeLimit=10)        # fast, pip-installable (highspy)
    return highs if highs.available() else pulp.PULP_CBC_CMD(msg=False, timeLimit=10)


def optimize(foods, remaining, day_targets, menu, meals, profile, capacity_left, strict=True):
    """
    foods         : food_id -> food (the user's catalog)
    remaining     : nutrient -> amount still needed today
    day_targets   : nutrient -> full-day target (scales the penalties)
    menu          : meal -> food ids served at that meal
    meals         : meals still to be eaten, in order
    capacity_left : food_id -> max units the user can still eat today
    """
    if not meals or remaining["kcal"] < 50:
        return {m: [] for m in meals}

    shares = meal_shares(meals)
    prob = pulp.LpProblem("eatfit_plan", pulp.LpMinimize)

    # 1) variables: n[meal, food] = number of steps (pieces / half-bowls)
    n = {}
    for m in meals:
        options = [f for f in menu.get(m, []) if f in foods and is_allowed(foods[f], profile)]
        if profile["allow_boosters"]:
            options += [fid for fid, f in foods.items()
                        if f["booster"] and fid not in options and is_allowed(f, profile)]
        for fid in options:
            f = foods[fid]
            n[m, fid] = pulp.LpVariable(f"n_{m}_{fid}", 0, int(f["max_per_meal"] / f["step"]),
                                        cat="Integer")

    def units(key):
        return foods[key[1]]["step"] * n[key]

    def amount(nutrient, keys):
        return pulp.lpSum(foods[k[1]]["nutrients"][nutrient] * units(k) for k in keys)

    # 2) how far from each target
    under = {k: pulp.LpVariable(f"under_{k}", 0) for k in NUTRIENTS}
    over = {k: pulp.LpVariable(f"over_{k}", 0) for k in NUTRIENTS}
    for k in NUTRIENTS:
        prob += amount(k, n.keys()) - remaining[k] == over[k] - under[k]

    # 3) objective
    boosters = [k for k in n if foods[k[1]]["booster"] and k[1] not in menu.get(k[0], [])]
    prob += (pulp.lpSum(UNDER_W[k] * under[k] / day_targets[k] for k in NUTRIENTS)
             + pulp.lpSum(OVER_W[k] * over[k] / day_targets[k] for k in NUTRIENTS)
             + BOOSTER_COST * pulp.lpSum(n[k] for k in boosters)
             + 0.001 * pulp.lpSum(n.values()))

    # 4) constraints
    R = remaining["kcal"]
    if strict:
        prob += amount("kcal", n.keys()) >= KCAL_WINDOW[0] * R
        prob += amount("kcal", n.keys()) <= KCAL_WINDOW[1] * R
        for m in meals:
            keys = [k for k in n if k[0] == m]
            if keys:
                prob += amount("kcal", keys) >= MEAL_SIZE[0] * shares[m] * R
                prob += amount("kcal", keys) <= MEAL_SIZE[1] * shares[m] * R
            # a real meal: if the menu has a staple, eat at least one unit of one
            staples = [k for k in keys
                       if k[1] in menu.get(m, []) and foods[k[1]]["category"] in STAPLE_CATEGORIES]
            if staples:
                prob += pulp.lpSum(n[k] for k in staples) >= 1

    for fid, cap in capacity_left.items():
        keys = [k for k in n if k[1] == fid]
        if keys:
            prob += pulp.lpSum(units(k) for k in keys) <= max(cap, 0)

    for m in meals:
        mb = [k for k in boosters if k[0] == m]
        if mb:
            prob += pulp.lpSum(n[k] for k in mb) <= MAX_BOOSTERS_PER_MEAL

    prob.solve(_solver())

    if pulp.LpStatus[prob.status] != "Optimal":
        if strict:   # menu too limited for the hard rules: just get as close as possible
            return optimize(foods, remaining, day_targets, menu, meals, profile,
                            capacity_left, strict=False)
        return {m: [] for m in meals}

    # 5) read the answer
    plan = {m: [] for m in meals}
    for (m, fid), var in n.items():
        count = round(var.value() or 0)
        if count > 0:
            f = foods[fid]
            plan[m].append({"food_id": fid, "name": f["name"], "unit": f["unit"],
                            "servings": count * f["step"], "booster": (m, fid) in boosters})
    return plan

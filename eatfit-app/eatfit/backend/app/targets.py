"""Daily nutrient targets from the user's profile (section 2.h).

Calories: Mifflin-St Jeor BMR x activity factor.
Micros:   ICMR-NIN 2020 RDAs for adults (double-check against the official table).
"""

ACTIVITY_FACTOR = {
    "sedentary": 1.2,      # desk job / mostly sitting
    "light": 1.375,        # walking around campus
    "moderate": 1.55,      # sport / gym 3-5 days a week
    "active": 1.725,       # hard exercise most days
}

GOAL_ADJUST = {"lose": -0.15, "maintain": 0.0, "gain": 0.10}


def daily_targets(p):
    w, h, a = p["weight_kg"], p["height_cm"], p["age"]
    male = p["sex"] == "male"

    bmr = 10 * w + 6.25 * h - 5 * a + (5 if male else -161)
    kcal = bmr * ACTIVITY_FACTOR[p["activity"]] * (1 + GOAL_ADJUST[p.get("goal", "maintain")])

    protein = max(0.83 * w, 0.12 * kcal / 4)   # ICMR RDA 0.83 g/kg, at least 12% of energy
    fat = 0.25 * kcal / 9                      # 25% of energy
    carbs = (kcal - 4 * protein - 9 * fat) / 4 # the rest

    return {
        "kcal": round(kcal),
        "protein": round(protein),
        "carbs": round(carbs),
        "fat": round(fat),
        "fibre": round(30 * kcal / 2000),      # ~30 g per 2000 kcal
        "iron": 19 if male else 29,            # mg
        "calcium": 1000,                       # mg
        "vitc": 80 if male else 65,            # mg
    }

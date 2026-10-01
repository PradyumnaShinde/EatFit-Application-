# How the planner works

File: `backend/app/optimizer.py`. Called by `planner.py` every time a day is requested or changed.

## The question it answers

> Given what's on the menu at each remaining meal, what I've already eaten today, and my limits, **how many rotis / bowls of what** should I eat, so that by the end of the day I'm as close as possible to all 8 nutrient targets?

That's a classic **integer linear program** (ILP), the same maths airlines use for crew scheduling. It's solved exactly in well under a second by HiGHS, an open-source solver installed with `pip`.

## The model

**Variables.** For every remaining meal *m* and every allowed food *f* (on that meal's menu, plus "boosters" if enabled), let *n₍m,f₎* be a whole number of **steps**. A step is one piece (rotis, idlis, fruit) or half a bowl/plate/glass, set by the `step` column in `foods.csv`. Servings = *n × step*, capped by `max_per_meal`.

**Distance from target.** For each nutrient *k*, with *R_k* = what's still needed today:

    Σ nutrient_k(f) × servings(m,f)  −  R_k  =  over_k − under_k,      over_k, under_k ≥ 0

**Objective** (minimise):

    Σ_k  UNDER_W[k] × under_k / T_k   +   OVER_W[k] × over_k / T_k
      + 0.05 × (number of booster add-ons)
      + 0.001 × (total steps)

*T_k* is the full-day target, so every nutrient is measured in "% of a day". That way 10 mg of vitamin C and 10 g of protein aren't compared as equals.

| Weight | Why |
|---|---|
| Protein under = 4 (highest) | The ICRISAT finding that motivated EatFit: protein shortfall is common, even in well-off households |
| Calories over and under = 3 | Energy balance matters both ways |
| Fat over = 2 | Excess fat is the main overshoot risk in mess food |
| Micronutrients over = 0 | Exceeding iron or vitamin C targets from normal food is harmless at these levels |

The tiny booster cost means a guava is only added when it actually closes a gap. The tiny per-step cost breaks ties toward eating less.

**Hard rules** (in "strict" mode):

1. **Calorie window:** total calories within **90–110%** of what's left. The plan can never starve or stuff anyone.
2. **Meal size:** each meal within **60–140%** of its usual share of the day. Shares are breakfast 25%, lunch 35%, dinner 30%, snacks 10%, brunch 40%, milk 5%, re-normalised over the meals left. This prevents the "9-roti lunch".
3. **A real meal:** if a meal's menu has a staple (roti, rice, idli, poha…), at least one unit of a staple is included.
4. **Eating capacity:** "max 4 rotis a day" from the profile, minus what's already eaten.
5. **At most 2 add-ons per meal.**
6. **Diet and allergies:** disallowed foods never become variables at all.

If the rules can't all be met (a very limited menu, say), the planner drops rules 1–3 and returns the closest possible plan, rather than nothing.

## Skips and re-planning

There's no special "re-plan" algorithm. Every request rebuilds the day from the database:
- eaten food is subtracted from the targets
- skipped and eaten meals are removed from the list of open meals
- the same ILP is solved for whatever is left

| Skip type | What happens |
|---|---|
| compensate = yes | the remaining meals' shares grow, so they absorb the gap (within the meal-size rule) |
| compensate = no | the day's targets are multiplied by (1 − that meal's share) |

## Targets

`backend/app/targets.py`:
- **Calories:** Mifflin-St Jeor BMR × activity factor (1.2 / 1.375 / 1.55 / 1.725) × goal (−15% / 0 / +10%).
- **Protein:** the larger of 0.83 g/kg (ICMR-NIN 2020 adult RDA) or 12% of energy.
- **Fat:** 25% of energy. **Carbs:** the rest.
- **Fibre:** 30 g per 2000 kcal.
- **Iron** 19 mg (men) / 29 mg (women), **calcium** 1000 mg, **vitamin C** 80 / 65 mg (ICMR-NIN 2020).

Check these against the official ICMR-NIN tables and have a nutritionist sign them off.

Known limits:
- adults only
- no pregnancy or lactation adjustments
- no medical conditions handled

All of these are blocked or disclaimed in the app.

## Tuning

Everything tunable sits at the top of `optimizer.py`.

| Symptom | Change |
|---|---|
| Too much of one cheap item (e.g. 2 bowls curd every meal) | lower that food's `max_per_meal` in `foods.csv` |
| Protein often short | raise `UNDER_W["protein"]` |
| Too many add-ons | raise `BOOSTER_COST`, or lower `MAX_BOOSTERS_PER_MEAL` |
| Meals feel too big after a skip | narrow `MEAL_SIZE`, e.g. `(0.7, 1.3)` |
| Plans too rigid on calories | widen `KCAL_WINDOW` |

After any change, run `python scripts/demo.py` to eyeball a real day and `pytest -q` to make sure the rules still hold. Ideally, collect a few days of real mess menus and save the demo output before and after, so the change is visible.

## Performance

About 0.6 s per plan on a laptop for 3 meals of about 20 options each, about the same with HiGHS or CBC. That's fine for v1, since one plan is computed per tap. If it ever matters:
- cache the plan per (user, day, last-change time)
- reduce the booster pool to the 6 most useful for the user's current gaps before solving

# The food database

The planner is only as good as these numbers. This is EatFit's most important asset, and its biggest risk.

## Where it lives

- `backend/data/foods.csv` is the **source of truth** for official foods, version-controlled in git.
- On every deploy, `seed_foods.py` upserts it into the `foods` table. Edit the CSV, commit, deploy, done.
- Users' custom foods live only in the database (`owner_id` = that user) and only they see them.

## Columns

| Column | Example | Meaning |
|---|---|---|
| `id` | `dal_tadka` | permanent id; **never rename** once live (logs point to it) |
| `name` | `Dal Tadka` | shown in the app |
| `aliases` | `dal\|dal fry\|toor dal` | other names on menus, `\|`-separated, lowercase. These make matching work |
| `unit` | `bowl` | what a serving is called |
| `grams` | `150` | weight of **one** unit, as served |
| `step` | `0.5` | smallest amount the planner suggests (1 = whole pieces) |
| `max_per_meal` | `2` | most units the planner will suggest at one meal |
| `diet` | `veg` / `egg` / `nonveg` | |
| `allergens` | `gluten\|dairy` | from: gluten, dairy, peanut, egg, fish |
| `category` | `staple`, `breakfast`, `dal`, `sabzi`, `side`, `drink`, `protein`, `snack`, `fruit`, `booster` | `staple`/`breakfast` count as "a real meal" in the planner |
| `booster` | `1` | may be suggested as an add-on even when not on the menu |
| `kcal … vitc` | | nutrients for **one unit** (not per 100 g) |
| `source` | `estimate` | how trustworthy the row is (see below) |

## Data quality levels (`source`)

| Value | Meaning | OK for launch? |
|---|---|---|
| `estimate` | typical value from general references (**all 45 current rows**) | ❌ |
| `ifct-recipe` | computed from a standard recipe using IFCT raw-ingredient values | ✅ with permission to use IFCT |
| `label` | from the packet's nutrition label | ✅ |
| `lab` | lab-analysed | ✅✅ |
| `user` | a user's custom food | only for that user |

Before launch: **no official row should still say `estimate`.** A quick check:
```bash
grep -c ",estimate$" backend/data/foods.csv
```

## How to make a row trustworthy (recipe method)

Mess dishes aren't in any table as "1 mess bowl", so you compute them:

1. **Get the recipe** from the mess or a standard cookbook, scaled to one batch: raw ingredients in grams, including oil and salt.
2. **Look up each raw ingredient** in a food composition table. **IFCT 2017** (ICMR-NIN) is the Indian standard for raw ingredients; USDA FoodData Central is public domain but less Indian-specific.
3. **Sum the nutrients** for the whole batch.
4. **Weigh the cooked batch** to get total cooked grams. Cooking changes water weight, which is why you weigh the cooked dish rather than adding up raw weights.
5. **Weigh one served portion** with a kitchen scale: one ladle of dal, one roti, one bowl of rice. Do this 5 times and average. This becomes the `grams` column.
6. **Per unit** = batch nutrients × (portion grams ÷ cooked batch grams).
7. Put the numbers in the CSV, set `source=ifct-recipe`, and note the recipe in a `data/recipes/` file so anyone can re-check.

Vitamin C is partly destroyed by cooking. IFCT has retention guidance, or be conservative.

Keep a spreadsheet with this workflow; it's the bit investors and nutritionists will ask to see. **Have a qualified nutritionist review the final table.**

## Licensing (important for a company)

- Food composition tables are copyrighted publications. **Before using IFCT 2017 values commercially, get written permission or a licence from ICMR-NIN** (or confirm their current terms).
- USDA FoodData Central data is public domain (US government work).
- Values you compute and lab-test yourself are yours. Over time, that's a moat.

## Adding a dish (everyday)

1. Add a row to `foods.csv` with a new unique `id` and generous `aliases`.
2. Run `python scripts/seed_foods.py` locally, then `pytest -q`.
3. Commit and push. The deploy re-seeds production.

## Adding a nutrient (e.g. vitamin B12, zinc)

1. Add a column to `foods.csv` and fill it in for every row.
2. Create a migration `backend/migrations/003_add_b12.sql`:
   ```sql
   alter table foods add column b12 double precision not null default 0;
   ```
3. Add it to `NUTRIENTS` in `dbtools.py`, `repo.py` and `optimizer.py`, and add its weights in `optimizer.py`.
4. Add the target in `targets.py`, and the label and unit in `planner.py`.
5. Run the tests, then update the app's Nutrients screen if needed. It already shows whatever the API sends.

# EatFit API reference

Interactive version, always up to date: run the backend and open **`/docs`**.

## Conventions

- **Base URL:** `https://<your-api>`. All app endpoints start with `/v1`.
- **Auth:** every `/v1` call needs `Authorization: Bearer <Supabase access token>`. In local dev mode (`AUTH_MODE=dev`), send `X-User-Id: <uuid>` instead.
- **Dates** are `YYYY-MM-DD` in the **user's local date**. The app sends its own date, so "today" is right in every timezone.
- **Meals** are any of `breakfast, brunch, lunch, snacks, dinner, milk`.
- **Errors:** JSON `{"detail": "..."}`. A `detail` that is a string is safe to show to the user.

| Code | Meaning |
|---|---|
| 400 | Bad input (unknown meal or food, date range too long) |
| 401 | Missing, invalid or expired login. The app refreshes the token and retries once |
| 404 | Profile not set up yet → show onboarding |
| 413 | Photo too large |
| 422 | Validation failed (e.g. age under 18) |
| 502 | Menu scanning failed or isn't configured; account login deletion failed |

---

## Health

`GET /health` → `{"ok": true}`. No auth. Also checks the database. Use it for uptime monitors.

## Profile

### `GET /v1/me`
Returns the profile and daily targets, or 404 if there's no profile yet.

### `PUT /v1/me`
Create or replace the profile. Returns the profile and its targets.
```json
{
  "name": "Asha", "age": 20, "sex": "female", "height_cm": 158, "weight_kg": 50,
  "activity": "light", "goal": "maintain", "diet": "veg",
  "allergens": [], "avoid": [], "meals": ["breakfast", "lunch", "dinner"],
  "capacity": {"roti": 4}, "allow_boosters": true, "location": "", "occupation": ""
}
```
| Field | Rule |
|---|---|
| age | 18–100 |
| sex | `male` / `female` |
| height_cm | 120–230 |
| weight_kg | 30–250 |
| activity | `sedentary` / `light` / `moderate` / `active` |
| goal | `lose` / `maintain` / `gain` |
| diet | `veg` (veg only) / `egg` (veg + egg) / `nonveg` (everything) |
| allergens | any of `gluten, dairy, peanut, egg, fish` |
| avoid | food ids the user never wants suggested |
| meals | non-empty subset of the meal list; returned in time-of-day order |
| capacity | food id → max units per day |
| allow_boosters | whether the planner may suggest add-ons not on the menu |

Response `targets` (real example):
```json
{"kcal": 1686, "protein": 51, "carbs": 266, "fat": 47, "fibre": 25, "iron": 29, "calcium": 1000, "vitc": 65}
```

### `DELETE /v1/me`
Deletes all of the user's data: profile, menus, logs, skips and custom foods. If `SUPABASE_SERVICE_ROLE_KEY` is set, it also deletes their login.

Response: `{"deleted": true, "login_deleted": true}`. The app signs out afterwards.

## Foods

### `GET /v1/foods?q=paneer&category=fruit`
Searches official foods plus the user's own custom foods. Both parameters are optional. Each food looks like:
```json
{"id": "dal_tadka", "name": "Dal Tadka", "aliases": ["dal", "dal fry"], "unit": "bowl", "grams": 150,
 "step": 0.5, "max_per_meal": 2, "diet": "veg", "allergens": [], "category": "dal", "booster": false,
 "source": "estimate", "custom": false,
 "nutrients": {"kcal": 170, "protein": 9, "carbs": 20, "fat": 6, "fibre": 4, "iron": 2, "calcium": 35, "vitc": 2}}
```
Nutrients are per **one unit** (one bowl, one piece…). `step` is the smallest amount the planner will suggest.

### `POST /v1/foods` → 201
Add a custom food, visible only to this user.
```json
{"name": "Hostel Special Upma", "unit": "plate", "grams": 150, "step": 0.5, "max_per_meal": 2,
 "diet": "veg", "kcal": 280, "protein": 6, "carbs": 40, "fat": 10, "fibre": 2}
```
Returns the food with an id like `c_1a2b3c4d5e`.

## Menus

### `POST /v1/menus`
Saves what's served on a date or a date range (max 62 days). Dish names are matched to foods automatically.
```json
{"start_date": "2026-10-05", "end_date": "2026-10-11",
 "meals": {"lunch": ["chapati", "dal fry", "curd rice"]}}
```
Real response. "curd rice" is a different dish from both rice and curd, so instead of guessing, the API asks:
```json
{"start_date": "2026-10-05", "end_date": "2026-10-11",
 "meals": {"lunch": {
   "matched": [
     {"input": "chapati", "food_id": "roti", "name": "Roti", "score": 100},
     {"input": "dal fry", "food_id": "dal_tadka", "name": "Dal Tadka", "score": 100}],
   "unmatched": [
     {"input": "curd rice", "suggestions": [
       {"food_id": "plain_rice", "name": "Plain Rice"},
       {"food_id": "curd", "name": "Curd"},
       {"food_id": "jeera_rice", "name": "Jeera Rice"}]}]}}}
```
Only matched items are saved. The app shows the suggestions; the user picks one or adds a custom food, and the app saves again. Newer menus override older ones for overlapping dates.

### `GET /v1/menus/{day}`
The menu in effect on that day: `{"lunch": [{"food_id": "roti", "name": "Roti"}, ...]}`.

### `POST /v1/menus/scan` (multipart, field `file`)
Reads a menu photo (JPEG/PNG, ≤ `MAX_UPLOAD_MB`). It returns the same `matched`/`unmatched` structure per meal, plus `prices`. **Nothing is saved**: the app shows the result for confirmation, then calls `POST /v1/menus`. If the menu isn't split by meal, everything comes back under `"all"`.

## The day

### `GET /v1/days/{day}`
The full picture for a day: what's eaten, skipped and planned, plus nutrient progress and tips. Real example, shortened:
```json
{
  "day": "2026-10-05",
  "targets": {"kcal": 1686, "protein": 51, "carbs": 266, "fat": 47, "fibre": 25, "iron": 29, "calcium": 1000, "vitc": 65},
  "meals": [
    {"meal": "breakfast", "status": "planned", "menu_missing": false, "items": [
      {"food_id": "idli", "name": "Idli", "unit": "piece", "servings": 2.0, "booster": false},
      {"food_id": "sambar", "name": "Sambar", "unit": "bowl", "servings": 2.0, "booster": false},
      {"food_id": "milk", "name": "Milk", "unit": "glass", "servings": 0.5, "booster": true},
      {"food_id": "orange", "name": "Orange", "unit": "piece", "servings": 1.0, "booster": true}]},
    {"meal": "lunch", "status": "eaten", "items": [...]},
    {"meal": "dinner", "status": "skipped", "compensate": true, "items": []}
  ],
  "nutrients": [
    {"key": "kcal", "label": "Calories", "unit": "kcal", "target": 1686.0, "consumed": 0.0, "expected": 1713.0}
  ],
  "tips": [{"nutrient": "iron", "percent": 59,
            "text": "Still short on Iron (59%). Add Moong Sprouts or Roasted Chana if you can."}]
}
```
| Field | Meaning |
|---|---|
| `status` | `planned` (suggested), `eaten` (logged) or `skipped` |
| `booster: true` | an add-on that is **not** on the menu (fruit, sprouts…) |
| `menu_missing` | no menu covers this meal on this day |
| `target` | today's goal. It shrinks if a meal was skipped **without** compensating |
| `consumed` | from logged food only |
| `expected` | consumed + what the plan still suggests |

### `POST /v1/days/{day}/meals/{meal}/eat`
Logs food for a meal and marks it eaten; the remaining meals are re-planned. Calling it again *adds* items to the same meal. Returns the updated day.
```json
{"items": [{"food_id": "roti", "servings": 3}, {"food_id": "dal_tadka", "servings": 1}]}
```

### `POST /v1/days/{day}/meals/{meal}/skip`
Body: `{"compensate": true}`. Removes any logs for that meal.
- `compensate: true` → later meals grow to make up the difference.
- `compensate: false` → today's target shrinks by that meal's usual share.

Returns the updated day.

### `DELETE /v1/days/{day}/meals/{meal}`
Undo: clears logs and skip for that meal so it's planned again. Returns the updated day.

### `GET /v1/days/{day}/suggestions?category=fruit`
Quick Suggest: for the two nutrients furthest behind, the snacks, fruits or add-ons where one serving covers the most of today's need.
```json
[{"for": "Iron", "food_id": "sprouts", "name": "Moong Sprouts", "unit": "bowl", "amount": 1.6, "nutrient_unit": "mg"}]
```

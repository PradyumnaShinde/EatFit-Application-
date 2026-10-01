# Everyday development

## Daily loop

```bash
# terminal 1: database (if using Docker)
docker compose up db
# terminal 2: backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
# terminal 3: app
cd app && flutter run --dart-define-from-file=env.json      # press r to hot-reload
```

Before every push, run `cd backend && pytest -q`. CI runs the same thing.

## Git workflow (small team)

1. Branch off main with `git checkout -b feature/skip-reasons`.
2. Commit small, clear steps.
3. Push, open a Pull Request, and get one teammate to review.
4. CI must be green → merge.
5. Never commit `.env`, `env.json` or keystores.

## Where things go

| You want to… | Edit |
|---|---|
| add or change a dish | `backend/data/foods.csv` (see NUTRITION_DATA.md) |
| change how much people should eat | `backend/app/targets.py` |
| change how plans are chosen | `backend/app/optimizer.py` (see OPTIMIZER.md) |
| change what a "day" returns | `backend/app/planner.py` |
| add a database query | `backend/app/repo.py`, the only file with SQL |
| add an endpoint | `backend/app/main.py` (+ request model in `schemas.py`) |
| change the database structure | a new file in `backend/migrations/` |
| change a screen | `app/lib/screens/...` |
| call a new endpoint from the app | `app/lib/api.dart` |

## Add an endpoint (example: weekly summary)

1. **Query** in `repo.py`:
   ```python
   def logs_between(uid, start, end):
       with conn() as c:
           return list(c.execute(
               "select day, food_id, servings from meal_logs where user_id=%s and day between %s and %s",
               (uid, start, end)))
   ```
   Always filter by `user_id`; that's what keeps users' data apart.
2. **Route** in `main.py`:
   ```python
   @app.get("/v1/weeks/{start}")
   def week(start: date, uid: str = Depends(current_user)):
       ...
   ```
   `Depends(current_user)` is what makes it require login. Never skip it on `/v1` routes.
3. **Test** in `tests/test_api.py`, including one that checks another user *can't* see the data.
4. **App:** add a method in `api.dart`, then use it in a screen.
5. Document it in `docs/API.md`.

## Change the database (migrations)

Never edit an applied migration file. Add a new one:

1. Create `backend/migrations/003_something.sql`. Names run in sort order, so number them.
2. If it only makes sense on Supabase (uses `auth.`), name it `003_something.supabase.sql`; it's skipped on plain Postgres.
3. Run `python scripts/migrate.py` locally and run the tests.
4. Deploy. Migrations run automatically at container start.
5. Prefer **additive** changes (new columns with defaults). Renaming or dropping something the running app uses needs two deploys: first stop using it, then remove it.

## Add a screen (Flutter)

1. Create `app/lib/screens/new_screen.dart` (copy the structure of `nutrients_screen.dart`: load in `initState`, show loading / error / data).
2. Add it to `pages` and `destinations` in `home_shell.dart`, or open it with `Navigator.push`.
3. Use `Api.*` for data and `toast(context, ...)` for messages.

## Logs and debugging

- The backend logs to stdout. On Render: **Logs** tab.
- Unexpected server errors return 500. The traceback is in the logs, never sent to the app.
- `/docs` is the fastest way to reproduce an API problem.

## Upgrading dependencies

- **Python:** versions are pinned in `requirements.txt`. To upgrade, bump a version, run `pip install -r requirements-dev.txt`, then `pytest -q`.
  - `pulp` stays on 2.9.x on purpose: PuLP 3+/4 changed its API.
- **Flutter:** `flutter pub upgrade --major-versions`, then test the login flow, the Today screen and menu scanning by hand.

"""Database setup helpers: run migrations, load the official food list."""
import csv
from pathlib import Path

import psycopg

from .config import settings

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "migrations"
FOODS_CSV = ROOT / "data" / "foods.csv"
NUTRIENTS = ["kcal", "protein", "carbs", "fat", "fibre", "iron", "calcium", "vitc"]


def _connect():
    return psycopg.connect(settings.database_url, prepare_threshold=None)


def migrate():
    """Apply every .sql file in migrations/ once, in name order."""
    with _connect() as c:
        c.execute("""create table if not exists schema_migrations (
                       name text primary key, applied_at timestamptz not null default now())""")
        done = {r[0] for r in c.execute("select name from schema_migrations")}
        on_supabase = c.execute("select to_regprocedure('auth.uid()') is not null").fetchone()[0]
        c.commit()

        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if f.name in done:
                continue
            if ".supabase." in f.name and not on_supabase:
                print(f"  skip   {f.name} (not a Supabase database)")
                continue
            c.execute(f.read_text())
            c.execute("insert into schema_migrations (name) values (%s)", (f.name,))
            c.commit()
            print(f"  apply  {f.name}")
    print("migrations up to date")


def seed_foods():
    """Insert/update the official foods from data/foods.csv (the CSV is the source of truth)."""
    with open(FOODS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    sql = f"""
      insert into foods (id, name, aliases, unit, grams, step, max_per_meal, diet, allergens,
                         category, booster, {", ".join(NUTRIENTS)}, source, owner_id)
      values (%(id)s, %(name)s, %(aliases)s, %(unit)s, %(grams)s, %(step)s, %(max_per_meal)s,
              %(diet)s, %(allergens)s, %(category)s, %(booster)s,
              {", ".join(f"%({n})s" for n in NUTRIENTS)}, %(source)s, null)
      on conflict (id) do update set
        name = excluded.name, aliases = excluded.aliases, unit = excluded.unit,
        grams = excluded.grams, step = excluded.step, max_per_meal = excluded.max_per_meal,
        diet = excluded.diet, allergens = excluded.allergens, category = excluded.category,
        booster = excluded.booster, {", ".join(f"{n} = excluded.{n}" for n in NUTRIENTS)},
        source = excluded.source, updated_at = now()
    """
    with _connect() as c:
        for r in rows:
            params = dict(r)
            params["aliases"] = [a.strip().lower() for a in r["aliases"].split("|") if a.strip()]
            params["allergens"] = [a for a in r["allergens"].split("|") if a]
            params["booster"] = r["booster"] == "1"
            for k in ["grams", "step", "max_per_meal"] + NUTRIENTS:
                params[k] = float(r[k])
            params["source"] = r.get("source") or "estimate"
            c.execute(sql, params)
        c.commit()
    print(f"seeded {len(rows)} official foods")

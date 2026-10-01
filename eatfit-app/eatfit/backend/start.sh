#!/bin/sh
# Container entrypoint: bring the database up to date, then serve.
set -e
python scripts/migrate.py
python scripts/seed_foods.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers

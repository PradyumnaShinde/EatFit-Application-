"""Usage (from backend/):  python scripts/migrate.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dbtools import migrate  # noqa: E402

migrate()

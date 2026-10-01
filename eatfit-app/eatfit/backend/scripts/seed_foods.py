"""Usage (from backend/):  python scripts/seed_foods.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dbtools import seed_foods  # noqa: E402

seed_foods()

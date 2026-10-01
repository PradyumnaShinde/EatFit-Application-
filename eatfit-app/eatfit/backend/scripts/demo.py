"""Walks through a full day against your local database and prints it.
Usage (from backend/, with AUTH_MODE=dev):  python scripts/demo.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

USER = {"X-User-Id": "00000000-0000-0000-0000-00000000d3e0"}
DAY = date.today().isoformat()


def show(title, d):
    print(f"\n===== {title} =====")
    for m in d["meals"]:
        print(f"{m['meal'].upper():10} [{m['status']}]")
        for it in m["items"]:
            tag = "  (add-on)" if it.get("booster") else ""
            print(f"   - {it['servings']:g} {it['unit']} {it['name']}{tag}")
    print("End of day if you follow this:")
    for n in d["nutrients"]:
        pct = round(100 * n["expected"] / n["target"]) if n["target"] else 0
        print(f"   {n['label']:10} {n['expected']:7.0f} / {n['target']:<7.0f}{n['unit']:5}{pct:4d}%")
    for t in d["tips"]:
        print("   TIP:", t["text"])


with TestClient(app) as c:
    c.put("/v1/me", headers=USER, json={
        "name": "Demo", "age": 19, "sex": "male", "height_cm": 172, "weight_kg": 62,
        "activity": "light", "diet": "veg", "capacity": {"roti": 5}})
    r = c.post("/v1/menus", headers=USER, json={"start_date": DAY, "meals": {
        "breakfast": ["Poha", "bread", "milk", "banana"],
        "lunch": ["chapati", "rice", "dal fry", "aloo sabzi", "curd", "salad"],
        "dinner": ["roti", "rice", "rajma", "bhindi", "buttermilk", "curd rice"]}}).json()
    for meal, v in r["meals"].items():
        for u in v["unmatched"]:
            print(f"Not sure what '{u['input']}' is -> did you mean {[s['name'] for s in u['suggestions']]}?")
    for meal in ["breakfast", "lunch", "dinner"]:
        c.delete(f"/v1/days/{DAY}/meals/{meal}", headers=USER)      # start the day fresh

    show("Today's plan", c.get(f"/v1/days/{DAY}", headers=USER).json())
    show("Skipped breakfast (will compensate)",
         c.post(f"/v1/days/{DAY}/meals/breakfast/skip", json={"compensate": True}, headers=USER).json())
    show("After eating lunch",
         c.post(f"/v1/days/{DAY}/meals/lunch/eat", headers=USER, json={"items": [
             {"food_id": "roti", "servings": 3}, {"food_id": "dal_tadka", "servings": 1},
             {"food_id": "plain_rice", "servings": 1}]}).json())

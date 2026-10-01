"""Food catalog for one user = official foods + that user's custom foods.
Handles name matching ('aloo prtha' -> Aloo Paratha) and diet/allergy filtering."""
from rapidfuzz import fuzz, process

from . import repo

_official_cache = None


def official():
    global _official_cache
    if _official_cache is None:
        _official_cache = repo.official_foods()
    return _official_cache


def clear_cache():
    global _official_cache
    _official_cache = None


class Catalog:
    def __init__(self, foods):
        self.foods = {f["id"]: f for f in foods}
        self._names, self._ids = [], []
        for f in foods:
            for name in [f["name"].lower()] + list(f["aliases"]):
                self._names.append(name)
                self._ids.append(f["id"])

    def get(self, fid):
        return self.foods.get(fid)

    def match(self, text, min_score=85):
        """Best food for a typed/scanned name.

        Returns (food, score, suggestions). food is None when we're not sure:
        'curd rice' must NOT silently become 'plain rice' -- the user picks instead.
        """
        text = (text or "").lower().strip()
        if not text:
            return None, 0, []
        if text in self.foods:
            return self.foods[text], 100, []
        if text in self._names:
            return self.foods[self._ids[self._names.index(text)]], 100, []
        hit = process.extractOne(text, self._names, scorer=fuzz.token_sort_ratio)
        if hit and hit[1] >= min_score:
            return self.foods[self._ids[hit[2]]], round(hit[1]), []
        return None, round(hit[1]) if hit else 0, self.suggest(text)

    def suggest(self, text, n=3):
        """Loose 'did you mean' candidates for a name we couldn't match."""
        out = []
        for _, score, idx in process.extract(text, self._names, scorer=fuzz.WRatio, limit=n * 4):
            f = self.foods[self._ids[idx]]
            if score >= 60 and f["id"] not in [x["food_id"] for x in out]:
                out.append({"food_id": f["id"], "name": f["name"]})
        return out[:n]

    def search(self, query="", category=None, limit=15):
        pool = [f for f in self.foods.values() if not category or f["category"] == category]
        if not query:
            return sorted(pool, key=lambda f: f["name"])[:limit]
        hits = process.extract(query.lower(), self._names, scorer=fuzz.WRatio, limit=limit * 4)
        seen, out = set(), []
        for _, score, idx in hits:
            f = self.foods[self._ids[idx]]
            if score >= 75 and f["id"] not in seen and (not category or f["category"] == category):
                seen.add(f["id"])
                out.append(f)
        return out[:limit]


def catalog_for(uid):
    return Catalog(official() + repo.custom_foods(uid))


DIET_ALLOWS = {"veg": {"veg"}, "egg": {"veg", "egg"}, "nonveg": {"veg", "egg", "nonveg"}}


def is_allowed(food, profile):
    """Respect diet type, allergies and foods the user wants to avoid."""
    if food["diet"] not in DIET_ALLOWS[profile["diet"]]:
        return False
    if set(food["allergens"]) & set(profile["allergens"]):
        return False
    return food["id"] not in profile["avoid"]

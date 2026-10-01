"""Shapes of request bodies. FastAPI validates every request against these."""
from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

MEALS = ["breakfast", "brunch", "lunch", "snacks", "dinner", "milk"]
ALLERGENS = ["gluten", "dairy", "peanut", "egg", "fish"]


class ProfileIn(BaseModel):
    name: str = Field("", max_length=80)
    age: int = Field(ge=18, le=100)            # v1 is adults-only (see README: minors & consent)
    sex: str = Field(pattern="^(male|female)$")
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=30, le=250)
    activity: str = Field("light", pattern="^(sedentary|light|moderate|active)$")
    goal: str = Field("maintain", pattern="^(lose|maintain|gain)$")
    diet: str = Field("veg", pattern="^(veg|egg|nonveg)$")
    allergens: List[str] = []
    avoid: List[str] = []
    meals: List[str] = ["breakfast", "lunch", "dinner"]
    capacity: Dict[str, float] = {}            # {"roti": 4}
    allow_boosters: bool = True
    location: str = Field("", max_length=80)
    occupation: str = Field("", max_length=80)

    @field_validator("meals")
    @classmethod
    def meals_valid(cls, v):
        bad = [m for m in v if m not in MEALS]
        if bad or not v:
            raise ValueError(f"meals must be a non-empty subset of {MEALS}")
        return [m for m in MEALS if m in v]    # keep the order of the day

    @field_validator("allergens")
    @classmethod
    def allergens_valid(cls, v):
        bad = [a for a in v if a not in ALLERGENS]
        if bad:
            raise ValueError(f"unknown allergens {bad}; allowed: {ALLERGENS}")
        return v


class MenuIn(BaseModel):
    start_date: date
    end_date: Optional[date] = None
    meals: Dict[str, List[str]]                # names as typed/scanned, or food ids

    @field_validator("meals")
    @classmethod
    def meals_valid(cls, v):
        bad = [m for m in v if m not in MEALS]
        if bad:
            raise ValueError(f"unknown meals {bad}")
        return v


class Item(BaseModel):
    food_id: str
    servings: float = Field(gt=0, le=20)


class EatIn(BaseModel):
    items: List[Item] = Field(min_length=1)


class SkipIn(BaseModel):
    compensate: bool = True


class CustomFoodIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    unit: str = Field("bowl", max_length=20)
    grams: float = Field(100, gt=0, le=2000)
    step: float = Field(0.5, gt=0, le=1)
    max_per_meal: float = Field(2, gt=0, le=10)
    diet: str = Field("veg", pattern="^(veg|egg|nonveg)$")
    allergens: List[str] = []
    category: str = "custom"
    kcal: float = Field(ge=0, le=3000)
    protein: float = Field(0, ge=0)
    carbs: float = Field(0, ge=0)
    fat: float = Field(0, ge=0)
    fibre: float = Field(0, ge=0)
    iron: float = Field(0, ge=0)
    calcium: float = Field(0, ge=0)
    vitc: float = Field(0, ge=0)

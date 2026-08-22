from decimal import Decimal

from pydantic import BaseModel


class FoodSearchResult(BaseModel):
    id: int
    food_name: str
    brand_name: str | None
    data_type: str | None
    calories_per_100g: Decimal | None
    protein_per_100g: Decimal | None
    carbs_per_100g: Decimal | None
    fat_per_100g: Decimal | None
    default_serving_g: Decimal | None

"""Importing this package registers every table on Base.metadata.

Alembic's env.py imports it for autogenerate; without that, autogenerate sees an
empty schema and happily writes a migration that drops all your tables.
"""

from app.models.diary import FoodEntry
from app.models.food import Food, FoodAlias
from app.models.photo import PhotoScan, PhotoScanItem
from app.models.rag import MealHistoryEmbedding
from app.models.recipe import Recipe, RecipeIngredient
from app.models.tracking import ExerciseLog, ExerciseType, WaterLog, WeightLog
from app.models.user import User, UserGoal

__all__ = [
    "ExerciseLog",
    "ExerciseType",
    "Food",
    "FoodAlias",
    "FoodEntry",
    "MealHistoryEmbedding",
    "PhotoScan",
    "PhotoScanItem",
    "Recipe",
    "RecipeIngredient",
    "User",
    "UserGoal",
    "WaterLog",
    "WeightLog",
]

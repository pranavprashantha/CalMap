from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FoodEntry(Base):
    """One logged food. The core row of the whole product."""

    __tablename__ = "food_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_method IN ('manual','barcode','photo','chat')",
            name="ck_food_entries_entry_method",
        ),
        CheckConstraint(
            "meal_type IN ('breakfast','lunch','dinner','snack')",
            name="ck_food_entries_meal_type",
        ),
        CheckConstraint(
            "confidence_tier IN ('high','medium','low')",
            name="ck_food_entries_confidence_tier",
        ),
        # The diary's only hot query, and it filters on the local date, not the instant.
        Index("idx_food_entries_user_date", "user_id", "logged_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Null when the item was fully AI-estimated with no confident database match.
    food_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("foods.id"))
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id"))

    entry_method: Mapped[str] = mapped_column(Text, nullable=False)
    meal_type: Mapped[str] = mapped_column(Text, nullable=False)

    # What was actually logged and shown, kept independently of food_id so the diary
    # still renders for AI-estimated items and survives food rows changing.
    food_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_g: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)

    # Snapshotted at log time. A later USDA correction must not rewrite history.
    calories: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    protein_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    fat_g: Mapped[float | None] = mapped_column(Numeric(7, 2))

    confidence_tier: Mapped[str | None] = mapped_column(Text)
    confidence_reason: Mapped[str | None] = mapped_column(Text)

    # Two time fields, deliberately:
    #   logged_at   — the exact UTC instant, for ordering and auditing.
    #   logged_date — the user's LOCAL calendar date, computed client-side at log
    #                 time, and the authoritative answer to "which day is this on".
    # Diary queries filter on logged_date only. Deriving the day from logged_at puts
    # an 8pm meal on tomorrow's page for anyone west of UTC.
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

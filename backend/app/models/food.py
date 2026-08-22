from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Food(Base):
    __tablename__ = "foods"
    __table_args__ = (
        # Makes the USDA/OFF importers idempotent: re-running upserts instead of
        # duplicating. Scoped to (source, external_id) because an fdc_id and an OFF
        # barcode can collide numerically while meaning different things.
        UniqueConstraint("source", "external_id", name="uq_foods_source_external_id"),
        Index("idx_foods_name_trgm", text("food_name gin_trgm_ops"), postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'usda'"))
    external_id: Mapped[str | None] = mapped_column(Text)
    food_name: Mapped[str] = mapped_column(Text, nullable=False)
    brand_name: Mapped[str | None] = mapped_column(Text)
    barcode: Mapped[str | None] = mapped_column(Text, unique=True)

    calories_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    protein_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    carbs_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    fat_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    fiber_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    sugar_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    sodium_mg_per_100g: Mapped[float | None] = mapped_column(Numeric(7, 2))

    default_serving_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FoodAlias(Base):
    """Solves "the model said 'soda', the database says 'Carbonated Soft Drink'".

    Checked before fuzzy search, so known synonyms resolve exactly rather than
    depending on a trigram similarity threshold.
    """

    __tablename__ = "food_aliases"
    __table_args__ = (
        UniqueConstraint("alias", "food_id", name="uq_food_aliases_alias_food"),
        Index("idx_food_aliases_alias_trgm", text("alias gin_trgm_ops"), postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    food_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )

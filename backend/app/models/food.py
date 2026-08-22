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
        Index(
            "idx_foods_name_trgm",
            "food_name",
            postgresql_using="gin",
            postgresql_ops={"food_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'usda'"))
    external_id: Mapped[str | None] = mapped_column(Text)

    # Which USDA dataset this came from, stored raw: 'foundation_food',
    # 'sr_legacy_food', 'branded_food'. Null for non-USDA sources. Search ranks on
    # this so that importing Branded later does not bury the generic result — a
    # query for "chicken breast" should not return forty store-brand fillets first.
    data_type: Mapped[str | None] = mapped_column(Text)

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


class FoodPortion(Base):
    """Household measures for a food: "1 cup" = 158g, "1 slice" = 28g.

    People log "a cup of rice", not "158 grams", so the logging UI needs real
    choices rather than one default. This is also where a vision model's portion
    estimate lands in Phase 2 — "about a cup" maps to a row here, not to grams.

    `amount` and `unit` are kept alongside `description` so the UI can format or
    scale a portion ("2 cups") instead of only displaying USDA's label verbatim.
    """

    __tablename__ = "food_portions"
    __table_args__ = (
        # Idempotent import: re-running updates rows rather than duplicating them.
        UniqueConstraint("food_id", "external_id", name="uq_food_portions_food_external"),
        Index("idx_food_portions_food_id", "food_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(Text)

    amount: Mapped[float | None] = mapped_column(Numeric(9, 3))
    unit: Mapped[str | None] = mapped_column(Text)
    modifier: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    gram_weight: Mapped[float] = mapped_column(Numeric(9, 2), nullable=False)

    # USDA's display order. Lowest sequence is the most conventional portion and
    # makes a reasonable default selection in the UI.
    seq_num: Mapped[int | None] = mapped_column(Integer)


class FoodAlias(Base):
    """Solves "the model said 'soda', the database says 'Carbonated Soft Drink'".

    Checked before fuzzy search, so known synonyms resolve exactly rather than
    depending on a trigram similarity threshold.
    """

    __tablename__ = "food_aliases"
    __table_args__ = (
        UniqueConstraint("alias", "food_id", name="uq_food_aliases_alias_food"),
        Index(
            "idx_food_aliases_alias_trgm",
            "alias",
            postgresql_using="gin",
            postgresql_ops={"alias": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    food_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )

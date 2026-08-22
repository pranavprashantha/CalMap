from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MealHistoryEmbedding(Base):
    """Phase 3. Semantic match against the user's own past phrasing.

    Vector search is correct here and wrong for nutrition lookup: the same dish gets
    described differently run to run ("chicken curry with rice" / "curry chicken
    bowl"), whereas "skim milk" must never semantically match "whole milk".

    No IVFFlat/HNSW index: brute force is fine at per-user scale (hundreds to low
    thousands of rows). Add one only if that assumption stops holding.
    """

    __tablename__ = "meal_history_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    meal_description: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    food_entry_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_entries.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PhotoScan(Base):
    """Phase 2. Raw vision output, kept before any diary entry is created."""

    __tablename__ = "photo_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Full structured model response, retained for debugging and re-running the
    # matching pipeline without re-billing a vision call.
    raw_model_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PhotoScanItem(Base):
    __tablename__ = "photo_scan_items"
    __table_args__ = (
        CheckConstraint(
            "confidence_tier IN ('high','medium','low')",
            name="ck_photo_scan_items_confidence_tier",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    photo_scan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("photo_scans.id", ondelete="CASCADE"), nullable=False
    )
    detected_name: Mapped[str] = mapped_column(Text, nullable=False)
    matched_food_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("foods.id"))
    estimated_quantity_g: Mapped[float | None] = mapped_column(Numeric(7, 2))
    confidence_tier: Mapped[str | None] = mapped_column(Text)
    confidence_reason: Mapped[str | None] = mapped_column(Text)
    # Low-confidence items require confirmation before becoming a diary entry.
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    resulting_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("food_entries.id")
    )

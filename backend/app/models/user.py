from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("sex IN ('male', 'female', 'other')", name="ck_users_sex"),
        CheckConstraint(
            "activity_level IN ('sedentary','light','moderate','active','very_active')",
            name="ck_users_activity_level",
        ),
        CheckConstraint("goal_type IN ('lose','maintain','gain')", name="ck_users_goal_type"),
        UniqueConstraint("auth_provider", "external_auth_id", name="uq_users_external_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    # Identity lives with the auth provider, not here. password_hash exists only so
    # local password auth remains possible; it stays null for provider-backed and
    # dev-stub users. auth_provider is 'dev_stub' until the auth milestone.
    password_hash: Mapped[str | None] = mapped_column(Text)
    auth_provider: Mapped[str | None] = mapped_column(Text)
    external_auth_id: Mapped[str | None] = mapped_column(Text)

    display_name: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(Text)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2))
    activity_level: Mapped[str | None] = mapped_column(Text)
    goal_type: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserGoal(Base):
    """Calorie/macro targets, recalculated when weight, activity, or goal changes.

    Kept as a history rather than columns on `users`: `effective_from` means a past
    diary day can still be read against the targets that applied at the time.
    """

    __tablename__ = "user_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    calorie_target: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_target_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    carbs_target_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    fat_target_g: Mapped[float | None] = mapped_column(Numeric(6, 2))
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

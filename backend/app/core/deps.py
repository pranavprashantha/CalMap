from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models.user import User

DEV_USER_EMAIL = "dev@calmap.local"
DEV_AUTH_PROVIDER = "dev_stub"


async def get_current_user(session: AsyncSession = Depends(get_session)) -> User:
    """Resolve the acting user.

    Phase 1 has no authentication: this returns a single seeded dev user, creating
    it on first use. That makes the API completely open, so the server must stay on
    the LAN until the auth milestone.

    The point of routing through a dependency now, rather than passing a user id
    around, is that swapping in real token verification later changes this function
    and nothing else. Services take `user_id` explicitly for the same reason.
    """
    if settings.environment != "development":
        raise RuntimeError(
            "The dev-user stub is development-only. Wire up the real auth provider "
            "before running with ENVIRONMENT set to anything else."
        )

    result = await session.execute(select(User).where(User.auth_provider == DEV_AUTH_PROVIDER))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=DEV_USER_EMAIL,
            auth_provider=DEV_AUTH_PROVIDER,
            display_name="Dev User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user

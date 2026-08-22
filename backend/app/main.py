from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db import get_session
from app.models.user import User

app = FastAPI(title="CalMap API")


class HealthResponse(BaseModel):
    status: str
    database: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None
    auth_provider: str | None


@app.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    """Round-trips the database on purpose.

    A health check that only proves the process is alive would pass while the
    database connection is misconfigured — which is what this exists to catch.
    """
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="connected")


@app.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    """Who the API thinks you are. Returns the dev stub until auth lands."""
    return user

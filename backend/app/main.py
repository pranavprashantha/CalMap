from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

app = FastAPI(title="CalMap API")


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Round-trips the database on purpose.

    A health check that only proves the process is alive would let M0 pass while the
    database connection is misconfigured — which is exactly what M0 exists to catch.
    """
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}

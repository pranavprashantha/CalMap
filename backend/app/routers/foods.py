from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas.food import FoodSearchResult
from app.services import foods as food_service

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("/search", response_model=list[FoodSearchResult])
async def search(
    q: str = Query(..., description="Search text, e.g. 'chicken breast'"),
    limit: int = Query(25, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[FoodSearchResult]:
    return await food_service.search_foods(session, q, limit)

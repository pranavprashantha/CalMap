from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.food import FoodSearchResult

# word_similarity, not similarity.
#
# Plain similarity() compares the query against the WHOLE name, so a search for
# "chicken" scores terribly against "Chicken, broiler or fryers, breast, skinless,
# boneless, meat only, cooked, braised" purely because that name is long.
# word_similarity() scores the query against the best-matching run of words inside
# the name instead, which is what a search box should do. Both use the same GIN
# trigram index, so this costs nothing.
#
# Trigram matching, deliberately, rather than vector similarity: "skim milk" must
# never semantically match "whole milk" and corrupt the macros.
SEARCH_SQL = text(
    """
    SELECT id,
           food_name,
           brand_name,
           data_type,
           calories_per_100g,
           protein_per_100g,
           carbs_per_100g,
           fat_per_100g,
           default_serving_g
    FROM foods
    WHERE :query <% food_name
    ORDER BY word_similarity(:query, food_name) DESC,
             -- Lab-analysed generics outrank older generics, which outrank brands.
             -- Without this, importing Branded Foods buries "Chicken, breast, raw"
             -- under dozens of store-brand fillets.
             CASE data_type
                 WHEN 'foundation_food' THEN 0
                 WHEN 'sr_legacy_food' THEN 1
                 ELSE 2
             END,
             -- Shorter names are the plainer, more generic item.
             length(food_name)
    LIMIT :limit
    """
)


async def search_foods(
    session: AsyncSession, query: str, limit: int = 25
) -> list[FoodSearchResult]:
    """Fuzzy-search foods by name. Returns [] for a blank query rather than
    scanning the table."""
    query = query.strip()
    if not query:
        return []

    result = await session.execute(SEARCH_SQL, {"query": query, "limit": limit})
    return [FoodSearchResult.model_validate(row, from_attributes=True) for row in result]

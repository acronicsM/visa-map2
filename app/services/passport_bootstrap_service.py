from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import (
    PASSPORT_BOOTSTRAP_KEY,
    PASSPORT_BOOTSTRAP_TTL,
    TRAVEL_COSTS_KEY,
    TRAVEL_COSTS_TTL,
    cache_get,
    cache_set,
)
from app.models.travel_cost_matrix import TravelCostMatrix
from app.schemas.passport_bootstrap import PassportBootstrapResponse
from app.schemas.travel_cost import BudgetTier
from app.schemas.visa_policy import VisaMapItem
from app.services.country_service import get_country_by_iso2
from app.services.travel_cost_service import get_travel_cost_currencies
from app.services.visa_service import get_visa_map


async def _fetch_scores_by_tier(
    db: AsyncSession,
    home_iso2: str,
) -> dict[BudgetTier, dict[str, float]]:
    result = await db.execute(
        select(
            TravelCostMatrix.dest_iso2,
            TravelCostMatrix.score_cheap,
            TravelCostMatrix.score_normal,
            TravelCostMatrix.score_expensive,
        ).where(TravelCostMatrix.home_iso2 == home_iso2)
    )

    scores_by_tier: dict[BudgetTier, dict[str, float]] = {
        BudgetTier.cheap: {},
        BudgetTier.normal: {},
        BudgetTier.expensive: {},
    }
    for row in result.all():
        dest = str(row.dest_iso2).strip().upper()
        cheap = row.score_cheap
        normal = row.score_normal
        expensive = row.score_expensive
        if cheap is not None:
            scores_by_tier[BudgetTier.cheap][dest] = float(cheap)
        if normal is not None:
            scores_by_tier[BudgetTier.normal][dest] = float(normal)
        if expensive is not None:
            scores_by_tier[BudgetTier.expensive][dest] = float(expensive)

    return scores_by_tier


async def _warm_travel_cost_tier_caches(
    home_iso2: str,
    scores_by_tier: dict[BudgetTier, dict[str, float]],
) -> None:
    for tier in BudgetTier:
        scores = scores_by_tier.get(tier, {})
        if not scores:
            continue
        cache_key = TRAVEL_COSTS_KEY.format(home_iso2=home_iso2, tier=tier.value)
        await cache_set(cache_key, scores, TRAVEL_COSTS_TTL)


async def get_passport_bootstrap(
    db: AsyncSession,
    home_iso2: str,
) -> PassportBootstrapResponse | None:
    """
    Агрегат для UI: visa-map, scores по всем tier, список валют.
    Возвращает None, если страна не найдена.
    """
    home = home_iso2.strip().upper()
    cache_key = PASSPORT_BOOTSTRAP_KEY.format(home_iso2=home)
    cached = await cache_get(cache_key)
    if cached is not None:
        return PassportBootstrapResponse.model_validate(cached)

    country = await get_country_by_iso2(db, home)
    if not country:
        return None

    visa_rows = await get_visa_map(db, home)
    visa_map = [VisaMapItem.model_validate(row) for row in visa_rows]
    scores_by_tier = await _fetch_scores_by_tier(db, home)
    currencies = await get_travel_cost_currencies(db, home)

    response = PassportBootstrapResponse(
        home_iso2=home,
        visa_map=visa_map,
        scores_by_tier=scores_by_tier,
        currencies=currencies,
    )
    await cache_set(cache_key, response.model_dump(mode="json"), PASSPORT_BOOTSTRAP_TTL)
    await _warm_travel_cost_tier_caches(home, scores_by_tier)
    return response

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import (
    VACATION_EXOTIC_KEY,
    VACATION_EXOTIC_TTL,
    VACATION_PROFILES_KEY,
    VACATION_PROFILES_TTL,
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
)
from app.models.country_vacation_profile import (
    CountryVacationExoticScore,
    CountryVacationProfile,
)
from app.schemas.vacation import (
    VacationExoticResponse,
    VacationProfileScalars,
    VacationProfilesResponse,
)

logger = logging.getLogger(__name__)


def _to_float(v) -> float | None:
    if v is None:
        return None
    return float(v)


async def invalidate_vacation_cache() -> None:
    await cache_delete(VACATION_PROFILES_KEY)
    await cache_delete_pattern("vacation:exotic:*")
    logger.info("Vacation cache invalidated")


async def get_vacation_profiles(db: AsyncSession) -> VacationProfilesResponse:
    cached = await cache_get(VACATION_PROFILES_KEY)
    if cached is not None:
        return VacationProfilesResponse.model_validate(cached)

    result = await db.execute(
        select(
            CountryVacationProfile.iso2,
            CountryVacationProfile.beach_score,
            CountryVacationProfile.ski_score,
            CountryVacationProfile.food_score,
            CountryVacationProfile.natural_score,
            CountryVacationProfile.culture_score,
        )
    )
    profiles: dict[str, VacationProfileScalars] = {}
    for row in result.all():
        iso2 = str(row.iso2).strip().upper()
        profiles[iso2] = VacationProfileScalars(
            beach=_to_float(row.beach_score),
            ski=_to_float(row.ski_score),
            food=_to_float(row.food_score),
            natural=_to_float(row.natural_score),
            culture=_to_float(row.culture_score),
        )

    payload = VacationProfilesResponse(profiles=profiles)
    await cache_set(
        VACATION_PROFILES_KEY,
        payload.model_dump(),
        VACATION_PROFILES_TTL,
    )
    return payload


async def get_vacation_exotic_for_home(
    db: AsyncSession,
    home_iso2: str,
) -> VacationExoticResponse:
    home = home_iso2.strip().upper()
    if len(home) != 2:
        raise ValueError("home_iso2 должен быть кодом из 2 букв")

    cache_key = VACATION_EXOTIC_KEY.format(home_iso2=home)
    cached = await cache_get(cache_key)
    if cached is not None:
        return VacationExoticResponse.model_validate(cached)

    result = await db.execute(
        select(
            CountryVacationExoticScore.dest_iso2,
            CountryVacationExoticScore.score,
        ).where(CountryVacationExoticScore.home_iso2 == home)
    )
    scores: dict[str, float] = {}
    for dest_iso2, score in result.all():
        dest = str(dest_iso2).strip().upper()
        if len(dest) == 2 and score is not None:
            scores[dest] = float(score)

    payload = VacationExoticResponse(home_iso2=home, scores=scores)
    await cache_set(cache_key, payload.model_dump(), VACATION_EXOTIC_TTL)
    return payload

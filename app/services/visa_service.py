from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.visa_policy import VisaPolicy
from app.models.passport import Passport
from app.models.country import Country
from app.cache import (
    cache_get, cache_set, cache_delete_pattern,
    VISA_MAP_KEY, VISA_MAP_TTL,
)


async def get_visa_map(db: AsyncSession, passport_iso2: str) -> list[dict]:
    """
    Возвращает список {iso2, visa_category} для всех стран.
    Кешируется на 1 час.
    """
    cache_key = VISA_MAP_KEY.format(iso2=passport_iso2.upper())
    cached = await cache_get(cache_key)
    if cached:
        return cached

    DestCountry = aliased(Country, name="dest_country")
    PassportCountry = aliased(Country, name="passport_country")

    result = await db.execute(
        select(DestCountry.iso2, VisaPolicy.visa_category)
        .join(VisaPolicy, VisaPolicy.destination_id == DestCountry.id)
        .join(Passport, Passport.id == VisaPolicy.passport_id)
        .join(PassportCountry, PassportCountry.id == Passport.country_id)
        .where(PassportCountry.iso2 == passport_iso2.upper())
        .where(Passport.type == "regular")
        .where(DestCountry.is_active == True)
    )

    items = [
        {"iso2": row.iso2, "visa_category": row.visa_category}
        for row in result.all()
    ]

    await cache_set(cache_key, items, VISA_MAP_TTL)
    return items


async def get_visa_detail(
    db: AsyncSession,
    passport_iso2: str,
    destination_iso2: str,
) -> VisaPolicy | None:
    """Детальная информация о визовом режиме между двумя странами"""
    DestCountry = aliased(Country, name="dest_country")
    PassportCountry = aliased(Country, name="passport_country")

    result = await db.execute(
        select(VisaPolicy)
        .join(Passport, Passport.id == VisaPolicy.passport_id)
        .join(PassportCountry, PassportCountry.id == Passport.country_id)
        .join(DestCountry, DestCountry.id == VisaPolicy.destination_id)
        .where(PassportCountry.iso2 == passport_iso2.upper())
        .where(Passport.type == "regular")
        .where(DestCountry.iso2 == destination_iso2.upper())
    )
    return result.scalar_one_or_none()


async def invalidate_visa_cache(passport_iso2: str) -> None:
    """Сбрасывает кеш визовой карты при обновлении данных"""
    cache_key = VISA_MAP_KEY.format(iso2=passport_iso2.upper())
    await cache_delete_pattern(cache_key)
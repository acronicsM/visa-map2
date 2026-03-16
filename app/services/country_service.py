from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country


async def get_all_countries(db: AsyncSession) -> list[Country]:
    """Все активные страны для дропдауна"""
    result = await db.execute(
        select(Country)
        .where(Country.is_active == True)
        .order_by(Country.name_ru)
    )
    return result.scalars().all()


async def get_country_by_iso2(db: AsyncSession, iso2: str) -> Country | None:
    """Одна страна по коду iso2"""
    result = await db.execute(
        select(Country)
        .where(Country.iso2 == iso2.upper())
        .where(Country.is_active == True)
    )
    return result.scalar_one_or_none()
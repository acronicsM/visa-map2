from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visa_policy import VisaPolicy
from app.models.passport import Passport
from app.models.country import Country


async def get_visa_map(db: AsyncSession, passport_iso2: str) -> list[dict]:
    """
    Возвращает список {iso2, visa_category} для всех стран —
    данные для окраски карты
    """
    result = await db.execute(
        select(Country.iso2, VisaPolicy.visa_category)
        .join(VisaPolicy, VisaPolicy.destination_id == Country.id)
        .join(Passport, Passport.id == VisaPolicy.passport_id)
        .join(
            Country,
            Passport.country_id == Country.id,
            isouter=False,
        )
        .where(Passport.country_id == (
            select(Country.id)
            .where(Country.iso2 == passport_iso2.upper())
            .scalar_subquery()
        ))
        .where(Passport.type == "regular")
        .where(Country.is_active == True)
    )
    return [{"iso2": row.iso2, "visa_category": row.visa_category}
            for row in result.all()]


async def get_visa_detail(
    db: AsyncSession,
    passport_iso2: str,
    destination_iso2: str,
) -> VisaPolicy | None:
    """Детальная информация о визовом режиме между двумя странами"""
    result = await db.execute(
        select(VisaPolicy)
        .join(Passport, Passport.id == VisaPolicy.passport_id)
        .join(Country, Country.id == Passport.country_id)
        .where(Country.iso2 == passport_iso2.upper())
        .where(Passport.type == "regular")
        .join(
            Country,
            VisaPolicy.destination_id == Country.id,
            isouter=False,
        )
        .where(Country.iso2 == destination_iso2.upper())
    )
    return result.scalar_one_or_none()
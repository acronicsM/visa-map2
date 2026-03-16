from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.visa_policy import VisaPolicy
from app.models.passport import Passport
from app.models.country import Country


async def get_visa_map(db: AsyncSession, passport_iso2: str) -> list[dict]:
    """
    Возвращает список {iso2, visa_category} для всех стран —
    данные для окраски карты
    """
    # Два алиаса для таблицы countries
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
    return [{"iso2": row.iso2, "visa_category": row.visa_category}
            for row in result.all()]


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
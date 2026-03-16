import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.country import Country
from app.models.passport import Passport
from app.models.visa_policy import VisaPolicy

# Визовые режимы для российского паспорта
# (passport_iso2, destination_iso2, category, max_stay, fee_usd, notes)
VISA_POLICIES_RU = [
    ("RU", "TR", "free", 60, None, None),
    ("RU", "TH", "voa", 30, 0, None),
    ("RU", "AE", "free", 90, None, None),
    ("RU", "GE", "free", 365, None, None),
    ("RU", "AM", "free", 180, None, None),
    ("RU", "RS", "free", 30, None, None),
    ("RU", "EG", "voa", 30, 25, None),
    ("RU", "TN", "free", 90, None, None),
    ("RU", "MA", "free", 90, None, None),
    ("RU", "CU", "free", 30, None, None),
    ("RU", "KZ", "free", 90, None, None),
    ("RU", "BY", "free", None, None, None),
    ("RU", "IN", "evisa", 90, 25, {"insurance_required": True}),
    ("RU", "CN", "embassy", 30, 50, {"processing_days": 7}),
    ("RU", "JP", "embassy", 15, 0, {"processing_days": 5}),
    ("RU", "DE", "embassy", 90, 80, {"processing_days": 10}),
    ("RU", "FR", "embassy", 90, 80, {"processing_days": 10}),
    ("RU", "US", "restricted", 180, 160, {
        "processing_days": 60,
        "notes_ru": "Высокий процент отказов, требуется собеседование"
    }),
    ("RU", "IL", "restricted", 90, 0, {
        "notes_ru": "Возможны дополнительные проверки на границе"
    }),
    ("RU", "RU", "unavailable", None, None, {
        "notes_ru": "Въезд в собственную страну — не применимо"
    }),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for passport_iso2, dest_iso2, category, max_stay, fee, conditions in VISA_POLICIES_RU:

            passport_country = await session.execute(
                select(Country).where(Country.iso2 == passport_iso2)
            )
            passport_country = passport_country.scalar_one_or_none()
            if not passport_country:
                print(f"  Страна паспорта {passport_iso2} не найдена, пропускаем")
                continue

            passport = await session.execute(
                select(Passport)
                .where(Passport.country_id == passport_country.id)
                .where(Passport.type == "regular")
            )
            passport = passport.scalar_one_or_none()
            if not passport:
                print(f"  Паспорт для {passport_iso2} не найден, пропускаем")
                continue

            dest_country = await session.execute(
                select(Country).where(Country.iso2 == dest_iso2)
            )
            dest_country = dest_country.scalar_one_or_none()
            if not dest_country:
                print(f"  Страна назначения {dest_iso2} не найдена, пропускаем")
                continue

            existing = await session.execute(
                select(VisaPolicy)
                .where(VisaPolicy.passport_id == passport.id)
                .where(VisaPolicy.destination_id == dest_country.id)
            )
            if existing.scalar_one_or_none():
                print(f"  Пропускаем {passport_iso2}→{dest_iso2} — уже существует")
                continue

            policy = VisaPolicy(
                passport_id=passport.id,
                destination_id=dest_country.id,
                visa_category=category,
                max_stay_days=max_stay,
                fee_usd=fee,
                conditions=conditions,
                verified_by="seed_script",
            )
            session.add(policy)
            print(f"  Добавлен режим: {passport_iso2} → {dest_iso2} ({category})")

        await session.commit()
        print("\nГотово! Визовые режимы добавлены.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
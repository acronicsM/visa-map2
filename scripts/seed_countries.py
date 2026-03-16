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

COUNTRIES = [
    {"iso2": "RU", "iso3": "RUS", "numeric_code": 643, "name_ru": "Россия", "name_en": "Russia", "name_native": "Россия", "region": "Europe", "subregion": "Eastern Europe", "capital": "Москва", "flag_emoji": "🇷🇺"},
    {"iso2": "DE", "iso3": "DEU", "numeric_code": 276, "name_ru": "Германия", "name_en": "Germany", "name_native": "Deutschland", "region": "Europe", "subregion": "Western Europe", "capital": "Берлин", "flag_emoji": "🇩🇪"},
    {"iso2": "FR", "iso3": "FRA", "numeric_code": 250, "name_ru": "Франция", "name_en": "France", "name_native": "France", "region": "Europe", "subregion": "Western Europe", "capital": "Париж", "flag_emoji": "🇫🇷"},
    {"iso2": "US", "iso3": "USA", "numeric_code": 840, "name_ru": "США", "name_en": "United States", "name_native": "United States", "region": "Americas", "subregion": "Northern America", "capital": "Вашингтон", "flag_emoji": "🇺🇸"},
    {"iso2": "CN", "iso3": "CHN", "numeric_code": 156, "name_ru": "Китай", "name_en": "China", "name_native": "中国", "region": "Asia", "subregion": "Eastern Asia", "capital": "Пекин", "flag_emoji": "🇨🇳"},
    {"iso2": "TR", "iso3": "TUR", "numeric_code": 792, "name_ru": "Турция", "name_en": "Turkey", "name_native": "Türkiye", "region": "Asia", "subregion": "Western Asia", "capital": "Анкара", "flag_emoji": "🇹🇷"},
    {"iso2": "TH", "iso3": "THA", "numeric_code": 764, "name_ru": "Таиланд", "name_en": "Thailand", "name_native": "ประเทศไทย", "region": "Asia", "subregion": "South-Eastern Asia", "capital": "Бангкок", "flag_emoji": "🇹🇭"},
    {"iso2": "AE", "iso3": "ARE", "numeric_code": 784, "name_ru": "ОАЭ", "name_en": "United Arab Emirates", "name_native": "الإمارات", "region": "Asia", "subregion": "Western Asia", "capital": "Абу-Даби", "flag_emoji": "🇦🇪"},
    {"iso2": "GE", "iso3": "GEO", "numeric_code": 268, "name_ru": "Грузия", "name_en": "Georgia", "name_native": "საქართველო", "region": "Asia", "subregion": "Western Asia", "capital": "Тбилиси", "flag_emoji": "🇬🇪"},
    {"iso2": "AM", "iso3": "ARM", "numeric_code": 51, "name_ru": "Армения", "name_en": "Armenia", "name_native": "Հայաստան", "region": "Asia", "subregion": "Western Asia", "capital": "Ереван", "flag_emoji": "🇦🇲"},
    {"iso2": "RS", "iso3": "SRB", "numeric_code": 688, "name_ru": "Сербия", "name_en": "Serbia", "name_native": "Србија", "region": "Europe", "subregion": "Southern Europe", "capital": "Белград", "flag_emoji": "🇷🇸"},
    {"iso2": "EG", "iso3": "EGY", "numeric_code": 818, "name_ru": "Египет", "name_en": "Egypt", "name_native": "مصر", "region": "Africa", "subregion": "Northern Africa", "capital": "Каир", "flag_emoji": "🇪🇬"},
    {"iso2": "TN", "iso3": "TUN", "numeric_code": 788, "name_ru": "Тунис", "name_en": "Tunisia", "name_native": "تونس", "region": "Africa", "subregion": "Northern Africa", "capital": "Тунис", "flag_emoji": "🇹🇳"},
    {"iso2": "IN", "iso3": "IND", "numeric_code": 356, "name_ru": "Индия", "name_en": "India", "name_native": "भारत", "region": "Asia", "subregion": "Southern Asia", "capital": "Нью-Дели", "flag_emoji": "🇮🇳"},
    {"iso2": "JP", "iso3": "JPN", "numeric_code": 392, "name_ru": "Япония", "name_en": "Japan", "name_native": "日本", "region": "Asia", "subregion": "Eastern Asia", "capital": "Токио", "flag_emoji": "🇯🇵"},
    {"iso2": "KZ", "iso3": "KAZ", "numeric_code": 398, "name_ru": "Казахстан", "name_en": "Kazakhstan", "name_native": "Қазақстан", "region": "Asia", "subregion": "Central Asia", "capital": "Астана", "flag_emoji": "🇰🇿"},
    {"iso2": "BY", "iso3": "BLR", "numeric_code": 112, "name_ru": "Беларусь", "name_en": "Belarus", "name_native": "Беларусь", "region": "Europe", "subregion": "Eastern Europe", "capital": "Минск", "flag_emoji": "🇧🇾"},
    {"iso2": "IL", "iso3": "ISR", "numeric_code": 376, "name_ru": "Израиль", "name_en": "Israel", "name_native": "ישראל", "region": "Asia", "subregion": "Western Asia", "capital": "Иерусалим", "flag_emoji": "🇮🇱"},
    {"iso2": "CU", "iso3": "CUB", "numeric_code": 192, "name_ru": "Куба", "name_en": "Cuba", "name_native": "Cuba", "region": "Americas", "subregion": "Caribbean", "capital": "Гавана", "flag_emoji": "🇨🇺"},
    {"iso2": "MA", "iso3": "MAR", "numeric_code": 504, "name_ru": "Марокко", "name_en": "Morocco", "name_native": "المغرب", "region": "Africa", "subregion": "Northern Africa", "capital": "Рабат", "flag_emoji": "🇲🇦"},
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for data in COUNTRIES:
            existing = await session.execute(
                select(Country).where(Country.iso2 == data["iso2"])
            )
            if existing.scalar_one_or_none():
                print(f"  Пропускаем {data['iso2']} — уже существует")
                continue

            country = Country(**data)
            session.add(country)
            await session.flush()

            passport = Passport(
                country_id=country.id,
                name_ru=f"{data['name_ru']} паспорт",
                type="regular",
                is_active=True,
            )
            session.add(passport)
            print(f"  Добавлена страна: {data['name_ru']} ({data['iso2']})")

        await session.commit()
        print("\nГотово! Страны и паспорта добавлены.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
import asyncio
import sys
import os
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.country import Country
from app.models.passport import Passport

RESTCOUNTRIES_URL = (
    "https://restcountries.com/v3.1/all"
    "?fields=cca2,cca3,ccn3,name,translations,capital,region,subregion,flag"
)


def parse_country(data: dict) -> dict | None:
    iso2 = data.get("cca2", "").strip().upper()
    if not iso2:
        return None

    iso3 = data.get("cca3", "").strip().upper()
    if not iso3:
        return None

    numeric_code = data.get("ccn3", "")
    try:
        numeric_code = int(numeric_code) if numeric_code else None
    except (ValueError, TypeError):
        numeric_code = None

    name_en = data.get("name", {}).get("common", "")
    if not name_en:
        return None

    native_names = data.get("name", {}).get("nativeName", {})
    name_native = None
    if native_names:
        first_native = next(iter(native_names.values()), {})
        name_native = first_native.get("common", None)

    translations = data.get("translations", {})
    name_ru = translations.get("rus", {}).get("common", name_en)

    capital_list = data.get("capital", [])
    capital = capital_list[0] if capital_list else None

    region = data.get("region", None)
    subregion = data.get("subregion", None)

    flag_emoji = data.get("flag", None)

    return {
        "iso2": iso2,
        "iso3": iso3,
        "numeric_code": numeric_code,
        "name_ru": name_ru,
        "name_en": name_en,
        "name_native": name_native,
        "region": region,
        "subregion": subregion,
        "capital": capital,
        "flag_emoji": flag_emoji,
        "is_active": True,
    }


async def load_countries():
    print("Загружаем данные с restcountries.com...")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(RESTCOUNTRIES_URL)
        response.raise_for_status()
        raw_countries = response.json()

    print(f"Получено {len(raw_countries)} стран от API")

    parsed = []
    skipped_parse = []
    for raw in raw_countries:
        country_data = parse_country(raw)
        if country_data:
            parsed.append(country_data)
        else:
            skipped_parse.append(raw.get("cca2", "???"))

    print(f"Распарсено: {len(parsed)}, пропущено при парсинге: {len(skipped_parse)}")
    if skipped_parse:
        print(f"  Пропущенные коды: {skipped_parse}")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    added = 0
    updated = 0
    skipped = 0

    async with async_session() as session:
        for data in sorted(parsed, key=lambda x: x["name_en"]):
            result = await session.execute(
                select(Country).where(Country.iso2 == data["iso2"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                changed = False
                for field, value in data.items():
                    if field == "is_active":
                        continue
                    current = getattr(existing, field, None)
                    if current is None and value is not None:
                        setattr(existing, field, value)
                        changed = True
                if changed:
                    updated += 1
                    print(f"  Обновлена: {data['name_ru']} ({data['iso2']})")
                else:
                    skipped += 1
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
            added += 1
            print(f"  Добавлена: {data['name_ru']} ({data['iso2']})")

        await session.commit()
    
    total = added + updated + skipped
    print(f"\nГотово!")
    print(f"  Добавлено новых: {added}")
    print(f"  Обновлено:       {updated}")
    print(f"  Без изменений:   {skipped}")
    print(f"  Итого в базе:    {total}")

    if skipped_parse:
        print(f"\nПропущено при парсинге ({len(skipped_parse)} шт):")
        for raw in raw_countries:
            cca2 = raw.get("cca2", "")
            if cca2 in skipped_parse:
                name = raw.get("name", {}).get("common", "???")
                iso3 = raw.get("cca3", "???")
                region = raw.get("region", "???")
                print(f"  [{cca2}] {iso3} — {name} ({region})")
                if not cca2:
                    print(f"    Причина: пустой cca2")
                if not raw.get("cca3"):
                    print(f"    Причина: пустой cca3")
                if not raw.get("name", {}).get("common"):
                    print(f"    Причина: пустое name.common")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_countries())
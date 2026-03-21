import asyncio
import sys
import os
import httpx
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.country import Country
from app.models.passport import Passport

RESTCOUNTRIES_URL = (
    "https://restcountries.com/v3.1/all"
    "?fields=cca2,cca3,ccn3,name,translations,capital,region,subregion,flag,languages,tld"
)


def greedy_set_cover(
    lang_to_countries: dict[str, list[str]],
    all_countries: set[str],
) -> dict[str, str]:
    """
    Жадный алгоритм Set Cover.
    Возвращает словарь cca2 -> primary_language_code
    """
    covered = set()
    country_to_lang = {}

    while covered < all_countries:
        best_lang = max(
            lang_to_countries.items(),
            key=lambda kv: len(set(kv[1]) - covered)
        )
        lang_code, countries = best_lang
        newly_covered = set(countries) - covered

        if not newly_covered:
            break

        for cca2 in newly_covered:
            country_to_lang[cca2] = lang_code

        covered |= newly_covered

    return country_to_lang


def parse_country(data: dict, primary_lang: str | None) -> dict | None:
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

    langs = data.get("languages", {})
    tlds = data.get("tld", [])

    name_translations = {
        lang_code: names.get("common", "")
        for lang_code, names in translations.items()
        if isinstance(names, dict) and names.get("common")
    }

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
        "primary_language": primary_lang,
        "language_name": langs.get(primary_lang) if primary_lang else None,
        "all_languages": langs if langs else None,
        "country_tld": tlds[0] if tlds else None,
        "name_translations": name_translations if name_translations else None,
    }


async def load_countries():
    print("Загружаем данные с restcountries.com...")

    async with httpx.AsyncClient(timeout=60) as client:
        # Запрос 1 — основные данные
        r1 = await client.get(
            "https://restcountries.com/v3.1/all"
            "?fields=cca2,cca3,ccn3,name,translations,capital,region,subregion,flag"
        )
        r1.raise_for_status()
        basic_data = r1.json()

        # Запрос 2 — языки и домены
        r2 = await client.get(
            "https://restcountries.com/v3.1/all"
            "?fields=cca2,languages,tld"
        )
        r2.raise_for_status()
        lang_data = r2.json()

    print(f"Получено стран: {len(basic_data)} (основные), {len(lang_data)} (языки)")

    # Объединяем по cca2
    lang_by_iso2 = {
        item["cca2"].strip().upper(): item
        for item in lang_data
        if item.get("cca2")
    }

    # Объединяем данные
    raw_countries = []
    for item in basic_data:
        cca2 = item.get("cca2", "").strip().upper()
        if cca2 and cca2 in lang_by_iso2:
            item["languages"] = lang_by_iso2[cca2].get("languages", {})
            item["tld"] = lang_by_iso2[cca2].get("tld", [])
        raw_countries.append(item)

    print(f"Объединено: {len(raw_countries)} стран")

    # Строим структуры для Set Cover
    lang_to_countries: dict[str, list[str]] = defaultdict(list)
    all_iso2: set[str] = set()

    for item in raw_countries:
        cca2 = item.get("cca2", "").strip().upper()
        if not cca2:
            continue
        all_iso2.add(cca2)
        for lang_code in item.get("languages", {}).keys():
            lang_to_countries[lang_code].append(cca2)

    print(f"Уникальных языков: {len(lang_to_countries)}")
    print(f"Запускаем Set Cover...")
    country_to_primary_lang = greedy_set_cover(lang_to_countries, all_iso2)
    print(f"Primary language определён для {len(country_to_primary_lang)} стран")

    # Парсим страны
    parsed = []
    for raw in raw_countries:
        cca2 = raw.get("cca2", "").strip().upper()
        primary_lang = country_to_primary_lang.get(cca2)
        country_data = parse_country(raw, primary_lang)
        if country_data:
            parsed.append(country_data)

    print(f"Распарсено: {len(parsed)} стран")

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
                # Обновляем все поля включая новые языковые
                changed = False
                for field, value in data.items():
                    if field == "is_active":
                        continue
                    current = getattr(existing, field, None)
                    if current != value and value is not None:
                        setattr(existing, field, value)
                        changed = True
                if changed:
                    updated += 1
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

    # Статистика по языкам
    lang_stats: dict[str, int] = defaultdict(int)
    for lang in country_to_primary_lang.values():
        lang_stats[lang] += 1

    print(f"\nТоп-10 языков по покрытию:")
    for lang_code, count in sorted(
        lang_stats.items(), key=lambda x: -x[1]
    )[:10]:
        print(f"  {lang_code:<6} — {count} стран")

    print(f"\nГотово!")
    print(f"  Добавлено:  {added}")
    print(f"  Обновлено:  {updated}")
    print(f"  Без изменений: {skipped}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_countries())
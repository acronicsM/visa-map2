import json
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.schemas.country import CountryShort
from app.cache import (
    cache_get,
    cache_set,
    GEODATA_KEY,
    GEODATA_TTL,
)


def official_language_codes(country: Country) -> list[str] | None:
    """Коды языков из all_languages (сортировка для стабильного API)."""
    if not country.all_languages or not isinstance(country.all_languages, dict):
        return None
    codes = sorted(country.all_languages.keys())
    return codes if codes else None


def currency_codes_for_country(country: Country) -> list[str] | None:
    """Коды ISO 4217 из currencies (сортировка для стабильного API)."""
    if not country.currencies or not isinstance(country.currencies, dict):
        return None
    codes = sorted(country.currencies.keys())
    return codes if codes else None


def build_country_short(country: Country) -> CountryShort:
    """CountryShort с вычисляемыми языковыми полями."""
    return CountryShort(
        iso2=country.iso2,
        name_ru=country.name_ru,
        name_en=country.name_en,
        flag_emoji=country.flag_emoji,
        region=country.region,
        primary_language=country.primary_language,
        official_language_codes=official_language_codes(country),
        currency_codes=currency_codes_for_country(country),
    )


async def get_all_countries(
    db: AsyncSession,
    region: str | None = None,
    search: str | None = None,
    has_language: str | None = None,
) -> list[Country]:
    """Все активные страны с опциональными фильтрами."""
    query = select(Country).where(Country.is_active)

    if region:
        query = query.where(Country.region == region)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            Country.name_ru.ilike(search_term) | Country.name_en.ilike(search_term)
        )

    if has_language:
        key = has_language.strip()
        if key:
            query = query.where(Country.all_languages.isnot(None))
            query = query.where(Country.all_languages.has_key(key))

    query = query.order_by(Country.name_ru)
    result = await db.execute(query)
    return result.scalars().all()


async def get_country_by_iso2(db: AsyncSession, iso2: str) -> Country | None:
    """Одна страна по коду iso2."""
    result = await db.execute(
        select(Country).where(Country.iso2 == iso2.upper()).where(Country.is_active)
    )
    return result.scalar_one_or_none()


async def get_country_geodata(db: AsyncSession, iso2: str) -> dict | None:
    """GeoJSON Feature одной страны по коду iso2."""
    result = await db.execute(
        select(
            Country.iso2,
            Country.name_ru,
            Country.name_en,
            Country.flag_emoji,
            Country.region,
            Country.bbox_min_lat,
            Country.bbox_max_lat,
            Country.bbox_min_lng,
            Country.bbox_max_lng,
            Country.safety_level,
            Country.cost_level,
            Country.cost_per_day_usd,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(Country.geom, 0.01)
            ).label("geometry"),
        )
        .where(Country.iso2 == iso2.upper())
        .where(Country.is_active)
        .where(Country.geom.isnot(None))
    )
    row = result.one_or_none()
    if not row or not row.geometry:
        return None
    return {
        "type": "Feature",
        "properties": {
            "iso2": row.iso2,
            "name_ru": row.name_ru,
            "name_en": row.name_en,
            "flag_emoji": row.flag_emoji,
            "region": row.region,
            "bbox": [
                row.bbox_min_lng,
                row.bbox_min_lat,
                row.bbox_max_lng,
                row.bbox_max_lat,
            ],
            "safety_level": row.safety_level,
            "cost_level": row.cost_level,
            "cost_per_day_usd": row.cost_per_day_usd,
        },
        "geometry": json.loads(row.geometry),
    }


async def get_countries_geodata(db: AsyncSession) -> dict:
    """
    GeoJSON FeatureCollection всех стран с границами.
    Кешируется на 24 часа.
    """
    cached = await cache_get(GEODATA_KEY)
    if cached:
        return cached

    result = await db.execute(
        select(
            Country.iso2,
            Country.name_ru,
            Country.name_en,
            Country.flag_emoji,
            Country.region,
            Country.bbox_min_lat,
            Country.bbox_max_lat,
            Country.bbox_min_lng,
            Country.bbox_max_lng,
            Country.safety_level,
            Country.cost_level,
            Country.cost_per_day_usd,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(Country.geom, 0.01)
            ).label("geometry"),
        )
        .where(Country.is_active)
        .where(Country.geom.isnot(None))
    )

    features = []
    for row in result.all():
        if not row.geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "iso2": row.iso2,
                    "name_ru": row.name_ru,
                    "name_en": row.name_en,
                    "flag_emoji": row.flag_emoji,
                    "region": row.region,
                    "bbox": [
                        row.bbox_min_lng,
                        row.bbox_min_lat,
                        row.bbox_max_lng,
                        row.bbox_max_lat,
                    ],
                    "safety_level": row.safety_level,
                    "cost_level": row.cost_level,
                    "cost_per_day_usd": row.cost_per_day_usd,
                },
                "geometry": json.loads(row.geometry),
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    await cache_set(GEODATA_KEY, geojson, GEODATA_TTL)
    return geojson


async def get_country_names_map(db: AsyncSession) -> dict[str, dict[str, Any]]:
    """
    Словарь iso2 -> поля для CountryNamesEntry (без Pydantic, для JSON-кеша).
    """
    result = await db.execute(
        select(
            Country.iso2,
            Country.iso3,
            Country.name_en,
            Country.name_ru,
            Country.name_native,
            Country.name_translations,
        ).where(Country.is_active)
    )
    out: dict[str, dict[str, Any]] = {}
    for row in result.all():
        trans = row.name_translations
        if trans is not None and not isinstance(trans, dict):
            trans = None
        out[row.iso2] = {
            "iso3": row.iso3,
            "name_en": row.name_en,
            "name_ru": row.name_ru,
            "name_native": row.name_native,
            "name_translations": trans,
        }
    return out

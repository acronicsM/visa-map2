from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.cache import (
    cache_get, cache_set,
    GEODATA_KEY, GEODATA_TTL,
)


async def get_all_countries(
    db: AsyncSession,
    region: str | None = None,
    search: str | None = None,
) -> list[Country]:
    """Все активные страны с опциональными фильтрами"""
    query = select(Country).where(Country.is_active == True)

    if region:
        query = query.where(Country.region == region)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            Country.name_ru.ilike(search_term) |
            Country.name_en.ilike(search_term)
        )

    query = query.order_by(Country.name_ru)
    result = await db.execute(query)
    return result.scalars().all()


async def get_country_by_iso2(db: AsyncSession, iso2: str) -> Country | None:
    """Одна страна по коду iso2"""
    result = await db.execute(
        select(Country)
        .where(Country.iso2 == iso2.upper())
        .where(Country.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_country_geodata(db: AsyncSession, iso2: str) -> dict | None:
    """GeoJSON Feature одной страны по коду iso2."""
    import json
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
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(Country.geom, 0.01)
            ).label("geometry"),
        )
        .where(Country.iso2 == iso2.upper())
        .where(Country.is_active == True)
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
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(Country.geom, 0.01)
            ).label("geometry"),
        )
        .where(Country.is_active == True)
        .where(Country.geom.isnot(None))
    )

    features = []
    for row in result.all():
        if not row.geometry:
            continue
        import json
        features.append({
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
            },
            "geometry": json.loads(row.geometry),
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    await cache_set(GEODATA_KEY, geojson, GEODATA_TTL)
    return geojson
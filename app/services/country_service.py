from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country


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


async def get_countries_geodata(db: AsyncSession) -> dict:
   
    """
    GeoJSON FeatureCollection всех стран с границами.
    Геометрия упрощается для уменьшения размера ответа.
    """

    result = await db.execute(
        select(
            Country.iso2,
            Country.name_ru,
            Country.name_en,
            Country.region,
            Country.flag_emoji,
            Country.bbox_min_lat,
            Country.bbox_max_lat,
            Country.bbox_min_lng,
            Country.bbox_max_lng,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(Country.geom, 0.1)
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
                "region": row.region,
                "flag_emoji": row.flag_emoji,
                "bbox": [
                    row.bbox_min_lng,
                    row.bbox_min_lat,
                    row.bbox_max_lng,
                    row.bbox_max_lat,
                ] if row.bbox_min_lng else None,
            },
            "geometry": json.loads(row.geometry),
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
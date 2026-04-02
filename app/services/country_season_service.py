import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country_season import CountrySeason


def _rows_to_geojson_features(rows) -> list[dict]:
    features: list[dict] = []
    for row in rows:
        if not row.geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(row.geometry),
                "properties": {
                    "iso2": row.iso2,
                    "month": row.month,
                    "season": row.season,
                },
            }
        )
    return features


async def list_distinct_seasons_lowercase(db: AsyncSession, month: int) -> list[str]:
    """Уникальные season за месяц (lower), без геометрии — для /meta и distinct_seasons."""
    distinct_result = await db.execute(
        select(func.lower(CountrySeason.season))
        .where(CountrySeason.month == month)
        .distinct()
        .order_by(func.lower(CountrySeason.season))
    )
    return [row[0] for row in distinct_result.all() if row[0] is not None]


async def get_country_season_month_meta(db: AsyncSession, month: int) -> dict:
    seasons = await list_distinct_seasons_lowercase(db, month)
    return {"month": month, "seasons": seasons}


async def get_country_seasons_geodata(db: AsyncSession, month: int) -> dict:
    distinct_seasons = await list_distinct_seasons_lowercase(db, month)

    result = await db.execute(
        select(
            CountrySeason.iso2,
            CountrySeason.month,
            CountrySeason.season,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(CountrySeason.geom, 0.01)
            ).label("geometry"),
        )
        .where(CountrySeason.month == month)
        .order_by(CountrySeason.iso2)
    )
    features = _rows_to_geojson_features(result.all())
    return {
        "type": "FeatureCollection",
        "features": features,
        "distinct_seasons": distinct_seasons,
    }


async def get_country_seasons_geojson_by_iso2(db: AsyncSession, iso2: str) -> dict:
    iso2_u = iso2.upper()
    result = await db.execute(
        select(
            CountrySeason.iso2,
            CountrySeason.month,
            CountrySeason.season,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(CountrySeason.geom, 0.01)
            ).label("geometry"),
        )
        .where(CountrySeason.iso2 == iso2_u)
        .order_by(CountrySeason.month, CountrySeason.season)
    )
    features = _rows_to_geojson_features(result.all())
    return {
        "type": "FeatureCollection",
        "features": features,
    }

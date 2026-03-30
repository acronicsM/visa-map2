import json

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country_season import CountrySeason


async def get_country_seasons_geodata(db: AsyncSession, month: int) -> dict:
    result = await db.execute(
        select(
            CountrySeason.iso2,
            CountrySeason.month,
            CountrySeason.season,
            func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(CountrySeason.geom, 0.01)
            ).label("geometry"),
        ).where(CountrySeason.month == month)
    )
    rows = result.all()
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

    return {
        "type": "FeatureCollection",
        "features": features,
    }


async def get_country_seasons_by_iso2(db: AsyncSession, iso2: str) -> list[dict]:
    result = await db.execute(
        select(
            CountrySeason.iso2,
            CountrySeason.month,
            CountrySeason.season,
        )
        .where(CountrySeason.iso2 == iso2.upper())
        .order_by(CountrySeason.month)
    )
    return [
        {
            "iso2": row.iso2,
            "month": row.month,
            "season": row.season,
        }
        for row in result.all()
    ]

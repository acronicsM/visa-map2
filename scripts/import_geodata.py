import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shapefile
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import json

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

from app.config import settings
from app.models.country import Country

SHAPEFILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "geodata",
    "ne_110m_admin_0_countries.shp"
)

# Маппинг iso2 из Natural Earth → наши коды
# Natural Earth иногда использует нестандартные коды
ISO2_FIXES = {
    "-99": None,  # Пропускаем неизвестные
    "GB": "GB",
    "GR": "GR",
}


async def import_geodata():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"Читаем shapefile: {SHAPEFILE_PATH}")

    if not os.path.exists(SHAPEFILE_PATH):
        print(f"ОШИБКА: файл не найден: {SHAPEFILE_PATH}")
        print("Скачайте Natural Earth 110m shapefile и распакуйте в scripts/geodata/")
        return

    sf = shapefile.Reader(SHAPEFILE_PATH)
    fields = [f[0] for f in sf.fields[1:]]

    print(f"Найдено записей в shapefile: {len(sf.shapes())}")

    async with async_session() as session:
        updated = 0
        skipped = 0

        for record in sf.shapeRecords():
            props = dict(zip(fields, record.record))
            iso2 = props.get("ISO_A2", "").strip()

            if not iso2 or iso2 == "-99":
                iso2_alt = props.get("ISO_A2_EH", "").strip()
                if iso2_alt and iso2_alt != "-99":
                    iso2 = iso2_alt
                else:
                    skipped += 1
                    continue

            iso2 = ISO2_FIXES.get(iso2, iso2)
            if not iso2:
                skipped += 1
                continue

            result = await session.execute(
                select(Country).where(Country.iso2 == iso2.upper())
            )
            country = result.scalar_one_or_none()

            if not country:
                skipped += 1
                continue

            try:
                geom_shape = shape(record.shape.__geo_interface__)

                if geom_shape.geom_type == "Polygon":
                    from shapely.geometry import MultiPolygon
                    geom_shape = MultiPolygon([geom_shape])

                geom_wkt = f"SRID=4326;{geom_shape.wkt}"

                bounds = geom_shape.bounds
                centroid = geom_shape.centroid
                center_wkt = f"SRID=4326;POINT({centroid.x} {centroid.y})"

                country.geom = geom_wkt
                country.center_point = center_wkt
                country.bbox_min_lng = bounds[0]
                country.bbox_min_lat = bounds[1]
                country.bbox_max_lng = bounds[2]
                country.bbox_max_lat = bounds[3]

                updated += 1
                print(f"  Обновлена геометрия: {country.name_ru} ({iso2})")

            except Exception as e:
                print(f"  Ошибка для {iso2}: {e}")
                skipped += 1

        await session.commit()
        print(f"\nГотово! Обновлено: {updated}, пропущено: {skipped}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_geodata())
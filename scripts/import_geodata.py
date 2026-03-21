import asyncio
import sys
import os
import zipfile
import tempfile
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import shapefile
from shapely.geometry import shape
from shapely.geometry import MultiPolygon

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.country import Country

NATURAL_EARTH_URL = (
    "https://naturalearth.s3.amazonaws.com"
    "/10m_cultural/ne_10m_admin_0_countries.zip"
)

ISO2_FIXES = {
    "CN-TW": "TW",
}


async def download_shapefile(tmp_dir: str) -> str:
    """Скачивает и распаковывает shapefile во временную папку"""
    zip_path = os.path.join(tmp_dir, "ne_10m.zip")

    print(f"Скачиваем Natural Earth 10m (~30 МБ)...")
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("GET", NATURAL_EARTH_URL) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(zip_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  Прогресс: {pct:.1f}%", end="", flush=True)

    print(f"\n  Скачано: {downloaded / 1024 / 1024:.1f} МБ")

    print("Распаковываем...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_dir)

    shp_path = os.path.join(tmp_dir, "ne_10m_admin_0_countries.shp")
    if not os.path.exists(shp_path):
        # Ищем .shp в распакованных файлах
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith(".shp"):
                    shp_path = os.path.join(root, file)
                    break

    return shp_path


async def import_geodata():
    tmp_dir = tempfile.mkdtemp(prefix="naturalearth_")

    try:
        shp_path = await download_shapefile(tmp_dir)

        if not os.path.exists(shp_path):
            print(f"ОШИБКА: shapefile не найден в {tmp_dir}")
            return

        print(f"Читаем shapefile...")
        sf = shapefile.Reader(shp_path)
        fields = [f[0] for f in sf.fields[1:]]
        print(f"Найдено записей: {len(sf.shapes())}")

        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        updated = 0
        skipped = 0
        no_iso2 = []
        not_in_db = []

        async with async_session() as session:
            for record in sf.shapeRecords():
                props = dict(zip(fields, record.record))
                iso2 = props.get("ISO_A2", "").strip()

                if not iso2 or iso2 == "-99":
                    iso2_alt = props.get("ISO_A2_EH", "").strip()
                    if iso2_alt and iso2_alt != "-99":
                        iso2 = iso2_alt
                    else:
                        name = props.get("NAME", "???")
                        no_iso2.append(name)
                        skipped += 1
                        continue

                iso2 = ISO2_FIXES.get(iso2, iso2).upper()

                if iso2 == "AU":
                    print(f"  AU запись: NAME={props.get('NAME', '?')}, геометрия типа {record.shape.shapeType}")

                result = await session.execute(
                    select(Country).where(Country.iso2 == iso2)
                )
                country = result.scalar_one_or_none()

                if not country:
                    name = props.get("NAME", "???")
                    not_in_db.append(f"{name} ({iso2})")
                    skipped += 1
                    continue

                try:
                    geom_shape = shape(record.shape.__geo_interface__)

                    if geom_shape.geom_type == "Polygon":
                        geom_shape = MultiPolygon([geom_shape])

                    # Если геометрия уже есть — объединяем
                    if country.geom is not None:
                        from sqlalchemy import text
                        result = await session.execute(
                            text("SELECT ST_AsText(geom) FROM countries WHERE iso2 = :iso2"),
                            {"iso2": iso2}
                        )
                        existing_wkt = result.scalar_one_or_none()
                        if existing_wkt:
                            from shapely.wkt import loads as wkt_loads
                            existing_shape = wkt_loads(existing_wkt)
                            from shapely.ops import unary_union
                            geom_shape = unary_union([existing_shape, geom_shape])
                            if geom_shape.geom_type == "Polygon":
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
                    print(f"  Обновлена: {country.name_ru} ({iso2})")

                except Exception as e:
                    print(f"  Ошибка геометрии для {iso2}: {e}")
                    skipped += 1

            await session.commit()

        print(f"\nГотово!")
        print(f"  Обновлено:  {updated}")
        print(f"  Пропущено:  {skipped}")

        if no_iso2:
            print(f"\nБез iso2 ({len(no_iso2)}) — спорные территории:")
            for name in no_iso2:
                print(f"  {name}")

        if not_in_db:
            print(f"\nЕсть в shapefile но нет в БД ({len(not_in_db)}):")
            for name in not_in_db:
                print(f"  {name}")

        await engine.dispose()

    finally:
        print(f"\nУдаляем временные файлы...")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"  Временная папка удалена")


if __name__ == "__main__":
    asyncio.run(import_geodata())
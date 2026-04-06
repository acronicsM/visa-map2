import asyncio
import os
import re
import shutil
import sys
import tempfile
import zipfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import shapefile
from shapely.geometry import MultiPolygon, shape
from shapely.ops import unary_union
from shapely.wkt import loads as wkt_loads
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.country import Country
from app.models.natural_earth_admin0 import NaturalEarthAdmin0

NATURAL_EARTH_URL = (
    "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_0_countries.zip"
)

ISO2_FIXES = {
    "CN-TW": "TW",
}


def resolve_iso2(props: dict) -> str | None:
    """ISO_A2 / ISO_A2_EH / ISO2_FIXES; None если кода нет или он невалиден."""
    iso2 = props.get("ISO_A2", "").strip()
    if not iso2 or iso2 == "-99":
        alt = props.get("ISO_A2_EH", "").strip()
        if alt and alt != "-99":
            iso2 = alt
        else:
            return None
    iso2 = ISO2_FIXES.get(iso2, iso2).upper()
    if len(iso2) != 2 or not re.match(r"^[A-Z]{2}$", iso2):
        return None
    return iso2


def adm0_a3_for_record(props: dict, index: int) -> str:
    raw = (props.get("ADM0_A3") or "").strip()
    if not raw or raw == "-99":
        return f"NE_{index:04d}"
    return raw[:10]


async def download_shapefile(tmp_dir: str) -> str:
    """Скачивает и распаковывает shapefile во временную папку."""
    zip_path = os.path.join(tmp_dir, "ne_10m.zip")

    print("Скачиваем Natural Earth 10m (~30 МБ)...")
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
        for root, _dirs, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith(".shp"):
                    shp_path = os.path.join(root, file)
                    break

    return shp_path


async def import_geodata() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="naturalearth_")

    try:
        shp_path = await download_shapefile(tmp_dir)

        if not os.path.exists(shp_path):
            print(f"ОШИБКА: shapefile не найден в {tmp_dir}")
            return

        print("Читаем shapefile...")
        sf = shapefile.Reader(shp_path)
        fields = [f[0] for f in sf.fields[1:]]
        print(f"Найдено записей: {len(sf.shapes())}")

        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        ne_upserted = 0
        country_updated = 0
        geom_errors = 0
        country_not_in_db = 0

        async with async_session() as session:
            for index, record in enumerate(sf.shapeRecords()):
                props = dict(zip(fields, record.record))
                adm0_a3 = adm0_a3_for_record(props, index)
                iso2 = resolve_iso2(props)
                name = (props.get("NAME") or "Unknown")[:255]

                try:
                    geom_shape = shape(record.shape.__geo_interface__)

                    if geom_shape.geom_type == "Polygon":
                        geom_shape = MultiPolygon([geom_shape])

                    geom_wkt = f"SRID=4326;{geom_shape.wkt}"
                    bounds = geom_shape.bounds
                    centroid = geom_shape.centroid
                    center_wkt = f"SRID=4326;POINT({centroid.x} {centroid.y})"

                    ne_row = await session.get(NaturalEarthAdmin0, adm0_a3)
                    if ne_row is None:
                        ne_row = NaturalEarthAdmin0(adm0_a3=adm0_a3)
                        session.add(ne_row)

                    ne_row.iso2 = iso2
                    ne_row.name = name
                    ne_row.geom = geom_wkt
                    ne_row.center_point = center_wkt
                    ne_row.bbox_min_lng = bounds[0]
                    ne_row.bbox_min_lat = bounds[1]
                    ne_row.bbox_max_lng = bounds[2]
                    ne_row.bbox_max_lat = bounds[3]
                    ne_upserted += 1

                    if iso2:
                        country_result = await session.execute(
                            select(Country).where(Country.iso2 == iso2)
                        )
                        country = country_result.scalar_one_or_none()
                        if country:
                            merged = geom_shape
                            if country.geom is not None:
                                wkt_row = await session.execute(
                                    text(
                                        "SELECT ST_AsText(geom) FROM countries "
                                        "WHERE iso2 = :iso2"
                                    ),
                                    {"iso2": iso2},
                                )
                                existing_wkt = wkt_row.scalar_one_or_none()
                                if existing_wkt:
                                    existing_shape = wkt_loads(existing_wkt)
                                    merged = unary_union([existing_shape, merged])
                                    if merged.geom_type == "Polygon":
                                        merged = MultiPolygon([merged])

                            merged_wkt = f"SRID=4326;{merged.wkt}"
                            mb = merged.bounds
                            mc = merged.centroid
                            country.geom = merged_wkt
                            country.center_point = f"SRID=4326;POINT({mc.x} {mc.y})"
                            country.bbox_min_lng = mb[0]
                            country.bbox_min_lat = mb[1]
                            country.bbox_max_lng = mb[2]
                            country.bbox_max_lat = mb[3]
                            country_updated += 1
                            print(f"  Обновлена страна: {country.name_ru} ({iso2})")
                        else:
                            country_not_in_db += 1

                except Exception as e:
                    print(f"  Ошибка геометрии для {adm0_a3}: {e}")
                    geom_errors += 1

            await session.commit()

        print("\nГотово!")
        print(f"  Natural Earth строк: {ne_upserted}")
        print(f"  Обновлено countries.geom: {country_updated}")
        print(f"  ISO2 есть, нет в БД: {country_not_in_db}")
        print(f"  Ошибок геометрии: {geom_errors}")

        await engine.dispose()

    finally:
        print("\nУдаляем временные файлы...")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("  Временная папка удалена")


if __name__ == "__main__":
    asyncio.run(import_geodata())

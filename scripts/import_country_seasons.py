import asyncio
import json
import os
import sys
from pathlib import Path

from shapely.geometry import MultiPolygon, shape
from sqlalchemy import literal_column, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.country import Country
from app.models.country_season import CountrySeason


def _normalize_multipolygon(geometry: dict) -> MultiPolygon:
    geom_shape = shape(geometry)
    if geom_shape.geom_type == "Polygon":
        return MultiPolygon([geom_shape])
    if geom_shape.geom_type == "MultiPolygon":
        return geom_shape
    raise ValueError(f"Unsupported geometry type: {geom_shape.geom_type}")


async def import_country_seasons() -> None:
    input_folder = settings.input_folder_seasons or os.getenv("INPUT_FOLDER_SEASONS")
    if not input_folder:
        raise RuntimeError("INPUT_FOLDER_SEASONS is not set")

    input_path = Path(input_folder)
    if not input_path.exists():
        repo_root = Path(__file__).resolve().parents[1]
        input_path = repo_root / input_folder.lstrip("\\/")
    if not input_path.exists() or not input_path.is_dir():
        raise RuntimeError(
            f"INPUT_FOLDER_SEASONS path does not exist or is not a directory: "
            f"{input_folder}"
        )

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    files_processed = 0
    inserted = 0
    updated = 0
    skipped = 0

    async with async_session() as session:
        country_rows = await session.execute(select(Country.iso2, Country.id))
        country_ids = {row.iso2.upper(): row.id for row in country_rows.all()}

        for month in range(1, 13):
            file_path = input_path / f"seasons_month_{month}.geojson"
            if not file_path.exists():
                print(f"Файл не найден: {file_path}")
                skipped += 1
                continue

            files_processed += 1
            with file_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            features = payload.get("features", [])
            for feature in features:
                try:
                    properties = feature.get("properties", {})
                    iso2 = str(properties.get("iso2", "")).strip().upper()
                    season = str(properties.get("season", "")).strip().lower()
                    feature_month = int(properties.get("month", month))
                    geometry = feature.get("geometry")

                    if not iso2 or len(iso2) != 2:
                        skipped += 1
                        continue
                    if feature_month < 1 or feature_month > 12:
                        skipped += 1
                        continue
                    if not season:
                        skipped += 1
                        continue
                    if not geometry:
                        skipped += 1
                        continue

                    country_id = country_ids.get(iso2)
                    if not country_id:
                        skipped += 1
                        continue

                    normalized_geom = _normalize_multipolygon(geometry)
                    geom_wkt = f"SRID=4326;{normalized_geom.wkt}"

                    upsert_stmt = (
                        insert(CountrySeason)
                        .values(
                            country_id=country_id,
                            iso2=iso2,
                            month=feature_month,
                            season=season,
                            geom=geom_wkt,
                        )
                        .on_conflict_do_update(
                            index_elements=["iso2", "month"],
                            set_={
                                "country_id": country_id,
                                "season": season,
                                "geom": geom_wkt,
                            },
                        )
                        .returning(literal_column("xmax = 0").label("inserted"))
                    )
                    result = await session.execute(upsert_stmt)
                    was_inserted = result.scalar_one()
                    if was_inserted:
                        inserted += 1
                    else:
                        updated += 1
                except Exception:
                    skipped += 1

        await session.commit()

    await engine.dispose()

    print("Импорт country_seasons завершен")
    print(f"Файлов обработано: {files_processed}")
    print(f"Вставлено: {inserted}")
    print(f"Обновлено: {updated}")
    print(f"Пропущено: {skipped}")


if __name__ == "__main__":
    asyncio.run(import_country_seasons())

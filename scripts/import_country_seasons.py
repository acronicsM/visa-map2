import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

from geoalchemy2.elements import WKTElement
from shapely.geometry import MultiPolygon, shape
from shapely.ops import unary_union
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.country import Country
from app.models.country_season import CountrySeason


def _merge_season_polygons(polygons: list[dict]) -> tuple[MultiPolygon, int]:
    """Собирает Polygon/MultiPolygon из списка в одну геометрию MULTIPOLYGON.

    Элементы с типом Point, LineString и т.п. пропускаются (часто артефакты
    в исходном GeoJSON). Возвращает (результат, число пропущенных элементов).
    """
    parts: list = []
    skipped = 0
    for geom_dict in polygons:
        if not geom_dict or not isinstance(geom_dict, dict):
            continue
        geom_shape = shape(geom_dict)
        if geom_shape.geom_type == "Polygon":
            parts.append(geom_shape)
        elif geom_shape.geom_type == "MultiPolygon":
            parts.extend(geom_shape.geoms)
        else:
            skipped += 1
    if not parts:
        raise ValueError("empty polygon list")
    merged = unary_union(parts)
    if merged.is_empty:
        raise ValueError("merged geometry is empty")
    if merged.geom_type == "Polygon":
        return MultiPolygon([merged]), skipped
    if merged.geom_type == "MultiPolygon":
        return merged, skipped
    raise ValueError(f"unexpected merged type: {merged.geom_type}")


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
    files_missing = 0
    inserted = 0
    skip_reasons: Counter[str] = Counter()
    error_samples: list[str] = []

    def _note_error(exc: BaseException, iso2_hint: str = "") -> None:
        if len(error_samples) >= 5:
            return
        hint = f" (iso2={iso2_hint})" if iso2_hint else ""
        error_samples.append(f"{type(exc).__name__}{hint}: {exc}")

    async with async_session() as session:
        country_rows = await session.execute(select(Country.iso2, Country.id))
        country_ids = {row.iso2.upper(): row.id for row in country_rows.all()}

        await session.execute(delete(CountrySeason))

        for month in range(1, 13):
            file_path = input_path / f"seasons_month_{month:02d}.geojson"
            if not file_path.exists():
                print(f"Файл не найден: {file_path}")
                files_missing += 1
                continue

            files_processed += 1

            with file_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            root_month = payload.get("month")
            if root_month is not None:
                try:
                    root_m_int = int(root_month)
                except (TypeError, ValueError):
                    print(
                        f"Некорректный month в корне файла {file_path}: {root_month!r}"
                    )
                    skip_reasons["invalid_root_month"] += 1
                    continue
                if root_m_int != month:
                    print(
                        f"Предупреждение: month в {file_path} ({root_m_int}) "
                        f"не совпадает с месяцем из имени файла ({month}); "
                        f"используется месяц из имени файла."
                    )

            countries = payload.get("countries")
            if not isinstance(countries, list):
                skip_reasons["invalid_payload"] += 1
                continue

            for country_entry in countries:
                if not isinstance(country_entry, dict):
                    skip_reasons["invalid_country_entry"] += 1
                    continue
                iso2 = str(country_entry.get("iso2", "")).strip().upper()
                seasons = country_entry.get("seasons")
                if not isinstance(seasons, list):
                    skip_reasons["invalid_seasons"] += 1
                    continue

                for season_entry in seasons:
                    iso2_inner = iso2
                    try:
                        if not isinstance(season_entry, dict):
                            skip_reasons["invalid_season_entry"] += 1
                            continue

                        season = str(season_entry.get("season", "")).strip().lower()
                        polygons = season_entry.get("polygons")

                        if not iso2_inner or len(iso2_inner) != 2:
                            skip_reasons["invalid_iso2"] += 1
                            continue
                        if not season:
                            skip_reasons["empty_season"] += 1
                            continue
                        if not isinstance(polygons, list) or not polygons:
                            skip_reasons["no_geometry"] += 1
                            continue

                        country_id = country_ids.get(iso2_inner)
                        if not country_id:
                            skip_reasons["unknown_country"] += 1
                            continue

                        normalized_geom, n_skipped = _merge_season_polygons(polygons)
                        if n_skipped:
                            skip_reasons["geometry_entries_skipped"] += n_skipped

                        geom = WKTElement(normalized_geom.wkt, srid=4326)

                        await session.execute(
                            insert(CountrySeason).values(
                                country_id=country_id,
                                iso2=iso2_inner,
                                month=month,
                                season=season,
                                geom=geom,
                            )
                        )
                        inserted += 1
                    except IntegrityError as e:
                        skip_reasons["integrity_error"] += 1
                        _note_error(e, iso2_inner)
                    except Exception as e:
                        skip_reasons["other_error"] += 1
                        _note_error(e, iso2_inner)

        await session.commit()

    await engine.dispose()

    skipped_total = int(sum(skip_reasons.values()))
    print("Импорт country_seasons завершен")
    print(f"Файлов обработано: {files_processed}")
    if files_missing:
        print(f"Файлов не найдено: {files_missing}")
    print(f"Вставлено строк: {inserted}")
    print(f"Пропущено записей (всего): {skipped_total}")
    for key, n in sorted(skip_reasons.items(), key=lambda x: (-x[1], x[0])):
        print(f"  — {key}: {n}")
    if skip_reasons["integrity_error"]:
        print(
            "Подсказка: много integrity_error часто из‑за UNIQUE(iso2, month). "
            "Примените миграцию b2c3d4e5f6a1 (снятие уникальности для нескольких "
            "полигонов на страну/месяц)."
        )
    if error_samples:
        print("Примеры ошибок (до 5):")
        for line in error_samples:
            print(f"  {line}")


if __name__ == "__main__":
    asyncio.run(import_country_seasons())

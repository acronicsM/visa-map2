import json
import logging
import re

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.country_vacation_profile import (
    CountryVacationExoticScore,
    CountryVacationProfile,
)
from app.schemas.country_profile import (
    CountryProfileFile,
    CountryProfileUploadResponse,
)
from app.services.vacation_data_service import invalidate_vacation_cache

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000
_MAX_FILE_SIZE_MB = 10
_ISO2_RE = re.compile(r"^[A-Z]{2}$")


async def import_country_profiles_from_file(
    db: AsyncSession,
    file: UploadFile,
) -> CountryProfileUploadResponse:
    """
    Загружает country_profile.json через UploadFile.
    Профили — UPSERT по iso2; exotic — DELETE по home_iso2 + batch UPSERT.
    """
    if file.content_type and file.content_type != "application/json":
        raise ValueError(
            f"Неверный content-type '{file.content_type}', "
            "ожидается application/json"
        )

    raw = await file.read()
    if len(raw) > _MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"Файл слишком большой (> {_MAX_FILE_SIZE_MB} MB)")

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Невалидный JSON: {exc}") from exc

    try:
        payload = CountryProfileFile.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Невалидная структура country_profile: {exc}") from exc

    valid_iso2 = await _load_valid_iso2_set(db)
    profiles_upserted = 0
    exotic_rows_upserted = 0

    profile_batch: list[dict] = []
    for raw_iso, entry in payload.countries.items():
        iso2 = raw_iso.strip().upper()
        if not _valid_iso2(iso2):
            logger.warning("Пропуск iso2 профиля: %s", raw_iso)
            continue
        if iso2 not in valid_iso2:
            logger.warning("Пропуск iso2 (нет в countries): %s", iso2)
            continue

        profile_batch.append(
            {
                "iso2": iso2,
                "beach_score": entry.beach_score,
                "ski_score": entry.ski_score,
                "food_score": entry.food_score,
                "natural_score": entry.natural_score,
                "culture_score": entry.culture_score,
            }
        )
        if len(profile_batch) >= _BATCH_SIZE:
            await _upsert_profiles_batch(db, profile_batch)
            profiles_upserted += len(profile_batch)
            profile_batch = []

        exotic_rows_upserted += await _replace_exotic_for_home(
            db,
            home_iso2=iso2,
            exotic_entries=entry.exotic_score,
            valid_iso2=valid_iso2,
        )

    if profile_batch:
        await _upsert_profiles_batch(db, profile_batch)
        profiles_upserted += len(profile_batch)

    await db.commit()
    await invalidate_vacation_cache()
    logger.info(
        "Country profiles imported: profiles=%s exotic_rows=%s",
        profiles_upserted,
        exotic_rows_upserted,
    )
    return CountryProfileUploadResponse(
        profiles_upserted=profiles_upserted,
        exotic_rows_upserted=exotic_rows_upserted,
    )


async def _load_valid_iso2_set(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Country.iso2))
    return {row[0].upper() for row in result.all()}


def _valid_iso2(v: str) -> bool:
    return bool(_ISO2_RE.match(v))


async def _upsert_profiles_batch(db: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(CountryVacationProfile).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["iso2"],
        set_={
            "beach_score": stmt.excluded.beach_score,
            "ski_score": stmt.excluded.ski_score,
            "food_score": stmt.excluded.food_score,
            "natural_score": stmt.excluded.natural_score,
            "culture_score": stmt.excluded.culture_score,
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)


async def _replace_exotic_for_home(
    db: AsyncSession,
    *,
    home_iso2: str,
    exotic_entries: list,
    valid_iso2: set[str],
) -> int:
    await db.execute(
        delete(CountryVacationExoticScore).where(
            CountryVacationExoticScore.home_iso2 == home_iso2
        )
    )

    batch: list[dict] = []
    imported = 0
    for item in exotic_entries:
        dest_iso2 = item.iso2
        if dest_iso2 not in valid_iso2:
            logger.warning(
                "Пропуск exotic dest (нет в countries): %s -> %s",
                home_iso2,
                dest_iso2,
            )
            continue
        batch.append(
            {
                "home_iso2": home_iso2,
                "dest_iso2": dest_iso2,
                "score": item.score,
            }
        )
        if len(batch) >= _BATCH_SIZE:
            await _upsert_exotic_batch(db, batch)
            imported += len(batch)
            batch = []

    if batch:
        await _upsert_exotic_batch(db, batch)
        imported += len(batch)
    return imported


async def _upsert_exotic_batch(db: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(CountryVacationExoticScore).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["home_iso2", "dest_iso2"],
        set_={"score": stmt.excluded.score},
    )
    await db.execute(stmt)

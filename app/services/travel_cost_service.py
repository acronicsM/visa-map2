import json
import logging
import re

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import (
    GEODATA_KEY,
    TRAVEL_COSTS_KEY,
    TRAVEL_COSTS_TTL,
    TRAVEL_COST_SCORE_BANDS_KEY,
    TRAVEL_COST_SCORE_BANDS_TTL,
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
)
from app.config import settings
from app.models.travel_cost_matrix import TravelCostMatrix
from app.schemas.travel_cost import (
    BudgetTier,
    TravelCostMapResponse,
    TravelCostScoreBandsResponse,
    TravelCostUploadResponse,
)

logger = logging.getLogger(__name__)

_BUDGET_TIER_MAP = {
    "cheap": BudgetTier.cheap,
    "normal": BudgetTier.normal,
    "expensive": BudgetTier.expensive,
}

_BATCH_SIZE = 1000
_MAX_FILE_SIZE_MB = 100

# Дефолт при пустом TRAVEL_COST_SCORE_BANDS; держите в синхроне с
# DEFAULT_TRAVEL_COST_SCORE_BANDS (visa-map2-frontend/app/lib/travel-cost-score-bands.ts).
_DEFAULT_SCORE_BANDS: dict[str, object] = {
    "thresholds": [0.5, 1, 2],
    "labels": [
        "Без забот",
        "Комфортно",
        "Придется экономить",
        "Вне бюджета",
    ],
    "colors": ["#22c55e", "#84cc16", "#eab308", "#ef4444"],
}


def _travel_cost_score_bands_from_settings() -> TravelCostScoreBandsResponse:
    raw = (settings.travel_cost_score_bands or "").strip()
    if not raw:
        return TravelCostScoreBandsResponse.model_validate(_DEFAULT_SCORE_BANDS)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"TRAVEL_COST_SCORE_BANDS: невалидный JSON: {exc}"
        ) from exc
    return TravelCostScoreBandsResponse.model_validate(data)


async def get_travel_cost_score_bands() -> TravelCostScoreBandsResponse:
    """Интервалы подписей/цветов score; кеш Redis 24 ч."""
    cached = await cache_get(TRAVEL_COST_SCORE_BANDS_KEY)
    if cached is not None:
        return TravelCostScoreBandsResponse.model_validate(cached)
    bands = _travel_cost_score_bands_from_settings()
    await cache_set(
        TRAVEL_COST_SCORE_BANDS_KEY,
        bands.model_dump(),
        TRAVEL_COST_SCORE_BANDS_TTL,
    )
    return bands


async def import_travel_costs_from_file(
    db: AsyncSession,
    file: UploadFile,
) -> TravelCostUploadResponse:
    """
    Загружает travel_country_model_tier_means.json через UploadFile,
    парсит матрицу home_iso2 x dest_iso2 и пишет в travel_cost_matrix
    батчами через UPSERT (on_conflict_do_update).
    """
    if file.content_type and file.content_type != "application/json":
        raise ValueError(
            f"Неверный content-type '{file.content_type}', ожидается application/json"
        )

    raw = await file.read()
    if len(raw) > _MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"Файл слишком большой (> {_MAX_FILE_SIZE_MB} MB)")

    data = json.loads(raw.decode("utf-8"))
    countries_data = data.get("countries", {})

    batch: list[dict] = []
    imported_count = 0

    for home_iso2_raw, home_entry in countries_data.items():
        home_iso2 = home_iso2_raw.strip().upper()
        if not _valid_iso2(home_iso2):
            logger.warning(f"Пропуск home_iso2: {home_iso2_raw}")
            continue

        dest_list = home_entry.get("countries", [])
        for dest_entry in dest_list:
            dest_iso2_raw = dest_entry.get("iso2", "")
            dest_iso2 = str(dest_iso2_raw).strip().upper()
            if not _valid_iso2(dest_iso2):
                continue

            batch.append(
                {
                    "home_iso2": home_iso2,
                    "dest_iso2": dest_iso2,
                    "score_cheap": _to_float(dest_entry.get("Score_cheap")),
                    "score_normal": _to_float(dest_entry.get("Score_normal")),
                    "score_expensive": _to_float(dest_entry.get("Score_expensive")),
                    "daily_cost_cheap": _to_float(dest_entry.get("DailyCost_cheap")),
                    "daily_cost_normal": _to_float(
                        dest_entry.get("DailyCost_normal")
                    ),
                    "daily_cost_expensive": _to_float(
                        dest_entry.get("DailyCost_expensive")
                    ),
                }
            )

            if len(batch) >= _BATCH_SIZE:
                await _upsert_batch(db, batch)
                imported_count += len(batch)
                batch = []

    if batch:
        await _upsert_batch(db, batch)
        imported_count += len(batch)

    await db.commit()

    await cache_delete(GEODATA_KEY)
    await cache_delete_pattern("travel_costs:*")
    logger.info(f"Travel costs imported: {imported_count} rows")

    return TravelCostUploadResponse(imported_count=imported_count)


def _valid_iso2(v: str) -> bool:
    return bool(re.match(r"^[A-Z]{2}$", v))


def _to_float(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


async def _upsert_batch(db: AsyncSession, rows: list[dict]) -> None:
    """UPSERT батча через PostgreSQL ON CONFLICT."""
    if not rows:
        return

    stmt = insert(TravelCostMatrix).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["home_iso2", "dest_iso2"],
        set_={
            "score_cheap": stmt.excluded.score_cheap,
            "score_normal": stmt.excluded.score_normal,
            "score_expensive": stmt.excluded.score_expensive,
            "daily_cost_cheap": stmt.excluded.daily_cost_cheap,
            "daily_cost_normal": stmt.excluded.daily_cost_normal,
            "daily_cost_expensive": stmt.excluded.daily_cost_expensive,
        },
    )
    await db.execute(stmt)


async def get_travel_cost_map(
    db: AsyncSession,
    home_iso2: str,
    budget_tier: str,
) -> TravelCostMapResponse:
    """
    Возвращает матрицу {dest_iso2: score} для заданной домашней страны
    и уровня бюджета.
    """
    tier = budget_tier.lower()
    if tier not in _BUDGET_TIER_MAP:
        raise ValueError(
            f"Недопустимый budget_tier: {budget_tier}. "
            f"Допустимые: cheap, normal, expensive"
        )

    cache_key = TRAVEL_COSTS_KEY.format(
        home_iso2=home_iso2.upper(), tier=tier
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return TravelCostMapResponse(
            home_iso2=home_iso2.upper(),
            budget_tier=_BUDGET_TIER_MAP[tier],
            scores=cached,
        )

    score_col = getattr(TravelCostMatrix, f"score_{tier}")
    result = await db.execute(
        select(TravelCostMatrix.dest_iso2, score_col)
        .where(TravelCostMatrix.home_iso2 == home_iso2.upper())
        .where(score_col.isnot(None))
    )

    scores: dict[str, float] = {}
    for row in result.all():
        scores[row[0]] = float(row[1])

    if scores:
        await cache_set(cache_key, scores, TRAVEL_COSTS_TTL)

    return TravelCostMapResponse(
        home_iso2=home_iso2.upper(),
        budget_tier=_BUDGET_TIER_MAP[tier],
        scores=scores,
    )
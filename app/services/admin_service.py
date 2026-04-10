import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visa_policy import VisaPolicy
from app.models.visa_policy_history import VisaPolicyHistory
from app.models.news_trigger import NewsTrigger
from app.models.passport import Passport
from app.models.country import Country
from app.cache import (
    GEODATA_KEY,
    SAFETY_FINAL_SCORES_KEY,
    cache_delete,
    cache_set_persistent,
)
from app.schemas.admin import (
    NewsTriggerCreate,
    NewsTriggerStatusUpdate,
    SafetyMergedPayload,
    SafetyScoresImportResponse,
    VisaPolicyUpdate,
)
from app.services.safety_level_mapping import final_score_to_safety_level
from app.services.visa_service import invalidate_visa_cache

logger = logging.getLogger(__name__)

_SAFETY_IMPORT_SOURCE = "safety_final_score"


async def update_visa_policy(
    db: AsyncSession,
    policy_id: UUID,
    data: VisaPolicyUpdate,
    changed_by: str = "admin",
) -> VisaPolicy | None:
    """
    Обновляет визовый режим:
    1. Сохраняет старую версию в историю
    2. Обновляет текущую запись
    3. Инвалидирует кеш
    """
    result = await db.execute(
        select(VisaPolicy).where(VisaPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        return None

    history = VisaPolicyHistory(
        policy_id=policy.id,
        visa_category=policy.visa_category,
        max_stay_days=policy.max_stay_days,
        conditions=policy.conditions,
        change_reason=data.change_reason,
        changed_by=changed_by,
        valid_from=policy.updated_at,
        valid_to=datetime.now(timezone.utc),
    )
    db.add(history)

    update_fields = data.model_dump(
        exclude={"change_reason"},
        exclude_none=True,
    )
    for field, value in update_fields.items():
        setattr(policy, field, value)

    if data.verified_by:
        policy.verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(policy)

    passport_result = await db.execute(
        select(Passport).where(Passport.id == policy.passport_id)
    )
    passport = passport_result.scalar_one_or_none()
    if passport:
        country_result = await db.execute(
            select(Country).where(Country.id == passport.country_id)
        )
        country = country_result.scalar_one_or_none()
        if country:
            await invalidate_visa_cache(country.iso2)
            logger.info(
                f"Visa policy {policy_id} updated, "
                f"cache invalidated for {country.iso2}"
            )

    return policy


async def create_news_trigger(
    db: AsyncSession,
    data: NewsTriggerCreate,
) -> NewsTrigger:
    """Создаёт новый новостной триггер"""
    trigger = NewsTrigger(
        headline=data.headline,
        source_name=data.source_name,
        source_url=data.source_url,
        status="new",
        affected_countries=data.affected_countries,
        notes=data.notes,
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    logger.info(f"News trigger created: {trigger.id} — {trigger.headline[:50]}")
    return trigger


async def update_trigger_status(
    db: AsyncSession,
    trigger_id: UUID,
    data: NewsTriggerStatusUpdate,
) -> NewsTrigger | None:
    """Обновляет статус триггера"""
    result = await db.execute(
        select(NewsTrigger).where(NewsTrigger.id == trigger_id)
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        return None

    trigger.status = data.status
    if data.notes:
        trigger.notes = data.notes
    if data.status in ("processed", "ignored"):
        trigger.processed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(trigger)
    logger.info(f"News trigger {trigger_id} status → {data.status}")
    return trigger


async def get_news_triggers(
    db: AsyncSession,
    status: str | None = None,
) -> list[NewsTrigger]:
    """Список триггеров с опциональным фильтром по статусу"""
    query = select(NewsTrigger).order_by(NewsTrigger.detected_at.desc())
    if status:
        query = query.where(NewsTrigger.status == status)
    result = await db.execute(query)
    return result.scalars().all()


async def store_safety_final_scores(
    db: AsyncSession,
    payload: SafetyMergedPayload,
) -> SafetyScoresImportResponse:
    """
    1) Карта iso2 -> safety_final_score в Redis.
    2) По порогам из Settings → countries.safety_level (safe/unsafe/dangerous).
    3) Сброс кеша GeoJSON.
    """
    out: dict[str, float] = {}
    for raw_iso, entry in payload.by_iso2.items():
        iso = raw_iso.strip().upper()
        if not re.match(r"^[A-Z]{2}$", iso):
            continue
        out[iso] = float(entry.safety_final_score)

    if not out:
        await cache_set_persistent(SAFETY_FINAL_SCORES_KEY, {})
        await cache_delete(GEODATA_KEY)
        return SafetyScoresImportResponse(stored_count=0, countries_safety_updated=0)

    now = datetime.now(timezone.utc)
    # Отдельные UPDATE по iso2: надёжно с asyncpg (jsonb_to_recordset + CAST
    # в text() часто даёт 0 затронутых строк из‑за привязки параметров).
    updated = 0
    for iso, score in out.items():
        level = final_score_to_safety_level(score)
        res = await db.execute(
            update(Country)
            .where(func.upper(func.trim(Country.iso2)) == iso)
            .values(
                safety_level=level,
                safety_updated_at=now,
                safety_source=_SAFETY_IMPORT_SOURCE,
                updated_at=now,
            )
        )
        updated += int(res.rowcount or 0)
    await db.commit()

    await cache_set_persistent(SAFETY_FINAL_SCORES_KEY, out)
    await cache_delete(GEODATA_KEY)
    if updated < len(out):
        logger.warning(
            "Safety import: в Redis %s кодов, в Postgres обновлено строк %s "
            "(нет совпадения iso2 в таблице countries?)",
            len(out),
            updated,
        )
    logger.info(
        "Safety import: redis=%s rows, postgres safety_level updated=%s",
        len(out),
        updated,
    )
    return SafetyScoresImportResponse(
        stored_count=len(out),
        countries_safety_updated=updated,
    )
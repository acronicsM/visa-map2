import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visa_policy import VisaPolicy
from app.models.visa_policy_history import VisaPolicyHistory
from app.models.news_trigger import NewsTrigger
from app.models.passport import Passport
from app.models.country import Country
from app.schemas.admin import VisaPolicyUpdate, NewsTriggerCreate, NewsTriggerStatusUpdate
from app.services.visa_service import invalidate_visa_cache

logger = logging.getLogger(__name__)


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
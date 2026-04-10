from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_api_key
from app.schemas.admin import (
    NewsTriggerCreate,
    NewsTriggerResponse,
    NewsTriggerStatusUpdate,
    SafetyMergedPayload,
    SafetyScoresImportResponse,
    VisaPolicyResponse,
    VisaPolicyUpdate,
)
from app.services.admin_service import (
    create_news_trigger,
    get_news_triggers,
    store_safety_final_scores,
    update_trigger_status,
    update_visa_policy,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_api_key)],
)


@router.put(
    "/countries/safety-final-scores",
    response_model=SafetyScoresImportResponse,
)
async def put_safety_final_scores(
    body: SafetyMergedPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Полная замена карты safety_final_score в Redis и выставление safety_level
    в Postgres (safe/unsafe/dangerous) по порогам из env.
    Тело как у safety_merged.json (поле by_iso2).
    """
    return await store_safety_final_scores(db, body)


@router.patch("/visa-policies/{policy_id}", response_model=VisaPolicyResponse)
async def patch_visa_policy(
    policy_id: UUID,
    data: VisaPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить визовый режим. Старая версия сохраняется в историю."""
    policy = await update_visa_policy(db, policy_id, data)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Визовый режим {policy_id} не найден",
        )
    return policy


@router.post("/news-triggers", response_model=NewsTriggerResponse)
async def create_trigger(
    data: NewsTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Создать новостной триггер — вручную или из RSS парсера."""
    trigger = await create_news_trigger(db, data)
    return trigger


@router.get("/news-triggers", response_model=list[NewsTriggerResponse])
async def list_triggers(
    status: str | None = Query(None, description="Фильтр: new, reviewing, processed, ignored"),
    db: AsyncSession = Depends(get_db),
):
    """Список триггеров для модератора."""
    triggers = await get_news_triggers(db, status=status)
    return triggers


@router.patch("/news-triggers/{trigger_id}/status", response_model=NewsTriggerResponse)
async def patch_trigger_status(
    trigger_id: UUID,
    data: NewsTriggerStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить статус триггера: new → reviewing → processed / ignored."""
    trigger = await update_trigger_status(db, trigger_id, data)
    if not trigger:
        raise HTTPException(
            status_code=404,
            detail=f"Триггер {trigger_id} не найден",
        )
    return trigger
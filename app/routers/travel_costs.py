from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.travel_cost import (
    TravelCurrencyListResponse,
    TravelCostMapResponse,
    TravelCostScoreBandsResponse,
    TravelExactBudgetDataResponse,
    TravelFxRateResponse,
)
from app.services.travel_cost_service import (
    get_exact_budget_data,
    get_travel_cost_currencies,
    get_travel_cost_fx_rate,
    get_travel_cost_map,
    get_travel_cost_score_bands,
)

router = APIRouter(prefix="/travel-costs", tags=["travel-costs"])


@router.get("/score-bands", response_model=TravelCostScoreBandsResponse)
async def travel_cost_score_bands():
    """
    Пороги относительного score, подписи (RU) и цвета для карты и попапа.
    Кешируется в Redis (24 ч); источник — `TRAVEL_COST_SCORE_BANDS` или значения
    по умолчанию.
    """
    try:
        return await get_travel_cost_score_bands()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=500,
            detail="Неверная конфигурация TRAVEL_COST_SCORE_BANDS",
        ) from exc


@router.get("/currencies", response_model=TravelCurrencyListResponse)
async def travel_cost_currencies(
    home_iso2: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Популярные валюты для ввода точного бюджета."""
    return await get_travel_cost_currencies(db, home_iso2)


@router.get("/fx-rate", response_model=TravelFxRateResponse)
async def travel_cost_fx_rate(
    currency: str = Query(..., min_length=3, max_length=3),
):
    """Курс USD -> currency, кешируется на backend 24 часа."""
    try:
        return await get_travel_cost_fx_rate(currency)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/{home_iso2}/exact-budget-data",
    response_model=TravelExactBudgetDataResponse,
)
async def travel_exact_budget_data(
    home_iso2: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Данные для точного бюджета: дневной доход домашней страны и
    daily-cost пороги направлений в USD.
    """
    return await get_exact_budget_data(db, home_iso2)


@router.get("/{home_iso2}", response_model=TravelCostMapResponse)
async def travel_cost_map(
    home_iso2: str,
    budget_tier: str = Query(..., enum=["cheap", "normal", "expensive"]),
    db: AsyncSession = Depends(get_db),
):
    """
    Матрица стоимостей для домашней страны и выбранного уровня бюджета.
    Возвращает {dest_iso2: score} — относительная стоимость поездки.
    """
    try:
        return await get_travel_cost_map(db, home_iso2, budget_tier)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

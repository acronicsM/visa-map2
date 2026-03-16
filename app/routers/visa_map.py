from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.visa_policy import VisaMapItem, VisaPolicyDetail
from app.services.country_service import get_country_by_iso2
from app.services.visa_service import get_visa_map, get_visa_detail

router = APIRouter(prefix="/visa-map", tags=["visa-map"])


@router.get("/{passport_iso2}", response_model=list[VisaMapItem])
async def visa_map(passport_iso2: str, db: AsyncSession = Depends(get_db)):
    """
    Данные для окраски карты — список всех стран с категорией визы
    для выбранного паспорта
    """
    country = await get_country_by_iso2(db, passport_iso2)
    if not country:
        raise HTTPException(
            status_code=404,
            detail=f"Страна с паспортом {passport_iso2} не найдена"
        )
    items = await get_visa_map(db, passport_iso2)
    return items


@router.get("/{passport_iso2}/{destination_iso2}", response_model=VisaPolicyDetail)
async def visa_detail(
    passport_iso2: str,
    destination_iso2: str,
    db: AsyncSession = Depends(get_db),
):
    """Детальная информация о визовом режиме между двумя странами"""
    policy = await get_visa_detail(db, passport_iso2, destination_iso2)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Визовый режим {passport_iso2} → {destination_iso2} не найден"
        )
    return policy
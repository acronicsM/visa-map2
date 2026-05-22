from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.countries import validate_iso2
from app.schemas.passport_bootstrap import PassportBootstrapResponse
from app.services.passport_bootstrap_service import get_passport_bootstrap

router = APIRouter(prefix="/passport-bootstrap", tags=["passport-bootstrap"])


@router.get("/{home_iso2}", response_model=PassportBootstrapResponse)
async def passport_bootstrap(
    home_iso2: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Агрегат для главной карты: visa-map, scores по всем budget tier,
    список валют для точного бюджета.
    """
    home_iso2 = validate_iso2(home_iso2)
    result = await get_passport_bootstrap(db, home_iso2)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Страна с кодом '{home_iso2}' не найдена",
        )
    return result

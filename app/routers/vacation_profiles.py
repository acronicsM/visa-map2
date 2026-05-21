from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.vacation import VacationExoticResponse, VacationProfilesResponse
from app.services.vacation_data_service import (
    get_vacation_exotic_for_home,
    get_vacation_profiles,
)

router = APIRouter(tags=["vacation-profiles"])


@router.get("/vacation-profiles", response_model=VacationProfilesResponse)
async def vacation_profiles(db: AsyncSession = Depends(get_db)):
    """Скалярные score типа отдыха по странам назначения (0..1)."""
    return await get_vacation_profiles(db)


@router.get(
    "/vacation-exotic/{home_iso2}",
    response_model=VacationExoticResponse,
)
async def vacation_exotic(
    home_iso2: str,
    db: AsyncSession = Depends(get_db),
):
    """Матрица экзотики home_iso2 x dest_iso2 (0..1)."""
    try:
        return await get_vacation_exotic_for_home(db, home_iso2)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

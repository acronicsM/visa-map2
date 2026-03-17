from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.country import CountryShort, CountryDetail
from app.services.country_service import (
    get_all_countries,
    get_country_by_iso2,
    get_countries_geodata,
)

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=list[CountryShort])
async def list_countries(db: AsyncSession = Depends(get_db)):
    """Список всех активных стран для дропдауна"""
    countries = await get_all_countries(db)
    return countries


@router.get("/geodata")
async def countries_geodata(db: AsyncSession = Depends(get_db)):
    """
    GeoJSON FeatureCollection всех стран с границами.
    Используется фронтендом для рендера карты.
    """
    data = await get_countries_geodata(db)
    return JSONResponse(content=data)


@router.get("/{iso2}", response_model=CountryDetail)
async def get_country(iso2: str, db: AsyncSession = Depends(get_db)):
    """Карточка страны по коду iso2"""
    country = await get_country_by_iso2(db, iso2)
    if not country:
        raise HTTPException(status_code=404, detail=f"Страна {iso2} не найдена")
    return country
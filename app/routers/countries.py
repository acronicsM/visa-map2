from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.database import get_db
from app.schemas.country import CountryShort, CountryDetail
from app.services.country_service import (
    get_all_countries,
    get_country_by_iso2,
    get_countries_geodata,
    get_country_geodata,
)

router = APIRouter(prefix="/countries", tags=["countries"])


def validate_iso2(iso2: str) -> str:
    iso2 = iso2.strip().upper()
    if not re.match(r"^[A-Z]{2}$", iso2):
        raise HTTPException(
            status_code=422,
            detail=f"Некорректный код страны '{iso2}' — нужно 2 латинские буквы (RU, DE, US)",
        )
    return iso2


@router.get("", response_model=list[CountryShort])
async def list_countries(
    region: str | None = Query(None, description="Фильтр по региону: Europe, Asia, Africa, Americas, Oceania"),
    search: str | None = Query(None, description="Поиск по названию страны"),
    db: AsyncSession = Depends(get_db),
):
    """Список всех активных стран для дропдауна"""
    countries = await get_all_countries(db, region=region, search=search)
    return countries


@router.get("/geodata", include_in_schema=False)
async def countries_geodata(db: AsyncSession = Depends(get_db)):
    """
    GeoJSON FeatureCollection всех стран с границами.
    Используется фронтендом для рендера карты.
    """
    geojson = await get_countries_geodata(db)
    return JSONResponse(content=geojson)


@router.get("/{iso2}/geodata", summary="GeoJSON одной страны")
async def get_country_geodata_route(iso2: str, db: AsyncSession = Depends(get_db)):
    """GeoJSON Feature одной страны по коду iso2. Удобен для тестирования геометрии."""
    iso2 = validate_iso2(iso2)
    feature = await get_country_geodata(db, iso2)
    if not feature:
        raise HTTPException(
            status_code=404,
            detail=f"Геоданные для страны '{iso2}' не найдены"
        )
    return JSONResponse(content=feature)


@router.get("/{iso2}", response_model=CountryDetail)
async def get_country(iso2: str, db: AsyncSession = Depends(get_db)):
    """Карточка страны по коду iso2"""
    iso2 = validate_iso2(iso2)
    country = await get_country_by_iso2(db, iso2)
    if not country:
        raise HTTPException(
            status_code=404,
            detail=f"Страна с кодом '{iso2}' не найдена"
        )
    return country
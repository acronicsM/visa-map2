from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.countries import validate_iso2
from app.schemas.country_season import CountrySeasonByCountryResponse
from app.services.country_season_service import (
    get_country_seasons_by_iso2,
    get_country_seasons_geodata,
)

router = APIRouter(prefix="/country-seasons", tags=["country-seasons"])


@router.get("/{month}/geodata")
async def country_seasons_geodata(
    month: int = Path(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    geojson = await get_country_seasons_geodata(db, month=month)
    if not geojson["features"]:
        raise HTTPException(
            status_code=404,
            detail=f"Сезонные геоданные за месяц '{month}' не найдены",
        )
    return JSONResponse(content=geojson)


@router.get("/{iso2}", response_model=CountrySeasonByCountryResponse)
async def country_seasons_by_country(iso2: str, db: AsyncSession = Depends(get_db)):
    iso2 = validate_iso2(iso2)
    seasons = await get_country_seasons_by_iso2(db, iso2=iso2)
    if not seasons:
        raise HTTPException(
            status_code=404,
            detail=f"Сезонные данные для страны '{iso2}' не найдены",
        )
    return {"iso2": iso2, "seasons": seasons}

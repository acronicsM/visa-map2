from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.countries import validate_iso2
from app.schemas.country_season import (
    CountrySeasonByCountryResponse,
    CountrySeasonMonthMeta,
)
from app.services.country_season_service import (
    get_country_season_month_meta,
    get_country_seasons_geodata,
    get_country_seasons_geojson_by_iso2,
)

router = APIRouter(prefix="/country-seasons", tags=["country-seasons"])


@router.get("/{month}/meta", response_model=CountrySeasonMonthMeta)
async def country_seasons_month_meta(
    month: int = Path(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """Только уникальные ``season`` за месяц; параллелится с ``/geodata`` на клиенте."""
    return await get_country_season_month_meta(db, month=month)


@router.get("/{month}/geodata")
async def country_seasons_geodata(
    month: int = Path(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """GeoJSON за месяц; при отсутствии строк в БД — пустая коллекция (200), не 404.

    В корне объекта дополнительно поле ``distinct_seasons``: уникальные значения
    ``season`` за месяц (в нижнем регистре), без отдельного запроса на клиенте.
    """
    geojson = await get_country_seasons_geodata(db, month=month)
    return JSONResponse(content=geojson)


@router.get("/{iso2}", response_model=CountrySeasonByCountryResponse)
async def country_seasons_by_country(iso2: str, db: AsyncSession = Depends(get_db)):
    iso2 = validate_iso2(iso2)
    geojson = await get_country_seasons_geojson_by_iso2(db, iso2=iso2)
    if not geojson["features"]:
        raise HTTPException(
            status_code=404,
            detail=f"Сезонные данные для страны '{iso2}' не найдены",
        )
    return {
        "iso2": iso2,
        "type": geojson["type"],
        "features": geojson["features"],
    }

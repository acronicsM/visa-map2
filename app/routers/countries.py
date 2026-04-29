from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.database import get_db
from app.schemas.country import CountryDetail, CountryNamesEntry, CountryShort
from app.services.country_service import (
    get_all_countries,
    get_country_by_iso2,
    get_countries_geodata,
    get_country_geodata,
    get_country_names_map,
    build_country_short,
)
from app.cache import (
    COUNTRY_NAMES_KEY,
    COUNTRY_NAMES_TTL,
    SAFETY_FINAL_SCORES_KEY,
    cache_get,
    cache_set,
)

router = APIRouter(prefix="/countries", tags=["countries"])


def validate_iso2(iso2: str) -> str:
    iso2 = iso2.strip().upper()
    if not re.match(r"^[A-Z]{2}$", iso2):
        raise HTTPException(
            status_code=422,
            detail=(
                "Некорректный код страны "
                f"'{iso2}' — нужно 2 латинские буквы (RU, DE, US)"
            ),
        )
    return iso2


@router.get("", response_model=list[CountryShort])
async def list_countries(
    region: str | None = Query(
        None,
        description=("Фильтр по региону: Europe, Asia, Africa, Americas, Oceania"),
    ),
    search: str | None = Query(None, description="Поиск по названию страны"),
    has_language: str | None = Query(
        None,
        description="Фильтр: JSONB all_languages содержит ключ (код языка)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Список всех активных стран для дропдауна"""
    countries = await get_all_countries(
        db,
        region=region,
        search=search,
        has_language=has_language,
    )
    return [build_country_short(c) for c in countries]


@router.get("/geodata", include_in_schema=False)
async def countries_geodata(db: AsyncSession = Depends(get_db)):
    """
    GeoJSON FeatureCollection всех стран с границами.
    Используется фронтендом для рендера карты.
    """
    geojson = await get_countries_geodata(db)
    return JSONResponse(content=geojson)


@router.get("/names", response_model=dict[str, CountryNamesEntry])
async def country_names(db: AsyncSession = Depends(get_db)):
    """Справочник имён и валют по iso2; кеш Redis 24 ч."""
    cached = await cache_get(COUNTRY_NAMES_KEY)
    if cached is not None:
        return cached
    data = await get_country_names_map(db)
    await cache_set(COUNTRY_NAMES_KEY, data, COUNTRY_NAMES_TTL)
    return data


@router.get("/safety-final-scores", response_model=dict[str, float])
async def safety_final_scores():
    """
    Карта iso2 -> safety_final_score из Redis (без БД).
    Пустой объект, если админ ещё не загружал данные.
    """
    data = await cache_get(SAFETY_FINAL_SCORES_KEY)
    if data is None:
        return {}
    return data


@router.get("/{iso2}/geodata", summary="GeoJSON одной страны")
async def get_country_geodata_route(iso2: str, db: AsyncSession = Depends(get_db)):
    """GeoJSON Feature одной страны по коду iso2. Удобен для тестирования."""
    iso2 = validate_iso2(iso2)
    feature = await get_country_geodata(db, iso2)
    if not feature:
        raise HTTPException(
            status_code=404,
            detail=f"Геоданные для страны '{iso2}' не найдены",
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
            detail=f"Страна с кодом '{iso2}' не найдена",
        )
    return CountryDetail.model_validate(country)

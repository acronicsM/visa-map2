from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.flight import DepartureCitiesResponse, DirectCountriesResponse
from app.services.flight_service import CityNotFoundError, get_direct_countries
from app.services.flights.departure_cities import get_departure_cities

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/departure-cities", response_model=DepartureCitiesResponse)
async def departure_cities(
    country_iso2: str = Query(..., min_length=2, max_length=2),
    international_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Города вылета по домашней стране (OpenFlights airports)."""
    try:
        return await get_departure_cities(
            db,
            country_iso2,
            international_only=international_only,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/direct-countries", response_model=DirectCountriesResponse)
async def direct_countries(
    city: str = Query(..., min_length=1, max_length=100),
    country_iso2: str = Query(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
):
    """
    Карта стран с теоретически возможным прямым перелётом из города.
    Источник данных задаётся env FLIGHTS_DATA_SOURCE.
    """
    try:
        return await get_direct_countries(db, city, country_iso2)
    except CityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.cache import (
    FLIGHTS_DEPARTURE_CITIES_KEY,
    FLIGHTS_DEPARTURE_CITIES_TTL,
    cache_get,
    cache_set,
)
from app.models.flight import Airport, FlightRoute
from app.schemas.flight import DepartureCitiesResponse, DepartureCityItem


def _cache_key(country_iso2: str, international_only: bool) -> str:
    suffix = "intl" if international_only else "all"
    return FLIGHTS_DEPARTURE_CITIES_KEY.format(
        country_iso2=country_iso2.upper(),
        scope=suffix,
    )


async def get_departure_cities(
    db: AsyncSession,
    country_iso2: str,
    *,
    international_only: bool = True,
) -> DepartureCitiesResponse:
    iso2 = country_iso2.strip().upper()
    if len(iso2) != 2:
        raise ValueError("country_iso2 must be a 2-letter code")

    cache_key = _cache_key(iso2, international_only)
    cached = await cache_get(cache_key)
    if cached is not None:
        return DepartureCitiesResponse.model_validate(cached)

    items = await _load_departure_cities(db, iso2, international_only=international_only)
    response = DepartureCitiesResponse(country_iso2=iso2, items=items)
    await cache_set(cache_key, response.model_dump(), FLIGHTS_DEPARTURE_CITIES_TTL)
    return response


async def _load_departure_cities(
    db: AsyncSession,
    iso2: str,
    *,
    international_only: bool,
) -> list[DepartureCityItem]:
    if international_only:
        return await _load_international_cities(db, iso2)
    return await _load_all_cities_with_iata(db, iso2)


async def _load_all_cities_with_iata(
    db: AsyncSession,
    iso2: str,
) -> list[DepartureCityItem]:
    stmt = (
        select(
            Airport.city,
            Airport.city_normalized,
            func.array_agg(func.distinct(Airport.iata)).label("airports"),
        )
        .where(
            Airport.country_iso2 == iso2,
            Airport.iata.is_not(None),
            Airport.is_active.is_(True),
        )
        .group_by(Airport.city, Airport.city_normalized)
        .order_by(Airport.city)
    )
    result = await db.execute(stmt)
    return [
        DepartureCityItem(
            city=row.city,
            city_normalized=row.city_normalized,
            airports=sorted(row.airports or []),
        )
        for row in result.all()
    ]


async def _load_international_cities(
    db: AsyncSession,
    iso2: str,
) -> list[DepartureCityItem]:
    dest_airport = aliased(Airport)

    stmt = (
        select(
            Airport.city,
            Airport.city_normalized,
            func.array_agg(func.distinct(Airport.iata)).label("airports"),
            func.count(func.distinct(FlightRoute.dest_iata)).label("intl_routes"),
        )
        .join(FlightRoute, FlightRoute.source_iata == Airport.iata)
        .join(
            dest_airport,
            and_(
                dest_airport.iata == FlightRoute.dest_iata,
                dest_airport.country_iso2.is_not(None),
                dest_airport.country_iso2 != Airport.country_iso2,
            ),
        )
        .where(
            Airport.country_iso2 == iso2,
            Airport.iata.is_not(None),
            Airport.is_active.is_(True),
            FlightRoute.stops == 0,
            FlightRoute.is_codeshare.is_(False),
        )
        .group_by(Airport.city, Airport.city_normalized)
        .order_by(func.count(func.distinct(FlightRoute.dest_iata)).desc(), Airport.city)
    )
    result = await db.execute(stmt)
    return [
        DepartureCityItem(
            city=row.city,
            city_normalized=row.city_normalized,
            airports=sorted(row.airports or []),
        )
        for row in result.all()
    ]

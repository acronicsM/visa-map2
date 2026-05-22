from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.flight import Airport, CountryHubAirport, FlightRoute
from app.services.flights.providers.base import DirectFlightProvider


class OpenFlightsProvider:
    source = "openflights"

    async def fetch_direct_countries(
        self,
        db: AsyncSession,
        origin_iatas: list[str],
        active_dest_iso2: set[str],
    ) -> dict[str, bool]:
        if not origin_iatas:
            return {iso2: False for iso2 in active_dest_iso2}

        stmt = (
            select(distinct(Airport.country_iso2))
            .select_from(FlightRoute)
            .join(
                Airport,
                Airport.iata == FlightRoute.dest_iata,
            )
            .where(
                FlightRoute.source_iata.in_(origin_iatas),
                FlightRoute.stops == 0,
                FlightRoute.is_codeshare.is_(False),
                Airport.country_iso2.is_not(None),
            )
        )
        result = await db.execute(stmt)
        direct = {row[0] for row in result.all() if row[0] in active_dest_iso2}
        return {iso2: iso2 in direct for iso2 in active_dest_iso2}


async def get_active_country_iso2(db: AsyncSession) -> set[str]:
    result = await db.execute(
        select(Country.iso2).where(Country.is_active.is_(True))
    )
    return {row[0] for row in result.all()}


async def get_country_hub_airports(
    db: AsyncSession,
    country_iso2: str,
) -> list[str]:
    result = await db.execute(
        select(CountryHubAirport.iata)
        .where(CountryHubAirport.country_iso2 == country_iso2)
        .order_by(CountryHubAirport.rank)
    )
    return [row[0] for row in result.all()]

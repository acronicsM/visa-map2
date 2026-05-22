import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flight import Airport, CountryHubAirport

logger = logging.getLogger(__name__)


async def load_iata_to_country(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(
        select(Airport.iata, Airport.country_iso2).where(
            Airport.iata.is_not(None),
            Airport.country_iso2.is_not(None),
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def load_country_hubs(db: AsyncSession) -> dict[str, list[str]]:
    result = await db.execute(
        select(
            CountryHubAirport.country_iso2,
            CountryHubAirport.iata,
            CountryHubAirport.rank,
        ).order_by(
            CountryHubAirport.country_iso2,
            CountryHubAirport.rank,
        )
    )
    hubs: dict[str, list[str]] = {}
    for country_iso2, iata, _rank in result.all():
        hubs.setdefault(country_iso2, []).append(iata)
    return hubs


async def probe_destinations(
    origin_iatas: list[str],
    active_dest_iso2: set[str],
    country_hubs: dict[str, list[str]],
    probe_fn: Callable[[str, str], Awaitable[bool]],
    max_concurrent: int,
    delay_ms: int,
) -> dict[str, bool]:
    """Проверяет прямые рейсы origin -> hub каждой страны назначения."""
    if not origin_iatas:
        return {iso2: False for iso2 in active_dest_iso2}

    semaphore = asyncio.Semaphore(max_concurrent)
    results: dict[str, bool] = {iso2: False for iso2 in active_dest_iso2}

    async def _check_country(dest_iso2: str) -> None:
        hubs = country_hubs.get(dest_iso2, [])
        if not hubs:
            return
        for origin in origin_iatas:
            for hub in hubs:
                async with semaphore:
                    try:
                        if await probe_fn(origin, hub):
                            results[dest_iso2] = True
                            return
                    except Exception as exc:
                        logger.warning(
                            "Probe failed %s -> %s (%s): %s",
                            origin,
                            hub,
                            dest_iso2,
                            exc,
                        )
                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000)

    await asyncio.gather(*(_check_country(iso2) for iso2 in active_dest_iso2))
    return results

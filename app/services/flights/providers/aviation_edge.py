import asyncio
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.flights.providers.probe_helpers import load_iata_to_country

logger = logging.getLogger(__name__)

_BASE_URL = "https://aviation-edge.com/v2/public/routes"


class AviationEdgeProvider:
    source = "aviation_edge"

    async def fetch_direct_countries(
        self,
        db: AsyncSession,
        origin_iatas: list[str],
        active_dest_iso2: set[str],
    ) -> dict[str, bool]:
        api_key = (settings.aviation_edge_api_key or "").strip()
        if not api_key:
            raise RuntimeError("AVIATION_EDGE_API_KEY не задан")

        iata_to_country = await load_iata_to_country(db)
        direct: set[str] = set()
        timeout = settings.aviation_edge_request_timeout_seconds
        semaphore = asyncio.Semaphore(settings.aviation_edge_max_concurrent)

        async with httpx.AsyncClient(timeout=timeout) as client:

            async def _fetch_origin(origin: str) -> None:
                async with semaphore:
                    try:
                        response = await client.get(
                            _BASE_URL,
                            params={
                                "key": api_key,
                                "departureIata": origin,
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()
                    except httpx.HTTPError as exc:
                        logger.warning(
                            "Aviation Edge request failed for %s: %s",
                            origin,
                            exc,
                        )
                        return

                if not isinstance(payload, list):
                    return
                for route in payload:
                    if not isinstance(route, dict):
                        continue
                    arrival = route.get("arrivalIata")
                    if not isinstance(arrival, str):
                        continue
                    dest_iso2 = iata_to_country.get(arrival.upper())
                    if dest_iso2 in active_dest_iso2:
                        direct.add(dest_iso2)

            await asyncio.gather(*(_fetch_origin(iata) for iata in origin_iatas))

        return {iso2: iso2 in direct for iso2 in active_dest_iso2}

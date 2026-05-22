import asyncio
import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.flights.providers.probe_helpers import (
    load_country_hubs,
    probe_destinations,
)

logger = logging.getLogger(__name__)

_IGNAV_URL = "https://ignav.com/api/fares/one-way"


class IgnavProvider:
    source = "ignav"

    async def fetch_direct_countries(
        self,
        db: AsyncSession,
        origin_iatas: list[str],
        active_dest_iso2: set[str],
    ) -> dict[str, bool]:
        api_key = (settings.ignav_api_key or "").strip()
        if not api_key:
            raise RuntimeError("IGNAV_API_KEY не задан")

        country_hubs = await load_country_hubs(db)
        departure_date = (
            date.today() + timedelta(days=settings.flights_probe_date_offset_days)
        ).isoformat()
        timeout = settings.ignav_request_timeout_seconds

        async with httpx.AsyncClient(timeout=timeout) as client:

            async def _probe(origin: str, destination: str) -> bool:
                response = await client.post(
                    _IGNAV_URL,
                    headers={
                        "X-Api-Key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_date,
                        "max_stops": 0,
                    },
                )
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                data = response.json()
                itineraries = data.get("itineraries")
                return isinstance(itineraries, list) and len(itineraries) > 0

            return await probe_destinations(
                origin_iatas=origin_iatas,
                active_dest_iso2=active_dest_iso2,
                country_hubs=country_hubs,
                probe_fn=_probe,
                max_concurrent=settings.flights_probe_max_concurrent,
                delay_ms=settings.flights_probe_delay_ms,
            )

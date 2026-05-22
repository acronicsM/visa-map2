from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.flights.providers.aviation_edge import AviationEdgeProvider
from app.services.flights.providers.base import DirectFlightProvider
from app.services.flights.providers.ignav import IgnavProvider
from app.services.flights.providers.openflights import OpenFlightsProvider

_PROVIDERS: dict[str, DirectFlightProvider] = {
    "openflights": OpenFlightsProvider(),
    "aviation_edge": AviationEdgeProvider(),
    "ignav": IgnavProvider(),
}


def get_flight_provider(source: str | None = None) -> DirectFlightProvider:
    key = (source or settings.flights_data_source).strip().lower()
    provider = _PROVIDERS.get(key)
    if provider is None:
        allowed = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"Неизвестный flights_data_source: {key}. Допустимо: {allowed}")
    return provider

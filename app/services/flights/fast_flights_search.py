import asyncio
import logging
import sys
from dataclasses import asdict
from datetime import date, timedelta
from typing import Callable, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.fast_flights_search import (
    FastFlightsFlightItem,
    FastFlightsOriginInput,
    FastFlightsOriginResolved,
    FastFlightsRouteResult,
    FastFlightsSearchResult,
)
from app.services.flight_service import CityNotFoundError
from app.services.flights.city_resolution import lookup_origin_iatas
from app.services.flights.providers.probe_helpers import load_country_hubs

logger = logging.getLogger(__name__)

SeatType = Literal["economy", "premium-economy", "business", "first"]

_NOISY_LOGGERS = (
    "primp",
    "primp.impersonate",
    "httpx",
    "httpcore",
    "hpack",
    "fast_flights",
)


class RouteProgress:
    """Простой progress bar в stderr (без доп. зависимостей)."""

    def __init__(self, total: int, *, width: int = 40) -> None:
        self.total = max(total, 1)
        self.width = width
        self.current = 0

    def update(self, label: str = "") -> None:
        self.current += 1
        ratio = min(self.current / self.total, 1.0)
        filled = int(self.width * ratio)
        bar = "#" * filled + "-" * (self.width - filled)
        suffix = f" {label}" if label else ""
        line = f"\r[{bar}] {self.current}/{self.total}{suffix}"
        sys.stderr.write(line[:140].ljust(140))
        sys.stderr.flush()

    def finish(self) -> None:
        sys.stderr.write("\n")
        sys.stderr.flush()


def configure_quiet_fast_flights_logging(script_logger: logging.Logger) -> None:
    """Гасит INFO-логи primp/httpx (response: https://...) и оставляет логи скрипта."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    script_logger.setLevel(logging.INFO)
    if not script_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        script_logger.addHandler(handler)
    script_logger.propagate = False


def default_departure_date() -> str:
    return (
        date.today() + timedelta(days=settings.flights_probe_date_offset_days)
    ).isoformat()


def parse_origin_arg(value: str) -> FastFlightsOriginInput:
    """Парсит 'Samara,RU', 'Saint Petersburg,RU' или 'Nizhny Novgorod|RU'."""
    for separator in (",", "|"):
        if separator in value:
            city, iso2 = value.rsplit(separator, 1)
            city = city.strip()
            iso2 = iso2.strip().upper()
            if not city:
                raise ValueError("Название города отправления не может быть пустым")
            if len(iso2) != 2:
                raise ValueError(
                    f"ISO2 страны должен быть из 2 букв, получено: {iso2!r}"
                )
            return FastFlightsOriginInput(city=city, country_iso2=iso2)

    raise ValueError(
        f"Неверный формат origin '{value}'. "
        "Ожидается CITY,ISO2 или CITY|ISO2 (напр. \"Nizhny Novgorod,RU\")"
    )


def build_origin_inputs(
    *,
    origin_values: list[str] | None = None,
    origin_cities: list[str] | None = None,
    origin_countries: list[str] | None = None,
) -> list[FastFlightsOriginInput]:
    origins: list[FastFlightsOriginInput] = []

    for value in origin_values or []:
        origins.append(parse_origin_arg(value))

    cities = [city.strip() for city in (origin_cities or []) if city.strip()]
    countries = [
        country.strip().upper()
        for country in (origin_countries or [])
        if country.strip()
    ]

    if cities:
        if not countries:
            raise ValueError(
                "Для --origin-city укажите --origin-country (напр. RU)"
            )
        if len(countries) == 1 and len(cities) > 1:
            countries = countries * len(cities)
        if len(countries) != len(cities):
            raise ValueError(
                "Число --origin-city и --origin-country должно совпадать "
                f"(городов: {len(cities)}, стран: {len(countries)})"
            )
        for city, iso2 in zip(cities, countries, strict=True):
            if len(iso2) != 2:
                raise ValueError(f"ISO2 страны должен быть из 2 букв: {iso2!r}")
            origins.append(FastFlightsOriginInput(city=city, country_iso2=iso2))

    if not origins:
        raise ValueError(
            "Укажите хотя бы один город отправления через --origin CITY,ISO2 "
            'или --origin-city "Nizhny Novgorod" --origin-country RU'
        )

    return origins


async def resolve_origins(
    db: AsyncSession,
    origins: list[FastFlightsOriginInput],
) -> list[FastFlightsOriginResolved]:
    resolved: list[FastFlightsOriginResolved] = []
    for origin in origins:
        iatas, matched_norm = await lookup_origin_iatas(
            db,
            origin.city,
            origin.country_iso2,
        )
        if not iatas:
            raise CityNotFoundError(
                f"Аэропорты для города '{origin.city}' ({origin.country_iso2}) "
                "не найдены. Проверьте написание или загрузите OpenFlights."
            )
        resolved.append(
            FastFlightsOriginResolved(
                city=origin.city.strip(),
                country_iso2=origin.country_iso2.upper(),
                airports=iatas,
                matched_city_normalized=matched_norm,
            )
        )
    return resolved


def _serialize_flight(flight) -> FastFlightsFlightItem:
    return FastFlightsFlightItem(
        is_best=bool(flight.is_best),
        name=str(flight.name),
        departure=str(flight.departure),
        arrival=str(flight.arrival),
        arrival_time_ahead=str(flight.arrival_time_ahead),
        duration=str(flight.duration),
        stops=int(flight.stops),
        delay=flight.delay,
        price=str(flight.price),
    )


def _search_route_sync(
    *,
    origin_iata: str,
    dest_iata: str,
    departure_date: str,
    seat: SeatType,
    max_stops: int | None,
):
    from fast_flights import FlightData, Passengers, get_flights

    return get_flights(
        flight_data=[
            FlightData(
                date=departure_date,
                from_airport=origin_iata,
                to_airport=dest_iata,
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=1),
        seat=seat,
        max_stops=max_stops,
    )


async def search_flights_to_country(
    db: AsyncSession,
    *,
    origins: list[FastFlightsOriginInput],
    dest_country_iso2: str,
    departure_date: str | None = None,
    max_stops: int | None = 0,
    seat: SeatType = "economy",
    show_progress: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> FastFlightsSearchResult:
    dest_iso2 = dest_country_iso2.strip().upper()
    if len(dest_iso2) != 2:
        raise ValueError(f"dest_country_iso2 должен быть ISO2, получено: {dest_iso2!r}")

    travel_date = departure_date or default_departure_date()
    resolved_origins = await resolve_origins(db, origins)
    country_hubs = await load_country_hubs(db)
    dest_hubs = country_hubs.get(dest_iso2, [])
    if not dest_hubs:
        raise ValueError(
            f"Hub-аэропорты для страны {dest_iso2} не найдены. "
            "Выполните import_openflights_data.py."
        )

    routes: list[FastFlightsRouteResult] = []
    total_flights = 0

    route_tasks: list[tuple[FastFlightsOriginResolved, str, str]] = []
    for origin in resolved_origins:
        for origin_iata in origin.airports:
            for dest_iata in dest_hubs:
                route_tasks.append((origin, origin_iata, dest_iata))

    progress = RouteProgress(len(route_tasks)) if show_progress else None

    for origin, origin_iata, dest_iata in route_tasks:
        route_label = f"{origin_iata}->{dest_iata}"
        if progress is not None:
            progress.update(route_label)
        elif progress_callback is not None:
            progress_callback(route_label)

        route = FastFlightsRouteResult(
            origin_city=origin.city,
            origin_country_iso2=origin.country_iso2,
            origin_iata=origin_iata,
            dest_iata=dest_iata,
            dest_country_iso2=dest_iso2,
            status="error",
        )
        try:
            result = await asyncio.to_thread(
                _search_route_sync,
                origin_iata=origin_iata,
                dest_iata=dest_iata,
                departure_date=travel_date,
                seat=seat,
                max_stops=max_stops,
            )
        except RuntimeError as exc:
            route.status = "no_flights"
            route.error = str(exc)
            routes.append(route)
            continue
        except Exception as exc:
            logger.warning(
                "fast-flights search failed %s -> %s: %s",
                origin_iata,
                dest_iata,
                exc,
            )
            route.status = "error"
            route.error = str(exc)
            routes.append(route)
            continue

        flights = [_serialize_flight(flight) for flight in result.flights]
        if max_stops == 0:
            flights = [f for f in flights if f.stops == 0]

        if not flights:
            route.status = "no_flights"
            route.error = "Рейсы не найдены"
        else:
            route.status = "ok"
            route.current_price = str(result.current_price)
            route.flights = flights
            total_flights += len(flights)

        routes.append(route)

    if progress is not None:
        progress.finish()

    routes_with_flights = sum(1 for route in routes if route.status == "ok")

    return FastFlightsSearchResult(
        search={
            "departure_date": travel_date,
            "dest_country_iso2": dest_iso2,
            "destination_hubs": dest_hubs,
            "max_stops": max_stops,
            "seat": seat,
            "origins": [
                {
                    "city": origin.city,
                    "country_iso2": origin.country_iso2,
                    "airports": origin.airports,
                    **(
                        {"matched_city_normalized": origin.matched_city_normalized}
                        if origin.matched_city_normalized
                        else {}
                    ),
                }
                for origin in resolved_origins
            ],
        },
        routes=routes,
        summary={
            "routes_searched": len(routes),
            "routes_with_flights": routes_with_flights,
            "total_flights": total_flights,
        },
    )


def flight_to_dict(flight: FastFlightsFlightItem) -> dict:
    return asdict(flight)

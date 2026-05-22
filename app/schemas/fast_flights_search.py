from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class FastFlightsOriginInput:
    city: str
    country_iso2: str


@dataclass
class FastFlightsOriginResolved:
    city: str
    country_iso2: str
    airports: list[str]
    matched_city_normalized: str | None = None


@dataclass
class FastFlightsFlightItem:
    is_best: bool
    name: str
    departure: str
    arrival: str
    arrival_time_ahead: str
    duration: str
    stops: int
    delay: str | None
    price: str


@dataclass
class FastFlightsRouteResult:
    origin_city: str
    origin_country_iso2: str
    origin_iata: str
    dest_iata: str
    dest_country_iso2: str
    status: Literal["ok", "no_flights", "error"]
    current_price: str | None = None
    flights: list[FastFlightsFlightItem] = field(default_factory=list)
    error: str | None = None


@dataclass
class FastFlightsSearchResult:
    search: dict[str, Any]
    routes: list[FastFlightsRouteResult]
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "search": self.search,
            "routes": [asdict(route) for route in self.routes],
            "summary": self.summary,
        }

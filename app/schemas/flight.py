from datetime import datetime

from pydantic import BaseModel


class FlightOriginInfo(BaseModel):
    city: str
    country_iso2: str
    airports: list[str]


class DirectCountriesResponse(BaseModel):
    origin: FlightOriginInfo
    direct_countries: dict[str, bool]
    source: str
    cached: bool
    fetched_at: datetime
    expires_at: datetime


class FlightCityStatsItem(BaseModel):
    city_key: str
    city: str
    country_iso2: str
    request_count: int
    last_requested_at: datetime


class FlightCityStatsResponse(BaseModel):
    items: list[FlightCityStatsItem]


class FlightOpenFlightsImportResponse(BaseModel):
    airports_upserted: int
    routes_upserted: int
    hub_airports_upserted: int


class DepartureCityItem(BaseModel):
    city: str
    city_normalized: str
    airports: list[str]


class DepartureCitiesResponse(BaseModel):
    country_iso2: str
    items: list[DepartureCityItem]

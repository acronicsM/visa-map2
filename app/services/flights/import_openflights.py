import csv
import io
import logging
from collections import defaultdict
from pathlib import Path

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.country import Country
from app.models.flight import Airport, CountryHubAirport, FlightRoute
from app.services.flights.utils import normalize_city_name

logger = logging.getLogger(__name__)

_OPENFLIGHTS_BASE = (
    "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
)
_FILES = ("countries.dat", "airports.dat", "routes.dat")
_BATCH_SIZE = 1000


def _null(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text == "\\N":
        return None
    return text


def _parse_float(value: str | None) -> float | None:
    text = _null(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    text = _null(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


async def _load_text(path: Path, filename: str) -> str:
    local = path / filename
    if local.exists():
        logger.info("Reading %s from %s", filename, local)
        return local.read_text(encoding="utf-8")

    url = f"{_OPENFLIGHTS_BASE}/{filename}"
    logger.info("Downloading %s", url)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        path.mkdir(parents=True, exist_ok=True)
        local.write_text(response.text, encoding="utf-8")
        return response.text


def _parse_countries(text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 3:
            continue
        name = _null(row[1])
        iso2 = _null(row[2])
        if name and iso2 and len(iso2) == 2:
            mapping[name.lower()] = iso2.upper()
    return mapping


async def _load_country_fallbacks(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(
        select(Country.name_en, Country.iso2).where(Country.is_active.is_(True))
    )
    mapping = {name.lower(): iso2 for name, iso2 in result.all()}
    result_ru = await db.execute(
        select(Country.name_ru, Country.iso2).where(Country.is_active.is_(True))
    )
    for name, iso2 in result_ru.all():
        mapping[name.lower()] = iso2
    return mapping


def _resolve_country_iso2(
    country_name: str | None,
    openflights_map: dict[str, str],
    fallback_map: dict[str, str],
) -> str | None:
    if not country_name:
        return None
    key = country_name.strip().lower()
    return openflights_map.get(key) or fallback_map.get(key)


async def import_openflights_data(db: AsyncSession) -> dict[str, int]:
    data_dir = Path(settings.openflights_data_dir)
    countries_text = await _load_text(data_dir, "countries.dat")
    airports_text = await _load_text(data_dir, "airports.dat")
    routes_text = await _load_text(data_dir, "routes.dat")

    openflights_countries = _parse_countries(countries_text)
    country_fallback = await _load_country_fallbacks(db)

    await db.execute(delete(Airport))
    await db.execute(delete(FlightRoute))
    await db.execute(delete(CountryHubAirport))

    airports_upserted = 0
    airport_batch: list[dict] = []

    reader = csv.reader(io.StringIO(airports_text))
    for row in reader:
        if len(row) < 8:
            continue
        iata = _null(row[4])
        if not iata or len(iata) != 3:
            continue
        country_name = _null(row[3]) or ""
        country_iso2 = _resolve_country_iso2(
            country_name,
            openflights_countries,
            country_fallback,
        )
        city = _null(row[2]) or country_name or iata
        airport_batch.append(
            {
                "openflights_id": _parse_int(row[0]),
                "iata": iata.upper(),
                "icao": (_null(row[5]) or "")[:4] or None,
                "name": (_null(row[1]) or iata)[:255],
                "city": city[:100],
                "city_normalized": normalize_city_name(city)[:100],
                "country_name": country_name[:100] if country_name else None,
                "country_iso2": country_iso2,
                "latitude": _parse_float(row[6]),
                "longitude": _parse_float(row[7]),
                "is_active": True,
            }
        )

        if len(airport_batch) >= _BATCH_SIZE:
            airports_upserted += await _insert_airports(db, airport_batch)
            airport_batch.clear()

    if airport_batch:
        airports_upserted += await _insert_airports(db, airport_batch)

    routes_upserted = 0
    route_batch: list[dict] = []
    route_reader = csv.reader(io.StringIO(routes_text))
    for row in route_reader:
        if len(row) < 8:
            continue
        source_iata = _null(row[2])
        dest_iata = _null(row[4])
        if not source_iata or not dest_iata:
            continue
        if len(source_iata) != 3 or len(dest_iata) != 3:
            continue
        stops = _parse_int(row[7]) or 0
        codeshare = (_null(row[6]) or "").upper() == "Y"
        route_batch.append(
            {
                "source_iata": source_iata.upper(),
                "dest_iata": dest_iata.upper(),
                "airline": (_null(row[0]) or "")[:10] or None,
                "stops": stops,
                "is_codeshare": codeshare,
            }
        )
        if len(route_batch) >= _BATCH_SIZE:
            routes_upserted += await _insert_routes(db, route_batch)
            route_batch.clear()

    if route_batch:
        routes_upserted += await _insert_routes(db, route_batch)

    hub_upserted = await _rebuild_country_hubs(db)
    await db.commit()

    return {
        "airports_upserted": airports_upserted,
        "routes_upserted": routes_upserted,
        "hub_airports_upserted": hub_upserted,
    }


async def _insert_airports(db: AsyncSession, batch: list[dict]) -> int:
    await db.execute(insert(Airport).values(batch))
    await db.flush()
    return len(batch)


async def _insert_routes(db: AsyncSession, batch: list[dict]) -> int:
    await db.execute(insert(FlightRoute).values(batch))
    await db.flush()
    return len(batch)


async def _rebuild_country_hubs(db: AsyncSession) -> int:
    await db.execute(delete(CountryHubAirport))

    stmt = (
        select(
            Airport.country_iso2,
            Airport.iata,
            func.count(FlightRoute.id).label("route_count"),
        )
        .join(FlightRoute, FlightRoute.source_iata == Airport.iata)
        .where(
            Airport.country_iso2.is_not(None),
            Airport.iata.is_not(None),
        )
        .group_by(Airport.country_iso2, Airport.iata)
    )
    result = await db.execute(stmt)
    by_country: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for country_iso2, iata, route_count in result.all():
        by_country[country_iso2].append((iata, int(route_count)))

    hub_rows: list[dict] = []
    for country_iso2, airports in by_country.items():
        ranked = sorted(airports, key=lambda item: item[1], reverse=True)[:3]
        for rank, (iata, route_count) in enumerate(ranked, start=1):
            hub_rows.append(
                {
                    "country_iso2": country_iso2,
                    "iata": iata,
                    "route_count": route_count,
                    "rank": rank,
                }
            )

    if not hub_rows:
        return 0

    await db.execute(insert(CountryHubAirport).values(hub_rows))
    await db.flush()
    return len(hub_rows)

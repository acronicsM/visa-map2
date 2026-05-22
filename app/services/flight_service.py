import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import (
    FLIGHTS_DIRECT_KEY,
    cache_get,
    cache_set,
)
from app.config import settings
from app.models.flight import FlightCityRequestStats, FlightDirectCache
from app.services.flights.providers.factory import get_flight_provider
from app.services.flights.providers.openflights import get_active_country_iso2
from app.services.flights.utils import build_city_key
from app.services.flights.city_resolution import lookup_origin_iatas
from app.schemas.flight import (
    DirectCountriesResponse,
    FlightCityStatsItem,
    FlightCityStatsResponse,
    FlightOriginInfo,
)

logger = logging.getLogger(__name__)


class CityNotFoundError(LookupError):
    pass


async def resolve_origin_airports(
    db: AsyncSession,
    city: str,
    country_iso2: str,
) -> tuple[str, list[str]]:
    iso2 = country_iso2.strip().upper()
    iatas, _matched = await lookup_origin_iatas(db, city, iso2)
    if not iatas:
        raise CityNotFoundError(
            f"Аэропорты для города '{city}' ({iso2}) не найдены. "
            "Проверьте написание на латинице или загрузите данные OpenFlights. "
            "Для городов из нескольких слов используйте кавычки: "
            "\"Nizhny Novgorod,RU\" или --origin-city \"Nizhny Novgorod\" --origin-country RU."
        )
    return build_city_key(city, iso2), iatas


def _cache_ttl() -> int:
    return settings.flights_cache_ttl_seconds


def _expires_at(now: datetime | None = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    return base + timedelta(seconds=_cache_ttl())


def _response_from_cache_row(
    row: FlightDirectCache,
    *,
    cached: bool,
) -> DirectCountriesResponse:
    return DirectCountriesResponse(
        origin=FlightOriginInfo(
            city=row.city,
            country_iso2=row.country_iso2,
            airports=list(row.origin_airports),
        ),
        direct_countries=dict(row.direct_countries),
        source=row.source,
        cached=cached,
        fetched_at=row.fetched_at,
        expires_at=row.expires_at,
    )


def _response_from_redis_payload(payload: dict) -> DirectCountriesResponse:
    origin = payload["origin"]
    return DirectCountriesResponse(
        origin=FlightOriginInfo.model_validate(origin),
        direct_countries=dict(payload["direct_countries"]),
        source=payload["source"],
        cached=True,
        fetched_at=datetime.fromisoformat(payload["fetched_at"]),
        expires_at=datetime.fromisoformat(payload["expires_at"]),
    )


def _redis_payload(response: DirectCountriesResponse) -> dict:
    return {
        "origin": response.origin.model_dump(),
        "direct_countries": response.direct_countries,
        "source": response.source,
        "fetched_at": response.fetched_at.isoformat(),
        "expires_at": response.expires_at.isoformat(),
    }


async def _load_pg_cache(
    db: AsyncSession,
    city_key: str,
    source: str,
) -> FlightDirectCache | None:
    result = await db.execute(
        select(FlightDirectCache).where(
            FlightDirectCache.city_key == city_key,
            FlightDirectCache.source == source,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


async def _save_cache(
    db: AsyncSession,
    *,
    city_key: str,
    city: str,
    country_iso2: str,
    origin_airports: list[str],
    direct_countries: dict[str, bool],
    source: str,
    fetched_at: datetime,
    expires_at: datetime,
) -> DirectCountriesResponse:
    stmt = insert(FlightDirectCache).values(
        city_key=city_key,
        source=source,
        city=city,
        country_iso2=country_iso2,
        origin_airports=origin_airports,
        direct_countries=direct_countries,
        fetched_at=fetched_at,
        expires_at=expires_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[FlightDirectCache.city_key, FlightDirectCache.source],
        set_={
            "city": city,
            "country_iso2": country_iso2,
            "origin_airports": origin_airports,
            "direct_countries": direct_countries,
            "fetched_at": fetched_at,
            "expires_at": expires_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

    response = DirectCountriesResponse(
        origin=FlightOriginInfo(
            city=city,
            country_iso2=country_iso2,
            airports=origin_airports,
        ),
        direct_countries=direct_countries,
        source=source,
        cached=False,
        fetched_at=fetched_at,
        expires_at=expires_at,
    )
    redis_key = FLIGHTS_DIRECT_KEY.format(city_key=city_key, source=source)
    ttl = max(int((expires_at - fetched_at).total_seconds()), 1)
    await cache_set(redis_key, _redis_payload(response), ttl)
    return response


async def _increment_stats(
    db: AsyncSession,
    *,
    city_key: str,
    city: str,
    country_iso2: str,
) -> None:
    now = datetime.now(timezone.utc)
    stmt = insert(FlightCityRequestStats).values(
        city_key=city_key,
        city=city,
        country_iso2=country_iso2,
        request_count=1,
        last_requested_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[FlightCityRequestStats.city_key],
        set_={
            "request_count": FlightCityRequestStats.request_count + 1,
            "last_requested_at": now,
            "city": city,
            "country_iso2": country_iso2,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def fetch_and_cache_direct_countries(
    db: AsyncSession,
    *,
    city: str,
    country_iso2: str,
    city_key: str | None = None,
    origin_airports: list[str] | None = None,
    source: str | None = None,
) -> DirectCountriesResponse:
    iso2 = country_iso2.strip().upper()
    if city_key is None or origin_airports is None:
        city_key, origin_airports = await resolve_origin_airports(db, city, iso2)

    provider = get_flight_provider(source)
    active_dest = await get_active_country_iso2(db)
    direct_countries = await provider.fetch_direct_countries(
        db,
        origin_airports,
        active_dest,
    )

    fetched_at = datetime.now(timezone.utc)
    expires_at = _expires_at(fetched_at)
    return await _save_cache(
        db,
        city_key=city_key,
        city=city.strip(),
        country_iso2=iso2,
        origin_airports=origin_airports,
        direct_countries=direct_countries,
        source=provider.source,
        fetched_at=fetched_at,
        expires_at=expires_at,
    )


async def get_direct_countries(
    db: AsyncSession,
    city: str,
    country_iso2: str,
) -> DirectCountriesResponse:
    iso2 = country_iso2.strip().upper()
    city_key, origin_airports = await resolve_origin_airports(db, city, iso2)
    provider = get_flight_provider()
    source = provider.source

    redis_key = FLIGHTS_DIRECT_KEY.format(city_key=city_key, source=source)
    cached_payload = await cache_get(redis_key)
    if isinstance(cached_payload, dict) and cached_payload.get("direct_countries"):
        response = _response_from_redis_payload(cached_payload)
        await _increment_stats(
            db,
            city_key=city_key,
            city=city.strip(),
            country_iso2=iso2,
        )
        return response

    pg_row = await _load_pg_cache(db, city_key, source)
    if pg_row is not None:
        response = _response_from_cache_row(pg_row, cached=True)
        ttl = max(
            int((pg_row.expires_at - datetime.now(timezone.utc)).total_seconds()),
            1,
        )
        await cache_set(redis_key, _redis_payload(response), ttl)
        await _increment_stats(
            db,
            city_key=city_key,
            city=city.strip(),
            country_iso2=iso2,
        )
        return response

    response = await fetch_and_cache_direct_countries(
        db,
        city=city,
        country_iso2=iso2,
        city_key=city_key,
        origin_airports=origin_airports,
        source=source,
    )
    await _increment_stats(
        db,
        city_key=city_key,
        city=city.strip(),
        country_iso2=iso2,
    )
    return response


async def refresh_direct_countries(
    db: AsyncSession,
    city_key: str,
    source: str | None = None,
) -> DirectCountriesResponse | None:
    provider_source = (source or settings.flights_data_source).strip().lower()
    stats_result = await db.execute(
        select(FlightCityRequestStats).where(
            FlightCityRequestStats.city_key == city_key
        )
    )
    stats = stats_result.scalar_one_or_none()
    if stats is None:
        cache_result = await db.execute(
            select(FlightDirectCache).where(
                FlightDirectCache.city_key == city_key,
                FlightDirectCache.source == provider_source,
            )
        )
        cache_row = cache_result.scalar_one_or_none()
        if cache_row is None:
            return None
        city = cache_row.city
        country_iso2 = cache_row.country_iso2
    else:
        city = stats.city
        country_iso2 = stats.country_iso2

    try:
        return await fetch_and_cache_direct_countries(
            db,
            city=city,
            country_iso2=country_iso2,
            city_key=city_key,
            source=provider_source,
        )
    except Exception as exc:
        logger.warning("Background refresh failed for %s: %s", city_key, exc)
        return None


async def list_cities_for_refresh(
    db: AsyncSession,
    source: str | None = None,
    batch_size: int | None = None,
) -> list[str]:
    threshold = datetime.now(timezone.utc) + timedelta(
        seconds=settings.flights_refresh_lead_seconds
    )
    provider_source = (source or settings.flights_data_source).strip().lower()
    limit = batch_size or settings.flights_refresh_batch_size
    stmt = (
        select(FlightCityRequestStats.city_key)
        .join(
            FlightDirectCache,
            (FlightDirectCache.city_key == FlightCityRequestStats.city_key)
            & (FlightDirectCache.source == provider_source),
        )
        .where(
            FlightCityRequestStats.request_count
            >= settings.flights_refresh_min_requests,
            FlightDirectCache.expires_at <= threshold,
        )
        .order_by(FlightCityRequestStats.request_count.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def get_flight_city_stats(
    db: AsyncSession,
    limit: int = 50,
) -> FlightCityStatsResponse:
    result = await db.execute(
        select(FlightCityRequestStats)
        .order_by(FlightCityRequestStats.request_count.desc())
        .limit(limit)
    )
    items = [
        FlightCityStatsItem(
            city_key=row.city_key,
            city=row.city,
            country_iso2=row.country_iso2,
            request_count=row.request_count,
            last_requested_at=row.last_requested_at,
        )
        for row in result.scalars().all()
    ]
    return FlightCityStatsResponse(items=items)

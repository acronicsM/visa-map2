import logging
from difflib import SequenceMatcher

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flight import Airport
from app.services.flights.utils import normalize_city_name

logger = logging.getLogger(__name__)

FUZZY_CITY_MATCH_CUTOFF = 0.85


def best_city_normalized_match(query: str, candidates: list[str]) -> str | None:
    """Находит ближайшее название города (Nizhny vs Nizhniy и т.п.)."""
    if not candidates:
        return None
    if query in candidates:
        return query

    best_ratio = 0.0
    best_candidate: str | None = None
    for candidate in candidates:
        ratio = SequenceMatcher(None, query, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = candidate

    if best_candidate and best_ratio >= FUZZY_CITY_MATCH_CUTOFF:
        return best_candidate
    return None


async def lookup_origin_iatas(
    db: AsyncSession,
    city: str,
    country_iso2: str,
) -> tuple[list[str], str | None]:
    """
    Ищет IATA аэропортов города в стране.
    Возвращает (iata_codes, matched_city_normalized или None при exact match).
    """
    iso2 = country_iso2.strip().upper()
    city_norm = normalize_city_name(city)

    iatas = await _iatas_for_city_norm(db, iso2, city_norm)
    if iatas:
        return iatas, None

    candidates_result = await db.execute(
        select(distinct(Airport.city_normalized)).where(
            Airport.country_iso2 == iso2,
            Airport.city_normalized.is_not(None),
            Airport.iata.is_not(None),
            Airport.is_active.is_(True),
        )
    )
    candidates = [row[0] for row in candidates_result.all() if row[0]]
    matched = best_city_normalized_match(city_norm, candidates)
    if matched is None:
        return [], None

    iatas = await _iatas_for_city_norm(db, iso2, matched)
    if iatas:
        logger.info(
            "Город '%s' сопоставлен с '%s' (%s)",
            city,
            matched,
            iso2,
        )
    return iatas, matched


async def _iatas_for_city_norm(
    db: AsyncSession,
    iso2: str,
    city_norm: str,
) -> list[str]:
    result = await db.execute(
        select(Airport.iata)
        .where(
            Airport.country_iso2 == iso2,
            Airport.city_normalized == city_norm,
            Airport.iata.is_not(None),
            Airport.is_active.is_(True),
        )
        .order_by(Airport.iata)
    )
    return sorted({row[0] for row in result.all() if row[0]})

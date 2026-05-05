import logging
from datetime import datetime, timezone

import httpx

from app.cache import FX_RATE_KEY, FX_RATE_TTL, cache_get, cache_set
from app.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_BUDGET_CURRENCIES: tuple[str, ...] = (
    "USD",
    "EUR",
    "RUB",
    "GBP",
    "CNY",
    "JPY",
    "TRY",
    "AED",
    "THB",
    "IDR",
    "INR",
    "KZT",
    "GEL",
    "AMD",
    "CAD",
    "AUD",
    "CHF",
)


def normalize_budget_currency(currency: str) -> str:
    code = currency.strip().upper()
    if code not in SUPPORTED_BUDGET_CURRENCIES:
        raise ValueError(f"Неподдерживаемая валюта бюджета: {currency}")
    return code


def default_budget_currency(home_currency: str | None) -> str:
    if not home_currency:
        return "USD"
    code = home_currency.strip().upper()
    return code if code in SUPPORTED_BUDGET_CURRENCIES else "USD"


async def get_usd_to_currency_rate(currency: str) -> float:
    """Курс USD -> currency. Для USD внешний запрос не нужен."""
    code = normalize_budget_currency(currency)
    if code == "USD":
        return 1.0

    cache_key = FX_RATE_KEY.format(currency=code)
    cached = await cache_get(cache_key)
    if isinstance(cached, dict):
        rate = _to_positive_float(cached.get("rate"))
        if rate is not None:
            return rate
    else:
        rate = _to_positive_float(cached)
        if rate is not None:
            return rate

    rate = await _fetch_usd_rate(code)
    await cache_set(
        cache_key,
        {
            "base": "USD",
            "currency": code,
            "rate": rate,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        },
        FX_RATE_TTL,
    )
    return rate


async def _fetch_usd_rate(currency: str) -> float:
    try:
        async with httpx.AsyncClient(
            timeout=settings.fx_request_timeout_seconds
        ) as client:
            response = await client.get(settings.fx_rates_url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("FX provider request failed: %s", exc)
        raise RuntimeError("Не удалось получить курс валют") from exc

    data = response.json()
    rates = data.get("rates")
    if not isinstance(rates, dict):
        raise RuntimeError("FX provider вернул ответ без rates")

    rate = _to_positive_float(rates.get(currency))
    if rate is None:
        raise RuntimeError(f"FX provider не вернул курс USD->{currency}")
    return rate


def _to_positive_float(value: object) -> float | None:
    try:
        rate = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if rate > 0:
        return rate
    return None

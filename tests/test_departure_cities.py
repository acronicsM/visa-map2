from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.flight import DepartureCitiesResponse, DepartureCityItem
from app.services.flights.departure_cities import _cache_key, get_departure_cities


def test_cache_key_international():
    assert _cache_key("ru", True) == "flights:departure_cities:RU:intl:v1"


def test_cache_key_all_airports():
    assert _cache_key("de", False) == "flights:departure_cities:DE:all:v1"


@pytest.mark.asyncio
async def test_get_departure_cities_cache_hit():
    cached_payload = {
        "country_iso2": "RU",
        "items": [
            {
                "city": "Moscow",
                "city_normalized": "moscow",
                "airports": ["SVO", "DME"],
            }
        ],
    }
    with patch(
        "app.services.flights.departure_cities.cache_get",
        new=AsyncMock(return_value=cached_payload),
    ) as cache_get:
        result = await get_departure_cities(AsyncMock(), "RU", international_only=True)

    cache_get.assert_awaited_once()
    assert result.country_iso2 == "RU"
    assert len(result.items) == 1
    assert result.items[0].city == "Moscow"


@pytest.mark.asyncio
async def test_get_departure_cities_loads_and_caches():
    items = [
        DepartureCityItem(
            city="Samara",
            city_normalized="samara",
            airports=["KUF"],
        )
    ]
    with (
        patch(
            "app.services.flights.departure_cities.cache_get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.flights.departure_cities.cache_set",
            new=AsyncMock(),
        ) as cache_set,
        patch(
            "app.services.flights.departure_cities._load_departure_cities",
            new=AsyncMock(return_value=items),
        ),
    ):
        result = await get_departure_cities(AsyncMock(), "RU", international_only=True)

    assert result.items[0].airports == ["KUF"]
    cache_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_departure_cities_invalid_iso2():
    with pytest.raises(ValueError):
        await get_departure_cities(AsyncMock(), "RUS", international_only=True)

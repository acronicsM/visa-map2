"""Тесты модуля прямых перелётов."""

import pytest

from app.services.flights.providers.factory import get_flight_provider
from app.services.flights.utils import build_city_key, normalize_city_name


def test_normalize_city_name_strips_and_lowercases() -> None:
    assert normalize_city_name("  Moscow  ") == "moscow"


def test_normalize_city_name_removes_accents() -> None:
    assert normalize_city_name("São Paulo") == "sao paulo"


def test_build_city_key() -> None:
    assert build_city_key("Moscow", "ru") == "moscow|RU"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("openflights", "openflights"),
        ("aviation_edge", "aviation_edge"),
        ("ignav", "ignav"),
    ],
)
def test_get_flight_provider(source: str, expected: str) -> None:
    provider = get_flight_provider(source)
    assert provider.source == expected


def test_get_flight_provider_unknown() -> None:
    with pytest.raises(ValueError, match="Неизвестный flights_data_source"):
        get_flight_provider("unknown")

"""Тесты fast-flights search (CLI-сервис)."""

import pytest

from app.services.flights.city_resolution import best_city_normalized_match
from app.services.flights.fast_flights_search import (
    RouteProgress,
    build_origin_inputs,
    parse_origin_arg,
)


def test_parse_origin_arg_simple() -> None:
    origin = parse_origin_arg("Samara,RU")
    assert origin.city == "Samara"
    assert origin.country_iso2 == "RU"


def test_parse_origin_arg_city_with_space() -> None:
    origin = parse_origin_arg("Saint Petersburg,RU")
    assert origin.city == "Saint Petersburg"
    assert origin.country_iso2 == "RU"


def test_parse_origin_arg_pipe_separator() -> None:
    origin = parse_origin_arg("Nizhny Novgorod|RU")
    assert origin.city == "Nizhny Novgorod"
    assert origin.country_iso2 == "RU"


def test_parse_origin_arg_invalid() -> None:
    with pytest.raises(ValueError, match="CITY,ISO2"):
        parse_origin_arg("Samara")


def test_build_origin_inputs_from_city_country() -> None:
    origins = build_origin_inputs(
        origin_cities=["Nizhny Novgorod", "Samara"],
        origin_countries=["RU"],
    )
    assert len(origins) == 2
    assert origins[0].city == "Nizhny Novgorod"
    assert origins[1].city == "Samara"


def test_best_city_normalized_match_nizhny() -> None:
    matched = best_city_normalized_match(
        "nizhny novgorod",
        ["nizhniy novgorod", "moscow"],
    )
    assert matched == "nizhniy novgorod"


def test_route_progress_updates() -> None:
    bar = RouteProgress(total=2, width=10)
    bar.update("GOJ->BKK")
    assert bar.current == 1
    bar.update("GOJ->HKT")
    assert bar.current == 2
    bar.finish()

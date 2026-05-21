"""Тесты vacation-fit: min–max + пороги 80/50/20."""

from app.services.vacation_fit_compute import (
    assign_vacation_fit_bands,
    compute_vacation_fit,
    normalize_scores_min_max,
)


def test_normalize_min_max_spread() -> None:
    raw = {"AA": 0.0, "BB": 50.0, "CC": 100.0}
    norm = normalize_scores_min_max(raw)
    assert norm["AA"] == 0.0
    assert norm["BB"] == 50.0
    assert norm["CC"] == 100.0


def test_all_zeros_unlikely() -> None:
    raw = {"ML": 0.0, "TG": 0.0, "AT": 73.6}
    bands = assign_vacation_fit_bands(raw)
    assert bands["ML"] == "unlikely"
    assert bands["TG"] == "unlikely"
    assert bands["AT"] == "excellent"


def test_compute_vacation_fit_ski_only() -> None:
    profiles = {
        "ML": {"beach": 0.0, "ski": 0.0, "food": 0.0, "natural": 0.0, "culture": 0.0},
        "AT": {"beach": 0.0, "ski": 0.736387, "food": 0.0, "natural": 0.0, "culture": 0.0},
    }
    weights = {"beach": 0, "ski": 6, "food": 0, "natural": 0, "culture": 0, "exotic": 0}
    scores, bands = compute_vacation_fit(profiles, {}, weights)
    assert scores["ML"] == 0.0
    assert scores["AT"] == 100.0
    assert bands["ML"] == "unlikely"
    assert bands["AT"] == "excellent"

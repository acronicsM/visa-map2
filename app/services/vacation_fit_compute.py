"""Чистые функции расчёта vacation-fit. Держать в синхроне с vacation-fit.ts."""

from __future__ import annotations

from typing import Literal

VacationDimensionKey = Literal[
    "beach", "ski", "food", "natural", "culture", "exotic"
]
VacationFitBandKey = Literal["excellent", "good", "doubtful", "unlikely"]

VACATION_FIT_BAND_THRESHOLDS: dict[str, float] = {
    "excellent": 80.0,
    "good": 50.0,
    "doubtful": 20.0,
}

_SCALAR_DIMS: tuple[VacationDimensionKey, ...] = (
    "beach",
    "ski",
    "food",
    "natural",
    "culture",
)

ProfileScalars = dict[str, float | None]


def _scalar_score(
    profiles: dict[str, ProfileScalars],
    dest_iso2: str,
    dim: VacationDimensionKey,
) -> float | None:
    row = profiles.get(dest_iso2)
    if not row:
        return None
    raw = row.get(dim)
    if raw is None:
        return None
    return float(raw) * 100.0


def compute_country_scores(
    profiles: dict[str, ProfileScalars],
    exotic_by_dest: dict[str, float],
    weights: dict[str, int],
) -> dict[str, float]:
    dest_keys: set[str] = set(profiles.keys()) | set(exotic_by_dest.keys())
    out: dict[str, float] = {}

    for dest in dest_keys:
        iso2 = dest.strip().upper()
        if len(iso2) != 2:
            continue

        weighted_sum = 0.0
        weight_sum = 0.0

        for dim in _SCALAR_DIMS:
            w = int(weights.get(dim, 0))
            if w <= 0:
                continue
            s = _scalar_score(profiles, iso2, dim)
            if s is None:
                continue
            weighted_sum += s * w
            weight_sum += w

        w_ex = int(weights.get("exotic", 0))
        if w_ex > 0:
            raw_ex = exotic_by_dest.get(iso2)
            if raw_ex is not None:
                weighted_sum += float(raw_ex) * 100.0 * w_ex
                weight_sum += w_ex

        if weight_sum > 0:
            out[iso2] = weighted_sum / weight_sum

    return out


def score_to_vacation_fit_band(index: float) -> VacationFitBandKey:
    if index >= VACATION_FIT_BAND_THRESHOLDS["excellent"]:
        return "excellent"
    if index >= VACATION_FIT_BAND_THRESHOLDS["good"]:
        return "good"
    if index >= VACATION_FIT_BAND_THRESHOLDS["doubtful"]:
        return "doubtful"
    return "unlikely"


def normalize_scores_min_max(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}

    values = list(scores.values())
    min_score = min(values)
    max_score = max(values)
    span = max_score - min_score

    out: dict[str, float] = {}
    for iso2, score in scores.items():
        if span <= 0:
            out[iso2] = 50.0 if min_score > 0 else 0.0
        else:
            out[iso2] = (score - min_score) / span * 100.0
    return out


def assign_vacation_fit_bands(scores: dict[str, float]) -> dict[str, VacationFitBandKey]:
    indices = normalize_scores_min_max(scores)
    return {iso2: score_to_vacation_fit_band(index) for iso2, index in indices.items()}


def compute_vacation_fit(
    profiles: dict[str, ProfileScalars],
    exotic_by_dest: dict[str, float],
    weights: dict[str, int],
) -> tuple[dict[str, float], dict[str, VacationFitBandKey]]:
    raw_scores = compute_country_scores(profiles, exotic_by_dest, weights)
    normalized = normalize_scores_min_max(raw_scores)
    bands = assign_vacation_fit_bands(raw_scores)
    return normalized, bands

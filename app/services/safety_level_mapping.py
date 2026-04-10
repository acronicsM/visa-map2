"""Перевод safety_final_score (0..100, выше — безопаснее) в safety_level для БД."""

from app.config import settings


def final_score_to_safety_level(score: float) -> str:
    """
    Уровни как в проекте: safe | unsafe | dangerous.

    Пороги задаются в Settings (safety_score_safe_min, safety_score_unsafe_min).
    """
    if score >= settings.safety_score_safe_min:
        return "safe"
    if score >= settings.safety_score_unsafe_min:
        return "unsafe"
    return "dangerous"

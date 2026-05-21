import re

from pydantic import BaseModel, ConfigDict, field_validator


class ExoticScoreEntry(BaseModel):
    iso2: str
    score: float

    @field_validator("iso2")
    @classmethod
    def validate_iso2(cls, v: str) -> str:
        code = v.strip().upper()
        if not re.match(r"^[A-Z]{2}$", code):
            raise ValueError(f"Некорректный iso2 в exotic_score: {v}")
        return code

    @field_validator("score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("score должен быть в диапазоне 0..1")
        return v


class CountryProfileEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beach_score: float | None = None
    ski_score: float | None = None
    food_score: float | None = None
    natural_score: float | None = None
    culture_score: float | None = None
    exotic_score: list[ExoticScoreEntry] = []

    @field_validator(
        "beach_score",
        "ski_score",
        "food_score",
        "natural_score",
        "culture_score",
    )
    @classmethod
    def scalar_score_in_range(cls, v: float | None) -> float | None:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("score должен быть в диапазоне 0..1")
        return v


class CountryProfileFile(BaseModel):
    countries: dict[str, CountryProfileEntry]


class CountryProfileUploadResponse(BaseModel):
    profiles_upserted: int
    exotic_rows_upserted: int

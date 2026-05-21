from pydantic import BaseModel, Field


class VacationProfileScalars(BaseModel):
    beach: float | None = None
    ski: float | None = None
    food: float | None = None
    natural: float | None = None
    culture: float | None = None


class VacationProfilesResponse(BaseModel):
    profiles: dict[str, VacationProfileScalars]


class VacationExoticResponse(BaseModel):
    home_iso2: str
    scores: dict[str, float] = Field(
        description="dest_iso2 -> exotic score (0..1)",
    )

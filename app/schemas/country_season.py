from pydantic import BaseModel, Field


class CountrySeasonItem(BaseModel):
    iso2: str = Field(min_length=2, max_length=2)
    month: int = Field(ge=1, le=12)
    season: str


class CountrySeasonMonthMeta(BaseModel):
    """Лёгкий ответ: список сезонов за месяц без GeoJSON (быстрее для фильтра на фронте)."""

    month: int = Field(ge=1, le=12)
    seasons: list[str]


class CountrySeasonGeoFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class CountrySeasonGeoResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[CountrySeasonGeoFeature]


class CountrySeasonByCountryResponse(BaseModel):
    """GeoJSON по стране: несколько полигонов на месяц/сезон допустимы."""

    iso2: str = Field(min_length=2, max_length=2)
    type: str = "FeatureCollection"
    features: list[CountrySeasonGeoFeature]

from pydantic import BaseModel, Field


class CountrySeasonItem(BaseModel):
    iso2: str = Field(min_length=2, max_length=2)
    month: int = Field(ge=1, le=12)
    season: str


class CountrySeasonGeoFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class CountrySeasonGeoResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[CountrySeasonGeoFeature]


class CountrySeasonByCountryResponse(BaseModel):
    iso2: str = Field(min_length=2, max_length=2)
    seasons: list[CountrySeasonItem]

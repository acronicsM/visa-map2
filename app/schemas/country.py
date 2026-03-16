from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class CountryBase(BaseModel):
    iso2: str
    iso3: str
    name_ru: str
    name_en: str
    name_native: str | None = None
    region: str | None = None
    subregion: str | None = None
    capital: str | None = None
    flag_emoji: str | None = None
    flag_svg_url: str | None = None
    is_active: bool = True


class CountryShort(BaseModel):
    """Для дропдауна — минимум полей"""
    iso2: str
    name_ru: str
    name_en: str
    flag_emoji: str | None = None
    region: str | None = None

    model_config = {"from_attributes": True}


class CountryDetail(CountryBase):
    """Полная карточка страны"""
    id: UUID
    numeric_code: int | None = None
    description_ru: str | None = None
    description_en: str | None = None
    bbox_min_lat: float | None = None
    bbox_max_lat: float | None = None
    bbox_min_lng: float | None = None
    bbox_max_lng: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
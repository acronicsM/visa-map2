from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class CurrencyInfo(BaseModel):
    """Одна валюта по данным restcountries (ISO 4217 — ключ родителя)."""

    name: str = ""
    symbol: str = ""


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
    primary_language: str | None = None
    official_language_codes: list[str] | None = None
    currency_codes: list[str] | None = None

    model_config = {"from_attributes": True}


class CountryNamesEntry(BaseModel):
    """Справочник имён для кешируемого API."""

    iso3: str
    name_en: str
    name_ru: str
    name_native: str | None = None
    name_translations: dict[str, str] | None = None
    currencies: dict[str, CurrencyInfo] | None = None


class CountryDetail(CountryBase):
    """Полная карточка страны"""
    id: UUID
    numeric_code: int | None = None
    currencies: dict[str, CurrencyInfo] | None = None
    description_ru: str | None = None
    description_en: str | None = None
    safety_level: str | None = None
    safety_note: str | None = None
    safety_source: str | None = None
    safety_updated_at: datetime | None = None
    bbox_min_lat: float | None = None
    bbox_max_lat: float | None = None
    bbox_min_lng: float | None = None
    bbox_max_lng: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
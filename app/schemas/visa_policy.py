from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class VisaMapItem(BaseModel):
    """Один элемент карты — iso2 + категория визы"""
    id: UUID
    iso2: str
    visa_category: str
    confidence_level: int = 3

    model_config = {"from_attributes": True}


class VisaPolicyDetail(BaseModel):
    id: UUID
    visa_category: str
    max_stay_days: int | None = None
    visa_validity_days: int | None = None
    processing_days: int | None = None
    fee_usd: Decimal | None = None
    conditions: dict | None = None
    source_url: str | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None
    updated_at: datetime
    confidence_level: int = 3
    confidence_note: str | None = None

    model_config = {"from_attributes": True}
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class VisaMapItem(BaseModel):
    """Один элемент карты — iso2 + категория визы"""
    iso2: str
    visa_category: str

    model_config = {"from_attributes": True}


class VisaPolicyDetail(BaseModel):
    """Детальная информация о визовом режиме"""
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

    model_config = {"from_attributes": True}
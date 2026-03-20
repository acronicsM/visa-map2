from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator


VALID_VISA_CATEGORIES = {
    "free", "voa", "evisa", "embassy", "restricted", "unavailable"
}

VALID_TRIGGER_STATUSES = {
    "new", "reviewing", "processed", "ignored"
}


class VisaPolicyUpdate(BaseModel):
    visa_category: str | None = None
    max_stay_days: int | None = None
    visa_validity_days: int | None = None
    processing_days: int | None = None
    fee_usd: Decimal | None = None
    conditions: dict | None = None
    source_url: str | None = None
    verified_by: str | None = None
    change_reason: str | None = None
    confidence_level: int | None = None
    confidence_note: str | None = None

    @field_validator("visa_category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v and v not in VALID_VISA_CATEGORIES:
            raise ValueError(
                f"Недопустимая категория '{v}'. "
                f"Допустимые: {', '.join(sorted(VALID_VISA_CATEGORIES))}"
            )
        return v

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, v: int | None) -> int | None:
        if v is not None and v not in (1, 2, 3):
            raise ValueError(
                "confidence_level должен быть 1 (МИД), 2 (проверено модератором) "
                "или 3 (автоматически из датасета)"
            )
        return v

class VisaPolicyResponse(BaseModel):
    id: UUID
    passport_id: UUID
    destination_id: UUID
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

class NewsTriggerCreate(BaseModel):
    headline: str
    source_name: str | None = None
    source_url: str | None = None
    affected_countries: list[str] | None = None
    notes: str | None = None

    @field_validator("affected_countries")
    @classmethod
    def validate_countries(cls, v: list[str] | None) -> list[str] | None:
        if v:
            import re
            for code in v:
                if not re.match(r"^[A-Z]{2}$", code.upper()):
                    raise ValueError(f"Некорректный код страны: {code}")
            return [c.upper() for c in v]
        return v


class NewsTriggerResponse(BaseModel):
    id: UUID
    headline: str
    source_name: str | None = None
    source_url: str | None = None
    status: str
    affected_countries: list[str] | None = None
    notes: str | None = None
    detected_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class NewsTriggerStatusUpdate(BaseModel):
    status: str
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_TRIGGER_STATUSES:
            raise ValueError(
                f"Недопустимый статус '{v}'. "
                f"Допустимые: {', '.join(sorted(VALID_TRIGGER_STATUSES))}"
            )
        return v
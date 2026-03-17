from pydantic import field_validator
import re


class Iso2Mixin:
    """Миксин для валидации iso2 кодов"""

    @field_validator("iso2", mode="before")
    @classmethod
    def validate_iso2(cls, v: str) -> str:
        if not v:
            raise ValueError("Код страны не может быть пустым")
        v = v.strip().upper()
        if not re.match(r"^[A-Z]{2}$", v):
            raise ValueError(
                f"Некорректный код страны '{v}' — должно быть 2 латинские буквы (например: RU, DE, US)"
            )
        return v
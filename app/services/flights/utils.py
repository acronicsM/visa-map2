import unicodedata


def normalize_city_name(city: str) -> str:
    """Нормализация названия города для сравнения и city_key."""
    text = city.strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def build_city_key(city: str, country_iso2: str) -> str:
    return f"{normalize_city_name(city)}|{country_iso2.strip().upper()}"

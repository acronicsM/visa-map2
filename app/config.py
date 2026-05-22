from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    redis_host: str = "localhost"
    redis_port: int = 6379

    api_key: str = "dev-secret-key"
    input_folder_seasons: str | None = None

    # Маппинг safety_final_score → countries.safety_level (выше score = безопаснее)
    safety_score_safe_min: float = 70.0
    safety_score_unsafe_min: float = 40.0

    # JSON: {"thresholds":[0.5,1.0],"labels":["..."],"colors":["#..","#..","#.."]}
    travel_cost_score_bands: str | None = Field(
        default=None,
        description=(
            "Интервалы относительной стоимости (score). "
            "Пусто — значения по умолчанию в коде."
        ),
    )
    fx_rates_url: str = Field(
        default="https://open.er-api.com/v6/latest/USD",
        description=(
            "URL публичного FX snapshot с базой USD. Ожидается JSON с объектом rates."
        ),
    )
    fx_request_timeout_seconds: float = 5.0

    # Direct flights module
    flights_data_source: str = Field(
        default="openflights",
        description=(
            "Источник данных о прямых рейсах для API /flights/direct-countries: "
            "openflights, ignav, aviation_edge"
        ),
    )
    flights_cache_ttl_seconds: int = 86400
    flights_refresh_lead_seconds: int = 3600
    flights_refresh_min_requests: int = 1
    flights_refresh_batch_size: int = 20
    flights_probe_date_offset_days: int = 30
    flights_probe_max_concurrent: int = 5
    flights_probe_delay_ms: int = 200
    openflights_data_dir: str = "./data/openflights"
    aviation_edge_api_key: str | None = None
    aviation_edge_request_timeout_seconds: float = 10.0
    aviation_edge_max_concurrent: int = 5
    ignav_api_key: str | None = None
    ignav_request_timeout_seconds: float = 15.0

    @model_validator(mode="after")
    def _validate_flights_source(self) -> "Settings":
        allowed = {"openflights", "ignav", "aviation_edge"}
        source = self.flights_data_source.strip().lower()
        if source not in allowed:
            raise ValueError(
                f"flights_data_source должен быть одним из: {', '.join(sorted(allowed))}"
            )
        self.flights_data_source = source
        return self

    @model_validator(mode="after")
    def _safety_thresholds_order(self) -> "Settings":
        if self.safety_score_safe_min <= self.safety_score_unsafe_min:
            raise ValueError(
                "safety_score_safe_min должен быть больше safety_score_unsafe_min"
            )
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
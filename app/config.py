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
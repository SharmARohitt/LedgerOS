from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str  # required — set DATABASE_URL in .env

    jwt_secret: str  # required — set JWT_SECRET in .env
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    cors_origins: str = "http://localhost:3000"

    dodo_api_key: str | None = None
    dodo_webhook_secret: str | None = None

    tensormux_api_key: str | None = None
    anthropic_api_key: str | None = None

    ao_api_key: str | None = None

    neatlogs_api_key: str | None = None
    neatlogs_project: str | None = None

    object_store_path: str = "./data/object_store"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dodo_is_live(self) -> bool:
        return bool(self.dodo_api_key and self.dodo_webhook_secret)

    @property
    def anthropic_is_live(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved relative to THIS file, not the process's working directory.
# `env_file="../.env"` previously resolved relative to os.getcwd(), so
# launching the backend from a different directory (repo root vs backend/,
# an IDE run config, a different Docker WORKDIR) could silently load a
# different .env (or none), producing a different JWT_SECRET across
# otherwise-identical process launches — tokens minted under one resolution
# become unverifiable under another. Anchoring to __file__ makes the
# resolved secret deterministic regardless of launch directory.
_PROJECT_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_PROJECT_ROOT_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str  # required — set DATABASE_URL in .env

    jwt_secret: str  # required — set JWT_SECRET in .env
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    cors_origins: str = "http://localhost:3000"

    dodo_api_key: str | None = None
    dodo_webhook_secret: str | None = None
    dodo_base_url: str = "https://test.dodopayments.com"

    tensormux_api_key: str | None = None
    tensormux_base_url: str = "https://api.tensormux.com/v1"
    tensormux_model: str = "glm-4-7-flash"
    anthropic_api_key: str | None = None

    ao_api_key: str | None = None

    neatlogs_api_key: str | None = None
    neatlogs_project: str | None = None

    object_store_path: str = "./data/object_store"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dodo_mode(self) -> str:
        """LIVE requires both an API key and a webhook secret (so inbound
        webhooks can be verified). SANDBOX means a real Dodo test-mode API
        key is present — outbound API calls are real, but inbound webhook
        signatures cannot be verified without a secret. SIMULATED means no
        credentials at all: everything runs through the local mock."""
        if self.dodo_api_key and self.dodo_webhook_secret:
            return "LIVE"
        if self.dodo_api_key:
            return "SANDBOX"
        return "SIMULATED"

    @property
    def dodo_is_live(self) -> bool:
        return self.dodo_mode in ("LIVE", "SANDBOX")

    @property
    def tensormux_is_live(self) -> bool:
        return bool(self.tensormux_api_key)

    @property
    def anthropic_is_live(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

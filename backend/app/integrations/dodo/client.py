from app.core.config import get_settings
from app.integrations.dodo.base import DodoProvider
from app.integrations.dodo.mock import MockDodoProvider


def get_dodo_provider() -> DodoProvider:
    settings = get_settings()
    if settings.dodo_is_live:
        from app.integrations.dodo.live import LiveDodoProvider

        return LiveDodoProvider(webhook_secret=settings.dodo_webhook_secret, api_key=settings.dodo_api_key)
    return MockDodoProvider()

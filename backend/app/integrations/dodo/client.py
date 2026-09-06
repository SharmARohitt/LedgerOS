from app.core.config import get_settings
from app.integrations.dodo.base import DodoProvider
from app.integrations.dodo.mock import MockDodoProvider


def get_dodo_provider() -> DodoProvider:
    settings = get_settings()
    mode = settings.dodo_mode

    if mode == "LIVE":
        from app.integrations.dodo.live import LiveDodoProvider

        return LiveDodoProvider(webhook_secret=settings.dodo_webhook_secret, api_key=settings.dodo_api_key)

    if mode == "SANDBOX":
        from app.integrations.dodo.sandbox import SandboxDodoProvider

        return SandboxDodoProvider(api_key=settings.dodo_api_key, base_url=settings.dodo_base_url)

    return MockDodoProvider()

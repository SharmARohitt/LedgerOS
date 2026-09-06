import base64
import hashlib
import hmac
import json

from app.integrations.dodo.base import DodoProvider


class LiveDodoProvider(DodoProvider):
    """Real Dodo Payments adapter. Dodo documents Standard Webhooks-style
    signing (webhook-id / webhook-timestamp / webhook-signature headers,
    base64 HMAC-SHA256 over "{id}.{timestamp}.{body}"). Verify this against
    Dodo's current webhook documentation before relying on it in production —
    this implementation has not been exercised against a live Dodo account."""

    mode = "LIVE"

    def __init__(self, webhook_secret: str, api_key: str):
        self._secret = webhook_secret
        self._api_key = api_key

    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool:
        raise NotImplementedError(
            "LiveDodoProvider.verify_signature requires the exact header names and secret "
            "encoding from your Dodo dashboard/docs — wire this up once real credentials are "
            "available rather than trusting an unverified implementation."
        )

    def parse_event(self, payload: bytes) -> dict:
        return json.loads(payload)

    def simulate_payment(self, *, amount: float, currency: str, invoice_reference: str, customer_reference: str) -> dict:
        raise NotImplementedError("simulate_payment is only available on MockDodoProvider")

    def _reference_signature(self, webhook_id: str, timestamp: str, body: bytes) -> str:
        """Standard Webhooks reference computation, kept for when real
        credentials are wired in — NOT used by verify_signature above."""
        signed_content = f"{webhook_id}.{timestamp}.{body.decode()}".encode()
        digest = hmac.new(base64.b64decode(self._secret.split("_")[-1] if "_" in self._secret else self._secret), signed_content, hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

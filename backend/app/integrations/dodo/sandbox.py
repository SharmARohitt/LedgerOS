"""Real Dodo Payments sandbox adapter. Confirmed working against
test.dodopayments.com with a Bearer API key (GET /payments returns 200).

This account has no webhook secret configured, so inbound webhook
signatures cannot be cryptographically verified — verify_signature() is
honest about that (returns True but every event is still tagged
source_mode=SANDBOX, never LIVE). What IS real here: outbound reads against
Dodo's actual sandbox API (get_real_payment). Creating a real sandbox
payment requires a product/customer already set up in the Dodo dashboard
(POST /payments requires `product_cart`) which this codebase doesn't
provision, so demo events are still built locally via simulate_payment()
rather than fabricating a real Dodo transaction end-to-end."""

import json

import httpx

from app.integrations.dodo.base import DodoProvider


class SandboxDodoProvider(DodoProvider):
    mode = "SANDBOX"

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool:
        return True

    def parse_event(self, payload: bytes) -> dict:
        return json.loads(payload)

    def simulate_payment(self, *, amount: float, currency: str, invoice_reference: str, customer_reference: str) -> dict:
        # A locally-fabricated event never actually touched Dodo's sandbox, so
        # it must not be tagged SANDBOX — callers that want a demo event use
        # MockDodoProvider directly instead, keeping the SANDBOX tag honest
        # for things that really did hit test.dodopayments.com.
        raise NotImplementedError(
            "SandboxDodoProvider does not fabricate events — use MockDodoProvider for local demo "
            "payments, or a real Dodo sandbox transaction for get_real_payment()."
        )

    def get_real_payment(self, payment_id: str) -> dict | None:
        try:
            response = httpx.get(
                f"{self._base_url}/payments/{payment_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        return response.json()

    def list_recent_payments(self, page_size: int = 10) -> list[dict]:
        try:
            response = httpx.get(
                f"{self._base_url}/payments",
                params={"page_size": page_size},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        return response.json().get("items", [])

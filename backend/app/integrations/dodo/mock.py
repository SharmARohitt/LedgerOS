import json
import uuid
from datetime import datetime, timezone

from app.integrations.dodo.base import DodoProvider


class MockDodoProvider(DodoProvider):
    """Local Dodo simulator used when DODO_API_KEY/DODO_WEBHOOK_SECRET are not
    configured. Produces the exact same normalized event schema a real Dodo
    webhook would, so the rest of the pipeline is provider-agnostic."""

    mode = "SIMULATED"

    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool:
        # No real secret to verify against in simulator mode; accepted but
        # every downstream record is tagged source_mode=SIMULATED.
        return True

    def parse_event(self, payload: bytes) -> dict:
        return json.loads(payload)

    def simulate_payment(self, *, amount: float, currency: str, invoice_reference: str, customer_reference: str) -> dict:
        return {
            "id": f"evt_sim_{uuid.uuid4().hex[:20]}",
            "type": "payment.succeeded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "amount": amount,
                "currency": currency,
                "invoice_reference": invoice_reference,
                "customer_reference": customer_reference,
                "metadata": {"simulated": True},
            },
        }

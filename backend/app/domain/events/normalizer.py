"""Normalizes a raw Dodo (or Dodo-simulator) payload into the canonical
FinancialEvent shape. This is the ONE place raw provider payloads get
translated into LedgerOS's internal event schema."""

import json
from dataclasses import dataclass


@dataclass
class NormalizedEvent:
    event_type: str
    source: str
    source_event_id: str
    source_mode: str  # LIVE | SIMULATED
    amount: float | None
    currency: str
    event_timestamp: str
    customer_reference: str | None
    invoice_reference: str | None
    metadata: dict
    raw: dict


_DODO_TYPE_MAP = {
    "payment.succeeded": "PAYMENT_SUCCEEDED",
    "payment.failed": "PAYMENT_FAILED",
    "refund.created": "REFUND",
    "dispute.created": "DISPUTE",
}


def normalize_dodo_event(payload: dict, source_mode: str) -> NormalizedEvent:
    dodo_type = payload.get("type", "")
    event_type = _DODO_TYPE_MAP.get(dodo_type, "PAYMENT_SUCCEEDED")
    data = payload.get("data", {})

    return NormalizedEvent(
        event_type=event_type,
        source="dodo",
        source_event_id=payload["id"],
        source_mode=source_mode,
        amount=data.get("amount"),
        currency=data.get("currency", "USD"),
        event_timestamp=payload.get("created_at", ""),
        customer_reference=data.get("customer_reference"),
        invoice_reference=data.get("invoice_reference"),
        metadata={"dodo_type": dodo_type, **data.get("metadata", {})},
        raw=payload,
    )


def canonical_metadata_str(metadata: dict) -> str:
    return json.dumps(metadata, sort_keys=True, default=str)

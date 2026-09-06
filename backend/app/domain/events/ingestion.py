"""End-to-end event ingestion: normalize -> idempotent event store -> payment
record -> exception detection -> investigation trigger. Runs synchronously
within the request/webhook transaction for the vertical slice (deterministic,
easy to test); moving this behind a queue is a drop-in change later."""

import json

from sqlalchemy.orm import Session

from app.agents.orchestrator import run_investigation
from app.domain.events.exception_detection import detect
from app.domain.events.normalizer import canonical_metadata_str, normalize_dodo_event
from app.domain.finance.graph import find_invoice_by_number
from app.models.finance import Payment
from app.storage.repositories.events_repo import upsert_event


def ingest_dodo_payload(db: Session, payload: dict, source_mode: str) -> dict:
    normalized = normalize_dodo_event(payload, source_mode)
    invoice = find_invoice_by_number(db, normalized.invoice_reference) if normalized.invoice_reference else None

    normalized_reference = {
        "invoice_number": normalized.invoice_reference,
        "customer_reference": normalized.customer_reference,
    }

    event, created = upsert_event(
        db,
        source=normalized.source,
        source_event_id=normalized.source_event_id,
        defaults={
            "event_type": normalized.event_type,
            "source_mode": normalized.source_mode,
            "entity_id": invoice.legal_entity_id if invoice else None,
            "customer_id": invoice.customer_id if invoice else None,
            "amount": normalized.amount,
            "currency": normalized.currency,
            "event_timestamp": normalized.event_timestamp,
            "metadata_json": canonical_metadata_str(normalized.metadata),
            "raw_reference": json.dumps(normalized.raw, default=str),
            "normalized_reference": json.dumps(normalized_reference),
            "processing_state": "RECEIVED",
        },
    )

    if not created:
        db.commit()
        return {
            "event_id": event.id,
            "duplicate": True,
            "processing_state": event.processing_state,
            "message": "Duplicate delivery — idempotent no-op, no new event/payment/action created.",
        }

    payment = None
    if normalized.event_type == "PAYMENT_SUCCEEDED":
        payment = Payment(
            source=normalized.source,
            source_event_id=normalized.source_event_id,
            invoice_id=invoice.id if invoice else None,
            customer_id=invoice.customer_id if invoice else None,
            amount=normalized.amount,
            currency=normalized.currency,
            status="SUCCEEDED",
            source_mode=source_mode,
        )
        db.add(payment)
        db.flush()

    event.processing_state = "NORMALIZED"
    db.flush()

    exception = detect(db, event)
    case = None
    try:
        if exception is not None:
            case = run_investigation(db, exception.id)
        event.processing_state = "PROCESSED"
    except Exception as exc:  # noqa: BLE001 - never let a failed investigation dead-letter the event silently
        event.processing_state = "DEAD_LETTER"
        db.flush()
        db.commit()
        raise exc

    db.commit()

    return {
        "event_id": event.id,
        "duplicate": False,
        "payment_id": payment.id if payment else None,
        "exception_id": exception.id if exception else None,
        "case_id": case.id if case else None,
        "decision_type": (
            json.loads(case.case_state_json).get("decision", {}).get("decision_type") if case else None
        ),
    }

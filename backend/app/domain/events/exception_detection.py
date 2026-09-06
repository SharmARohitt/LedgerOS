"""Deterministic exception detection: an exact-match payment needs no
investigation; anything else creates an ExceptionRecord and kicks off the
agent pipeline."""

import json

from sqlalchemy.orm import Session

from app.domain.finance.graph import find_invoice_by_number
from app.models.events import FinancialEvent
from app.models.investigations import ExceptionRecord

AMOUNT_TOLERANCE = 0.01


def detect(db: Session, event: FinancialEvent) -> ExceptionRecord | None:
    if event.event_type != "PAYMENT_SUCCEEDED":
        return None

    try:
        normalized = json.loads(event.normalized_reference or "{}")
    except json.JSONDecodeError:
        normalized = {}

    invoice_number = normalized.get("invoice_number")
    invoice = find_invoice_by_number(db, invoice_number) if invoice_number else None

    if invoice is None:
        exc = ExceptionRecord(
            event_id=event.id,
            exception_type="MISSING_INVOICE",
            status="OPEN",
            summary=f"No invoice found for reference '{invoice_number}'.",
        )
        db.add(exc)
        db.flush()
        return exc

    discrepancy = float(event.amount) - float(invoice.total_amount)
    if abs(discrepancy) <= AMOUNT_TOLERANCE:
        return None

    exc = ExceptionRecord(
        event_id=event.id,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        exception_type="AMOUNT_MISMATCH",
        discrepancy_amount=discrepancy,
        status="OPEN",
        summary=f"Payment of {event.amount} does not match invoice {invoice.invoice_number} total of {invoice.total_amount}.",
    )
    db.add(exc)
    db.flush()
    return exc

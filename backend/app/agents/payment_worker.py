from sqlalchemy.orm import Session

from app.integrations.ao.orchestration import WorkerResult, WorkerStatus
from app.models.events import FinancialEvent
from app.models.finance import Payment
from app.models.investigations import ExceptionRecord


def run(db: Session, case_state: dict) -> WorkerResult:
    exception = db.get(ExceptionRecord, case_state["exception_id"])
    event = db.get(FinancialEvent, exception.event_id)

    payment = (
        db.query(Payment)
        .filter(Payment.source == event.source, Payment.source_event_id == event.source_event_id)
        .one_or_none()
    )

    if payment is None:
        return WorkerResult(status=WorkerStatus.FAILED, output={}, error="no payment record for this event")

    is_duplicate = (
        db.query(Payment)
        .filter(Payment.invoice_id == payment.invoice_id, Payment.id != payment.id, Payment.status == "SUCCEEDED")
        .count()
        > 0
        if payment.invoice_id
        else False
    )

    output = {
        "payment_id": payment.id,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "source_mode": payment.source_mode,
        "verified": payment.status == "SUCCEEDED",
        "is_duplicate_payment": is_duplicate,
    }
    return WorkerResult(status=WorkerStatus.SUCCESS, output=output)

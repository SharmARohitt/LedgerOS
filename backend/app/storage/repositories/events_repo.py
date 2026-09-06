from sqlalchemy.orm import Session

from app.models.events import FinancialEvent


def get_by_source_event_id(db: Session, source: str, source_event_id: str) -> FinancialEvent | None:
    return (
        db.query(FinancialEvent)
        .filter(FinancialEvent.source == source, FinancialEvent.source_event_id == source_event_id)
        .one_or_none()
    )


def upsert_event(db: Session, *, source: str, source_event_id: str, defaults: dict) -> tuple[FinancialEvent, bool]:
    """Idempotent insert: a redelivered webhook with the same
    (source, source_event_id) updates the existing row and reports
    created=False instead of inserting a duplicate."""
    existing = get_by_source_event_id(db, source, source_event_id)
    if existing is not None:
        existing.retry_count += 1
        db.flush()
        return existing, False

    event = FinancialEvent(source=source, source_event_id=source_event_id, **defaults)
    db.add(event)
    db.flush()
    return event, True

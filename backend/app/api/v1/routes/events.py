from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.events import FinancialEvent
from app.storage.repositories.events_repo import upsert_event

router = APIRouter(prefix="/events", tags=["events"])


class CreateEventRequest(BaseModel):
    event_type: str
    source: str = "manual"
    source_event_id: str
    amount: float | None = None
    currency: str = "USD"
    event_timestamp: str
    metadata: dict = {}


def _serialize(event: FinancialEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "source": event.source,
        "source_event_id": event.source_event_id,
        "source_mode": event.source_mode,
        "amount": float(event.amount) if event.amount is not None else None,
        "currency": event.currency,
        "event_timestamp": event.event_timestamp,
        "risk_state": event.risk_state,
        "processing_state": event.processing_state,
        "retry_count": event.retry_count,
        "created_at": event.created_at.isoformat(),
    }


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    event_type: str | None = None,
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    query = db.query(FinancialEvent)
    if event_type:
        query = query.filter(FinancialEvent.event_type == event_type)
    total = query.count()
    items = query.order_by(FinancialEvent.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_serialize(e) for e in items], "total": total, "limit": limit, "offset": offset}


@router.post("")
def create_event(body: CreateEventRequest, db: Session = Depends(get_db)) -> dict:
    import json

    event, created = upsert_event(
        db,
        source=body.source,
        source_event_id=body.source_event_id,
        defaults={
            "event_type": body.event_type,
            "source_mode": "SIMULATED" if body.source == "manual" else "LIVE",
            "amount": body.amount,
            "currency": body.currency,
            "event_timestamp": body.event_timestamp,
            "metadata_json": json.dumps(body.metadata, default=str),
            "processing_state": "RECEIVED",
        },
    )
    db.commit()
    return {**_serialize(event), "created": created}

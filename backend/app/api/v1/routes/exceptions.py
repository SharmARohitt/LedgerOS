import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_investigation
from app.api.v1.deps import get_db
from app.models.finance import Invoice
from app.models.investigations import ExceptionRecord, InvestigationCase
from app.models.parties import Customer

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


def _serialize(exc: ExceptionRecord, db: Session) -> dict:
    invoice = db.get(Invoice, exc.invoice_id) if exc.invoice_id else None
    customer = db.get(Customer, exc.customer_id) if exc.customer_id else None
    return {
        "id": exc.id,
        "event_id": exc.event_id,
        "exception_type": exc.exception_type,
        "status": exc.status,
        "discrepancy_amount": float(exc.discrepancy_amount) if exc.discrepancy_amount is not None else None,
        "risk_score": exc.risk_score,
        "risk_level": exc.risk_level,
        "summary": exc.summary,
        "invoice_number": invoice.invoice_number if invoice else None,
        "customer_name": customer.name if customer else None,
        "created_at": exc.created_at.isoformat(),
    }


@router.get("")
def list_exceptions(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    query = db.query(ExceptionRecord)
    if status_filter:
        query = query.filter(ExceptionRecord.status == status_filter)
    total = query.count()
    items = query.order_by(ExceptionRecord.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [_serialize(e, db) for e in items], "total": total, "limit": limit, "offset": offset}


@router.get("/{exception_id}")
def get_exception(exception_id: str, db: Session = Depends(get_db)) -> dict:
    exc = db.get(ExceptionRecord, exception_id)
    if exc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")

    case = (
        db.query(InvestigationCase)
        .filter(InvestigationCase.exception_id == exception_id)
        .order_by(InvestigationCase.created_at.desc())
        .first()
    )
    payload = _serialize(exc, db)
    payload["case_id"] = case.id if case else None
    payload["case_status"] = case.status if case else None
    return payload


@router.post("/{exception_id}/investigate")
def investigate_exception(exception_id: str, db: Session = Depends(get_db)) -> dict:
    exc = db.get(ExceptionRecord, exception_id)
    if exc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    if exc.status not in ("OPEN",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Exception is already '{exc.status}' — investigation already ran.",
        )

    case = run_investigation(db, exception_id)
    db.commit()
    case_state = json.loads(case.case_state_json)
    return {"case_id": case.id, "status": case.status, "decision": case_state.get("decision")}

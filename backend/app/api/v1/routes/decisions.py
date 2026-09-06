import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.decision_worker import apply_payment_to_invoice
from app.api.v1.deps import CurrentUser, get_db, require_role
from app.models.decisions import ApprovalRequest, Decision, DecisionMemoryEntry
from app.models.investigations import ExceptionRecord, InvestigationCase

router = APIRouter(prefix="/decisions", tags=["decisions"])


class ReviewRequest(BaseModel):
    note: str | None = None


def _load_pending_approval(db: Session, decision_id: str) -> tuple[Decision, ApprovalRequest]:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    approval = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.decision_id == decision_id, ApprovalRequest.status == "PENDING")
        .one_or_none()
    )
    if approval is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No pending approval for this decision")
    return decision, approval


@router.post("/{decision_id}/approve")
def approve_decision(
    decision_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("CFO", "ADMIN")),
) -> dict:
    decision, approval = _load_pending_approval(db, decision_id)

    case = db.get(InvestigationCase, decision.case_id)
    case_state = json.loads(case.case_state_json)
    evidence = case_state.get("evidence", {})
    payment = case_state.get("payment", {})

    if evidence.get("invoice_id") and payment.get("payment_id"):
        apply_payment_to_invoice(db, evidence, payment["payment_id"])
        decision.action_taken = "APPLY_PAYMENT_TO_INVOICE"

    approval.status = "APPROVED"
    approval.reviewed_by = user.user_id
    approval.note = body.note

    exception = db.get(ExceptionRecord, decision.exception_id)
    exception.status = "RESOLVED"
    case.status = "COMPLETED"

    for entry in db.query(DecisionMemoryEntry).filter(DecisionMemoryEntry.decision_id == decision_id).all():
        entry.human_outcome = "APPROVED"

    db.commit()
    return {"decision_id": decision_id, "status": "APPROVED", "action_taken": decision.action_taken}


@router.post("/{decision_id}/reject")
def reject_decision(
    decision_id: str,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("CFO", "ADMIN")),
) -> dict:
    decision, approval = _load_pending_approval(db, decision_id)

    approval.status = "REJECTED"
    approval.reviewed_by = user.user_id
    approval.note = body.note
    decision.action_taken = "REJECTED_NO_ACTION"

    exception = db.get(ExceptionRecord, decision.exception_id)
    exception.status = "OPEN"
    case = db.get(InvestigationCase, decision.case_id)
    case.status = "COMPLETED"

    for entry in db.query(DecisionMemoryEntry).filter(DecisionMemoryEntry.decision_id == decision_id).all():
        entry.human_outcome = "REJECTED"

    db.commit()
    return {"decision_id": decision_id, "status": "REJECTED", "action_taken": decision.action_taken}

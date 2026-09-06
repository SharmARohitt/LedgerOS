import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.decisions import ApprovalRequest, Decision
from app.models.investigations import ExceptionRecord, InvestigationCase

router = APIRouter(prefix="/decision-room", tags=["decision-room"])


@router.get("")
def decision_room(db: Session = Depends(get_db)) -> dict:
    """Every decision still awaiting human authorization — HUMAN_REVIEW and
    BLOCK cases the agent workforce could not (and, for BLOCK, must not)
    resolve on its own."""
    rows = (
        db.query(Decision, ApprovalRequest, ExceptionRecord)
        .join(ApprovalRequest, ApprovalRequest.decision_id == Decision.id)
        .join(ExceptionRecord, ExceptionRecord.id == Decision.exception_id)
        .filter(ApprovalRequest.status == "PENDING")
        .order_by(Decision.created_at.desc())
        .all()
    )

    items = []
    total_exposure = 0.0
    for decision, approval, exception in rows:
        case = db.get(InvestigationCase, decision.case_id)
        case_state = json.loads(case.case_state_json) if case and case.case_state_json else {}
        evidence = case_state.get("evidence", {})
        amount = abs(float(exception.discrepancy_amount or 0))
        total_exposure += amount
        items.append(
            {
                "decision_id": decision.id,
                "approval_id": approval.id,
                "exception_id": exception.id,
                "amount": round(amount, 2),
                "risk_level": decision.risk_level,
                "recommendation": decision.decision_type,
                "reason": decision.reason,
                "confidence": float(decision.confidence),
                "policy_version": decision.policy_version,
                "evidence_count": len([v for v in evidence.values() if v]),
                "created_at": decision.created_at.isoformat(),
            }
        )

    return {
        "pending_count": len(items),
        "total_exposure": round(total_exposure, 2),
        "items": items,
    }

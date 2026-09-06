from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.decisions import Decision
from app.models.finance import Payment
from app.models.investigations import ExceptionRecord
from app.models.observability import Span, Trace
from app.models.proofs import ProofCapsule

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    total_volume = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == "SUCCEEDED").scalar()

    open_exceptions = db.query(ExceptionRecord).filter(ExceptionRecord.status.in_(["OPEN", "INVESTIGATING"])).all()
    at_risk_capital = sum(abs(float(e.discrepancy_amount or 0)) for e in open_exceptions)

    auto_resolved = db.query(Decision).filter(Decision.decision_type == "AUTO_RESOLVE").count()
    human_reviews = db.query(Decision).filter(Decision.decision_type == "HUMAN_REVIEW").count()
    blocked = db.query(Decision).filter(Decision.decision_type == "BLOCK").count()

    avg_investigation_ms = db.query(func.avg(Trace.duration_ms)).filter(Trace.duration_ms.isnot(None)).scalar()
    total_inference_cost = db.query(func.coalesce(func.sum(Trace.total_cost_estimate), 0)).scalar()
    evidence_count = db.query(Span).filter(Span.agent_id == "evidence_worker", Span.status == "SUCCESS").count()

    return {
        "transactions_processed": db.query(Payment).count(),
        "total_volume": float(total_volume or 0),
        "exceptions_detected": db.query(ExceptionRecord).count(),
        "exceptions_open": len(open_exceptions),
        "at_risk_capital": round(at_risk_capital, 2),
        "exceptions_auto_resolved": auto_resolved,
        "human_escalations": human_reviews,
        "blocked_actions": blocked,
        "average_investigation_time_ms": float(avg_investigation_ms) if avg_investigation_ms else None,
        "estimated_inference_cost": float(total_inference_cost or 0),
        "evidence_count": evidence_count,
        "proofs_generated": db.query(ProofCapsule).count(),
    }

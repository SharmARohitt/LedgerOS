from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.observability import Span, Trace

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{trace_id}")
def get_trace(trace_id: str, db: Session = Depends(get_db)) -> dict:
    trace = db.get(Trace, trace_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    spans = db.query(Span).filter(Span.trace_id == trace_id).order_by(Span.created_at).all()

    return {
        "id": trace.id,
        "case_id": trace.case_id,
        "workflow_id": trace.workflow_id,
        "status": trace.status,
        "duration_ms": trace.duration_ms,
        "total_cost_estimate": float(trace.total_cost_estimate),
        "spans": [
            {
                "id": s.id,
                "parent_span_id": s.parent_span_id,
                "agent_id": s.agent_id,
                "tool_name": s.tool_name,
                "tool_arguments_hash": s.tool_arguments_hash,
                "model": s.model,
                "model_version": s.model_version,
                "prompt_version": s.prompt_version,
                "inference_mode": s.inference_mode,
                "policy_version": s.policy_version,
                "risk_level": s.risk_level,
                "decision": s.decision,
                "confidence": float(s.confidence) if s.confidence is not None else None,
                "human_approval": s.human_approval,
                "status": s.status,
                "error": s.error,
                "retry_count": s.retry_count,
                "duration_ms": s.duration_ms,
                "cost_estimate": float(s.cost_estimate),
                "created_at": s.created_at.isoformat(),
            }
            for s in spans
        ],
    }

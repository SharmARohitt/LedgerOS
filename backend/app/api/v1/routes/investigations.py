import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.investigations import CaseTask, InvestigationCase

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("/{case_id}")
def get_investigation(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found")

    tasks = db.query(CaseTask).filter(CaseTask.case_id == case_id).order_by(CaseTask.created_at).all()
    case_state = json.loads(case.case_state_json) if case.case_state_json else {}

    return {
        "id": case.id,
        "exception_id": case.exception_id,
        "trace_id": case.trace_id,
        "status": case.status,
        "case_state": case_state,
        "tasks": [
            {
                "id": t.id,
                "worker_name": t.worker_name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "error": t.error,
                "output": json.loads(t.output_json) if t.output_json else {},
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
    }

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.domain.financial_twin.engine import compute_snapshot, gather_inputs

router = APIRouter(prefix="/financial-twin", tags=["financial-twin"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return compute_snapshot(gather_inputs(db))


@router.get("/capital")
def capital(db: Session = Depends(get_db)) -> dict:
    snapshot = compute_snapshot(gather_inputs(db))
    return {
        "capital_map": snapshot["capital_map"],
        "deployment_opportunities": snapshot["deployment_opportunities"],
    }


@router.get("/obligations")
def obligations(db: Session = Depends(get_db)) -> dict:
    snapshot = compute_snapshot(gather_inputs(db))
    return snapshot["obligations"]


@router.get("/early-warnings")
def early_warnings(db: Session = Depends(get_db)) -> dict:
    snapshot = compute_snapshot(gather_inputs(db))
    return {"warnings": snapshot["early_warnings"]}

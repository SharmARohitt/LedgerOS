import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.contracts import Policy

router = APIRouter(prefix="/policies", tags=["policies"])

# Static autonomy matrix: what the agent workforce may do without human
# sign-off vs what always requires a human. This is deliberately not
# database-backed — changing what an AI system is allowed to do unattended
# is exactly the kind of change that should live in reviewed source code,
# not a runtime-editable row.
AUTONOMY_MATRIX = [
    {"capability": "READ_TRANSACTIONS", "allowed": True},
    {"capability": "INVESTIGATE_EXCEPTIONS", "allowed": True},
    {"capability": "RECOMMEND_DECISION", "allowed": True},
    {"capability": "AUTO_RESOLVE_UNDER_POLICY_THRESHOLD", "allowed": True},
    {"capability": "EXECUTE_ABOVE_THRESHOLD", "allowed": False},
    {"capability": "RELEASE_PAYROLL", "allowed": False},
    {"capability": "CHANGE_POLICY", "allowed": False},
    {"capability": "OVERRIDE_HUMAN_DECISION", "allowed": False},
    {"capability": "DEPLOY_CAPITAL", "allowed": False},
]


@router.get("")
def list_policies(db: Session = Depends(get_db)) -> dict:
    policies = db.query(Policy).order_by(Policy.policy_key, Policy.version).all()
    items = []
    for p in policies:
        try:
            rules = json.loads(p.rules_json)
        except (json.JSONDecodeError, TypeError):
            rules = {}
        items.append(
            {
                "id": p.id,
                "policy_key": p.policy_key,
                "version": p.version,
                "policy_type": p.policy_type,
                "status": p.status,
                "created_by": p.created_by,
                "effective_date": p.effective_date,
                "description": p.description,
                "rules": rules,
            }
        )
    return {"items": items}


@router.get("/autonomy-matrix")
def autonomy_matrix() -> dict:
    return {"capabilities": AUTONOMY_MATRIX, "principle": "AI reasons. Deterministic policy authorizes. Humans control high-risk capital."}

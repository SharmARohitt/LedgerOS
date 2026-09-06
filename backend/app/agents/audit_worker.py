import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.integrations.ao.orchestration import WorkerResult, WorkerStatus
from app.models.decisions import Decision
from app.models.observability import Span
from app.models.proofs import ProofCapsule
from app.storage.object_store.local_fs import get_object_store

AGENT_VERSION = "ledgeros-agents-v0.1"


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def run(db: Session, case_state: dict) -> WorkerResult:
    decision_row = db.get(Decision, case_state["decision"]["decision_id"])
    trace_id = case_state.get("trace_id")

    spans = db.query(Span).filter(Span.trace_id == trace_id).order_by(Span.created_at).all() if trace_id else []
    tool_calls = [
        {
            "span_id": s.id,
            "agent_id": s.agent_id,
            "tool_name": s.tool_name,
            "tool_arguments_hash": s.tool_arguments_hash,
            "status": s.status,
            "duration_ms": s.duration_ms,
        }
        for s in spans
    ]

    evidence = case_state["evidence"]
    evidence_refs = [
        ref
        for ref in [
            {"type": "INVOICE", "id": evidence.get("invoice_id"), "reference": evidence.get("invoice_number")},
            {"type": "CUSTOMER", "id": evidence.get("customer_id"), "reference": evidence.get("customer_name")},
            {"type": "CONTRACT", "id": evidence.get("contract_id"), "reference": evidence.get("contract_name")},
            {"type": "CREDIT_MEMO", "id": evidence.get("credit_memo_id"), "reference": evidence.get("credit_memo_number")},
            {"type": "POLICY", "id": evidence.get("policy_id"), "reference": evidence.get("policy_version")},
        ]
        if ref["id"] is not None
    ]

    canonical_payload = {
        "case_id": case_state["case_id"],
        "exception_id": case_state["exception_id"],
        "decision_id": decision_row.id,
        "decision_type": decision_row.decision_type,
        "confidence": float(decision_row.confidence),
        "risk_level": decision_row.risk_level,
        "policy_version": decision_row.policy_version,
        "agent_version": AGENT_VERSION,
        "model": case_state["decision"].get("model"),
        "model_version": case_state["decision"].get("model_version"),
        "prompt_version": case_state["decision"].get("prompt_version"),
        "evidence": evidence_refs,
        "tool_calls": tool_calls,
        "human_approval": None,
        "action": decision_row.action_taken,
        "trace_id": trace_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    canonical_json = _canonical_json(canonical_payload)
    sha256_hash = hashlib.sha256(canonical_json.encode()).hexdigest()

    proof = ProofCapsule(
        decision_id=decision_row.id,
        case_id=case_state["case_id"],
        trace_id=trace_id,
        canonical_json=canonical_json,
        sha256_hash=sha256_hash,
    )
    db.add(proof)
    db.flush()

    get_object_store().put_object(f"proofs/{proof.id}.json", canonical_json)

    output = {"proof_id": proof.id, "sha256_hash": sha256_hash}
    return WorkerResult(status=WorkerStatus.SUCCESS, output=output)

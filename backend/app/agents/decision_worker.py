from sqlalchemy.orm import Session

from app.domain.decisions.memory import find_similar_cases, make_pattern_key, record_decision_memory
from app.integrations.ao.orchestration import WorkerResult, WorkerStatus
from app.integrations.tensormux.router import LocalInferenceRouter
from app.models.decisions import ApprovalRequest, Decision
from app.models.finance import Invoice, Payment


def _compute_confidence(decision_type: str, risk_score: int, approval_rate: float | None) -> float:
    base = {"AUTO_RESOLVE": 85.0, "HUMAN_REVIEW": 55.0, "BLOCK": 90.0}[decision_type]
    confidence = base - risk_score * 0.15
    if approval_rate is not None:
        confidence += (approval_rate - 0.5) * 20
    return round(max(1.0, min(99.0, confidence)), 1)


def apply_payment_to_invoice(db: Session, evidence: dict, payment_id: str) -> None:
    payment = db.get(Payment, payment_id)
    payment.applied_to_invoice = True
    if not payment.invoice_id:
        payment.invoice_id = evidence["invoice_id"]

    invoice = db.get(Invoice, evidence["invoice_id"])
    credited = abs(evidence.get("credit_memo_amount") or 0)
    remaining = float(invoice.total_amount) - float(payment.amount) - credited
    invoice.status = "PAID" if abs(remaining) <= 0.01 else "PARTIAL"
    db.flush()


def run(db: Session, case_state: dict) -> WorkerResult:
    evidence = case_state["evidence"]
    payment = case_state["payment"]
    policy = case_state["policy"]

    decision_type = policy["decision_type"]
    discrepancy = policy.get("discrepancy_amount")
    band_amount = abs(discrepancy) if discrepancy is not None else payment["amount"]
    pattern_key = make_pattern_key(evidence.get("policy_key"), band_amount)
    similar = find_similar_cases(db, pattern_key)

    confidence = _compute_confidence(decision_type, policy["risk_score"], similar.approval_rate)

    router = LocalInferenceRouter()
    complexity = "simple" if len(policy.get("signals_fired", [])) <= 1 else "multi_document_investigation"
    inference = router.explain(
        risk_level=policy["risk_level"],
        complexity=complexity,
        evidence={
            "invoice_number": evidence.get("invoice_number"),
            "discrepancy_amount": discrepancy,
            "credit_memo_number": evidence.get("credit_memo_number"),
            "credit_memo_amount": evidence.get("credit_memo_amount"),
            "policy_version": evidence.get("policy_version"),
            "similar_case_stats": {
                "total_cases": similar.total_cases,
                "approved": similar.approved,
                "rejected": similar.rejected,
            },
        },
    )

    decision = Decision(
        case_id=case_state["case_id"],
        exception_id=case_state["exception_id"],
        decision_type=decision_type,
        confidence=confidence,
        risk_level=policy["risk_level"],
        policy_id=evidence.get("policy_id"),
        policy_version=evidence.get("policy_version"),
        reason=policy["policy_reason"],
        explanation=inference.text,
        trace_id=case_state.get("trace_id"),
    )
    db.add(decision)
    db.flush()

    if decision_type == "AUTO_RESOLVE" and payment.get("payment_id") and evidence.get("invoice_id"):
        apply_payment_to_invoice(db, evidence, payment["payment_id"])
        decision.action_taken = "APPLY_PAYMENT_TO_INVOICE"
    else:
        db.add(ApprovalRequest(decision_id=decision.id, status="PENDING"))
        decision.action_taken = None

    record_decision_memory(db, decision, pattern_key)
    db.flush()

    output = {
        "decision_id": decision.id,
        "decision_type": decision_type,
        "confidence": confidence,
        "explanation": inference.text,
        "action_taken": decision.action_taken,
        "model": inference.model,
        "model_version": inference.model_version,
        "prompt_version": inference.prompt_version,
        "inference_mode": inference.inference_mode,
        "cost_estimate": inference.estimated_cost,
        "similar_case_stats": {
            "pattern_key": pattern_key,
            "total_cases": similar.total_cases,
            "approved": similar.approved,
            "rejected": similar.rejected,
            "approval_rate": similar.approval_rate,
        },
    }
    return WorkerResult(status=WorkerStatus.SUCCESS, output=output)

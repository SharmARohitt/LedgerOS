from sqlalchemy.orm import Session

from app.domain.policy.engine import PolicyInput, evaluate, load_rules
from app.domain.risk.engine import RiskSignals, score_risk
from app.integrations.ao.orchestration import WorkerResult, WorkerStatus
from app.models.investigations import ExceptionRecord


def run(db: Session, case_state: dict) -> WorkerResult:
    exception = db.get(ExceptionRecord, case_state["exception_id"])
    evidence = case_state["evidence"]
    payment = case_state["payment"]

    credit_memo_amount = evidence.get("credit_memo_amount")

    signals = RiskSignals(
        amount=payment["amount"],
        invoice_amount=evidence.get("invoice_amount"),
        is_new_customer=evidence.get("is_new_customer", False),
        is_new_vendor=False,
        has_invoice=evidence.get("has_invoice", False),
        entity_mismatch=False,
        is_duplicate_payment=payment.get("is_duplicate_payment", False),
        evidence_complete=evidence.get("evidence_complete", False),
    )
    risk = score_risk(signals)

    exception.risk_score = risk.risk_score
    exception.risk_level = risk.risk_level
    exception.discrepancy_amount = risk.discrepancy_amount
    db.flush()

    rules = load_rules(evidence.get("policy_rules_json", "{}"))
    tolerance = rules.get("sla_credit_tolerance", 5.00)
    has_credit_memo_match = (
        credit_memo_amount is not None
        and risk.discrepancy_amount is not None
        and abs(abs(credit_memo_amount) - abs(risk.discrepancy_amount)) <= tolerance
    )

    policy_input = PolicyInput(
        discrepancy_amount=risk.discrepancy_amount,
        credit_memo_amount=credit_memo_amount,
        has_invoice=evidence.get("has_invoice", False),
        has_credit_memo_match=has_credit_memo_match,
        is_new_vendor=False,
        evidence_complete=evidence.get("evidence_complete", False),
        risk_level=risk.risk_level,
    )
    verdict = evaluate(policy_input, rules)

    output = {
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "signals_fired": risk.signals,
        "discrepancy_amount": risk.discrepancy_amount,
        "decision_type": verdict.decision_type,
        "policy_reason": verdict.reason,
        "matched_rule": verdict.matched_rule,
        "has_credit_memo_match": has_credit_memo_match,
    }
    return WorkerResult(status=WorkerStatus.SUCCESS, output=output)

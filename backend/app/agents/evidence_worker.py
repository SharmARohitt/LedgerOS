import json

from sqlalchemy.orm import Session

from app.domain.finance.graph import build_evidence_chain, find_invoice_by_number
from app.integrations.ao.orchestration import WorkerResult, WorkerStatus
from app.models.events import FinancialEvent
from app.models.investigations import ExceptionRecord


def run(db: Session, case_state: dict) -> WorkerResult:
    exception = db.get(ExceptionRecord, case_state["exception_id"])
    event = db.get(FinancialEvent, exception.event_id)

    try:
        normalized = json.loads(event.normalized_reference or "{}")
    except json.JSONDecodeError:
        normalized = {}

    invoice_number = normalized.get("invoice_number")
    invoice = find_invoice_by_number(db, invoice_number) if invoice_number else None
    chain = build_evidence_chain(db, invoice)

    if chain.invoice:
        exception.invoice_id = chain.invoice.id
    if chain.customer:
        exception.customer_id = chain.customer.id
    db.flush()

    credit_memo = chain.credit_memos[0] if chain.credit_memos else None

    output = {
        "has_invoice": chain.invoice is not None,
        "invoice_id": chain.invoice.id if chain.invoice else None,
        "invoice_number": chain.invoice.invoice_number if chain.invoice else None,
        "invoice_amount": float(chain.invoice.total_amount) if chain.invoice else None,
        "customer_id": chain.customer.id if chain.customer else None,
        "customer_name": chain.customer.name if chain.customer else None,
        "is_new_customer": chain.customer.is_new_customer if chain.customer else False,
        "contract_id": chain.contract.id if chain.contract else None,
        "contract_name": chain.contract.name if chain.contract else None,
        "policy_id": chain.policy.id if chain.policy else None,
        "policy_key": chain.policy.policy_key if chain.policy else None,
        "policy_version": chain.policy.version if chain.policy else None,
        "policy_rules_json": chain.policy.rules_json if chain.policy else "{}",
        "credit_memo_id": credit_memo.id if credit_memo else None,
        "credit_memo_number": credit_memo.memo_number if credit_memo else None,
        "credit_memo_amount": float(credit_memo.amount) if credit_memo else None,
        "evidence_complete": chain.is_complete,
    }
    return WorkerResult(status=WorkerStatus.SUCCESS, output=output)

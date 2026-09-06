import hashlib
import json

from app.domain.events.ingestion import ingest_dodo_payload
from app.integrations.dodo.mock import MockDodoProvider
from app.models.decisions import Decision
from app.models.finance import Invoice, Payment
from app.models.investigations import ExceptionRecord, InvestigationCase
from app.models.observability import Span, Trace
from app.models.proofs import ProofCapsule


def test_case01_full_pipeline_auto_resolves_with_verifiable_proof(db, case01_seed):
    provider = MockDodoProvider()
    payload = provider.simulate_payment(
        amount=48750.00, currency="USD", invoice_reference="INV-4821", customer_reference=case01_seed["customer"].id
    )

    result = ingest_dodo_payload(db, payload, source_mode="SIMULATED")

    assert result["duplicate"] is False
    assert result["exception_id"] is not None
    assert result["case_id"] is not None
    assert result["decision_type"] == "AUTO_RESOLVE"

    exception = db.get(ExceptionRecord, result["exception_id"])
    assert exception.status == "RESOLVED"
    assert abs(float(exception.discrepancy_amount) - (-1250.00)) < 0.01

    case = db.get(InvestigationCase, result["case_id"])
    assert case.status == "COMPLETED"

    decision = db.query(Decision).filter(Decision.case_id == case.id).one()
    assert decision.decision_type == "AUTO_RESOLVE"
    assert decision.action_taken == "APPLY_PAYMENT_TO_INVOICE"
    assert 0 < float(decision.confidence) <= 99.0

    invoice = db.get(Invoice, case01_seed["invoice"].id)
    assert invoice.status == "PAID"

    payment = db.query(Payment).filter(Payment.source_event_id == payload["id"]).one()
    assert payment.applied_to_invoice is True

    # Every worker in the pipeline ran and left a span in one trace.
    trace = db.get(Trace, case.trace_id)
    assert trace.status == "SUCCESS"
    spans = db.query(Span).filter(Span.trace_id == trace.id).all()
    assert {s.agent_id for s in spans} == {
        "evidence_worker",
        "payment_worker",
        "policy_worker",
        "decision_worker",
        "audit_worker",
    }
    assert all(s.status == "SUCCESS" for s in spans)

    # Proof capsule is present and its hash is reproducible/tamper-evident.
    proof = db.query(ProofCapsule).filter(ProofCapsule.decision_id == decision.id).one()
    recomputed = hashlib.sha256(proof.canonical_json.encode()).hexdigest()
    assert recomputed == proof.sha256_hash

    canonical_payload = json.loads(proof.canonical_json)
    assert canonical_payload["decision_type"] == "AUTO_RESOLVE"
    assert canonical_payload["action"] == "APPLY_PAYMENT_TO_INVOICE"
    assert len(canonical_payload["evidence"]) >= 4  # invoice, customer, contract, credit memo

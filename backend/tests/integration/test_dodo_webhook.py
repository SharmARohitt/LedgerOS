from app.domain.events.ingestion import ingest_dodo_payload
from app.integrations.dodo.mock import MockDodoProvider
from app.models.events import FinancialEvent
from app.models.finance import Payment


def test_duplicate_dodo_delivery_creates_exactly_one_event_and_payment(db, case01_seed):
    provider = MockDodoProvider()
    payload = provider.simulate_payment(
        amount=48750.00, currency="USD", invoice_reference="INV-4821", customer_reference=case01_seed["customer"].id
    )
    # Redeliver the exact same event id, as a webhook provider legitimately can.
    payload_redelivered = {**payload}

    first = ingest_dodo_payload(db, payload, source_mode="SIMULATED")
    second = ingest_dodo_payload(db, payload_redelivered, source_mode="SIMULATED")

    assert first["duplicate"] is False
    assert second["duplicate"] is True

    events = db.query(FinancialEvent).filter(FinancialEvent.source_event_id == payload["id"]).all()
    payments = db.query(Payment).filter(Payment.source_event_id == payload["id"]).all()

    assert len(events) == 1
    assert len(payments) == 1


def test_missing_invoice_creates_exception_without_crashing(db, case01_seed):
    provider = MockDodoProvider()
    payload = provider.simulate_payment(
        amount=87000.00, currency="USD", invoice_reference="INV-DOES-NOT-EXIST", customer_reference="unknown"
    )
    result = ingest_dodo_payload(db, payload, source_mode="SIMULATED")

    assert result["duplicate"] is False
    assert result["exception_id"] is not None

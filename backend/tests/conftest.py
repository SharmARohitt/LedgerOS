import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: E402,F401,F403
from app.models.contracts import Contract, Policy  # noqa: E402
from app.models.finance import CreditMemo, Invoice  # noqa: E402
from app.models.org import Company, LegalEntity  # noqa: E402
from app.models.parties import Customer  # noqa: E402

CASE01_POLICY_RULES = {
    "auto_resolve_max_amount": 5000,
    "human_review_max_amount": 25000,
    "block_new_vendor_without_invoice": True,
    "block_missing_evidence": True,
    "sla_credit_tolerance": 5.00,
}


@pytest.fixture()
def db():
    # StaticPool: keeps every checkout on the SAME single connection. Without
    # it, SQLAlchemy's default per-thread pool for sqlite:///:memory: hands a
    # brand-new, tableless database to any other thread (e.g. FastAPI
    # TestClient's request runs in a worker thread) than the one that ran
    # create_all() here.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def case01_seed(db):
    """Seeds the minimal CASE 01 entity chain: invoice INV-4821 ($50,000) for
    Acme Corp under contract C-102 / policy V3.2, with a $1,250 SLA credit
    memo (CM-129) already on file."""
    import json

    company = Company(name="Northwind Financial")
    db.add(company)
    db.flush()

    entity = LegalEntity(company_id=company.id, name="Northwind Financial US Inc", country="US")
    db.add(entity)
    db.flush()

    policy = Policy(
        policy_key="revenue_sla_credit",
        version="V3.2",
        policy_type="REVENUE_SLA_CREDIT",
        status="ACTIVE",
        created_by="test",
        effective_date="2025-01-01",
        rules_json=json.dumps(CASE01_POLICY_RULES),
    )
    db.add(policy)
    db.flush()

    customer = Customer(company_id=company.id, name="Acme Corp", is_new_customer=False)
    db.add(customer)
    db.flush()

    contract = Contract(
        customer_id=customer.id,
        legal_entity_id=entity.id,
        revenue_policy_id=policy.id,
        name="Acme Corp — Enterprise Agreement C-102",
        status="ACTIVE",
    )
    db.add(contract)
    db.flush()

    invoice = Invoice(
        invoice_number="INV-4821",
        customer_id=customer.id,
        contract_id=contract.id,
        legal_entity_id=entity.id,
        currency="USD",
        total_amount=50000.00,
        status="OPEN",
    )
    db.add(invoice)
    db.flush()

    credit_memo = CreditMemo(
        memo_number="CM-129", invoice_id=invoice.id, amount=1250.00, reason="SLA_CREDIT", approved_by="Account Manager"
    )
    db.add(credit_memo)
    db.commit()

    return {
        "company": company,
        "entity": entity,
        "policy": policy,
        "customer": customer,
        "contract": contract,
        "invoice": invoice,
        "credit_memo": credit_memo,
    }

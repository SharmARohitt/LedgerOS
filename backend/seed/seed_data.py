"""Seeds a realistic mock ERP for the CASE 01 golden path (spec section 34):
a $48,750 Dodo payment against a $50,000 invoice, explained by a $1,250 SLA
credit memo. Also seeds 37 historical SLA-credit decisions (36 approved / 1
rejected) so the decision memory feature has real organizational history to
retrieve, matching the spec's "37 previous SLA credit cases" example.

Run with: python -m seed.seed_data
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.decisions.memory import amount_band  # noqa: E402
from app.models.contracts import Contract, Policy  # noqa: E402
from app.models.decisions import Decision, DecisionMemoryEntry  # noqa: E402
from app.models.events import FinancialEvent  # noqa: E402
from app.models.finance import CreditMemo, Invoice  # noqa: E402
from app.models.investigations import ExceptionRecord, InvestigationCase  # noqa: E402
from app.models.org import Company, LegalEntity, User  # noqa: E402
from app.models.parties import Customer  # noqa: E402
from app.models.treasury import BankAccount, Obligation  # noqa: E402

POLICY_KEY = "revenue_sla_credit"
POLICY_RULES = {
    "auto_resolve_max_amount": 5000,
    "human_review_max_amount": 25000,
    "block_new_vendor_without_invoice": True,
    "block_missing_evidence": True,
    "sla_credit_tolerance": 5.00,
}

CAPITAL_RESERVE_POLICY_KEY = "capital_reserve"
CAPITAL_RESERVE_RULES = {
    "minimum_reserve": 3_000_000.00,
    "operational_buffer": 500_000.00,
}

SEED_USERS = [
    ("cfo@ledgeros.dev", "CFO", "Dana CFO"),
    ("analyst@ledgeros.dev", "ANALYST", "Alex Analyst"),
    ("auditor@ledgeros.dev", "AUDITOR", "Ari Auditor"),
    ("admin@ledgeros.dev", "ADMIN", "Sam Admin"),
]
SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "")
if not SEED_PASSWORD:
    raise RuntimeError("SEED_PASSWORD env var is required to run seed_data. Set it in .env.")


def _gen(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Company).count() > 0:
            print("Seed data already present — skipping. Delete the database to reseed.")
            return

        company = Company(id=_gen("co"), name="Northwind Financial")
        db.add(company)
        db.flush()

        entity = LegalEntity(id=_gen("ent"), company_id=company.id, name="Northwind Financial US Inc", country="US")
        db.add(entity)
        db.flush()

        for email, role, name in SEED_USERS:
            db.add(User(id=_gen("usr"), email=email, password_hash=hash_password(SEED_PASSWORD), name=name, role=role))
        db.flush()

        policy = Policy(
            id=_gen("pol"),
            policy_key=POLICY_KEY,
            version="V3.2",
            policy_type="REVENUE_SLA_CREDIT",
            status="ACTIVE",
            created_by="admin@ledgeros.dev",
            effective_date="2025-01-01",
            description="SLA credit and payment-tolerance policy for enterprise revenue contracts.",
            rules_json=json.dumps(POLICY_RULES),
        )
        db.add(policy)
        db.flush()

        customer = Customer(id=_gen("cust"), company_id=company.id, name="Acme Corp", is_new_customer=False)
        db.add(customer)
        db.flush()

        contract = Contract(
            id=_gen("contract"),
            customer_id=customer.id,
            legal_entity_id=entity.id,
            revenue_policy_id=policy.id,
            name="Acme Corp — Enterprise Agreement C-102",
            status="ACTIVE",
        )
        db.add(contract)
        db.flush()

        today = datetime.now(timezone.utc).date()

        invoice = Invoice(
            id=_gen("inv"),
            invoice_number="INV-4821",
            customer_id=customer.id,
            contract_id=contract.id,
            legal_entity_id=entity.id,
            currency="USD",
            total_amount=50000.00,
            status="OPEN",
            due_date=(today + timedelta(days=15)).isoformat(),
        )
        db.add(invoice)
        db.flush()

        credit_memo = CreditMemo(
            id=_gen("cm"),
            memo_number="CM-129",
            invoice_id=invoice.id,
            amount=1250.00,
            reason="SLA_CREDIT",
            approved_by="Account Manager",
        )
        db.add(credit_memo)
        db.flush()

        # --- Financial Twin: capital reserve policy, bank accounts, obligations ---
        capital_policy = Policy(
            id=_gen("pol"),
            policy_key=CAPITAL_RESERVE_POLICY_KEY,
            version="V1.0",
            policy_type="APPROVAL_THRESHOLD",
            status="ACTIVE",
            created_by="admin@ledgeros.dev",
            effective_date="2025-01-01",
            description="Minimum cash reserve and operational buffer the Financial Twin must preserve before capital is considered deployable.",
            rules_json=json.dumps(CAPITAL_RESERVE_RULES),
        )
        db.add(capital_policy)

        db.add(
            BankAccount(
                id=_gen("bank_acct"),
                company_id=company.id,
                legal_entity_id=entity.id,
                name="Operating Account",
                account_type="OPERATING",
                currency="USD",
                current_balance=2_600_000.00,
                is_restricted=False,
            )
        )
        db.add(
            BankAccount(
                id=_gen("bank_acct"),
                company_id=company.id,
                legal_entity_id=entity.id,
                name="Reserve Account",
                account_type="RESERVE",
                currency="USD",
                current_balance=2_000_000.00,
                is_restricted=True,
            )
        )
        db.flush()

        obligation_seed = [
            ("PAYROLL", "Biweekly payroll run", "Payroll", 620_000.00, 12),
            ("TAX", "Quarterly estimated tax payment", "State & Federal Tax Authority", 310_000.00, 25),
            ("VENDOR", "Cloud infrastructure invoice", "CloudCore Infrastructure", 380_000.00, 10),
            ("VENDOR", "Office & facilities services", "OfficeSupply Co", 210_000.00, 20),
            ("VENDOR", "Data & analytics platform", "DataVendor Inc", 140_000.00, 35),
            ("DEBT", "Term loan installment", "Silicon Valley Bank Term Loan", 300_000.00, 45),
            ("SUBSCRIPTION", "SaaS tooling bundle renewal", "SaaS Tools Bundle", 18_000.00, 5),
        ]
        for obligation_type, description, counterparty, amount, days_out in obligation_seed:
            db.add(
                Obligation(
                    id=_gen("oblig"),
                    company_id=company.id,
                    obligation_type=obligation_type,
                    description=description,
                    counterparty=counterparty,
                    amount=amount,
                    due_date=(today + timedelta(days=days_out)).isoformat(),
                    status="SCHEDULED",
                )
            )
        db.flush()

        # --- 37 historical SLA-credit cases: 36 approved, 1 rejected ---
        pattern_key = f"{POLICY_KEY}:{amount_band(1250.00)}"
        base_time = datetime.now(timezone.utc) - timedelta(days=200)

        for i in range(37):
            occurred_at = (base_time + timedelta(days=i * 5)).isoformat()
            event = FinancialEvent(
                id=_gen("evt"),
                event_type="PAYMENT_SUCCEEDED",
                source="dodo",
                source_event_id=_gen("evt_hist"),
                source_mode="SIMULATED",
                entity_id=entity.id,
                customer_id=customer.id,
                amount=48750.00,
                currency="USD",
                event_timestamp=occurred_at,
                metadata_json="{}",
                raw_reference="{}",
                normalized_reference=json.dumps({"invoice_number": "INV-HIST", "customer_reference": customer.id}),
                risk_state="LOW",
                processing_state="PROCESSED",
            )
            db.add(event)
            db.flush()

            exc = ExceptionRecord(
                id=_gen("ex"),
                event_id=event.id,
                invoice_id=invoice.id,
                customer_id=customer.id,
                exception_type="AMOUNT_MISMATCH",
                discrepancy_amount=-1250.00,
                status="RESOLVED",
                risk_score=20,
                risk_level="MEDIUM",
                summary="Historical SLA credit case (seed data).",
            )
            db.add(exc)
            db.flush()

            case = InvestigationCase(
                id=_gen("case"), exception_id=exc.id, status="COMPLETED", case_state_json="{}"
            )
            db.add(case)
            db.flush()

            decision = Decision(
                id=_gen("dec"),
                case_id=case.id,
                exception_id=exc.id,
                decision_type="AUTO_RESOLVE",
                confidence=90.0 + (i % 9),
                risk_level="MEDIUM",
                policy_id=policy.id,
                policy_version=policy.version,
                reason="Discrepancy fully explained by matching SLA credit memo (seed data).",
                explanation="Historical case seeded for decision-memory demonstration.",
                action_taken="APPLY_PAYMENT_TO_INVOICE",
            )
            db.add(decision)
            db.flush()

            is_rejected = i == 36  # last one is the single historical rejection
            db.add(
                DecisionMemoryEntry(
                    id=_gen("mem"),
                    pattern_key=pattern_key,
                    decision_id=decision.id,
                    human_outcome="REJECTED" if is_rejected else "APPROVED",
                    learning_stage="ADVISORY",
                )
            )

        db.commit()
        print(
            "Seed complete: CASE 01 entities + Financial Twin (bank accounts, obligations, capital reserve policy) "
            "+ 37 historical decision-memory entries + 4 users."
        )
        print(f"Login with any of: {[u[0] for u in SEED_USERS]} (password set via SEED_PASSWORD env var)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

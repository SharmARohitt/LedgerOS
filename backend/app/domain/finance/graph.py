"""Read-side helpers over the relational schema that answer graph-shaped
questions (payment -> invoice -> contract -> policy -> credit memo) without
introducing a separate graph database, per the spec's MVP guidance."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.contracts import Contract, Policy
from app.models.finance import CreditMemo, Invoice
from app.models.parties import Customer


@dataclass
class EvidenceChain:
    invoice: Invoice | None
    customer: Customer | None
    contract: Contract | None
    policy: Policy | None
    credit_memos: list[CreditMemo]

    @property
    def is_complete(self) -> bool:
        return self.invoice is not None and self.customer is not None and self.contract is not None


def find_invoice_by_number(db: Session, invoice_number: str) -> Invoice | None:
    return db.query(Invoice).filter(Invoice.invoice_number == invoice_number).one_or_none()


def build_evidence_chain(db: Session, invoice: Invoice | None) -> EvidenceChain:
    if invoice is None:
        return EvidenceChain(invoice=None, customer=None, contract=None, policy=None, credit_memos=[])

    customer = db.get(Customer, invoice.customer_id)
    contract = db.get(Contract, invoice.contract_id) if invoice.contract_id else None
    policy = db.get(Policy, contract.revenue_policy_id) if contract else None
    credit_memos = db.query(CreditMemo).filter(CreditMemo.invoice_id == invoice.id).all()

    return EvidenceChain(invoice=invoice, customer=customer, contract=contract, policy=policy, credit_memos=credit_memos)

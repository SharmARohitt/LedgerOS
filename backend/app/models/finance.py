from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

INVOICE_STATUSES = ("OPEN", "PARTIAL", "PAID", "VOID")
PAYMENT_STATUSES = ("SUCCEEDED", "FAILED", "REFUNDED", "DISPUTED")


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("acct"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)  # ASSET/LIABILITY/REVENUE/EXPENSE


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("inv"))
    invoice_number: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    legal_entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO date, drives AR forecasting

    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice")
    contract: Mapped["Contract"] = relationship()
    customer: Mapped["Customer"] = relationship()


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("invline"))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")


class CreditMemo(Base, TimestampMixin):
    __tablename__ = "credit_memos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("cm"))
    memo_number: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)  # e.g. SLA_CREDIT
    approved_by: Mapped[str] = mapped_column(String, nullable=False)

    invoice: Mapped["Invoice"] = relationship()


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("pay"))
    source: Mapped[str] = mapped_column(String, nullable=False, default="dodo")
    source_event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String, nullable=False, default="SUCCEEDED")
    source_mode: Mapped[str] = mapped_column(String, nullable=False, default="LIVE")  # LIVE | SIMULATED
    applied_to_invoice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    invoice: Mapped["Invoice | None"] = relationship()


class BankTransaction(Base, TimestampMixin):
    __tablename__ = "bank_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("bank"))
    reference: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    matched_payment_id: Mapped[str | None] = mapped_column(ForeignKey("payments.id"), nullable=True)


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("je"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    debit_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    credit_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    source_reference: Mapped[str] = mapped_column(String, nullable=False, default="")

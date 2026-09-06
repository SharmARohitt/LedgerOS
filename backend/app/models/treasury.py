from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

BANK_ACCOUNT_TYPES = ("OPERATING", "RESERVE", "PAYROLL")
OBLIGATION_TYPES = ("PAYROLL", "TAX", "VENDOR", "DEBT", "SUBSCRIPTION", "OTHER")
OBLIGATION_STATUSES = ("SCHEDULED", "PAID", "OVERDUE")


class BankAccount(Base, TimestampMixin):
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("bank_acct"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    legal_entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False, default="OPERATING")
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    current_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    is_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Obligation(Base, TimestampMixin):
    """A committed future outflow (payroll, tax, vendor payment, debt
    service, subscription). Feeds the Financial Twin's obligations
    breakdown and the scenario engine's burn calculation."""

    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("oblig"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    obligation_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    counterparty: Mapped[str] = mapped_column(String, nullable=False, default="")
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    status: Mapped[str] = mapped_column(String, nullable=False, default="SCHEDULED")

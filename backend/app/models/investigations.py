from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

EXCEPTION_STATUSES = ("OPEN", "INVESTIGATING", "RESOLVED", "BLOCKED")
CASE_STATUSES = ("PENDING", "RUNNING", "AWAITING_APPROVAL", "COMPLETED", "FAILED")
TASK_STATUSES = ("IDLE", "RUNNING", "WAITING", "SUCCESS", "FAILED", "ESCALATED")


class ExceptionRecord(Base, TimestampMixin):
    """A detected financial exception (named ExceptionRecord to avoid clashing
    with the Python builtin `Exception`)."""

    __tablename__ = "exceptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("ex"))
    event_id: Mapped[str] = mapped_column(ForeignKey("financial_events.id"), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    exception_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g. AMOUNT_MISMATCH, MISSING_INVOICE
    discrepancy_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
    risk_score: Mapped[int] = mapped_column(default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False, default="UNKNOWN")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")


class InvestigationCase(Base, TimestampMixin):
    __tablename__ = "investigation_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("case"))
    exception_id: Mapped[str] = mapped_column(ForeignKey("exceptions.id"), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(ForeignKey("traces.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    case_state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class CaseTask(Base, TimestampMixin):
    """One worker's execution within a case — the explicit structured state
    workers communicate through (no free-form agent chat)."""

    __tablename__ = "case_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("task"))
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_cases.id"), nullable=False)
    worker_name: Mapped[str] = mapped_column(String, nullable=False)  # EVIDENCE, PAYMENT, POLICY, DECISION, AUDIT
    status: Mapped[str] = mapped_column(String, nullable=False, default="IDLE")
    span_id: Mapped[str | None] = mapped_column(ForeignKey("spans.id"), nullable=True)
    input_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)

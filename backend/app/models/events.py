from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

EVENT_TYPES = (
    "PAYMENT_SUCCEEDED",
    "PAYMENT_FAILED",
    "REFUND",
    "DISPUTE",
    "INVOICE_CREATED",
    "INVOICE_PAID",
    "INVOICE_PARTIAL",
    "CREDIT_ISSUED",
    "JOURNAL_CREATED",
    "BANK_TRANSACTION",
    "CONTRACT_UPDATED",
    "POLICY_UPDATED",
)

PROCESSING_STATES = ("RECEIVED", "NORMALIZED", "PROCESSED", "FAILED", "DEAD_LETTER")
RISK_STATES = ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")


class FinancialEvent(Base, TimestampMixin):
    """Canonical financial event. (source, source_event_id) is unique so a
    redelivered webhook is idempotent — it updates processing_state on the
    existing row instead of creating a duplicate event.
    """

    __tablename__ = "financial_events"
    __table_args__ = (UniqueConstraint("source", "source_event_id", name="uq_event_source_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("evt"))
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="dodo")
    source_event_id: Mapped[str] = mapped_column(String, nullable=False)
    source_mode: Mapped[str] = mapped_column(String, nullable=False, default="LIVE")  # LIVE | SIMULATED

    entity_id: Mapped[str | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    event_timestamp: Mapped[str] = mapped_column(String, nullable=False)

    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    raw_reference: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    normalized_reference: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    risk_state: Mapped[str] = mapped_column(String, nullable=False, default="UNKNOWN")
    processing_state: Mapped[str] = mapped_column(String, nullable=False, default="RECEIVED")
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

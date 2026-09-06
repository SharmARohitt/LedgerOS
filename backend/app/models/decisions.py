from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

DECISION_TYPES = ("AUTO_RESOLVE", "HUMAN_REVIEW", "BLOCK")
APPROVAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("dec"))
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_cases.id"), nullable=False)
    exception_id: Mapped[str] = mapped_column(ForeignKey("exceptions.id"), nullable=False)
    decision_type: Mapped[str] = mapped_column(String, nullable=False)  # AUTO_RESOLVE | HUMAN_REVIEW | BLOCK
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id"), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_taken: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. APPLY_PAYMENT_TO_INVOICE
    trace_id: Mapped[str | None] = mapped_column(ForeignKey("traces.id"), nullable=True)


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("appr"))
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class DecisionMemoryEntry(Base, TimestampMixin):
    """Organizational decision memory. Learning is ADVISORY only here —
    promoting a pattern to an active policy is a separate, human-gated step."""

    __tablename__ = "decision_memory_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("mem"))
    pattern_key: Mapped[str] = mapped_column(String, nullable=False, index=True)  # e.g. policy_key + amount band
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    human_outcome: Mapped[str | None] = mapped_column(String, nullable=True)  # APPROVED | REJECTED | None
    learning_stage: Mapped[str] = mapped_column(String, nullable=False, default="ADVISORY")

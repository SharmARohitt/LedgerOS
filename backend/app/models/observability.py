from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

SPAN_STATUSES = ("RUNNING", "SUCCESS", "FAILED")


class Trace(Base, TimestampMixin):
    """One trace per investigation case — the root of the flight recorder."""

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("trace"))
    case_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, default="investigation")
    status: Mapped[str] = mapped_column(String, nullable=False, default="RUNNING")
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    total_cost_estimate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)


class Span(Base, TimestampMixin):
    """One agent/tool call within a trace. tool_arguments are hashed, not
    stored raw, to avoid leaking sensitive payloads into observability data."""

    __tablename__ = "spans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("span"))
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.id"), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(ForeignKey("spans.id"), nullable=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)  # e.g. evidence_worker
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_arguments_hash: Mapped[str] = mapped_column(String, nullable=False, default="")
    tool_result_reference: Mapped[str | None] = mapped_column(String, nullable=True)

    model: Mapped[str | None] = mapped_column(String, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    inference_mode: Mapped[str | None] = mapped_column(String, nullable=True)  # LIVE | FALLBACK

    policy_version: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    human_approval: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="RUNNING")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    cost_estimate: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)

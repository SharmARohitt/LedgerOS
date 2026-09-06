from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id


class ProofCapsule(Base, TimestampMixin):
    """Tamper-evident record of one decision: canonical JSON + SHA-256 hash.
    Verification recomputes the hash from current DB state and compares."""

    __tablename__ = "proof_capsules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("proof"))
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), nullable=False, unique=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_cases.id"), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(ForeignKey("traces.id"), nullable=True)
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)

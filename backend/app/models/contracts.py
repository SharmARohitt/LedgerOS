from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

# Policy types
POLICY_TYPES = ("REVENUE_SLA_CREDIT", "PAYMENT_TOLERANCE", "APPROVAL_THRESHOLD", "VENDOR_RISK")
POLICY_STATUSES = ("DRAFT", "ACTIVE", "SUPERSEDED")


class Policy(Base, TimestampMixin):
    """A versioned policy. Historical decisions reference the exact version
    that was active at decision time — a new version never rewrites history.
    """

    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("pol"))
    policy_key: Mapped[str] = mapped_column(String, nullable=False, index=True)  # stable identity across versions
    version: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "V3.2"
    policy_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # rules stored as JSON-serializable dict via Text column loaded by app code
    rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("contract"))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    legal_entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), nullable=False)
    revenue_policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")

    customer: Mapped["Customer"] = relationship(back_populates="contracts")
    revenue_policy: Mapped["Policy"] = relationship()

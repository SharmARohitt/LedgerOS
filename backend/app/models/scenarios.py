from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

SCENARIO_TYPES = (
    "REVENUE_CHANGE",
    "COLLECTIONS_CHANGE",
    "FUNDING_CHANGE",
    "EXPENSE_CHANGE",
    "DELAY_PAYMENT",
)


class Scenario(Base, TimestampMixin):
    """A persisted what-if run: baseline Financial Twin snapshot vs the
    recalculated scenario snapshot. Always SIMULATED/PROJECTED — never
    confused with actual financial state."""

    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("scenario"))
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False, default="")
    input_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    baseline_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    scenario_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

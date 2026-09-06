from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("cust"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_new_customer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    contracts: Mapped[list["Contract"]] = relationship(back_populates="customer")


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("vend"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_new_vendor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

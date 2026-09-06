from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, gen_id

# Roles: CFO, ANALYST, AUDITOR, ADMIN
ROLES = ("CFO", "ANALYST", "AUDITOR", "ADMIN")


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("co"))
    name: Mapped[str] = mapped_column(String, nullable=False)

    legal_entities: Mapped[list["LegalEntity"]] = relationship(back_populates="company")


class LegalEntity(Base, TimestampMixin):
    __tablename__ = "legal_entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("ent"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False, default="US")

    company: Mapped["Company"] = relationship(back_populates="legal_entities")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("usr"))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

"""Reference data the specialist checks read. Never written during a run.

`registry_records` is seeded sample data standing in for a real records system.
It is not a live government database, and `is_sample` exists so that claim is
backed by a column the interface can read rather than by prose alone.
"""

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.document import DocumentTypeEnum
from app.models.finding import FindingSeverityEnum
from app.models.types import portable_enum

RULE_TYPES = ("eligibility", "expiry", "required_attachment", "field_format")
RuleTypeEnum = portable_enum(*RULE_TYPES, name="rule_type")


class RegistryRecord(Base):
    __tablename__ = "registry_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(DocumentTypeEnum)

    full_name: Mapped[str] = mapped_column(String(255))
    date_of_birth: Mapped[date | None] = mapped_column(Date, default=None)
    father_name: Mapped[str | None] = mapped_column(String(255), default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    annual_income: Mapped[int | None] = mapped_column(Integer, default=None)
    issued_on: Mapped[date | None] = mapped_column(Date, default=None)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), default=None)

    # Always true for seeded data. A real records integration would be a second
    # RecordsProvider implementation, not a change to this flag.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(DocumentTypeEnum)
    rule_type: Mapped[str] = mapped_column(RuleTypeEnum)

    field_name: Mapped[str | None] = mapped_column(String(64), default=None)
    operator: Mapped[str | None] = mapped_column(String(16), default=None)
    threshold_value: Mapped[str | None] = mapped_column(String(255), default=None)

    severity: Mapped[str] = mapped_column(FindingSeverityEnum, default="warning")
    description_en: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

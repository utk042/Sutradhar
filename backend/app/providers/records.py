"""Where reference records come from.

Today there is one implementation, reading the seeded `registry_records` table
through the READ-ONLY session. A real DigiLocker or state registry integration
would be a second implementation of this same interface — which is the point of
having the interface at all.

The seeded table is sample data standing in for a real records system. It is not
a live government database, and `RegistryRecord.is_sample` is true on every row
so the interface can say so on screen rather than only in prose.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import RegistryRecord


@dataclass(frozen=True)
class ReferenceRecord:
    """One official record, flattened to the fields the checks compare."""

    record_ref: str
    is_sample: bool
    fields: dict[str, str]

    @property
    def citation(self) -> str:
        """How this record is cited on the officer's screen."""
        return f"registry_records #{self.record_ref}"


class RecordsProvider(ABC):
    @abstractmethod
    def find(self, *, doc_type: str, record_ref: str | None, full_name: str | None) -> ReferenceRecord | None:
        """Locate the official record a document claims to correspond to."""


class SeededRecordsProvider(RecordsProvider):
    """Reads the seeded table. Holds a read-only session and cannot write."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _flatten(row: RegistryRecord) -> ReferenceRecord:
        fields: dict[str, str] = {}
        if row.full_name:
            fields["full_name"] = row.full_name
        if row.date_of_birth:
            fields["date_of_birth"] = row.date_of_birth.isoformat()
        if row.father_name:
            fields["father_name"] = row.father_name
        if row.address:
            fields["address"] = row.address
        if row.annual_income is not None:
            fields["annual_income"] = str(row.annual_income)
        if row.issued_on:
            fields["issued_on"] = row.issued_on.isoformat()
        if row.issuing_authority:
            fields["issuing_authority"] = row.issuing_authority
        return ReferenceRecord(
            record_ref=row.record_ref, is_sample=row.is_sample, fields=fields
        )

    def find(
        self, *, doc_type: str, record_ref: str | None, full_name: str | None
    ) -> ReferenceRecord | None:
        # The certificate number is the reliable key; the name is a fallback for
        # documents that do not carry one.
        if record_ref:
            row = self._session.scalar(
                select(RegistryRecord).where(RegistryRecord.record_ref == record_ref)
            )
            if row is not None:
                return self._flatten(row)

        if full_name:
            row = self._session.scalar(
                select(RegistryRecord).where(
                    RegistryRecord.doc_type == doc_type,
                    RegistryRecord.full_name == full_name,
                )
            )
            if row is not None:
                return self._flatten(row)

        return None


@dataclass(frozen=True)
class ApplicableRule:
    """One rule the checks evaluate, flattened away from the ORM row."""

    rule_code: str
    rule_type: str
    field_name: str | None
    operator: str | None
    threshold_value: str | None
    severity: str
    description_en: str

    @property
    def citation(self) -> str:
        return f"rules #{self.rule_code}"


class RulesProvider(ABC):
    @abstractmethod
    def for_document_type(self, doc_type: str) -> list[ApplicableRule]:
        """The active rules that apply to this kind of document."""


class SeededRulesProvider(RulesProvider):
    """Reads the seeded `rules` table. Holds a read-only session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def for_document_type(self, doc_type: str) -> list[ApplicableRule]:
        from app.models.reference import Rule

        rows = self._session.scalars(
            select(Rule)
            .where(Rule.doc_type == doc_type, Rule.active.is_(True))
            .order_by(Rule.rule_code)
        ).all()
        return [
            ApplicableRule(
                rule_code=r.rule_code,
                rule_type=r.rule_type,
                field_name=r.field_name,
                operator=r.operator,
                threshold_value=r.threshold_value,
                severity=r.severity,
                description_en=r.description_en,
            )
            for r in rows
        ]

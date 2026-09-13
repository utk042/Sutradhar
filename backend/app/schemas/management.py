"""Schemas for a head of department managing their office."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class OfficerOut(BaseModel):
    """A colleague as the roster shows them. No password hash, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    mobile_number: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class OfficerWithWorkload(OfficerOut):
    pending: int
    decided: int


class CreateOfficer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mobile_number: str = Field(min_length=10, max_length=15, pattern=r"^[0-9]{10,15}$")
    full_name: str = Field(min_length=2, max_length=255)
    #: Long enough to be worth having. The head sets it and tells the officer;
    #: there is no email in this system and no reset flow.
    password: str = Field(min_length=12, max_length=256)


class SetActive(BaseModel):
    is_active: bool


class Reassign(BaseModel):
    assigned_to: int


class DepartmentStats(BaseModel):
    """The three numbers on the dashboard, plus what they are drawn from."""

    processed_today: int
    average_seconds: float | None
    flags_raised: int
    pending_now: int
    officers: int


class AuditRowOut(BaseModel):
    """One line of the department's audit trail.

    Carries no personal data — `detail` holds decisions and counts only, and
    `audit.record` refuses anything else.
    """

    model_config = ConfigDict(from_attributes=True)

    sequence: int
    action: str
    actor_user_id: int | None
    actor_role: str | None
    document_id: int | None
    detail_json: str
    created_at: datetime


class AuditPage(BaseModel):
    rows: list[AuditRowOut]
    total: int
    #: Whether the hash chain still verifies, so the screen can say so plainly
    #: rather than implying it.
    chain_intact: bool


class ProviderSetting(BaseModel):
    provider: str


class DecisionOut(BaseModel):
    """One decision in a document's history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    decision: str
    decided_by: int
    decided_as: str
    reason: str | None
    override_note: str | None
    superseded_by: int | None
    created_at: datetime

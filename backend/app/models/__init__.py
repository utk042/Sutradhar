"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""

from app.models.audit import AuditLogEntry
from app.models.document import Document, ExtractedField
from app.models.finding import AgentRun, Finding
from app.models.reference import RegistryRecord, Rule
from app.models.setting import Setting
from app.models.user import User

__all__ = [
    "AgentRun",
    "AuditLogEntry",
    "Document",
    "ExtractedField",
    "Finding",
    "RegistryRecord",
    "Rule",
    "Setting",
    "User",
]

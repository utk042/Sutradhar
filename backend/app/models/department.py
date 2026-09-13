"""Departments.

Every user belongs to one, and so does every document. A head of department sees
their own department and nothing else — that boundary is enforced in every query
rather than checked once at the door, because a single missed `where` clause is
how one office ends up reading another's files.
"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import UTCDateTime, utcnow


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Department {self.code}>"

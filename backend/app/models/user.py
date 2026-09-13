from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import UTCDateTime, portable_enum, utcnow

ROLES = ("officer", "dept_head")
RoleEnum = portable_enum(*ROLES, name="user_role")


class User(Base):
    """An office user. Seeded only — Sutradhar has no self-registration."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    mobile_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    # The role is also a JWT claim, but this column is the authority: every
    # request re-reads it server-side rather than trusting the token's copy.
    role: Mapped[str] = mapped_column(RoleEnum, default="officer")
    #: Which office this person works in. A head of department sees this
    #: department and no other.
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Who provisioned this account. Null for the users the seed script creates.
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        # Deliberately excludes name and mobile number: application logs must
        # never carry personally identifying data.
        return f"<User id={self.id} role={self.role}>"

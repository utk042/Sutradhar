"""Shared column types.

`portable_enum` produces a VARCHAR plus a CHECK constraint rather than a native
database ENUM. That keeps SQLite and Postgres behaviour identical and avoids
Postgres' ALTER TYPE dance when a value is added later.
"""

from datetime import datetime, timezone

from sqlalchemy import Enum, String
from sqlalchemy.types import DateTime, TypeDecorator


def portable_enum(*values: str, name: str) -> Enum:
    return Enum(*values, name=name, native_enum=False, validate_strings=True)


class UTCDateTime(TypeDecorator):
    """Timezone-aware datetime stored as UTC.

    SQLite has no native timestamptz and returns naive datetimes. Comparing a
    naive value against an aware one raises, so normalise on the way in and
    re-attach UTC on the way out.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Refusing to store a naive datetime; pass an aware one.")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


SHORT = String(64)
MEDIUM = String(255)
LONG = String(1024)

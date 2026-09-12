"""Read-write database access. The application layer only.

    ┌──────────────────────────────────────────────────────────────────┐
    │  NOTHING UNDER app/agents/ MAY IMPORT THIS MODULE.               │
    │                                                                  │
    │  Agent code imports app/db/readonly.py, which opens SQLite with  │
    │  mode=ro so the driver rejects writes before they reach the file. │
    │  tests/test_readonly_isolation.py asserts this by walking the     │
    │  import graph, and fails the build if the rule is broken.        │
    └──────────────────────────────────────────────────────────────────┘

Agents return Pydantic findings; this layer is what persists them. That keeps
"the AI can read, never write" true even for the system's own bookkeeping.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()
_settings.db_path.parent.mkdir(parents=True, exist_ok=True)

app_engine: Engine = create_engine(
    _settings.app_database_url,
    echo=False,
    future=True,
)


@event.listens_for(app_engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    """Enforce foreign keys and use WAL.

    SQLite leaves foreign keys off per connection by default, which would let
    an orphaned finding reference a deleted document. WAL lets the read-only
    agent connections read while the application writes.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


AppSessionLocal = sessionmaker(bind=app_engine, autoflush=False, expire_on_commit=False)


def get_app_session() -> Iterator[Session]:
    """FastAPI dependency yielding a read-write session."""
    session = AppSessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def app_session_scope() -> Iterator[Session]:
    """Transactional scope for scripts and background work."""
    session = AppSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

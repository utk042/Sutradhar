"""Read-only database access. The ONLY database module agent code may import.

The engine opens SQLite through a URI with `mode=ro`. This is enforced by the
driver, not by convention: an INSERT, UPDATE or DELETE raises
`sqlalchemy.exc.OperationalError` ("attempt to write a readonly database")
before anything reaches the database file. No amount of agent code, prompt
injection, or tool misuse can write through this connection.

Porting to Postgres changes this module and nothing else: point the URL at a
role created with

    CREATE ROLE sutradhar_agent LOGIN PASSWORD '...';
    GRANT CONNECT ON DATABASE sutradhar TO sutradhar_agent;
    GRANT USAGE ON SCHEMA public TO sutradhar_agent;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO sutradhar_agent;

which holds SELECT and nothing else. The guarantee is identical and it is still
the database refusing the write, not the application.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

readonly_engine: Engine = create_engine(
    _settings.readonly_database_url,
    echo=False,
    future=True,
    # A read-only connection can never hold a write lock, so pooling is safe
    # and cheap here.
    pool_pre_ping=True,
)

ReadOnlySessionLocal = sessionmaker(
    bind=readonly_engine,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def readonly_session_scope() -> Iterator[Session]:
    """Session scope for agent reads. Never commits — there is nothing to commit."""
    session = ReadOnlySessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_readonly_session() -> Iterator[Session]:
    """FastAPI dependency yielding a read-only session."""
    with readonly_session_scope() as session:
        yield session

"""Liveness and readiness.

Checks both engines, because the read-only connection failing while the
read-write one works is exactly the misconfiguration that would silently break
every check in the system.
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.db.app import app_engine
from app.db.readonly import readonly_engine
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

VERSION = "0.1.0"


def _probe(engine, label: str) -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.warning("health probe failed for %s", label, exc_info=True)
        return "unavailable"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database = _probe(app_engine, "app")
    readonly = _probe(readonly_engine, "readonly")
    return HealthResponse(
        status="ok" if database == "ok" and readonly == "ok" else "degraded",
        database=database,
        readonly_database=readonly,
        version=VERSION,
    )

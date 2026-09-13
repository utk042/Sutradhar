"""FastAPI application factory.

Routes are mounted under /api. The frontend talks to this over HTTP with
credentials included, so CORS is restricted to the configured frontend origin —
a wildcard origin cannot be combined with credentialed requests anyway.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, documents, health, management, review, stream, work
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Sutradhar",
        description=(
            "Document verification desk. Specialist checks prepare a decision; "
            "a human officer makes it."
        ),
        version=health.VERSION,
        docs_url="/api/docs" if settings.environment == "development" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.environment == "development" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(review.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")
    app.include_router(management.router, prefix="/api")
    app.include_router(work.router, prefix="/api")
    return app


app = create_app()

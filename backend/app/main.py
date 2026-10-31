"""FastAPI application factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.session import engine
from app.routers import API_ROUTERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DESCRIPTION = """
Enterprise Human Resource Management System API.

**Authentication** — call `POST /api/v1/auth/login`, then click **Authorize** and paste the
`access_token`. Browsers use the httpOnly cookie set by login instead (with the `X-CSRF-Token`
header for state-changing requests).

**Roles** — `ADMIN`, `HR`, `EMPLOYEE`. Authorization is enforced on every endpoint by the backend.
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=DESCRIPTION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,  # explicit list — never "*" with credentials
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", settings.CSRF_HEADER_NAME],
    )

    register_exception_handlers(app)

    for router in API_ROUTERS:
        app.include_router(router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """Opening the bare API address shows the interactive docs."""
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Health"], summary="Liveness + database connectivity")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()

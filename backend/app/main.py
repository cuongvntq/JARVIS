"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.errors import (
    JarvisError,
    RequestIDMiddleware,
    http_exception_handler,
    jarvis_exception_handler,
    validation_exception_handler,
)
from app.middleware.rate_limit import limiter
from app.routers import (
    auth,
    chat,
    dashboard,
    health,
    memories,
    notes,
    notifications,
    reminders,
    todos,
)

settings = get_settings()
log = structlog.get_logger()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("jarvis.startup", env=settings.app_env, version="0.1.0")
    # Auto-create schema for SQLite (E2E test environment — Alembic not run)
    if settings.database_url.startswith("sqlite"):
        from app.database import Base, engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("jarvis.sqlite_schema_created")
    if settings.app_env != "test":
        from app.services.scheduler_service import start_scheduler

        start_scheduler()
    yield
    if settings.app_env != "test":
        from app.services.scheduler_service import stop_scheduler

        stop_scheduler()
    log.info("jarvis.shutdown")


app = FastAPI(
    title="J.A.R.V.I.S Backend API",
    version="0.1.0",
    description="Personal AI Assistant — MVP 1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach limiter to app state (required by SlowAPI)
app.state.limiter = limiter

# Middleware (order matters — RequestID first so handlers can read it)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 in JARVIS error envelope format."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                "details": {},
                "request_id": request_id,
            }
        },
        headers={"Retry-After": "60"},
    )


# Exception handlers
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
app.add_exception_handler(JarvisError, jarvis_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

# Routers
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(todos.router, prefix="/v1/todos", tags=["todos"])
app.include_router(notes.router, prefix="/v1/notes", tags=["notes"])
app.include_router(memories.router, prefix="/v1/memories", tags=["memories"])
app.include_router(reminders.router, prefix="/v1/reminders", tags=["reminders"])
app.include_router(dashboard.router, prefix="/v1/dashboard", tags=["dashboard"])
app.include_router(notifications.router, prefix="/v1/notifications", tags=["notifications"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "jarvis-backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }

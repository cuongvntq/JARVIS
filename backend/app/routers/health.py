"""Health check endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check — không cần DB."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness check — verify DB connection."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}


@router.get("/health/sentry-test")
async def sentry_test() -> dict[str, str]:
    """Sentry smoke test — disabled unless ENABLE_SENTRY_TEST_ROUTE=true."""
    if os.getenv("ENABLE_SENTRY_TEST_ROUTE") != "true":
        raise HTTPException(status_code=404)
    raise ValueError("Sentry smoke test")

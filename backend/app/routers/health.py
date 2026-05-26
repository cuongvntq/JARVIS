"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness check — không cần DB."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    """Readiness check — verify DB connection."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}

"""Dashboard endpoints."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import dashboard_service

log = structlog.get_logger()
router = APIRouter()


@router.get("/today")
async def get_today_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    user_tz = current_user.timezone or "Asia/Ho_Chi_Minh"
    log.info("dashboard.today.request", user_id=str(current_user.id))
    return await dashboard_service.get_today_dashboard(db, current_user.id, user_tz)

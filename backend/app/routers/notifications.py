"""Push notification subscription endpoints."""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import JarvisError
from app.database import get_db
from app.repositories import push_subscription_repo

log = structlog.get_logger()
router = APIRouter()


class SubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.post("/subscribe", status_code=201)
async def subscribe(
    req: SubscribeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await push_subscription_repo.upsert(
        db,
        user_id=current_user.id,
        endpoint=req.endpoint,
        p256dh=req.p256dh,
        auth=req.auth,
    )
    return {
        "id": str(sub.id),
        "user_id": str(sub.user_id),
        "is_active": sub.is_active,
    }


@router.post("/unsubscribe", status_code=204)
async def unsubscribe(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    found = await push_subscription_repo.deactivate_by_user_id(db, current_user.id)
    if not found:
        raise JarvisError(404, "subscription_not_found", "Không tìm thấy subscription")

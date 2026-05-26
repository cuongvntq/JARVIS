"""FastAPI dependencies: get_current_user."""

import uuid

import structlog
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db

log = structlog.get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException

    from app.models.user import User  # local import avoids circular

    payload = decode_access_token(token)
    user_id = uuid.UUID(payload["sub"])

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=401, detail="Người dùng không tồn tại hoặc đã bị vô hiệu hóa"
        )

    return user

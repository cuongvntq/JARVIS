"""Google Calendar OAuth endpoints (Sprint 8)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.google import GoogleCalendarOut, GoogleConnectOut, GoogleStatusOut
from app.services import google_calendar_service, google_oauth_service

router = APIRouter()


@router.post("/connect", response_model=GoogleConnectOut)
async def connect(
    current_user: User = Depends(get_current_user),
) -> GoogleConnectOut:
    authorize_url = await google_oauth_service.start_connect(current_user.id)
    return GoogleConnectOut(authorize_url=authorize_url)


@router.get("/status", response_model=GoogleStatusOut)
async def status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoogleStatusOut:
    data = await google_oauth_service.get_status(db, current_user.id)
    return GoogleStatusOut.model_validate(data)


@router.delete("/disconnect", status_code=204)
async def disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await google_oauth_service.disconnect(db, current_user.id)
    return Response(status_code=204)


@router.get("/calendars", response_model=list[GoogleCalendarOut])
async def list_calendars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GoogleCalendarOut]:
    items = await google_calendar_service.list_calendars(db, current_user.id)
    return [GoogleCalendarOut.model_validate(item) for item in items]

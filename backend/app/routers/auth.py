"""Auth endpoints."""

from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import JarvisError
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/register",
    response_model=TokenResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    req: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    token_resp, raw_refresh = await auth_service.register(db, req, request)
    auth_service.set_refresh_cookie(response, raw_refresh, settings.jwt_refresh_ttl_days)
    return token_resp


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
async def login(
    req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    token_resp, raw_refresh = await auth_service.login(db, req, request)
    auth_service.set_refresh_cookie(response, raw_refresh, settings.jwt_refresh_ttl_days)
    return token_resp


def _check_csrf_origin(request: Request) -> None:
    """Reject cookie requests whose Origin is not in the allowed list.

    SameSite=Lax is site-based, not origin-based: a sibling subdomain on the
    same eTLD+1 can still send cookies. Validating Origin/Referer on every
    cookie-authenticated state-changing endpoint closes that gap regardless of
    the SameSite setting. Body-only requests (no cookie) are API/test clients
    and are always exempt.
    """
    if not request.cookies.get("refresh_token"):
        return  # body-only flow, attacker has no token to exploit

    def _origin_key(url: str) -> str:
        """Return normalized scheme://host[:port] from a URL or Origin header value."""
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}" if p.netloc else ""

    raw = request.headers.get("origin") or request.headers.get("referer", "")
    request_origin = _origin_key(raw)
    allowed = {_origin_key(o) for o in settings.cors_origins_list}
    if not request_origin or request_origin not in allowed:
        raise JarvisError(403, "forbidden", "Origin not allowed")


def _resolve_refresh_token(request: Request, req: RefreshRequest | None) -> str:
    """Cookie takes priority (browser flow); body is fallback (API/test clients)."""
    token = request.cookies.get("refresh_token") or (req.refresh_token if req else None)
    if not token:
        raise JarvisError(
            401, "invalid_refresh_token", "Refresh token không hợp lệ hoặc đã hết hạn"
        )
    return token


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: Annotated[RefreshRequest | None, Body()] = None,
) -> TokenResponse:
    _check_csrf_origin(request)
    token = _resolve_refresh_token(request, req)
    token_resp, raw_refresh = await auth_service.refresh_tokens(db, token)
    auth_service.set_refresh_cookie(response, raw_refresh, settings.jwt_refresh_ttl_days)
    return token_resp


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: Annotated[RefreshRequest | None, Body()] = None,
) -> None:
    _check_csrf_origin(request)
    token = request.cookies.get("refresh_token") or (req.refresh_token if req else None)
    if token:
        await auth_service.logout(db, token)
    auth_service.clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    return await auth_service.update_profile(db, current_user.id, req)

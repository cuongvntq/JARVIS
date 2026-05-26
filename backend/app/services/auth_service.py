"""Auth business logic."""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import JarvisError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.repositories import auth_repo, user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

log = structlog.get_logger()
settings = get_settings()


async def register(db: AsyncSession, req: RegisterRequest, request: Request) -> tuple[TokenResponse, str]:
    """Register new user. Returns (TokenResponse, raw_refresh_token)."""
    try:
        validate_password_strength(req.password)
    except ValueError as e:
        raise JarvisError(422, "weak_password", str(e))

    existing = await user_repo.get_by_email(db, req.email)
    if existing:
        raise JarvisError(409, "email_taken", "Email này đã được sử dụng")

    pw_hash = hash_password(req.password)
    user = await user_repo.create(db, req.email, pw_hash, req.name)
    log.info("auth.register", user_id=str(user.id), email=user.email)

    return await _issue_tokens(db, user, request)


async def login(db: AsyncSession, req: LoginRequest, request: Request) -> tuple[TokenResponse, str]:
    """Login with email+password. Returns (TokenResponse, raw_refresh_token)."""
    user = await user_repo.get_by_email(db, req.email)
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise JarvisError(401, "invalid_credentials", "Email hoặc mật khẩu không đúng")

    if not user.is_active:
        raise JarvisError(423, "account_disabled", "Tài khoản đã bị vô hiệu hóa")

    await user_repo.update_last_login(db, user.id)
    log.info("auth.login", user_id=str(user.id))

    return await _issue_tokens(db, user, request)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[TokenResponse, str]:
    """Rotate refresh token. Returns (TokenResponse, new_raw_refresh_token)."""
    token_hash = hash_refresh_token(refresh_token)
    session = await auth_repo.get_session_by_hash(db, token_hash)
    if not session:
        raise JarvisError(401, "invalid_refresh_token", "Refresh token không hợp lệ hoặc đã hết hạn")

    await auth_repo.revoke_session(db, session.id)

    user = await user_repo.get_by_id(db, session.user_id)
    if not user or not user.is_active:
        raise JarvisError(401, "invalid_credentials", "Tài khoản không hợp lệ")

    raw_refresh, token_hash_new = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days)
    await auth_repo.create_session(db, user.id, token_hash_new, session.user_agent, session.ip_address, expires_at)

    access_token = create_access_token(user.id, user.name)
    token_resp = TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=UserOut.model_validate(user),
    )
    return token_resp, raw_refresh


async def logout(db: AsyncSession, refresh_token_raw: str) -> None:
    token_hash = hash_refresh_token(refresh_token_raw)
    session = await auth_repo.get_session_by_hash(db, token_hash)
    if session:
        await auth_repo.revoke_session(db, session.id)
        log.info("auth.logout", session_id=str(session.id))


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    request: Request,
) -> tuple[TokenResponse, str]:
    """Create session + tokens. Returns (TokenResponse, raw_refresh_token)."""
    raw_refresh, token_hash = create_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days)

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    await auth_repo.create_session(db, user.id, token_hash, user_agent, ip_address, expires_at)

    access_token = create_access_token(user.id, user.name)
    token_resp = TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=UserOut.model_validate(user),
    )
    return token_resp, raw_refresh


def set_refresh_cookie(response: Response, raw_refresh: str, ttl_days: int) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        samesite=settings.cookie_samesite,
        max_age=ttl_days * 86400,
        path="/auth",
        secure=settings.cookie_secure,
        domain=settings.cookie_domain,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/auth", domain=settings.cookie_domain)

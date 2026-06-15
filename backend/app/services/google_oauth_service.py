"""Google Calendar OAuth (Sprint 8) — desktop loopback + PKCE flow.

Security model (`.claude/rules/05_security.md`):
- PKCE S256 + random `state` (CSRF), random loopback port (RFC 8252).
- Tokens stored only via keyring (token_store); DB keeps metadata only.
- Loopback HTTP server lives only during auth, then closes; times out if the user
  never completes consent.

This OAuth flow is entirely separate from the app's own JWT/refresh auth.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import html
import json
import secrets
import urllib.parse
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.config import get_settings
from app.core import token_store
from app.core.errors import JarvisError
from app.repositories import calendar_event_repo, calendar_sync_repo, google_repo

log = structlog.get_logger()

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_ACCESS_TOKEN_EXPIRY_BUFFER = timedelta(seconds=60)


@dataclass
class _PendingAuth:
    user_id: uuid.UUID
    code_verifier: str
    redirect_uri: str
    server: asyncio.AbstractServer
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    timeout_task: asyncio.Task[None] | None = None


# In-memory pending auth flows, keyed by `state`. Single-process desktop sidecar.
_pending: dict[str, _PendingAuth] = {}


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _require_configured() -> tuple[str, str]:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise JarvisError(
            503,
            "google_not_configured",
            "Chưa cấu hình Google OAuth (thiếu GOOGLE_CLIENT_ID/SECRET)",
        )
    return settings.google_client_id, settings.google_client_secret


# ── Connect (start OAuth) ────────────────────────────────────────────────────


async def start_connect(user_id: uuid.UUID) -> str:
    """Start a loopback OAuth flow and return the Google authorize URL to open."""
    client_id, _ = _require_configured()
    settings = get_settings()

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _s256(code_verifier)
    state = secrets.token_urlsafe(32)

    # Bind a temporary loopback server on a random free port (RFC 8252).
    server = await asyncio.start_server(
        lambda r, w: _handle_callback(state, r, w), host="127.0.0.1", port=0
    )
    port = server.sockets[0].getsockname()[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    pending = _PendingAuth(
        user_id=user_id,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        server=server,
    )
    pending.timeout_task = asyncio.create_task(
        _expire_pending(state, settings.google_oauth_callback_timeout_seconds)
    )
    _pending[state] = pending

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": settings.google_oauth_scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"
    log.info("google.connect_started", user_id=str(user_id), port=port)
    return authorize_url


async def _expire_pending(state: str, timeout_seconds: int) -> None:
    await asyncio.sleep(timeout_seconds)
    pending = _pending.pop(state, None)
    if pending is not None:
        pending.server.close()
        log.info("google.connect_timeout", user_id=str(pending.user_id))


async def _cleanup(state: str) -> None:
    pending = _pending.pop(state, None)
    if pending is None:
        return
    if pending.timeout_task is not None:
        pending.timeout_task.cancel()
    pending.server.close()


# ── Loopback callback handling ───────────────────────────────────────────────


async def _handle_callback(
    expected_state: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Handle a single HTTP request hitting the loopback redirect URI."""
    try:
        request_line = await reader.readline()
        code, state, error = _parse_callback_request(request_line)
        _, html = await process_callback(expected_state, code, state, error)
        _write_http_response(writer, html)
        await writer.drain()
    except Exception as e:
        log.error("google.callback_handler_error", error=str(e), exc_info=True)
    finally:
        writer.close()


def _parse_callback_request(request_line: bytes) -> tuple[str | None, str | None, str | None]:
    """Extract (code, state, error) from the HTTP request line 'GET /?... HTTP/1.1'."""
    try:
        parts = request_line.decode("latin-1").split(" ")
        if len(parts) < 2:
            return None, None, None
        query = urllib.parse.urlparse(parts[1]).query
        params = urllib.parse.parse_qs(query)
        return (
            params.get("code", [None])[0],
            params.get("state", [None])[0],
            params.get("error", [None])[0],
        )
    except (UnicodeDecodeError, ValueError):
        return None, None, None


async def process_callback(
    expected_state: str, code: str | None, state: str | None, error: str | None
) -> tuple[bool, str]:
    """Verify state, exchange code, store tokens. Returns (success, html_page)."""
    pending = _pending.get(expected_state)
    if pending is None or state != expected_state:
        # Wrong/unknown state — possible CSRF or expired flow. Do NOT exchange.
        log.warning("google.callback_bad_state")
        return False, _html_page("Lỗi xác thực", "State không hợp lệ hoặc phiên đã hết hạn.")
    if error or not code:
        await _cleanup(expected_state)
        return False, _html_page("Đã hủy", f"Google trả về lỗi: {error or 'thiếu mã code'}.")
    try:
        await _exchange_and_store(pending, code)
        await _cleanup(expected_state)
        return True, _html_page(
            "✅ Đã kết nối Google Calendar", "Bạn có thể đóng tab này và quay lại JARVIS."
        )
    except Exception as e:
        # exc_info=True records the full traceback; the HTTP error body (the real
        # OAuth reason, e.g. invalid_grant) is logged in _exchange_and_store below.
        log.error("google.exchange_failed", error=str(e), exc_info=True)
        await _cleanup(expected_state)
        return False, _html_page("Lỗi", "Không hoàn tất kết nối. Vui lòng thử lại.")


async def _exchange_and_store(pending: _PendingAuth, code: str) -> None:
    client_id, client_secret = _require_configured()
    settings = get_settings()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": pending.code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": pending.redirect_uri,
            },
        )
    if resp.status_code >= 400:
        # The token endpoint's error body carries the real reason (invalid_grant,
        # redirect_uri_mismatch, ...). Safe to log: error responses contain no tokens.
        log.error("google.token_exchange_http_error", status=resp.status_code, body=resp.text)
    resp.raise_for_status()
    tokens = resp.json()

    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        # Without a refresh token we can't refresh later — treat as failure.
        raise RuntimeError("Google did not return a refresh_token")
    expires_in = int(tokens.get("expires_in", 3600))
    scope = tokens.get("scope", settings.google_oauth_scopes)
    email = _email_from_id_token(tokens.get("id_token"))
    if not email:
        email = await _email_from_userinfo(access_token)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    await token_store.save_tokens(pending.user_id, refresh_token, access_token, expires_at)
    async with database.AsyncSessionLocal() as db:
        await google_repo.upsert(db, pending.user_id, email, scope, expires_at)
        await db.commit()
    log.info("google.connected", user_id=str(pending.user_id))


def _email_from_id_token(id_token: str | None) -> str | None:
    """Decode the email claim from an id_token (no signature check — TLS-trusted)."""
    if not id_token:
        return None
    try:
        payload_b64 = id_token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        email = data.get("email")
        return str(email) if email else None
    except (ValueError, json.JSONDecodeError):
        return None


async def _email_from_userinfo(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    resp.raise_for_status()
    return str(resp.json().get("email", "unknown"))


# ── Status / disconnect / token refresh ──────────────────────────────────────


_NOT_CONNECTED: dict[str, object | None] = {
    "connected": False,
    "email": None,
    "scopes": None,
    "access_token_expires_at": None,
}


async def _delete_local_state(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Remove account metadata + cached calendar data (caller must commit).

    calendar_events/calendar_sync_states FK to users, not google_oauth_accounts —
    every path that drops the account (disconnect, self-heal, forced reauth) must
    clear them too so the UI/chat don't keep showing stale cached events.
    """
    await google_repo.delete_by_user(db, user_id)
    await calendar_event_repo.delete_all_for_user(db, user_id)
    await calendar_sync_repo.delete_all_for_user(db, user_id)


async def get_status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, object | None]:
    """Report connection status.

    Connected only if BOTH the DB metadata AND the keyring token exist. If the DB
    row is present but the token is gone/corrupt (keyring cleared, machine restore,
    bad JSON), self-heal by dropping the stale row so the UI shows "not connected"
    instead of claiming connected while every calendar call 404s.
    """
    account = await google_repo.get_by_user(db, user_id)
    if account is None:
        return dict(_NOT_CONNECTED)

    tokens = await token_store.get_tokens(user_id)
    if tokens is None:
        await _delete_local_state(db, user_id)
        await db.commit()
        log.info("google.status_self_healed", user_id=str(user_id))
        return dict(_NOT_CONNECTED)

    return {
        "connected": True,
        "email": account.google_email,
        "scopes": account.scopes,
        "access_token_expires_at": account.access_token_expires_at,
    }


async def disconnect(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Revoke the token at Google (best-effort) and remove all local traces."""
    tokens = await token_store.get_tokens(user_id)
    if tokens:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(_REVOKE_URL, params={"token": tokens["refresh_token"]})
        except httpx.HTTPError as e:
            log.warning("google.revoke_failed", user_id=str(user_id), error=str(e))
    await token_store.delete_tokens(user_id)
    await _delete_local_state(db, user_id)
    await db.commit()
    log.info("google.disconnected", user_id=str(user_id))


async def get_valid_access_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return a non-expired access token, refreshing via the refresh token if needed."""
    tokens = await token_store.get_tokens(user_id)
    if tokens is None:
        raise JarvisError(404, "google_not_connected", "Chưa kết nối Google Calendar")

    expires_at = datetime.fromisoformat(tokens["access_token_expires_at"])
    if expires_at - _ACCESS_TOKEN_EXPIRY_BUFFER > datetime.now(UTC):
        return tokens["access_token"]
    return await _refresh_access_token(db, user_id, tokens["refresh_token"])


async def _refresh_access_token(db: AsyncSession, user_id: uuid.UUID, refresh_token: str) -> str:
    client_id, client_secret = _require_configured()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )

    if resp.status_code == 400:
        # invalid_grant: refresh token revoked/expired → force re-auth.
        await token_store.delete_tokens(user_id)
        await _delete_local_state(db, user_id)
        await db.commit()
        raise JarvisError(401, "google_reauth_required", "Cần kết nối lại Google Calendar")
    if resp.status_code >= 400:
        log.error("google.token_refresh_http_error", status=resp.status_code, body=resp.text)
    resp.raise_for_status()

    data = resp.json()
    new_access = str(data["access_token"])
    expires_in = int(data.get("expires_in", 3600))
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    # Refresh responses normally omit a new refresh_token; keep the existing one.
    await token_store.save_tokens(user_id, refresh_token, new_access, expires_at)
    await google_repo.update_expiry(db, user_id, expires_at)
    await db.commit()
    log.info("google.token_refreshed", user_id=str(user_id))
    return new_access


async def force_refresh_access_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Refresh the access token regardless of its stored expiry.

    Used when a calendar API call returns 401 even though the cached token has not
    expired yet (e.g. the token was revoked server-side). Raises
    google_not_connected / google_reauth_required if no usable token remains.
    """
    tokens = await token_store.get_tokens(user_id)
    if tokens is None:
        raise JarvisError(404, "google_not_connected", "Chưa kết nối Google Calendar")
    return await _refresh_access_token(db, user_id, tokens["refresh_token"])


async def clear_local_connection(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Drop local token + DB metadata + cached calendar data WITHOUT calling Google revoke.

    For when the token is already invalid server-side (revoked); there is nothing
    useful to revoke, we just need the local state to reflect "not connected".
    """
    await token_store.delete_tokens(user_id)
    await _delete_local_state(db, user_id)
    await db.commit()
    log.info("google.connection_cleared", user_id=str(user_id))


def _html_page(title: str, message: str) -> str:
    # Escape: `message` may include the OAuth `error` query param reflected from the
    # callback. Low impact (local loopback, correct state required) but escape anyway.
    title = html.escape(title)
    message = html.escape(message)
    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        f"<title>{title}</title></head>"
        "<body style='font-family:system-ui;background:#0b1929;color:#dff3fd;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "height:100vh;margin:0'>"
        f"<h1 style='color:#00b4d8'>{title}</h1><p>{message}</p></body></html>"
    )


def _write_http_response(writer: asyncio.StreamWriter, html: str) -> None:
    body = html.encode("utf-8")
    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
    )
    writer.write(headers.encode("ascii") + body)

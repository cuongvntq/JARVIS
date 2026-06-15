"""Google Calendar OAuth tests (Sprint 8).

The real flow opens a loopback HTTP server, calls Google's token endpoint, and
stores tokens in the OS keyring. Tests mock httpx (external Google calls) and
keyring (token_store) while using the real SQLite test DB.
"""

import base64
import json
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import sqlalchemy as sa

from app.config import get_settings
from app.core.errors import JarvisError
from app.database import AsyncSessionLocal
from app.models.calendar_event import CalendarEvent
from app.repositories import calendar_event_repo, calendar_sync_repo, google_repo
from app.services import google_calendar_service, google_oauth_service

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_user_id(async_client, auth_headers) -> uuid.UUID:
    resp = await async_client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return uuid.UUID(resp.json()["id"])


def _fake_id_token(email: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).decode().rstrip("=")
    return f"header.{payload}.sig"


class _FakeResp:
    def __init__(self, status_code: int = 200, json_data: dict | None = None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)  # type: ignore[arg-type]


class _FakeClient:
    def __init__(self, post_resp: _FakeResp | None = None, get_resp: _FakeResp | None = None):
        self._post_resp = post_resp
        self._get_resp = get_resp

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def post(self, *args: object, **kwargs: object) -> _FakeResp:
        assert self._post_resp is not None
        return self._post_resp

    async def get(self, *args: object, **kwargs: object) -> _FakeResp:
        assert self._get_resp is not None
        return self._get_resp

    async def request(self, method: str, *args: object, **kwargs: object) -> _FakeResp:
        if method.upper() == "POST":
            return await self.post(*args, **kwargs)
        return await self.get(*args, **kwargs)


@pytest.fixture
def google_configured():
    """Make settings look like Google OAuth is configured."""
    settings = get_settings()
    old_id, old_secret = settings.google_client_id, settings.google_client_secret
    settings.google_client_id = "test-client-id.apps.googleusercontent.com"
    settings.google_client_secret = "test-secret"
    yield
    settings.google_client_id, settings.google_client_secret = old_id, old_secret


# ── Status / connect ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_not_connected(async_client, auth_headers):
    resp = await async_client.get("/v1/google/calendar/status", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["email"] is None


@pytest.mark.asyncio
async def test_connect_returns_authorize_url_with_pkce(
    async_client, auth_headers, google_configured
):
    resp = await async_client.post("/v1/google/calendar/connect", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    url = resp.json()["authorize_url"]

    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    assert parsed.hostname == "accounts.google.com"
    assert params["code_challenge_method"] == ["S256"]
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert "code_challenge" in params
    assert "calendar.readonly" in params["scope"][0]
    assert params["redirect_uri"][0].startswith("http://127.0.0.1:")
    state = params["state"][0]

    # Clean up the loopback server + timeout task this opened.
    await google_oauth_service._cleanup(state)


@pytest.mark.asyncio
async def test_connect_not_configured(async_client, auth_headers):
    # Force creds absent (the loaded .env may define them) → 503 google_not_configured.
    settings = get_settings()
    old_id, old_secret = settings.google_client_id, settings.google_client_secret
    settings.google_client_id = None
    settings.google_client_secret = None
    try:
        resp = await async_client.post("/v1/google/calendar/connect", headers=auth_headers)
    finally:
        settings.google_client_id, settings.google_client_secret = old_id, old_secret
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "google_not_configured"


# ── Callback processing ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_callback_rejects_bad_state():
    # Unknown/mismatched state must not trigger any token exchange.
    success, html = await google_oauth_service.process_callback(
        "expected-state", code="some-code", state="attacker-state", error=None
    )
    assert success is False
    assert "State không hợp lệ" in html


@pytest.mark.asyncio
async def test_callback_exchange_success_persists_account(
    async_client, auth_headers, google_configured
):
    user_id = await _get_user_id(async_client, auth_headers)

    # Start a real flow to register pending + loopback server, then drive the callback.
    authorize_url = await google_oauth_service.start_connect(user_id)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(authorize_url).query)["state"][0]

    token_resp = _FakeResp(
        json_data={
            "access_token": "ya29.access",
            "refresh_token": "1//refresh",
            "expires_in": 3600,
            "scope": "openid email https://www.googleapis.com/auth/calendar.readonly",
            "id_token": _fake_id_token("me@gmail.com"),
        }
    )

    with (
        patch("app.core.token_store.save_tokens", new_callable=AsyncMock) as mock_save,
        patch(
            "app.services.google_oauth_service.httpx.AsyncClient",
            return_value=_FakeClient(post_resp=token_resp),
        ),
    ):
        success, html = await google_oauth_service.process_callback(
            state, code="auth-code", state=state, error=None
        )

    assert success is True
    assert "Đã kết nối" in html
    mock_save.assert_awaited_once()

    async with AsyncSessionLocal() as db:
        account = await google_repo.get_by_user(db, user_id)
    assert account is not None
    assert account.google_email == "me@gmail.com"


# ── Token refresh ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_valid_access_token_returns_cached_when_fresh(async_client, auth_headers):
    user_id = await _get_user_id(async_client, auth_headers)
    future = datetime.now(UTC) + timedelta(minutes=30)
    tokens = {
        "refresh_token": "1//refresh",
        "access_token": "ya29.fresh",
        "access_token_expires_at": future.isoformat(),
    }
    with patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=tokens):
        async with AsyncSessionLocal() as db:
            token = await google_oauth_service.get_valid_access_token(db, user_id)
    assert token == "ya29.fresh"


@pytest.mark.asyncio
async def test_get_valid_access_token_refreshes_when_expired(
    async_client, auth_headers, google_configured
):
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await google_repo.upsert(
            db, user_id, "me@gmail.com", "scope", datetime.now(UTC) - timedelta(minutes=5)
        )
        await db.commit()

    expired = datetime.now(UTC) - timedelta(minutes=5)
    tokens = {
        "refresh_token": "1//refresh",
        "access_token": "ya29.old",
        "access_token_expires_at": expired.isoformat(),
    }
    refresh_resp = _FakeResp(json_data={"access_token": "ya29.new", "expires_in": 3600})

    with (
        patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=tokens),
        patch("app.core.token_store.save_tokens", new_callable=AsyncMock) as mock_save,
        patch(
            "app.services.google_oauth_service.httpx.AsyncClient",
            return_value=_FakeClient(post_resp=refresh_resp),
        ),
    ):
        async with AsyncSessionLocal() as db:
            token = await google_oauth_service.get_valid_access_token(db, user_id)

    assert token == "ya29.new"
    mock_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_invalid_grant_forces_reauth(async_client, auth_headers, google_configured):
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await google_repo.upsert(
            db, user_id, "me@gmail.com", "scope", datetime.now(UTC) - timedelta(minutes=5)
        )
        await db.commit()

    expired = datetime.now(UTC) - timedelta(minutes=5)
    tokens = {
        "refresh_token": "1//revoked",
        "access_token": "ya29.old",
        "access_token_expires_at": expired.isoformat(),
    }
    invalid_grant = _FakeResp(status_code=400, json_data={"error": "invalid_grant"})

    with (
        patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=tokens),
        patch("app.core.token_store.delete_tokens", new_callable=AsyncMock) as mock_del,
        patch(
            "app.services.google_oauth_service.httpx.AsyncClient",
            return_value=_FakeClient(post_resp=invalid_grant),
        ),
    ):
        async with AsyncSessionLocal() as db:
            with pytest.raises(JarvisError) as exc:
                await google_oauth_service.get_valid_access_token(db, user_id)

    assert exc.value.code == "google_reauth_required"
    mock_del.assert_awaited_once()
    async with AsyncSessionLocal() as db:
        assert await google_repo.get_by_user(db, user_id) is None


# ── Disconnect ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disconnect_revokes_and_clears(async_client, auth_headers):
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await google_repo.upsert(
            db, user_id, "me@gmail.com", "scope", datetime.now(UTC) + timedelta(hours=1)
        )
        await db.commit()

    tokens = {
        "refresh_token": "1//refresh",
        "access_token": "ya29.x",
        "access_token_expires_at": datetime.now(UTC).isoformat(),
    }
    with (
        patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=tokens),
        patch("app.core.token_store.delete_tokens", new_callable=AsyncMock) as mock_del,
        patch(
            "app.services.google_oauth_service.httpx.AsyncClient",
            return_value=_FakeClient(post_resp=_FakeResp()),
        ),
    ):
        resp = await async_client.delete("/v1/google/calendar/disconnect", headers=auth_headers)

    assert resp.status_code == 204
    mock_del.assert_awaited_once()
    async with AsyncSessionLocal() as db:
        assert await google_repo.get_by_user(db, user_id) is None


# ── List calendars ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_calendars_maps_fields(async_client, auth_headers):
    cal_resp = _FakeResp(
        json_data={
            "items": [
                {
                    "id": "primary@gmail.com",
                    "summary": "Lịch chính",
                    "primary": True,
                    "timeZone": "Asia/Ho_Chi_Minh",
                },
                {"id": "work@group.calendar.google.com", "summary": "Công việc"},
            ]
        }
    )
    with (
        patch(
            "app.services.google_oauth_service.get_valid_access_token",
            new_callable=AsyncMock,
            return_value="ya29.access",
        ),
        patch(
            "app.services.google_calendar_service.httpx.AsyncClient",
            return_value=_FakeClient(get_resp=cal_resp),
        ),
    ):
        resp = await async_client.get("/v1/google/calendar/calendars", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items[0]["primary"] is True
    assert items[0]["time_zone"] == "Asia/Ho_Chi_Minh"
    assert items[1]["primary"] is False


@pytest.mark.asyncio
async def test_list_calendars_not_connected_returns_404(async_client, auth_headers):
    # No tokens stored → get_valid_access_token raises google_not_connected.
    with patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=None):
        resp = await async_client.get("/v1/google/calendar/calendars", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "google_not_connected"


# ── Review fixes: status self-heal + 401 recovery ─────────────────────────────


@pytest.mark.asyncio
async def test_status_self_heals_when_token_missing(async_client, auth_headers):
    """DB says connected but keyring token is gone → status returns not connected,
    the stale DB row is removed, AND cached calendar data is cleared (P2a) so the
    dashboard/chat don't keep showing events from a calendar JARVIS no longer
    has access to."""
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await google_repo.upsert(
            db, user_id, "me@gmail.com", "scope", datetime.now(UTC) + timedelta(hours=1)
        )
        await calendar_sync_repo.upsert_from_calendar_list(
            db,
            user_id,
            [
                {
                    "google_calendar_id": "primary",
                    "calendar_summary": "Primary",
                    "is_primary": True,
                    "time_zone": "UTC",
                    "access_role": "owner",
                }
            ],
        )
        await calendar_event_repo.upsert(
            db,
            user_id,
            "primary",
            "evt1",
            summary="Stale meeting",
            is_all_day=False,
            status="confirmed",
        )
        await db.commit()

    with patch("app.core.token_store.get_tokens", new_callable=AsyncMock, return_value=None):
        resp = await async_client.get("/v1/google/calendar/status", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    async with AsyncSessionLocal() as db:
        assert await google_repo.get_by_user(db, user_id) is None  # self-healed
        assert await calendar_sync_repo.list_for_user(db, user_id) == []
        result = await db.execute(sa.select(CalendarEvent).where(CalendarEvent.user_id == user_id))
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_list_calendars_force_refreshes_on_401(async_client, auth_headers):
    """Calendar API 401 (token revoked before expiry) → force refresh once + retry
    succeeds (P2b)."""
    items = {"items": [{"id": "primary@gmail.com", "summary": "Lịch", "primary": True}]}
    with (
        patch(
            "app.services.google_oauth_service.get_valid_access_token",
            new_callable=AsyncMock,
            return_value="ya29.stale",
        ),
        patch(
            "app.services.google_oauth_service.force_refresh_access_token",
            new_callable=AsyncMock,
            return_value="ya29.fresh",
        ) as mock_fr,
        patch(
            "app.services.google_calendar_service._request",
            new_callable=AsyncMock,
            side_effect=[_FakeResp(status_code=401), _FakeResp(json_data=items)],
        ),
    ):
        resp = await async_client.get("/v1/google/calendar/calendars", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["id"] == "primary@gmail.com"
    mock_fr.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_calendars_clears_state_when_still_401(async_client, auth_headers):
    """If the calendar API still 401s after a forced refresh → clear local state
    (account metadata + cached calendar events/sync state) and require reconnect
    (P2b), so the dashboard/chat don't keep showing events from a calendar JARVIS
    no longer has access to."""
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await google_repo.upsert(
            db, user_id, "me@gmail.com", "scope", datetime.now(UTC) + timedelta(hours=1)
        )
        await calendar_sync_repo.upsert_from_calendar_list(
            db,
            user_id,
            [
                {
                    "google_calendar_id": "primary",
                    "calendar_summary": "Primary",
                    "is_primary": True,
                    "time_zone": "UTC",
                    "access_role": "owner",
                }
            ],
        )
        await calendar_event_repo.upsert(
            db,
            user_id,
            "primary",
            "evt1",
            summary="Stale meeting",
            is_all_day=False,
            status="confirmed",
        )
        await db.commit()

    with (
        patch(
            "app.services.google_oauth_service.get_valid_access_token",
            new_callable=AsyncMock,
            return_value="ya29.stale",
        ),
        patch(
            "app.services.google_oauth_service.force_refresh_access_token",
            new_callable=AsyncMock,
            return_value="ya29.fresh",
        ),
        patch("app.core.token_store.delete_tokens", new_callable=AsyncMock),
        patch(
            "app.services.google_calendar_service._request",
            new_callable=AsyncMock,
            side_effect=[_FakeResp(status_code=401), _FakeResp(status_code=401)],
        ),
    ):
        resp = await async_client.get("/v1/google/calendar/calendars", headers=auth_headers)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "google_reauth_required"
    async with AsyncSessionLocal() as db:
        assert await google_repo.get_by_user(db, user_id) is None
        assert await calendar_sync_repo.list_for_user(db, user_id) == []
        result = await db.execute(sa.select(CalendarEvent).where(CalendarEvent.user_id == user_id))
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_callback_html_escapes_error(async_client, auth_headers, google_configured):
    """Reflected OAuth error must be HTML-escaped in the callback page (P3)."""
    user_id = await _get_user_id(async_client, auth_headers)
    authorize_url = await google_oauth_service.start_connect(user_id)
    state = urllib.parse.parse_qs(urllib.parse.urlparse(authorize_url).query)["state"][0]

    _, page = await google_oauth_service.process_callback(
        state, code=None, state=state, error="<script>alert(1)</script>"
    )
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


# Reference google_calendar_service so linters keep the import (used via patched paths).
assert google_calendar_service is not None

"""Sprint 9 — Google Calendar read-only sync tests.

Covers: repositories (calendar_event_repo, calendar_sync_repo), service
(sync_calendar/sync_all_selected/list_events/selection), endpoints
(/events, /sync, /selected), and the list_calendar_events/get_today_summary
chat tools. External Google HTTP calls are mocked via `_authed_request`.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.database import AsyncSessionLocal
from app.repositories import calendar_event_repo, calendar_sync_repo
from app.services import google_calendar_service
from app.tools.executors import execute_get_today_summary, execute_list_calendar_events
from tests.conftest import _TestSession


@pytest_asyncio.fixture
async def db_session():
    async with _TestSession() as session:
        yield session
        await session.rollback()


class _FakeResp:
    def __init__(self, status_code: int = 200, json_data: dict | None = None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


async def _get_user_id(async_client, auth_headers) -> uuid.UUID:
    resp = await async_client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return uuid.UUID(resp.json()["id"])


_PRIMARY_CALENDAR = {
    "google_calendar_id": "primary",
    "calendar_summary": "Primary",
    "is_primary": True,
    "time_zone": "UTC",
    "access_role": "owner",
}
_WORK_CALENDAR = {
    "google_calendar_id": "work",
    "calendar_summary": "Work",
    "is_primary": False,
    "time_zone": "UTC",
    "access_role": "reader",
}


# ── calendar_event_repo ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(db_session):
    user_id = uuid.uuid4()
    event = await calendar_event_repo.upsert(
        db_session, user_id, "primary", "evt1", summary="Old", is_all_day=False, status="confirmed"
    )
    await db_session.commit()
    assert event.summary == "Old"

    event2 = await calendar_event_repo.upsert(
        db_session, user_id, "primary", "evt1", summary="New", is_all_day=False, status="confirmed"
    )
    await db_session.commit()
    assert event2.id == event.id
    assert event2.summary == "New"


@pytest.mark.asyncio
async def test_list_in_range_timed_event(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt1",
        summary="Meeting",
        is_all_day=False,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        status="confirmed",
    )
    await db_session.commit()

    events = await calendar_event_repo.list_in_range(
        db_session, user_id, now, now + timedelta(days=1), "UTC"
    )
    assert [e.summary for e in events] == ["Meeting"]

    # Out of range query returns nothing.
    far_future = now + timedelta(days=10)
    events_out = await calendar_event_repo.list_in_range(
        db_session, user_id, far_future, far_future + timedelta(days=1), "UTC"
    )
    assert events_out == []


@pytest.mark.asyncio
async def test_list_in_range_allday_event_spans_range(db_session):
    user_id = uuid.uuid4()
    today = datetime.now(UTC).date()
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt-allday",
        summary="Holiday",
        is_all_day=True,
        start_date=today,
        end_date=today + timedelta(days=2),
        status="confirmed",
    )
    await db_session.commit()

    time_min = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    events = await calendar_event_repo.list_in_range(
        db_session, user_id, time_min, time_min + timedelta(days=1), "UTC"
    )
    assert [e.summary for e in events] == ["Holiday"]


@pytest.mark.asyncio
async def test_list_today_excludes_future_events(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt-today",
        summary="Today",
        is_all_day=False,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status="confirmed",
    )
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt-future",
        summary="Future",
        is_all_day=False,
        start_at=now + timedelta(days=5),
        end_at=now + timedelta(days=5, hours=1),
        status="confirmed",
    )
    await db_session.commit()

    events = await calendar_event_repo.list_today(db_session, user_id, "UTC")
    assert [e.summary for e in events] == ["Today"]


@pytest.mark.asyncio
async def test_delete_all_for_calendar(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt1",
        summary="A",
        is_all_day=False,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status="confirmed",
    )
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "work",
        "evt2",
        summary="B",
        is_all_day=False,
        start_at=now,
        end_at=now + timedelta(hours=1),
        status="confirmed",
    )
    await db_session.commit()

    await calendar_event_repo.delete_all_for_calendar(db_session, user_id, "primary")
    await db_session.commit()

    now = datetime.now(UTC)
    remaining = await calendar_event_repo.list_in_range(
        db_session, user_id, now - timedelta(days=1), now + timedelta(days=1), "UTC"
    )
    assert [e.google_calendar_id for e in remaining] == ["work"]


# ── calendar_sync_repo ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_from_calendar_list_selection_rule(db_session):
    user_id = uuid.uuid4()
    states, vanished = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR, _WORK_CALENDAR]
    )
    await db_session.commit()

    assert vanished == []
    by_id = {s.google_calendar_id: s for s in states}
    assert by_id["primary"].selected is True
    assert by_id["work"].selected is False


@pytest.mark.asyncio
async def test_upsert_from_calendar_list_reconciles_vanished(db_session):
    user_id = uuid.uuid4()
    await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR, _WORK_CALENDAR]
    )
    await db_session.commit()

    _, vanished = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    assert vanished == ["work"]

    remaining = await calendar_sync_repo.list_for_user(db_session, user_id)
    assert [s.google_calendar_id for s in remaining] == ["primary"]


@pytest.mark.asyncio
async def test_set_selected_returns_newly_unselected(db_session):
    user_id = uuid.uuid4()
    await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR, _WORK_CALENDAR]
    )
    await db_session.commit()

    newly_unselected = await calendar_sync_repo.set_selected(db_session, user_id, ["work"])
    await db_session.commit()
    assert newly_unselected == ["primary"]

    states = await calendar_sync_repo.list_for_user(db_session, user_id)
    by_id = {s.google_calendar_id: s for s in states}
    assert by_id["primary"].selected is False
    assert by_id["work"].selected is True


# ── google_calendar_service: sync_calendar ──────────────────────────────────────


@pytest.mark.asyncio
async def test_full_sync_upserts_events_and_sets_horizon(db_session):
    user_id = uuid.uuid4()
    states, _ = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    sync_state = states[0]

    events_page = {
        "items": [
            {
                "id": "evt1",
                "summary": "Meeting",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-16T01:00:00+00:00"},
                "end": {"dateTime": "2026-06-16T02:00:00+00:00"},
            }
        ],
        "nextSyncToken": "sync-token-1",
    }
    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        return_value=_FakeResp(json_data=events_page),
    ):
        result = await google_calendar_service.sync_calendar(db_session, user_id, sync_state)

    assert result == {"upserted": 1, "deleted": 0}

    refreshed = await calendar_sync_repo.get(db_session, user_id, "primary")
    assert refreshed is not None
    assert refreshed.sync_token == "sync-token-1"
    assert refreshed.horizon_until is not None
    assert refreshed.last_full_synced_at is not None


@pytest.mark.asyncio
async def test_incremental_sync_sends_sync_token(db_session):
    user_id = uuid.uuid4()
    states, _ = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    sync_state = states[0]

    now = datetime.now(UTC)
    sync_state.sync_token = "old-token"
    sync_state.horizon_until = now + timedelta(days=360)
    sync_state.last_full_synced_at = now
    sync_state.last_synced_at = now
    await db_session.flush()
    await db_session.commit()

    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        return_value=_FakeResp(json_data={"items": [], "nextSyncToken": "new-token"}),
    ) as mock_request:
        result = await google_calendar_service.sync_calendar(db_session, user_id, sync_state)

    assert result == {"upserted": 0, "deleted": 0}
    _, kwargs = mock_request.call_args
    assert kwargs["params"]["syncToken"] == "old-token"

    refreshed = await calendar_sync_repo.get(db_session, user_id, "primary")
    assert refreshed is not None
    assert refreshed.sync_token == "new-token"


@pytest.mark.asyncio
async def test_full_sync_pagination_keeps_time_range_on_later_pages(db_session):
    user_id = uuid.uuid4()
    states, _ = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    sync_state = states[0]

    page1 = {
        "items": [
            {
                "id": "evt1",
                "summary": "Meeting 1",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-16T01:00:00+00:00"},
                "end": {"dateTime": "2026-06-16T02:00:00+00:00"},
            }
        ],
        "nextPageToken": "page-2",
    }
    page2 = {
        "items": [
            {
                "id": "evt2",
                "summary": "Meeting 2",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-17T01:00:00+00:00"},
                "end": {"dateTime": "2026-06-17T02:00:00+00:00"},
            }
        ],
        "nextSyncToken": "sync-token-2",
    }
    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        side_effect=[_FakeResp(json_data=page1), _FakeResp(json_data=page2)],
    ) as mock_request:
        result = await google_calendar_service.sync_calendar(db_session, user_id, sync_state)

    assert result == {"upserted": 2, "deleted": 0}

    _, kwargs1 = mock_request.call_args_list[0]
    _, kwargs2 = mock_request.call_args_list[1]
    assert "timeMin" in kwargs1["params"]
    assert "timeMax" in kwargs1["params"]
    assert kwargs2["params"]["pageToken"] == "page-2"
    assert kwargs2["params"]["timeMin"] == kwargs1["params"]["timeMin"]
    assert kwargs2["params"]["timeMax"] == kwargs1["params"]["timeMax"]


@pytest.mark.asyncio
async def test_incremental_sync_pagination_keeps_sync_token_on_later_pages(db_session):
    user_id = uuid.uuid4()
    states, _ = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    sync_state = states[0]

    now = datetime.now(UTC)
    sync_state.sync_token = "old-token"
    sync_state.horizon_until = now + timedelta(days=360)
    sync_state.last_full_synced_at = now
    sync_state.last_synced_at = now
    await db_session.flush()
    await db_session.commit()

    page1 = {
        "items": [
            {
                "id": "evt1",
                "summary": "Meeting 1",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-16T01:00:00+00:00"},
                "end": {"dateTime": "2026-06-16T02:00:00+00:00"},
            }
        ],
        "nextPageToken": "page-2",
    }
    page2 = {
        "items": [
            {
                "id": "evt2",
                "summary": "Meeting 2",
                "status": "confirmed",
                "start": {"dateTime": "2026-06-17T01:00:00+00:00"},
                "end": {"dateTime": "2026-06-17T02:00:00+00:00"},
            }
        ],
        "nextSyncToken": "new-token",
    }
    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        side_effect=[_FakeResp(json_data=page1), _FakeResp(json_data=page2)],
    ) as mock_request:
        result = await google_calendar_service.sync_calendar(db_session, user_id, sync_state)

    assert result == {"upserted": 2, "deleted": 0}

    _, kwargs1 = mock_request.call_args_list[0]
    _, kwargs2 = mock_request.call_args_list[1]
    assert kwargs1["params"]["syncToken"] == "old-token"
    assert kwargs2["params"]["pageToken"] == "page-2"
    assert kwargs2["params"]["syncToken"] == "old-token"

    refreshed = await calendar_sync_repo.get(db_session, user_id, "primary")
    assert refreshed is not None
    assert refreshed.sync_token == "new-token"


@pytest.mark.asyncio
async def test_sync_falls_back_to_full_on_410(db_session):
    user_id = uuid.uuid4()
    states, _ = await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR]
    )
    await db_session.commit()
    sync_state = states[0]

    now = datetime.now(UTC)
    sync_state.sync_token = "expired-token"
    sync_state.horizon_until = now + timedelta(days=360)
    sync_state.last_full_synced_at = now
    sync_state.last_synced_at = now
    await db_session.flush()
    await db_session.commit()

    responses = [
        _FakeResp(status_code=410),
        _FakeResp(json_data={"items": [], "nextSyncToken": "fresh-token"}),
    ]
    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        side_effect=responses,
    ):
        result = await google_calendar_service.sync_calendar(db_session, user_id, sync_state)

    assert result == {"upserted": 0, "deleted": 0}
    refreshed = await calendar_sync_repo.get(db_session, user_id, "primary")
    assert refreshed is not None
    assert refreshed.sync_token == "fresh-token"
    assert refreshed.last_full_synced_at is not None


# ── google_calendar_service: sync_all_selected + lock ────────────────────────────


@pytest.mark.asyncio
async def test_sync_all_selected_swallows_per_calendar_errors(db_session):
    user_id = uuid.uuid4()
    await calendar_sync_repo.upsert_from_calendar_list(
        db_session, user_id, [_PRIMARY_CALENDAR, _WORK_CALENDAR]
    )
    await calendar_sync_repo.set_selected(db_session, user_id, ["primary", "work"])
    await db_session.commit()

    calendar_list_resp = _FakeResp(
        json_data={
            "items": [
                {"id": "primary", "summary": "Primary", "primary": True, "timeZone": "UTC"},
                {"id": "work", "summary": "Work", "primary": False, "timeZone": "UTC"},
            ]
        }
    )

    async def fake_sync_calendar(db, uid, sync_state):
        if sync_state.google_calendar_id == "work":
            raise RuntimeError("boom")
        return {"upserted": 1, "deleted": 0}

    with (
        patch(
            "app.services.google_calendar_service._authed_request",
            new_callable=AsyncMock,
            return_value=calendar_list_resp,
        ),
        patch(
            "app.services.google_calendar_service.sync_calendar",
            side_effect=fake_sync_calendar,
        ),
    ):
        result = await google_calendar_service.sync_all_selected(db_session, user_id)

    assert result["upserted"] == 1
    assert result["deleted"] == 0
    assert result["failed"] == 1
    assert result["errors"] == [{"calendar_id": "work", "message": "boom"}]


@pytest.mark.asyncio
async def test_sync_all_selected_reports_failure_when_calendar_list_refresh_fails(db_session):
    """No calendars selected yet + refresh_calendar_list fails (e.g. auth) must
    not be reported as a clean "synced" — see PR review finding."""
    user_id = uuid.uuid4()

    with patch(
        "app.services.google_calendar_service._authed_request",
        new_callable=AsyncMock,
        side_effect=RuntimeError("token invalid"),
    ):
        result = await google_calendar_service.sync_all_selected(db_session, user_id)

    assert result["upserted"] == 0
    assert result["deleted"] == 0
    assert result["failed"] == 1
    assert result["errors"] == [{"calendar_id": "_calendar_list", "message": "token invalid"}]


@pytest.mark.asyncio
async def test_is_sync_running_reflects_lock_state():
    user_id = uuid.uuid4()
    assert google_calendar_service.is_sync_running(user_id) is False

    lock = google_calendar_service._get_lock(user_id)
    async with lock:
        assert google_calendar_service.is_sync_running(user_id) is True

    assert google_calendar_service.is_sync_running(user_id) is False


# ── Endpoints ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_events_returns_cached_events(async_client, auth_headers):
    user_id = await _get_user_id(async_client, auth_headers)
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        await calendar_event_repo.upsert(
            db,
            user_id,
            "primary",
            "evt1",
            summary="Demo Event",
            is_all_day=False,
            start_at=now + timedelta(hours=1),
            end_at=now + timedelta(hours=2),
            status="confirmed",
        )
        await db.commit()

    resp = await async_client.get("/v1/google/calendar/events", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    summaries = [e["summary"] for e in resp.json()]
    assert "Demo Event" in summaries


@pytest.mark.asyncio
async def test_get_events_unauthenticated(async_client):
    resp = await async_client.get("/v1/google/calendar/events")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_events_rejects_naive_time_min(async_client, auth_headers):
    resp = await async_client.get(
        "/v1/google/calendar/events",
        params={"time_min": "2026-06-18T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "naive_datetime"


@pytest.mark.asyncio
async def test_get_events_rejects_naive_time_max(async_client, auth_headers):
    resp = await async_client.get(
        "/v1/google/calendar/events",
        params={"time_max": "2026-06-18T00:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "naive_datetime"


@pytest.mark.asyncio
async def test_get_events_accepts_aware_time_range(async_client, auth_headers):
    resp = await async_client.get(
        "/v1/google/calendar/events",
        params={
            "time_min": "2026-06-18T00:00:00+07:00",
            "time_max": "2026-06-19T00:00:00+07:00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_post_sync_already_running(async_client, auth_headers):
    user_id = await _get_user_id(async_client, auth_headers)
    lock = google_calendar_service._get_lock(user_id)
    await lock.acquire()
    try:
        resp = await async_client.post("/v1/google/calendar/sync", headers=auth_headers)
    finally:
        lock.release()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "already_running"
    assert body["synced_at"] is None


@pytest.mark.asyncio
async def test_post_sync_synced(async_client, auth_headers):
    with patch(
        "app.services.google_calendar_service.sync_all_selected",
        new_callable=AsyncMock,
        return_value={"upserted": 2, "deleted": 1, "failed": 0, "errors": []},
    ):
        resp = await async_client.post("/v1/google/calendar/sync", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "synced"
    assert body["upserted"] == 2
    assert body["deleted"] == 1
    assert body["synced_at"] is not None


@pytest.mark.asyncio
async def test_post_sync_partial_on_per_calendar_failure(async_client, auth_headers):
    with patch(
        "app.services.google_calendar_service.sync_all_selected",
        new_callable=AsyncMock,
        return_value={
            "upserted": 1,
            "deleted": 0,
            "failed": 1,
            "errors": [{"calendar_id": "work", "message": "boom"}],
        },
    ):
        resp = await async_client.post("/v1/google/calendar/sync", headers=auth_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "partial"
    assert body["failed"] == 1
    assert body["errors"] == [{"calendar_id": "work", "message": "boom"}]


@pytest.mark.asyncio
async def test_post_sync_unauthenticated(async_client):
    resp = await async_client.post("/v1/google/calendar/sync")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_and_put_selected(async_client, auth_headers):
    user_id = await _get_user_id(async_client, auth_headers)
    async with AsyncSessionLocal() as db:
        await calendar_sync_repo.upsert_from_calendar_list(
            db, user_id, [_PRIMARY_CALENDAR, _WORK_CALENDAR]
        )
        await db.commit()

    resp = await async_client.get("/v1/google/calendar/selected", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    selection = {c["google_calendar_id"]: c["selected"] for c in resp.json()}
    assert selection == {"primary": True, "work": False}

    resp2 = await async_client.put(
        "/v1/google/calendar/selected",
        json={"calendar_ids": ["work"]},
        headers=auth_headers,
    )
    assert resp2.status_code == 200, resp2.text
    selection2 = {c["google_calendar_id"]: c["selected"] for c in resp2.json()}
    assert selection2 == {"primary": False, "work": True}


@pytest.mark.asyncio
async def test_selected_unauthenticated(async_client):
    resp = await async_client.get("/v1/google/calendar/selected")
    assert resp.status_code == 401


# ── Chat tools ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_calendar_events_today(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt1",
        summary="Standup",
        is_all_day=False,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        status="confirmed",
    )
    await db_session.commit()

    result = await execute_list_calendar_events(db_session, user_id, {"range": "today"}, "UTC")
    assert result["success"] is True
    assert result["data"]["events"][0]["summary"] == "Standup"


@pytest.mark.asyncio
async def test_list_calendar_events_invalid_range(db_session):
    result = await execute_list_calendar_events(
        db_session, uuid.uuid4(), {"range": "invalid"}, "UTC"
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_range"


@pytest.mark.asyncio
async def test_get_today_summary_includes_events(db_session):
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    await calendar_event_repo.upsert(
        db_session,
        user_id,
        "primary",
        "evt1",
        summary="Standup",
        is_all_day=False,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=2),
        status="confirmed",
    )
    await db_session.commit()

    result = await execute_get_today_summary(db_session, user_id, {}, "UTC")
    assert result["success"] is True
    assert result["data"]["events_today"][0]["summary"] == "Standup"
    assert "sự kiện" in result["summary"]

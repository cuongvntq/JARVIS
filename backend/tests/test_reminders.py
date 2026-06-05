"""Reminder API + tool executor integration tests."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from tests.conftest import _TestSession


@pytest_asyncio.fixture
async def db_session():
    async with _TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a real user row for executor tests that need a valid user_id FK."""
    import uuid as _uuid

    from app.models.user import User

    user = User(
        id=_uuid.uuid4(),
        email=f"exec_{_uuid.uuid4().hex[:8]}@jarvis.dev",
        name="Executor Test User",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _future(hours: int = 2) -> str:
    """ISO 8601 UTC string `hours` from now."""
    return (datetime.now(UTC) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _past(hours: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _create_reminder(async_client, auth_headers, title="Uống thuốc", **extra):
    payload = {"title": title, "remind_at": _future(), **extra}
    return await async_client.post("/v1/reminders", json=payload, headers=auth_headers)


# ── POST /v1/reminders ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_reminder_happy_path(async_client, auth_headers):
    resp = await _create_reminder(async_client, auth_headers, "Uống thuốc buổi tối")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Uống thuốc buổi tối"
    assert data["status"] == "pending"
    assert data["source"] == "ui"
    assert "id" in data
    assert "remind_at" in data


@pytest.mark.asyncio
async def test_create_reminder_with_description(async_client, auth_headers):
    resp = await _create_reminder(
        async_client, auth_headers, "Họp team", description="Phòng 201", source="chat"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Phòng 201"
    assert data["source"] == "chat"


@pytest.mark.asyncio
async def test_create_reminder_missing_title(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/reminders", json={"remind_at": _future()}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_reminder_missing_remind_at(async_client, auth_headers):
    resp = await async_client.post("/v1/reminders", json={"title": "Test"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_reminder_remind_at_in_past(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/reminders",
        json={"title": "Đã qua", "remind_at": _past()},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "remind_at_past"


@pytest.mark.asyncio
async def test_create_reminder_naive_datetime_rejected(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/reminders",
        json={"title": "Test", "remind_at": "2026-12-01T10:00:00"},  # no tz
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_reminder_unauthenticated(async_client):
    resp = await async_client.post("/v1/reminders", json={"title": "Test", "remind_at": _future()})
    assert resp.status_code == 401


# ── GET /v1/reminders/{id} ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_reminder_happy_path(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Uống nước")
    reminder_id = create_resp.json()["id"]

    resp = await async_client.get(f"/v1/reminders/{reminder_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == reminder_id
    assert resp.json()["title"] == "Uống nước"


@pytest.mark.asyncio
async def test_get_reminder_not_found(async_client, auth_headers):
    resp = await async_client.get(f"/v1/reminders/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "reminder_not_found"


@pytest.mark.asyncio
async def test_get_reminder_ownership_isolation(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Riêng tư")
    reminder_id = create_resp.json()["id"]

    user_b = {"email": "other_reminder@jarvis.dev", "password": "Test1234!", "name": "User B"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.get(f"/v1/reminders/{reminder_id}", headers=headers_b)
    assert resp.status_code == 404


# ── GET /v1/reminders ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_reminders_returns_own_only(async_client, auth_headers):
    await _create_reminder(async_client, auth_headers, "R1")
    await _create_reminder(async_client, auth_headers, "R2")

    resp = await async_client.get("/v1/reminders", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_reminders_invalid_status(async_client, auth_headers):
    resp = await async_client.get("/v1/reminders?status=bogus", headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_list_reminders_filter_by_status(async_client, auth_headers):
    await _create_reminder(async_client, auth_headers, "Pending reminder")

    resp = await async_client.get("/v1/reminders?status=pending", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(r["status"] == "pending" for r in items)


# ── PATCH /v1/reminders/{id} ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_reminder_title(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Cũ")
    reminder_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/reminders/{reminder_id}", json={"title": "Mới"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Mới"


@pytest.mark.asyncio
async def test_update_reminder_remind_at_in_past(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Test")
    reminder_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/reminders/{reminder_id}",
        json={"remind_at": _past()},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "remind_at_past"


# ── PATCH /v1/reminders/{id}/cancel ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_reminder_happy_path(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Hủy thôi")
    reminder_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_reminder_already_cancelled(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Hủy 2 lần")
    reminder_id = create_resp.json()["id"]

    await async_client.patch(f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers)
    resp = await async_client.patch(f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "reminder_not_cancellable"


# ── DELETE /v1/reminders/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_reminder_happy_path(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Xóa")
    reminder_id = create_resp.json()["id"]

    resp = await async_client.delete(f"/v1/reminders/{reminder_id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await async_client.get(f"/v1/reminders/{reminder_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_reminder_not_found(async_client, auth_headers):
    resp = await async_client.delete(f"/v1/reminders/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ── Tool executor: create_reminder ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executor_create_reminder_happy_path(db_session, test_user):
    from app.tools.executors import execute_create_reminder

    result = await execute_create_reminder(
        db_session,
        test_user.id,
        {"title": "Gym", "remind_at": _future(3)},
        user_tz="Asia/Ho_Chi_Minh",
    )
    assert result["success"] is True
    assert "Gym" in result["summary"]
    assert result["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_executor_create_reminder_missing_remind_at(db_session, test_user):
    from app.tools.executors import execute_create_reminder

    result = await execute_create_reminder(
        db_session, test_user.id, {"title": "Không có giờ"}, user_tz="UTC"
    )
    assert result["success"] is False
    assert result["error"]["code"] == "missing_remind_at"


@pytest.mark.asyncio
async def test_executor_create_reminder_past_time(db_session, test_user):
    from app.tools.executors import execute_create_reminder

    result = await execute_create_reminder(
        db_session,
        test_user.id,
        {"title": "Quá khứ", "remind_at": _past()},
        user_tz="UTC",
    )
    assert result["success"] is False
    assert result["error"]["code"] == "remind_at_past"


@pytest.mark.asyncio
async def test_executor_create_reminder_vietnamese_datetime(db_session, test_user):
    """Vietnamese expressions like 'chiều nay' must be parsed via datetime_parser."""
    from app.tools.executors import execute_create_reminder

    result = await execute_create_reminder(
        db_session,
        test_user.id,
        {"title": "Uống thuốc", "remind_at": "sáng mai"},
        user_tz="Asia/Ho_Chi_Minh",
    )
    # "sáng mai" → tomorrow 08:00 local → always future → should succeed
    assert result["success"] is True
    assert result["data"]["status"] == "pending"


# ── Tool executor: list_reminders ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executor_list_reminders(db_session, test_user):
    from app.tools.executors import execute_create_reminder, execute_list_reminders

    await execute_create_reminder(
        db_session, test_user.id, {"title": "R1", "remind_at": _future(1)}, user_tz="UTC"
    )
    await execute_create_reminder(
        db_session, test_user.id, {"title": "R2", "remind_at": _future(2)}, user_tz="UTC"
    )
    await db_session.commit()

    result = await execute_list_reminders(
        db_session, test_user.id, {"status": "pending", "limit": 10}, user_tz="UTC"
    )
    assert result["success"] is True
    assert result["data"]["count"] >= 2


@pytest.mark.asyncio
async def test_executor_list_reminders_explicit_null_status_returns_all(db_session, test_user):
    """Explicit status=None should return all statuses, not default to pending."""
    from app.tools.executors import execute_list_reminders

    result = await execute_list_reminders(db_session, test_user.id, {"status": None}, user_tz="UTC")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_executor_list_reminders_invalid_status_returns_error(db_session, test_user):
    from app.tools.executors import execute_list_reminders

    result = await execute_list_reminders(
        db_session, test_user.id, {"status": "bogus"}, user_tz="UTC"
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_executor_list_reminders_missing_status_defaults_pending(db_session, test_user):
    """Missing status key should default to pending."""
    from app.tools.executors import execute_create_reminder, execute_list_reminders

    await execute_create_reminder(
        db_session, test_user.id, {"title": "Pending", "remind_at": _future(1)}, user_tz="UTC"
    )
    await db_session.commit()

    result = await execute_list_reminders(db_session, test_user.id, {}, user_tz="UTC")
    assert result["success"] is True
    items = result["data"]["reminders"]
    assert all(r["status"] == "pending" for r in items)


# ── Repository: claim_pending_due ─────────────────────────────────────────────


def _make_reminder(user_id, title: str, remind_at):
    from app.models.reminder import Reminder

    return Reminder(user_id=user_id, title=title, remind_at=remind_at, status="pending")


@pytest.mark.asyncio
async def test_claim_pending_due_transitions_status_to_due(db_session, test_user):
    """claim_pending_due() must atomically flip status pending→due and return those rows."""
    from datetime import UTC, datetime, timedelta

    from app.repositories.reminder_repo import claim_pending_due

    now = datetime.now(UTC)
    due = _make_reminder(test_user.id, "Due now", now - timedelta(minutes=5))
    future = _make_reminder(test_user.id, "Not due yet", now + timedelta(hours=2))
    db_session.add(due)
    db_session.add(future)
    await db_session.flush()

    claimed = await claim_pending_due(db_session, before_utc=now)
    await db_session.commit()

    assert len(claimed) == 1
    assert claimed[0].title == "Due now"

    # synchronize_session=False means the identity-map object is not updated in-memory;
    # refresh to verify the DB was actually written
    await db_session.refresh(claimed[0])
    assert claimed[0].status == "due"

    # The future reminder must remain pending
    await db_session.refresh(future)
    assert future.status == "pending"


@pytest.mark.asyncio
async def test_claim_pending_due_ignores_non_pending_status(db_session, test_user):
    """Already-sending / cancelled / sent reminders must not be claimed again."""
    from datetime import UTC, datetime, timedelta

    from app.models.reminder import Reminder
    from app.repositories.reminder_repo import claim_pending_due

    now = datetime.now(UTC)
    past = now - timedelta(minutes=1)

    for status in ("sending", "sent", "cancelled", "failed"):
        r = Reminder(
            user_id=test_user.id,
            title=f"Status {status}",
            remind_at=past,
            status=status,
        )
        db_session.add(r)
    await db_session.flush()

    claimed = await claim_pending_due(db_session, before_utc=now)
    await db_session.commit()

    assert claimed == []


@pytest.mark.asyncio
async def test_claim_pending_due_ignores_soft_deleted(db_session, test_user):
    """Soft-deleted reminders must not be claimed."""
    from datetime import UTC, datetime, timedelta

    from app.repositories.reminder_repo import claim_pending_due

    now = datetime.now(UTC)
    deleted = _make_reminder(test_user.id, "Deleted due", now - timedelta(minutes=1))
    deleted.deleted_at = now - timedelta(seconds=30)
    db_session.add(deleted)
    await db_session.flush()

    claimed = await claim_pending_due(db_session, before_utc=now)
    await db_session.commit()

    assert claimed == []

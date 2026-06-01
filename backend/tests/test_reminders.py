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
    resp = await async_client.post(
        "/v1/reminders", json={"title": "Test"}, headers=auth_headers
    )
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
async def test_create_reminder_unauthenticated(async_client):
    resp = await async_client.post(
        "/v1/reminders", json={"title": "Test", "remind_at": _future()}
    )
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

    resp = await async_client.patch(
        f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_reminder_already_cancelled(async_client, auth_headers):
    create_resp = await _create_reminder(async_client, auth_headers, "Hủy 2 lần")
    reminder_id = create_resp.json()["id"]

    await async_client.patch(f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers)
    resp = await async_client.patch(
        f"/v1/reminders/{reminder_id}/cancel", headers=auth_headers
    )
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

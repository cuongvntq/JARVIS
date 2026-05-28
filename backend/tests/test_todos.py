"""Todo API integration tests."""

from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _create_todo(async_client, auth_headers, title="Mua sữa", **extra):
    payload = {"title": title, **extra}
    return await async_client.post("/v1/todos", json=payload, headers=auth_headers)


# ── POST /v1/todos ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_todo_happy_path(async_client, auth_headers):
    resp = await _create_todo(async_client, auth_headers, "Mua sữa tươi")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Mua sữa tươi"
    assert data["status"] == "pending"
    assert data["priority"] == "medium"
    assert data["tags"] == []
    assert data["source"] == "ui"
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_todo_with_all_fields(async_client, auth_headers):
    resp = await _create_todo(
        async_client,
        auth_headers,
        "Tập gym",
        description="Ngực + tay",
        priority="high",
        tags=["sport", "health"],
        source="chat",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["priority"] == "high"
    assert data["tags"] == ["sport", "health"]
    assert data["source"] == "chat"


@pytest.mark.asyncio
async def test_create_todo_missing_title(async_client, auth_headers):
    resp = await async_client.post("/v1/todos", json={}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_empty_title(async_client, auth_headers):
    resp = await async_client.post("/v1/todos", json={"title": ""}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_todo_unauthenticated(async_client):
    resp = await async_client.post("/v1/todos", json={"title": "Mua sữa"})
    assert resp.status_code == 401


# ── GET /v1/todos/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_todo_happy_path(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers, "Đọc sách")
    todo_id = create_resp.json()["id"]

    resp = await async_client.get(f"/v1/todos/{todo_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == todo_id
    assert resp.json()["title"] == "Đọc sách"


@pytest.mark.asyncio
async def test_get_todo_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.get(f"/v1/todos/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "todo_not_found"


@pytest.mark.asyncio
async def test_get_todo_ownership_isolation(async_client, auth_headers):
    """User B cannot get user A's todo."""
    create_resp = await _create_todo(async_client, auth_headers, "Todo riêng tư")
    todo_id = create_resp.json()["id"]

    user_b = {"email": "other@jarvis.dev", "password": "Test1234!", "name": "User B"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.get(f"/v1/todos/{todo_id}", headers=headers_b)
    assert resp.status_code == 404


# ── GET /v1/todos ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_todos_returns_own_todos(async_client, auth_headers):
    await _create_todo(async_client, auth_headers, "Todo 1")
    await _create_todo(async_client, auth_headers, "Todo 2")

    resp = await async_client.get("/v1/todos", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_todos_unauthenticated(async_client):
    resp = await async_client.get("/v1/todos")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_todos_filter_completed(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers, "Việc hoàn thành")
    todo_id = create_resp.json()["id"]
    await async_client.patch(f"/v1/todos/{todo_id}/complete", headers=auth_headers)
    await _create_todo(async_client, auth_headers, "Việc chưa xong")

    resp = await async_client.get("/v1/todos?filter=completed", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(t["status"] == "completed" for t in items)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_list_todos_invalid_filter(async_client, auth_headers):
    resp = await async_client.get("/v1/todos?filter=invalid_value", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_todos_search_q(async_client, auth_headers):
    await _create_todo(async_client, auth_headers, "Mua cà phê")
    await _create_todo(async_client, auth_headers, "Nấu cơm")

    resp = await async_client.get("/v1/todos?q=cà phê", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert "cà phê" in items[0]["title"]


# ── PUT /v1/todos/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replace_todo_happy_path(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers, "Cũ")
    todo_id = create_resp.json()["id"]

    resp = await async_client.put(
        f"/v1/todos/{todo_id}",
        json={"title": "Mới", "priority": "high"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Mới"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_replace_todo_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.put(
        f"/v1/todos/{uuid.uuid4()}",
        json={"title": "X"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── PATCH /complete and /uncomplete ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_todo(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers)
    todo_id = create_resp.json()["id"]

    resp = await async_client.patch(f"/v1/todos/{todo_id}/complete", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_uncomplete_todo(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers)
    todo_id = create_resp.json()["id"]
    await async_client.patch(f"/v1/todos/{todo_id}/complete", headers=auth_headers)

    resp = await async_client.patch(f"/v1/todos/{todo_id}/uncomplete", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["completed_at"] is None


@pytest.mark.asyncio
async def test_complete_todo_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.patch(f"/v1/todos/{uuid.uuid4()}/complete", headers=auth_headers)
    assert resp.status_code == 404


# ── DELETE /v1/todos/{id} ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_todo_soft_delete(async_client, auth_headers):
    create_resp = await _create_todo(async_client, auth_headers)
    todo_id = create_resp.json()["id"]

    del_resp = await async_client.delete(f"/v1/todos/{todo_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Deleted todo must not be accessible
    get_resp = await async_client.get(f"/v1/todos/{todo_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_todo_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.delete(f"/v1/todos/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deleted_todo_excluded_from_list(async_client, auth_headers):
    r1 = await _create_todo(async_client, auth_headers, "Xóa đi")
    await _create_todo(async_client, auth_headers, "Giữ lại")
    await async_client.delete(f"/v1/todos/{r1.json()['id']}", headers=auth_headers)

    resp = await async_client.get("/v1/todos", headers=auth_headers)
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["items"]]
    assert "Giữ lại" in titles
    assert "Xóa đi" not in titles


# ── _today_range_utc unit tests ────────────────────────────────────────────────


class TestTodayRangeUtc:
    def test_span_is_exactly_one_day(self):
        from app.repositories.todo_repo import _today_range_utc

        start, end = _today_range_utc("Asia/Ho_Chi_Minh")
        assert end - start == timedelta(days=1)

    def test_start_is_local_midnight(self):
        from app.repositories.todo_repo import _today_range_utc

        start, _ = _today_range_utc("Asia/Ho_Chi_Minh")
        local = start.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        assert local.hour == 0 and local.minute == 0 and local.second == 0

    def test_hcm_start_is_17h_utc(self):
        """Asia/Ho_Chi_Minh is UTC+7 (no DST): local midnight always = 17:00 UTC."""
        from app.repositories.todo_repo import _today_range_utc

        start, _ = _today_range_utc("Asia/Ho_Chi_Minh")
        assert start.hour == 17

    def test_invalid_tz_falls_back_to_utc(self):
        from app.repositories.todo_repo import _today_range_utc

        start, end = _today_range_utc("Not/A_Valid_TZ")
        assert end - start == timedelta(days=1)
        assert start.hour == 0 and start.minute == 0  # UTC midnight fallback


# ── today filter integration ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_todos_today_filter_includes_current_moment(async_client, auth_headers):
    """A todo due right now must appear in the today filter (current moment is always within local today)."""
    from datetime import UTC, datetime

    due_now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    due_far_future = "2099-12-31T12:00:00Z"

    await _create_todo(async_client, auth_headers, "Due today", due_at=due_now)
    await _create_todo(async_client, auth_headers, "Due 2099", due_at=due_far_future)

    resp = await async_client.get("/v1/todos", params={"filter": "today"}, headers=auth_headers)
    assert resp.status_code == 200
    titles = {t["title"] for t in resp.json()["items"]}
    assert "Due today" in titles
    assert "Due 2099" not in titles

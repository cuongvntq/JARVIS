"""Note API integration tests."""

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _create_note(async_client, auth_headers, title="Ghi chú test", **extra):
    payload = {"title": title, **extra}
    return await async_client.post("/v1/notes", json=payload, headers=auth_headers)


# ── POST /v1/notes ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_note_happy_path(async_client, auth_headers):
    resp = await _create_note(async_client, auth_headers, "Công thức nấu phở")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Công thức nấu phở"
    assert data["content"] == ""
    assert data["pinned"] is False
    assert data["tags"] == []
    assert data["source"] == "ui"
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_note_with_all_fields(async_client, auth_headers):
    resp = await _create_note(
        async_client,
        auth_headers,
        "Ý tưởng dự án",
        content="Xây dựng app quản lý chi tiêu",
        tags=["idea", "project"],
        pinned=True,
        source="chat",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Xây dựng app quản lý chi tiêu"
    assert data["tags"] == ["idea", "project"]
    assert data["pinned"] is True
    assert data["source"] == "chat"


@pytest.mark.asyncio
async def test_create_note_missing_title(async_client, auth_headers):
    resp = await async_client.post("/v1/notes", json={}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_note_empty_title(async_client, auth_headers):
    resp = await async_client.post("/v1/notes", json={"title": ""}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_note_unauthenticated(async_client):
    resp = await async_client.post("/v1/notes", json={"title": "Test"})
    assert resp.status_code == 401


# ── GET /v1/notes/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_note_happy_path(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Đọc sách hàng ngày")
    note_id = create_resp.json()["id"]

    resp = await async_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == note_id
    assert resp.json()["title"] == "Đọc sách hàng ngày"


@pytest.mark.asyncio
async def test_get_note_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.get(f"/v1/notes/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "note_not_found"


@pytest.mark.asyncio
async def test_get_note_ownership_isolation(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Ghi chú riêng tư")
    note_id = create_resp.json()["id"]

    user_b = {"email": "other_note@jarvis.dev", "password": "Test1234!", "name": "User B"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.get(f"/v1/notes/{note_id}", headers=headers_b)
    assert resp.status_code == 404


# ── GET /v1/notes ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_notes_empty(async_client, auth_headers):
    resp = await async_client.get("/v1/notes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_notes_returns_created(async_client, auth_headers):
    await _create_note(async_client, auth_headers, "Ghi chú A")
    await _create_note(async_client, auth_headers, "Ghi chú B")

    resp = await async_client.get("/v1/notes", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_list_notes_filter_pinned(async_client, auth_headers):
    await _create_note(async_client, auth_headers, "Không ghim")
    await _create_note(async_client, auth_headers, "Có ghim", pinned=True)

    resp = await async_client.get("/v1/notes?pinned=true", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["pinned"] is True


@pytest.mark.asyncio
async def test_list_notes_search(async_client, auth_headers):
    await _create_note(async_client, auth_headers, "Công thức bánh mì")
    await _create_note(async_client, auth_headers, "Kế hoạch du lịch")

    resp = await async_client.get("/v1/notes?q=bánh", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert "bánh" in items[0]["title"]


# ── PATCH /v1/notes/{id} ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_note_happy_path(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Tiêu đề cũ")
    note_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/notes/{note_id}",
        json={"title": "Tiêu đề mới", "content": "Nội dung cập nhật"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Tiêu đề mới"
    assert data["content"] == "Nội dung cập nhật"


@pytest.mark.asyncio
async def test_update_note_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.patch(
        f"/v1/notes/{uuid.uuid4()}",
        json={"title": "Không tìm thấy"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── PATCH /v1/notes/{id}/pin + /unpin ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_pin_and_unpin_note(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Ghi chú chờ ghim")
    note_id = create_resp.json()["id"]
    assert create_resp.json()["pinned"] is False

    pin_resp = await async_client.patch(f"/v1/notes/{note_id}/pin", headers=auth_headers)
    assert pin_resp.status_code == 200
    assert pin_resp.json()["pinned"] is True

    unpin_resp = await async_client.patch(f"/v1/notes/{note_id}/unpin", headers=auth_headers)
    assert unpin_resp.status_code == 200
    assert unpin_resp.json()["pinned"] is False


# ── DELETE /v1/notes/{id} ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_note_happy_path(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Sẽ bị xóa")
    note_id = create_resp.json()["id"]

    del_resp = await async_client.delete(f"/v1/notes/{note_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await async_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_note_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.delete(f"/v1/notes/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_note_ownership(async_client, auth_headers):
    create_resp = await _create_note(async_client, auth_headers, "Ghi chú user A")
    note_id = create_resp.json()["id"]

    user_b = {"email": "del_note@jarvis.dev", "password": "Test1234!", "name": "User B"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.delete(f"/v1/notes/{note_id}", headers=headers_b)
    assert resp.status_code == 404

    # Original still exists
    get_resp = await async_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
    assert get_resp.status_code == 200


# ── Pinned notes appear first in list ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_pinned_notes_appear_first(async_client, auth_headers):
    await _create_note(async_client, auth_headers, "Thường A")
    await _create_note(async_client, auth_headers, "Ghim B", pinned=True)
    await _create_note(async_client, auth_headers, "Thường C")

    resp = await async_client.get("/v1/notes", headers=auth_headers)
    items = resp.json()["items"]
    assert items[0]["pinned"] is True
    assert items[0]["title"] == "Ghim B"

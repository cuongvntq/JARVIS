"""Memory API integration tests."""

import uuid

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _create_memory(async_client, auth_headers, content="Người dùng thích cà phê đen", **extra):
    payload = {"content": content, **extra}
    return await async_client.post("/v1/memories", json=payload, headers=auth_headers)


# ── POST /v1/memories ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_memory_happy_path(async_client, auth_headers):
    resp = await _create_memory(async_client, auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Người dùng thích cà phê đen"
    assert data["memory_type"] == "fact"
    assert data["importance"] == 5
    assert data["is_active"] is True
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_memory_all_fields(async_client, auth_headers):
    resp = await _create_memory(
        async_client, auth_headers,
        "Người dùng dị ứng tôm",
        memory_type="fact",
        importance=9,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["memory_type"] == "fact"
    assert data["importance"] == 9


@pytest.mark.asyncio
async def test_create_memory_invalid_importance(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/memories",
        json={"content": "test", "importance": 11},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_memory_empty_content(async_client, auth_headers):
    resp = await async_client.post("/v1/memories", json={"content": ""}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_memory_unauthenticated(async_client):
    resp = await async_client.post("/v1/memories", json={"content": "test"})
    assert resp.status_code == 401


# ── GET /v1/memories/{id} ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_memory_happy_path(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Người dùng thích đọc sách")
    memory_id = create_resp.json()["id"]

    resp = await async_client.get(f"/v1/memories/{memory_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == memory_id
    assert resp.json()["content"] == "Người dùng thích đọc sách"


@pytest.mark.asyncio
async def test_get_memory_not_found(async_client, auth_headers):
    resp = await async_client.get(f"/v1/memories/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "memory_not_found"


@pytest.mark.asyncio
async def test_get_memory_ownership_isolation(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Memory riêng tư")
    memory_id = create_resp.json()["id"]

    user_b = {"email": "other_mem@jarvis.dev", "password": "Test1234!", "name": "User B"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.get(f"/v1/memories/{memory_id}", headers=headers_b)
    assert resp.status_code == 404


# ── GET /v1/memories ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_memories_empty(async_client, auth_headers):
    resp = await async_client.get("/v1/memories", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["next_cursor"] is None


@pytest.mark.asyncio
async def test_list_memories_returns_created(async_client, auth_headers):
    await _create_memory(async_client, auth_headers, "Memory A")
    await _create_memory(async_client, auth_headers, "Memory B")

    resp = await async_client.get("/v1/memories", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_list_memories_filter_by_type(async_client, auth_headers):
    await _create_memory(async_client, auth_headers, "Fact memory", memory_type="fact")
    await _create_memory(async_client, auth_headers, "Goal memory", memory_type="goal")

    resp = await async_client.get("/v1/memories?memory_type=goal", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["memory_type"] == "goal"


# ── PATCH /v1/memories/{id} ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_memory_happy_path(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Nội dung cũ")
    memory_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/memories/{memory_id}",
        json={"content": "Nội dung mới", "importance": 8},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Nội dung mới"
    assert data["importance"] == 8


@pytest.mark.asyncio
async def test_update_memory_not_found(async_client, auth_headers):
    resp = await async_client.patch(
        f"/v1/memories/{uuid.uuid4()}",
        json={"content": "Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "memory_not_found"


@pytest.mark.asyncio
async def test_update_memory_explicit_null_content_rejected(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Memory content")
    memory_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/memories/{memory_id}",
        json={"content": None},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_memory_explicit_null_importance_rejected(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Memory content")
    memory_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/memories/{memory_id}",
        json={"importance": None},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_memory_unknown_field_rejected(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Memory content")
    memory_id = create_resp.json()["id"]

    resp = await async_client.patch(
        f"/v1/memories/{memory_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── DELETE /v1/memories/{id} ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_memory_happy_path(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Memory to delete")
    memory_id = create_resp.json()["id"]

    resp = await async_client.delete(f"/v1/memories/{memory_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Confirm soft-deleted: GET returns 404
    get_resp = await async_client.get(f"/v1/memories/{memory_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory_not_found(async_client, auth_headers):
    resp = await async_client.delete(f"/v1/memories/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "memory_not_found"


@pytest.mark.asyncio
async def test_delete_memory_ownership_isolation(async_client, auth_headers):
    create_resp = await _create_memory(async_client, auth_headers, "Protected memory")
    memory_id = create_resp.json()["id"]

    user_b = {"email": "attacker_mem@jarvis.dev", "password": "Test1234!", "name": "Attacker"}
    reg = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = await async_client.delete(f"/v1/memories/{memory_id}", headers=headers_b)
    assert resp.status_code == 404

    # Original owner can still access it
    get_resp = await async_client.get(f"/v1/memories/{memory_id}", headers=auth_headers)
    assert get_resp.status_code == 200


# ── POST /v1/memories/search ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_memories_returns_empty_on_sqlite(async_client, auth_headers):
    await _create_memory(async_client, auth_headers, "Người dùng thích lập trình Python")

    resp = await async_client.post(
        "/v1/memories/search",
        json={"query": "lập trình", "limit": 5, "min_similarity": 0.7},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] == len(data["items"])
    # SQLite dialect returns [] — no LiteLLM call
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_search_memories_unauthenticated(async_client):
    resp = await async_client.post(
        "/v1/memories/search",
        json={"query": "test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_memories_invalid_request(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/memories/search",
        json={"query": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422

"""Chat endpoint integration tests."""

import pytest

from tests.conftest import TEST_USER


@pytest.mark.asyncio
async def test_send_message_authenticated(async_client, auth_headers, mock_llm):
    resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Xin chào JARVIS", "conversation_id": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    assert len(data["assistant_message"]["content"]) > 0


@pytest.mark.asyncio
async def test_send_creates_conversation_when_null(async_client, auth_headers, mock_llm):
    resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Tạo cuộc hội thoại mới", "conversation_id": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["conversation_id"] is not None


@pytest.mark.asyncio
async def test_send_resumes_existing_conversation(async_client, auth_headers, mock_llm):
    resp1 = await async_client.post(
        "/v1/chat/send",
        json={"content": "Tin nhắn 1", "conversation_id": None},
        headers=auth_headers,
    )
    conv_id = resp1.json()["conversation_id"]

    resp2 = await async_client.post(
        "/v1/chat/send",
        json={"content": "Tin nhắn 2", "conversation_id": conv_id},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_send_unauthenticated(async_client):
    resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Xin chào", "conversation_id": None},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_conversations(async_client, auth_headers, mock_llm):
    # Create a conversation first
    await async_client.post(
        "/v1/chat/send",
        json={"content": "Hello", "conversation_id": None},
        headers=auth_headers,
    )
    resp = await async_client.get("/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_conversation_ownership_returns_404_not_403(async_client, mock_llm):
    """User B accessing user A's conversation must get 404, not 403 (no ownership leak via status code)."""
    # User A creates a conversation
    resp_a = await async_client.post("/auth/register", json=TEST_USER)
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}
    resp_conv = await async_client.post(
        "/v1/chat/send",
        json={"content": "Hello", "conversation_id": None},
        headers=headers_a,
    )
    conv_id = resp_conv.json()["conversation_id"]

    # User B registers and tries to send a message into user A's conversation
    user_b = {**TEST_USER, "email": "other@jarvis.dev"}
    resp_b = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Unauthorized", "conversation_id": conv_id},
        headers=headers_b,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "conversation_not_found"


# ── GET /v1/chat/conversations/{id} ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_conversation_detail(async_client, auth_headers, mock_llm):
    send_resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Xin chào", "conversation_id": None},
        headers=auth_headers,
    )
    conv_id = send_resp.json()["conversation_id"]

    resp = await async_client.get(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == conv_id
    assert "messages" in data
    assert len(data["messages"]) == 2  # user + assistant
    assert "has_more" in data
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_conversation_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.get(f"/v1/chat/conversations/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "conversation_not_found"


@pytest.mark.asyncio
async def test_get_conversation_ownership(async_client, mock_llm):
    """User B cannot GET user A's conversation detail."""
    resp_a = await async_client.post("/auth/register", json=TEST_USER)
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}
    conv_resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Hello", "conversation_id": None},
        headers=headers_a,
    )
    conv_id = conv_resp.json()["conversation_id"]

    user_b = {**TEST_USER, "email": "other2@jarvis.dev"}
    resp_b = await async_client.post("/auth/register", json=user_b)
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    resp = await async_client.get(f"/v1/chat/conversations/{conv_id}", headers=headers_b)
    assert resp.status_code == 404


# ── PATCH /v1/chat/conversations/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_conversation_title(async_client, auth_headers, mock_llm):
    send_resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Hello", "conversation_id": None},
        headers=auth_headers,
    )
    conv_id = send_resp.json()["conversation_id"]

    resp = await async_client.patch(
        f"/v1/chat/conversations/{conv_id}",
        json={"title": "Cuộc trò chuyện về AI"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Cuộc trò chuyện về AI"


@pytest.mark.asyncio
async def test_update_conversation_title_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.patch(
        f"/v1/chat/conversations/{uuid.uuid4()}",
        json={"title": "New title"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── DELETE /v1/chat/conversations/{id} ────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_conversation(async_client, auth_headers, mock_llm):
    send_resp = await async_client.post(
        "/v1/chat/send",
        json={"content": "Hello", "conversation_id": None},
        headers=auth_headers,
    )
    conv_id = send_resp.json()["conversation_id"]

    del_resp = await async_client.delete(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Deleted conversation must not be accessible
    get_resp = await async_client.get(f"/v1/chat/conversations/{conv_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_not_found(async_client, auth_headers):
    import uuid

    resp = await async_client.delete(f"/v1/chat/conversations/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404

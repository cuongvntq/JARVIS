"""Chat endpoint integration tests."""

import pytest


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

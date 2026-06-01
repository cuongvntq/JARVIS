"""Push notification subscription endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_subscribe_happy_path(async_client, auth_headers):
    resp = await async_client.post(
        "/v1/notifications/subscribe",
        json={
            "endpoint": "https://push.example.com/sub/abc123",
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtZ5MqRMqsXCIKh7oMHJ7KtUCIKh7oMHJ7KtUtest",
            "auth": "tEsTaUtHkEy",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_subscribe_overwrites_existing(async_client, auth_headers):
    """Re-subscribing updates the existing record (1 per user)."""
    sub_data = {
        "endpoint": "https://push.example.com/sub/first",
        "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtZ5MqRMqsXCIKh7oMtest1",
        "auth": "authKey1",
    }
    r1 = await async_client.post("/v1/notifications/subscribe", json=sub_data, headers=auth_headers)
    assert r1.status_code == 201
    first_id = r1.json()["id"]

    sub_data2 = {
        **sub_data,
        "endpoint": "https://push.example.com/sub/second",
        "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtZ5MqRMqsXCIKh7test2",
    }
    r2 = await async_client.post(
        "/v1/notifications/subscribe", json=sub_data2, headers=auth_headers
    )
    assert r2.status_code == 201
    # Same record updated (same id)
    assert r2.json()["id"] == first_id


@pytest.mark.asyncio
async def test_unsubscribe_happy_path(async_client, auth_headers):
    await async_client.post(
        "/v1/notifications/subscribe",
        json={
            "endpoint": "https://push.example.com/sub/unsub",
            "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtZ5MqRMqsXCIKh7oMtest",
            "auth": "authForUnsub",
        },
        headers=auth_headers,
    )
    resp = await async_client.post("/v1/notifications/unsubscribe", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unsubscribe_not_found(async_client, auth_headers):
    resp = await async_client.post("/v1/notifications/unsubscribe", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "subscription_not_found"


@pytest.mark.asyncio
async def test_subscribe_unauthenticated(async_client):
    resp = await async_client.post(
        "/v1/notifications/subscribe",
        json={"endpoint": "https://x.com", "p256dh": "key", "auth": "auth"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_push_service_no_vapid_keys():
    """send_push returns False gracefully when VAPID keys are not configured."""
    from unittest.mock import patch

    from app.config import Settings
    from app.services import push_service

    mock_settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        gemini_api_key="fake",
        openai_api_key="sk-fake",
        jwt_secret="test-jwt-secret-key-must-be-32-chars!!",
        vapid_public_key=None,
        vapid_private_key=None,
    )
    with patch("app.services.push_service.get_settings", return_value=mock_settings):
        result = await push_service.send_push(
            endpoint="https://x.com",
            p256dh="key",
            auth="auth",
            title="Test",
            body="Body",
        )
    assert result is False

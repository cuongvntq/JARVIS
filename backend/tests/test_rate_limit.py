"""Rate limit response format tests."""

import json

import pytest
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request


@pytest.mark.asyncio
async def test_rate_limit_handler_returns_jarvis_format():
    """429 response must match JARVIS error envelope format."""
    from app.main import _rate_limit_handler

    # Build a minimal mock request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/chat/send",
        "headers": [],
        "query_string": b"",
    }
    request = Request(scope)
    # Attach fake request_id as middleware would
    request.state.request_id = "test-request-id"

    from unittest.mock import MagicMock

    exc = MagicMock(spec=RateLimitExceeded)
    response = await _rate_limit_handler(request, exc)

    assert response.status_code == 429
    body = json.loads(response.body)
    assert "error" in body
    err = body["error"]
    assert err["code"] == "rate_limit_exceeded"
    assert err["request_id"] == "test-request-id"
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_chat_send_requires_auth(async_client):
    """Unauthenticated requests to /v1/chat/send → 401 (not rate limited)."""
    resp = await async_client.post(
        "/v1/chat/send",
        json={"message": "test", "stream": False},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_send_rate_limit_enforced(async_client, auth_headers, mock_llm):
    """After 20 authenticated requests the 21st must return 429.

    Verifies that @limiter.limit('20/minute') on send_message is wired correctly
    through the full ASGI stack (not just the handler unit test above).
    """
    from app.middleware.rate_limit import limiter

    # Reset in-memory counters so this test is not affected by other requests
    limiter._storage.reset()

    payload = {"content": "hi", "stream": False}
    for i in range(20):
        resp = await async_client.post("/v1/chat/send", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Request {i + 1} should succeed, got {resp.status_code}"

    resp = await async_client.post("/v1/chat/send", json=payload, headers=auth_headers)
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in resp.headers

    # Restore clean state for subsequent tests
    limiter._storage.reset()

"""Auth endpoint integration tests."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import TEST_USER


@pytest.mark.asyncio
async def test_register_success(async_client):
    resp = await async_client.post("/auth/register", json=TEST_USER)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == TEST_USER["email"]
    # refresh token delivered as httponly cookie, not in response body
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    await async_client.post("/auth/register", json=TEST_USER)
    resp = await async_client.post("/auth/register", json=TEST_USER)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_register_weak_password(async_client):
    payload = {**TEST_USER, "email": "weak@jarvis.dev", "password": "short"}
    resp = await async_client.post("/auth/register", json=payload)
    assert resp.status_code in (422, 400)


@pytest.mark.asyncio
async def test_login_success(async_client):
    await async_client.post("/auth/register", json=TEST_USER)
    resp = await async_client.post("/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    await async_client.post("/auth/register", json=TEST_USER)
    resp = await async_client.post("/auth/login", json={"email": TEST_USER["email"], "password": "WrongPass9"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_authenticated(async_client, auth_headers):
    resp = await async_client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == TEST_USER["email"]


@pytest.mark.asyncio
async def test_me_unauthenticated(async_client):
    resp = await async_client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_via_cookie(async_client):
    """Browser flow: register sets cookie, /auth/refresh uses it automatically (no body)."""
    reg = await async_client.post("/auth/register", json=TEST_USER)
    initial_token = reg.cookies["refresh_token"]

    resp = await async_client.post("/auth/refresh")  # cookie sent automatically
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    # new cookie issued (token rotated)
    assert resp.cookies["refresh_token"] != initial_token


@pytest.mark.asyncio
async def test_logout_via_cookie(async_client):
    """Browser flow: logout via cookie, subsequent refresh is rejected."""
    await async_client.post("/auth/register", json=TEST_USER)

    resp = await async_client.post("/auth/logout")
    assert resp.status_code == 204

    # cookie cleared — /auth/refresh should now fail
    resp2 = await async_client.post("/auth/refresh")
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_old_token_rejected_after_rotation(async_client):
    """Rotated-away token must be rejected (replay attack prevention)."""
    reg = await async_client.post("/auth/register", json=TEST_USER)
    old_token = reg.cookies["refresh_token"]

    # Rotate the token
    await async_client.post("/auth/refresh")

    # Try old token via body in a fresh client (no active cookie)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as fresh:
        resp = await fresh.post("/auth/refresh", json={"refresh_token": old_token})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_concurrent_refresh_no_double_issue(async_client):
    """Two concurrent requests with the same refresh token: at most one succeeds, no 500.

    SQLite StaticPool serializes requests so races are not truly parallel here, but
    the atomic UPDATE ensures correctness on real Postgres under concurrent load too.
    """
    reg = await async_client.post("/auth/register", json=TEST_USER)
    token = reg.cookies["refresh_token"]

    async def try_refresh():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            return await c.post("/auth/refresh", json={"refresh_token": token})

    r1, r2 = await asyncio.gather(try_refresh(), try_refresh())
    codes = [r1.status_code, r2.status_code]
    assert 500 not in codes, f"Unexpected 500: {codes}"
    assert sorted(codes) == [200, 401], f"Expected exactly one 200 and one 401, got {codes}"


@pytest.mark.asyncio
async def test_register_race_condition_maps_to_409(async_client):
    """IntegrityError from a concurrent insert must surface as 409, not 500.

    Simulates the race by bypassing the get_by_email check (as if it ran before
    the concurrent commit landed) so the unique constraint fires on insert.
    True DB-level concurrency cannot be reproduced with SQLite StaticPool; this
    test verifies the catch(IntegrityError) → JarvisError(409) mapping.
    """
    from unittest.mock import AsyncMock, patch

    await async_client.post("/auth/register", json=TEST_USER)

    with patch("app.services.auth_service.user_repo.get_by_email", new_callable=AsyncMock, return_value=None):
        resp = await async_client.post("/auth/register", json=TEST_USER)

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_email_case_insensitive(async_client):
    """Registering with uppercase email and logging in with lowercase must work."""
    upper_payload = {**TEST_USER, "email": "Test@Jarvis.Dev"}
    await async_client.post("/auth/register", json=upper_payload)

    resp = await async_client.post(
        "/auth/login",
        json={"email": "test@jarvis.dev", "password": TEST_USER["password"]},
    )
    assert resp.status_code == 200

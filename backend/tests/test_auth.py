"""Auth endpoint integration tests."""

import pytest

from tests.conftest import TEST_USER


@pytest.mark.asyncio
async def test_register_success(async_client):
    resp = await async_client.post("/auth/register", json=TEST_USER)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == TEST_USER["email"]


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
async def test_refresh_token(async_client):
    reg = await async_client.post("/auth/register", json=TEST_USER)
    refresh_token = reg.json()["refresh_token"]
    resp = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["refresh_token"] != refresh_token  # rotating


@pytest.mark.asyncio
async def test_logout(async_client):
    reg = await async_client.post("/auth/register", json=TEST_USER)
    refresh_token = reg.json()["refresh_token"]
    resp = await async_client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 204
    # Verify refresh token is revoked
    resp2 = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 401

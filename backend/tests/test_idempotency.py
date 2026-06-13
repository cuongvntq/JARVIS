"""Idempotency-Key middleware tests."""

import pytest


@pytest.mark.asyncio
async def test_idempotency_key_returns_cached_response(async_client, auth_headers):
    """Same Idempotency-Key + same body → second request returns cached response,
    does not create a duplicate todo."""
    payload = {"title": "Mua sữa"}
    headers = {**auth_headers, "Idempotency-Key": "key-1"}

    first = await async_client.post("/v1/todos", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = await async_client.post("/v1/todos", json=payload, headers=headers)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    listed = await async_client.get("/v1/todos", headers=auth_headers)
    titles = [item["title"] for item in listed.json()["items"]]
    assert titles.count("Mua sữa") == 1


@pytest.mark.asyncio
async def test_idempotency_key_conflict_on_different_body(async_client, auth_headers):
    """Same Idempotency-Key + different body → 409 idempotency_conflict."""
    headers = {**auth_headers, "Idempotency-Key": "key-2"}

    first = await async_client.post("/v1/todos", json={"title": "Mua sữa"}, headers=headers)
    assert first.status_code == 201

    second = await async_client.post("/v1/todos", json={"title": "Mua trứng"}, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_conflict"


@pytest.mark.asyncio
async def test_without_idempotency_key_creates_separate_todos(async_client, auth_headers):
    """No Idempotency-Key header → behaves as before, each request creates a new todo."""
    payload = {"title": "Đọc sách"}

    first = await async_client.post("/v1/todos", json=payload, headers=auth_headers)
    second = await async_client.post("/v1/todos", json=payload, headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

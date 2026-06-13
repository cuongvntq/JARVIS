"""Idempotency-Key middleware tests."""

import asyncio

import pytest

from app.middleware.idempotency import _cache, _locks


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


@pytest.mark.asyncio
async def test_idempotency_key_conflict_across_routes(async_client, auth_headers):
    """Same Idempotency-Key + same body but different route → 409 idempotency_conflict
    (must not return the other route's cached response)."""
    payload = {"title": "Mua sữa"}
    headers = {**auth_headers, "Idempotency-Key": "key-cross-route"}

    todo_resp = await async_client.post("/v1/todos", json=payload, headers=headers)
    assert todo_resp.status_code == 201

    note_resp = await async_client.post("/v1/notes", json=payload, headers=headers)
    assert note_resp.status_code == 409
    assert note_resp.json()["error"]["code"] == "idempotency_conflict"


@pytest.mark.asyncio
async def test_idempotency_key_concurrent_requests_create_one_todo(async_client, auth_headers):
    """Two concurrent requests with the same Idempotency-Key + body must not both
    create a todo — the second must wait and return the first's cached response."""
    payload = {"title": "Đặt vé máy bay"}
    headers = {**auth_headers, "Idempotency-Key": "key-concurrent"}

    first, second = await asyncio.gather(
        async_client.post("/v1/todos", json=payload, headers=headers),
        async_client.post("/v1/todos", json=payload, headers=headers),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listed = await async_client.get("/v1/todos", headers=auth_headers)
    titles = [item["title"] for item in listed.json()["items"]]
    assert titles.count("Đặt vé máy bay") == 1


@pytest.mark.asyncio
async def test_idempotency_key_ignored_for_memory_search(async_client, auth_headers):
    """POST /v1/memories/search is a subroute of /v1/memories, not the create endpoint —
    middleware must not treat it as idempotent (no caching, no conflict)."""
    headers = {**auth_headers, "Idempotency-Key": "key-search"}
    payload = {"query": "cà phê"}

    first = await async_client.post("/v1/memories/search", json=payload, headers=headers)
    second = await async_client.post("/v1/memories/search", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert not any(key[1] == "key-search" for key in _cache)
    assert not any(key[1] == "key-search" for key in _locks)


@pytest.mark.asyncio
async def test_idempotency_lock_cleaned_up_after_failed_request(async_client, auth_headers):
    """A request with an Idempotency-Key that fails validation (4xx) must not leave a
    stale lock in _locks — otherwise repeated failed requests grow _locks forever."""
    headers = {**auth_headers, "Idempotency-Key": "key-invalid"}

    resp = await async_client.post("/v1/todos", json={"title": ""}, headers=headers)

    assert resp.status_code == 422
    assert not any(key[1] == "key-invalid" for key in _cache)
    assert not any(key[1] == "key-invalid" for key in _locks)

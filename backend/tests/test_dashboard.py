"""Dashboard API tests."""

from datetime import UTC, datetime, timedelta

import pytest


def _future_iso(hours: int = 2) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.asyncio
async def test_dashboard_today_returns_200(async_client, auth_headers):
    resp = await async_client.get("/v1/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "todos_today" in data
    assert "todos_count" in data
    assert "reminders_upcoming" in data
    assert "memories_count" in data
    assert "as_of" in data


@pytest.mark.asyncio
async def test_dashboard_todos_count_shape(async_client, auth_headers):
    resp = await async_client.get("/v1/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    count = resp.json()["todos_count"]
    assert "today" in count
    assert "overdue" in count
    assert "upcoming" in count
    assert all(isinstance(v, int) for v in count.values())


@pytest.mark.asyncio
async def test_dashboard_reminders_upcoming_empty(async_client, auth_headers):
    resp = await async_client.get("/v1/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["reminders_upcoming"], list)


@pytest.mark.asyncio
async def test_dashboard_with_reminder_appears(async_client, auth_headers):
    """Create a pending reminder → it appears in reminders_upcoming."""
    await async_client.post(
        "/v1/reminders",
        json={"title": "Dashboard test reminder", "remind_at": _future_iso(1)},
        headers=auth_headers,
    )
    resp = await async_client.get("/v1/dashboard/today", headers=auth_headers)
    assert resp.status_code == 200
    reminders = resp.json()["reminders_upcoming"]
    assert any(r["title"] == "Dashboard test reminder" for r in reminders)


@pytest.mark.asyncio
async def test_dashboard_unauthenticated(async_client):
    resp = await async_client.get("/v1/dashboard/today")
    assert resp.status_code == 401

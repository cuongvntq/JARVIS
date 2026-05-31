"""Tool executor unit tests — memory tools (save_memory, search_memory, forget_memory)."""

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio

from app.tools.executors import execute_forget_memory, execute_save_memory, execute_search_memory
from tests.conftest import _TestSession


@pytest_asyncio.fixture
async def db_session():
    async with _TestSession() as session:
        yield session
        await session.rollback()


# ── execute_save_memory ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_memory_happy_path(db_session):
    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        result = await execute_save_memory(
            db=db_session,
            user_id=uuid.uuid4(),
            params={"content": "Người dùng thích cà phê đen", "memory_type": "preference", "importance": 7},
        )
    assert result["success"] is True
    assert result["data"]["content"] == "Người dùng thích cà phê đen"
    assert result["data"]["memory_type"] == "preference"
    assert result["data"]["importance"] == 7
    assert "cà phê đen" in result["summary"]


@pytest.mark.asyncio
async def test_save_memory_default_importance(db_session):
    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        result = await execute_save_memory(
            db=db_session,
            user_id=uuid.uuid4(),
            params={"content": "Người dùng thích đọc sách", "memory_type": "preference"},
        )
    assert result["success"] is True
    assert result["data"]["importance"] == 5


@pytest.mark.asyncio
async def test_save_memory_content_too_short(db_session):
    result = await execute_save_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"content": "ab", "memory_type": "fact"},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_content"


@pytest.mark.asyncio
async def test_save_memory_invalid_type(db_session):
    result = await execute_save_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"content": "valid content here", "memory_type": "unknown_type"},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_memory_type"


@pytest.mark.asyncio
async def test_save_memory_invalid_importance(db_session):
    result = await execute_save_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"content": "valid content here", "memory_type": "fact", "importance": 15},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_importance"


# ── execute_search_memory ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_memory_returns_empty_on_sqlite(db_session):
    """SQLite test env always returns [] without calling embedding service."""
    result = await execute_search_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"query": "cà phê", "limit": 5},
    )
    assert result["success"] is True
    assert result["data"]["memories"] == []
    assert result["data"]["count"] == 0


@pytest.mark.asyncio
async def test_search_memory_missing_query(db_session):
    result = await execute_search_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"query": ""},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "missing_query"


@pytest.mark.asyncio
async def test_search_memory_with_memory_type_param(db_session):
    """memory_type is forwarded without error; SQLite path still returns []."""
    result = await execute_search_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"query": "sở thích ăn uống", "memory_type": "preference"},
    )
    assert result["success"] is True
    assert result["data"]["count"] == 0


@pytest.mark.asyncio
async def test_search_memory_null_memory_type_treated_as_all(db_session):
    """Explicit null memory_type should not filter — behaves like absent."""
    result = await execute_search_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"query": "test", "memory_type": None},
    )
    assert result["success"] is True


# ── execute_forget_memory ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_forget_memory_happy_path(db_session):
    user_id = uuid.uuid4()
    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        save_result = await execute_save_memory(
            db=db_session,
            user_id=user_id,
            params={"content": "Người dùng dị ứng tôm biển", "memory_type": "fact", "importance": 9},
        )
    assert save_result["success"] is True
    memory_id = save_result["data"]["id"]

    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        forget_result = await execute_forget_memory(
            db=db_session,
            user_id=user_id,
            params={"memory_id": memory_id},
        )
    assert forget_result["success"] is True
    assert forget_result["data"]["memory_id"] == memory_id


@pytest.mark.asyncio
async def test_forget_memory_not_found(db_session):
    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        result = await execute_forget_memory(
            db=db_session,
            user_id=uuid.uuid4(),
            params={"memory_id": str(uuid.uuid4())},
        )
    assert result["success"] is False
    assert result["error"]["code"] == "memory_not_found"


@pytest.mark.asyncio
async def test_forget_memory_invalid_id(db_session):
    result = await execute_forget_memory(
        db=db_session,
        user_id=uuid.uuid4(),
        params={"memory_id": "not-a-valid-uuid"},
    )
    assert result["success"] is False
    assert result["error"]["code"] == "invalid_memory_id"


@pytest.mark.asyncio
async def test_forget_memory_ownership_isolation(db_session):
    """User B cannot forget User A's memory — returns memory_not_found."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        save_result = await execute_save_memory(
            db=db_session,
            user_id=user_a,
            params={"content": "Memory riêng tư của user A", "memory_type": "fact"},
        )
    memory_id = save_result["data"]["id"]

    with patch("app.services.memory_service.AsyncSessionLocal", _TestSession):
        result = await execute_forget_memory(
            db=db_session,
            user_id=user_b,
            params={"memory_id": memory_id},
        )
    assert result["success"] is False
    assert result["error"]["code"] == "memory_not_found"

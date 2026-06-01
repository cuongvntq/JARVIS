"""Pytest fixtures for JARVIS backend tests."""

import os

# Must set env vars BEFORE any app imports so Settings() picks them up
os.environ.setdefault("APP_ENV", "test")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL_DIRECT"] = "sqlite:///./test_direct.db"
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key-for-tests")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-openai-key-for-tests")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-must-be-32-chars!!")
# Allow the httpx test base URL as a valid CSRF origin so cookie-based tests pass
os.environ.setdefault("BACKEND_CORS_ORIGINS", "http://test")

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.database as db_module
from app.database import Base, get_db
from app.llm.models import LLMResponse
from app.llm.orchestrator import OrchestratorResult
from app.llm.router import Intent, RouteResult
from app.main import app

# ── SQLite in-memory engine (StaticPool = single shared connection) ───────────
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Override module-level engine so repositories use SQLite
db_module.engine = _test_engine
db_module.AsyncSessionLocal = _TestSession


# ── Create tables once per test session ──────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Wipe all rows between tests ───────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with _test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ── Override get_db dependency ────────────────────────────────────────────────
async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db

# ── Shared test data ──────────────────────────────────────────────────────────
TEST_USER = {"email": "test@jarvis.dev", "password": "Test1234!", "name": "Test User"}


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_llm():
    """Patch orchestrator.run to avoid real LLM calls in chat endpoint tests."""
    _route = RouteResult(
        intent=Intent.CHITCHAT,
        model="gemini-mock",
        confidence=1.0,
        classify_source="prefilter",
        effective_tools=[],
    )
    _orch = OrchestratorResult(
        final_response=LLMResponse(
            content="Xin chào! Tôi là JARVIS.",
            model="gemini-mock",
            tokens_in=10,
            tokens_out=20,
        ),
        route=_route,
        tool_results=[],
        total_tokens_in=10,
        total_tokens_out=20,
        total_llm_calls=1,
    )
    with patch(
        "app.llm.orchestrator.run",
        new_callable=AsyncMock,
        return_value=_orch,
    ):
        yield


@pytest_asyncio.fixture
async def auth_headers(async_client):
    """Register a test user and return Bearer auth headers."""
    resp = await async_client.post("/auth/register", json=TEST_USER)
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_llm_stream():
    """Patch orchestrator.run_stream with a fake async generator (success path)."""
    _route = RouteResult(
        intent=Intent.CHITCHAT,
        model="gemini-mock",
        confidence=1.0,
        classify_source="prefilter",
        effective_tools=[],
    )

    async def _fake_stream(**kwargs):
        for char in "Xin chào! Tôi là JARVIS.":
            yield {"type": "delta", "content": char}
        yield {
            "type": "orchestrator_done",
            "content": "Xin chào! Tôi là JARVIS.",
            "model": "gemini-mock",
            "route": _route,
            "total_tokens_in": 10,
            "total_tokens_out": 20,
            "total_llm_calls": 1,
            "tool_results": [],
        }

    with patch("app.llm.orchestrator.run_stream", new=_fake_stream):
        yield


@pytest.fixture
def mock_llm_stream_error():
    """Patch orchestrator.run_stream to raise RuntimeError after yielding one delta."""

    async def _fake_stream_error(**kwargs):
        yield {"type": "delta", "content": "Partial"}
        raise RuntimeError("LLM timeout")

    with patch("app.llm.orchestrator.run_stream", new=_fake_stream_error):
        yield

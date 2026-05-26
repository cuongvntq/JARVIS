"""Health endpoint smoke test."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """GET /health returns 200 with status=ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    """GET / returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "jarvis-backend"
    assert "version" in data

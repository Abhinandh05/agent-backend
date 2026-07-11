"""Tests for POST /api/v1/agents/research (Day 6)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from core.dependencies import get_current_active_user
from database import get_db


def _mock_user():
    user = MagicMock()
    user.id = 1
    user.name = "Test"
    user.email = "test@example.com"
    user.is_active = True
    return user


def _mock_db():
    db = MagicMock()
    stored = {}

    def add(obj):
        obj.id = 1
        stored["task"] = obj

    def refresh(obj):
        obj.id = 1

    db.add.side_effect = add
    db.refresh.side_effect = refresh
    return db


def test_research_unauthenticated():
    """No JWT → 401 from OAuth2PasswordBearer."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/research",
        json={"topic": "AI market trends 2026"},
    )
    assert response.status_code == 401


def test_research_success():
    """Authenticated request with valid topic → 200 + standard response shape."""
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch(
            "agents.research_agent.run_research",
            return_value="## Findings\n- Point one",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/research",
                json={"topic": "AI market trends 2026"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Research completed"
    assert body["data"]["result"] == "## Findings\n- Point one"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_research_empty_topic():
    """Empty topic fails Pydantic validation → 422."""
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/research",
            json={"topic": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422

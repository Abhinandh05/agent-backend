"""Tests for POST /api/v1/agents/analytics (Day 12)."""
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

    def add(obj):
        obj.id = 1

    def refresh(obj):
        obj.id = 1

    db.add.side_effect = add
    db.refresh.side_effect = refresh
    return db


def test_analytics_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/analytics",
        json={"request": "Forecast sales for Technology in the West"},
    )
    assert response.status_code == 401


def test_analytics_success():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch(
            "agents.analytics_agent.run_analytics",
            return_value="## Analytics\n- Predicted sales look strong in Q4",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/analytics",
                json={"request": "Forecast sales for Technology West in November"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Analytics completed"
    assert "Predicted sales" in body["data"]["result"]
    assert mock_db.add.called


def test_analytics_empty_request():
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/analytics",
            json={"request": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422

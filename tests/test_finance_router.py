"""Tests for POST /api/v1/agents/finance (Day 11)."""
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


def test_finance_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/finance",
        json={"request": "Assess this loan applicant"},
    )
    assert response.status_code == 401


def test_finance_success():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch(
            "agents.finance_agent.run_finance_analysis",
            return_value="## Credit assessment\n- Approve",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/finance",
                json={"request": "Assess this loan applicant with good credit history"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Finance analysis completed"
    assert "Approve" in body["data"]["result"]
    assert mock_db.add.called


def test_finance_empty_request():
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/finance",
            json={"request": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422

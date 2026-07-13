"""Tests for POST /api/v1/agents/coding and /api/v1/tools/execute-code (Day 13)."""
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


def test_coding_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/coding",
        json={"request": "Write a function to check if a number is prime"},
    )
    assert response.status_code == 401


def test_coding_success():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch(
            "agents.coding_agent.run_coding_task",
            return_value="## Code\n```python\ndef is_prime(n): ...\n```\nTested successfully.",
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/coding",
                json={"request": "Write a function to check if a number is prime"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Coding completed"
    assert "is_prime" in body["data"]["result"]
    assert mock_db.add.called


def test_coding_empty_request():
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/coding",
            json={"request": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_execute_code_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/tools/execute-code",
        json={"code": 'print("hello")'},
    )
    assert response.status_code == 401


def test_execute_code_success():
    app.dependency_overrides[get_current_active_user] = _mock_user

    try:
        with patch(
            "tools.code_execution_tool.execute_python_code",
            return_value={
                "stdout": "hello\n",
                "stderr": "",
                "exit_code": 0,
                "success": True,
            },
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/tools/execute-code",
                json={"code": 'print("hello")'},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Code execution completed"
    assert body["data"]["success"] is True
    assert "hello" in body["data"]["stdout"]


def test_execute_code_empty():
    app.dependency_overrides[get_current_active_user] = _mock_user

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/tools/execute-code",
            json={"code": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422

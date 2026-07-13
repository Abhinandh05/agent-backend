"""Router tests for POST /api/v1/agents/manager (Day 16)."""
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
        obj.id = 99

    def refresh(obj):
        obj.id = 99

    db.add.side_effect = add
    db.refresh.side_effect = refresh
    return db


MANAGER_RESULT = {
    "plan": [
        {"agent": "research", "subtask": "Research EV batteries"},
        {"agent": "finance", "subtask": "Investment timing"},
    ],
    "step_results": [
        {
            "agent": "research",
            "subtask": "Research EV batteries",
            "status": "completed",
            "output": "Market is growing.",
        },
        {
            "agent": "finance",
            "subtask": "Investment timing",
            "status": "completed",
            "output": "Cautiously positive.",
        },
    ],
    "final_response": "EV battery market looks promising with caveats.",
}


def test_manager_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/manager",
        json={
            "request": "Research the EV market and analyze investment timing"
        },
    )
    assert response.status_code == 401


def test_manager_validation_too_short():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/manager",
            json={"request": "ab"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_manager_success():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch(
            "agents.manager_agent.run_manager_explicit_plan",
            return_value=MANAGER_RESULT,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/manager",
                json={
                    "request": (
                        "Research the current EV battery market, analyze "
                        "whether it's a good time to invest, and summarize"
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["final_response"].startswith("EV battery")
    assert len(body["data"]["plan"]) == 2
    assert len(body["data"]["step_results"]) == 2
    assert body["data"]["task_id"] == 99
    # Persisted plan_details on the Task row
    assert mock_db.commit.called
    saved_task = mock_db.add.call_args[0][0]
    # After success path, plan_details should be set on the same object
    assert saved_task.agent_type == "manager"
    assert saved_task.status == "completed"
    assert saved_task.plan_details is not None
    assert "research" in saved_task.plan_details

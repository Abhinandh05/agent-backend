"""Tests for email draft/send routes and parse_email_output (Day 14)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agents.email_agent import parse_email_output
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


def test_parse_email_output_happy_path():
    raw = "SUBJECT: Meeting tomorrow\nBODY:\nHi team,\n\nSee you at 10.\n"
    parsed = parse_email_output(raw)
    assert parsed["subject"] == "Meeting tomorrow"
    assert "See you at 10" in parsed["body"]
    assert "SUBJECT:" in parsed["raw"]


def test_email_draft_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/email",
        json={"request": "Write a thank-you email to a client"},
    )
    assert response.status_code == 401


def test_email_draft_success_includes_sentiment():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    draft = {
        "subject": "Thank you",
        "body": "Thank you so much, this is wonderful news!",
        "raw": "SUBJECT: Thank you\nBODY:\nThank you so much, this is wonderful news!",
    }
    sentiment = {
        "label": "POSITIVE",
        "confidence": 0.99,
        "tone_warning": None,
        "truncated": False,
    }

    try:
        with patch(
            "agents.email_agent.run_email_draft",
            return_value=draft,
        ), patch(
            "services.sentiment_service.analyze_sentiment",
            return_value=sentiment,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/email",
                json={"request": "Write a thank-you email to a client"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["subject"] == "Thank you"
    assert "wonderful" in body["data"]["body"]
    assert body["data"]["sentiment"]["label"] == "POSITIVE"
    assert body["data"]["sentiment"]["tone_warning"] is None


def test_email_draft_sentiment_failure_omits_field():
    """Sentiment errors must not fail the draft — sentiment becomes null."""
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    draft = {
        "subject": "Update",
        "body": "Here is an update.",
        "raw": "SUBJECT: Update\nBODY:\nHere is an update.",
    }

    try:
        with patch(
            "agents.email_agent.run_email_draft",
            return_value=draft,
        ), patch(
            "services.sentiment_service.analyze_sentiment",
            side_effect=RuntimeError("model offline"),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/email",
                json={"request": "Draft a short status update email"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["subject"] == "Update"
    assert body["data"]["sentiment"] is None


def test_email_draft_empty_request():
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agents/email",
            json={"request": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_email_send_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/email/send",
        json={
            "to": "client@example.com",
            "subject": "Hi",
            "body": "Hello",
        },
    )
    assert response.status_code == 401


def test_email_send_missing_sendgrid_config():
    mock_db = _mock_db()
    app.dependency_overrides[get_current_active_user] = _mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch.dict(
            "os.environ",
            {"SENDGRID_API_KEY": "", "SENDGRID_FROM_EMAIL": ""},
            clear=False,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/agents/email/send",
                json={
                    "to": "client@example.com",
                    "subject": "Hi",
                    "body": "Hello",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "SENDGRID" in (body["error"] or "").upper()

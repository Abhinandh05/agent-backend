"""Tests for POST /api/v1/ml/spam-check and /fraud-check."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from core.dependencies import get_current_active_user


def _mock_user():
    user = MagicMock()
    user.id = 1
    user.name = "Test"
    user.email = "test@example.com"
    user.is_active = True
    return user


def test_spam_check_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/ml/spam-check",
        json={"text": "WIN FREE MONEY NOW"},
    )
    assert response.status_code == 401


def test_fraud_check_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/ml/fraud-check",
        json={"features": {"Amount": 10.0}},
    )
    assert response.status_code == 401


def test_spam_check_success():
    app.dependency_overrides[get_current_active_user] = _mock_user
    try:
        with patch(
            "ml.predict_spam.classify_message",
            return_value={
                "is_spam": True,
                "confidence": 0.97,
                "label": "spam",
            },
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/ml/spam-check",
                json={"text": "WIN FREE MONEY NOW CLICK HERE"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["is_spam"] is True
    assert body["data"]["label"] == "spam"
    assert body["message"] == "Spam check completed"


def test_fraud_check_success():
    app.dependency_overrides[get_current_active_user] = _mock_user
    try:
        with patch(
            "ml.predict_fraud.check_transaction",
            return_value={
                "is_anomalous": False,
                "anomaly_score": 0.12,
                "risk_note": "Looks normal.",
            },
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/ml/fraud-check",
                json={"features": {"V1": 0.1, "Amount": 50.0}},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["is_anomalous"] is False
    assert "anomaly_score" in body["data"]
    assert body["message"] == "Fraud check completed"

"""Pytest for predict_spam — skips if .pkl not trained yet."""
from pathlib import Path

import pytest

from ml.predict_spam import MODEL_PATH, classify_message

MODEL_EXISTS = MODEL_PATH.is_file()


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_spam_classifier",
)
def test_classify_message_spam_shape():
    result = classify_message(
        "WIN FREE MONEY NOW CLICK HERE to claim your prize urgently!!!"
    )
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"is_spam", "confidence", "label"}
    assert isinstance(result["is_spam"], bool)
    assert 0.0 <= float(result["confidence"]) <= 1.0
    assert result["label"] in ("spam", "ham")


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_spam_classifier",
)
def test_classify_message_ham_shape():
    result = classify_message(
        "Hi team, please review the budget draft and reply by Friday."
    )
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"is_spam", "confidence", "label"}
    assert result["label"] in ("spam", "ham")

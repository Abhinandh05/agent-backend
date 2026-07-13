"""Pytest for predict_segment — skips gracefully if the .pkl is not trained yet."""
from pathlib import Path

import pytest

from ml.predict_customer_segment import MODEL_PATH, predict_segment

MODEL_EXISTS = MODEL_PATH.is_file()

SAMPLE_CUSTOMER = {
    "age": 32,
    "annual_income": 60,
    "spending_score": 55,
}


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=(
        f"Model not found at {MODEL_PATH}; "
        "run: python -m ml.train_customer_segments"
    ),
)
def test_predict_segment_shape():
    result = predict_segment(SAMPLE_CUSTOMER)

    assert isinstance(result, dict)
    assert set(result.keys()) >= {"segment", "cluster_id", "profile_note"}
    assert isinstance(result["segment"], str)
    assert len(result["segment"]) > 0
    assert isinstance(result["cluster_id"], int)
    assert isinstance(result["profile_note"], str)
    assert result["segment"] in result["profile_note"]

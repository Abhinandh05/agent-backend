"""Pytest for predict_sales — skips if .pkl not trained yet."""
from pathlib import Path

import pytest

from ml.predict_sales_forecast import MODEL_PATH, predict_sales

MODEL_EXISTS = MODEL_PATH.is_file()

SAMPLE_FEATURES = {
    "year": 2017,
    "month": 11,
    "day_of_week": 1,
    "quarter": 4,
    "Category": "Technology",
    "Region": "West",
    "Segment": "Consumer",
}


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_sales_forecast_model",
)
def test_predict_sales_shape():
    result = predict_sales(SAMPLE_FEATURES)

    assert isinstance(result, dict)
    assert set(result.keys()) >= {"predicted_sales", "confidence_note"}
    assert isinstance(result["predicted_sales"], (int, float))
    assert float(result["predicted_sales"]) >= 0.0
    assert isinstance(result["confidence_note"], str)
    assert len(result["confidence_note"]) > 10

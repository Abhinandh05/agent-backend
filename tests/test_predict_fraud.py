"""Pytest for predict_fraud — skips if .pkl not trained yet."""
from pathlib import Path

import pytest

from ml.predict_fraud import MODEL_PATH, check_transaction

MODEL_EXISTS = MODEL_PATH.is_file()

# Minimal synthetic row — only used when model exists; columns come from artifact.
# If training used V1..V28 + Amount, missing keys raise ValueError — so we load
# feature list from the artifact when present.
def _sample_features() -> dict:
    import joblib

    artifact = joblib.load(MODEL_PATH)
    cols = artifact["feature_columns"]
    return {c: 0.0 for c in cols}


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_fraud_detector",
)
def test_check_transaction_shape():
    result = check_transaction(_sample_features())
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"is_anomalous", "anomaly_score", "risk_note"}
    assert isinstance(result["is_anomalous"], bool)
    assert isinstance(result["anomaly_score"], float)
    assert isinstance(result["risk_note"], str)
    assert len(result["risk_note"]) > 10

"""
Load the trained IsolationForest fraud detector and score one transaction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "fraud_detector.pkl"

_artifact: dict[str, Any] | None = None

_NORMAL_NOTE = (
    "This transaction's pattern looks consistent with typical activity; "
    "no anomaly flag raised."
)
_ANOMALY_NOTE = (
    "This transaction's pattern differs significantly from typical "
    "transactions and warrants review."
)


def _load_artifact() -> dict[str, Any]:
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_fraud_detector"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _row_from_features(features: dict, columns: list[str]) -> pd.DataFrame:
    """Build a one-row DataFrame aligned to training feature order."""
    lower = {str(k).lower(): v for k, v in features.items()}
    values: dict[str, float] = {}
    missing: list[str] = []
    for col in columns:
        if col in features:
            values[col] = float(features[col])
        elif col.lower() in lower:
            values[col] = float(lower[col.lower()])
        else:
            missing.append(col)
    if missing:
        raise ValueError(
            f"Missing required feature(s): {missing}. "
            f"Expected columns: {columns}"
        )
    return pd.DataFrame([values], columns=columns)


def check_transaction(features: dict) -> dict:
    """
    Score one transaction for anomalous / fraud-like patterns.

    Returns
    -------
    {
      "is_anomalous": bool,
      "anomaly_score": float,  # IsolationForest decision_function (higher=more normal)
      "risk_note": str
    }

    anomaly_score interpretation: sklearn's decision_function returns higher
    values for more "normal" points and lower (often negative) for outliers.
    We expose the raw score; is_anomalous is the model's binary flag.
    """
    artifact = _load_artifact()
    model = artifact["model"]
    scaler = artifact["scaler"]
    columns = artifact["feature_columns"]

    row = _row_from_features(features, columns)
    X_scaled = scaler.transform(row)
    raw = int(model.predict(X_scaled)[0])  # -1 anomaly, 1 normal
    score = float(model.decision_function(X_scaled)[0])
    is_anomalous = raw == -1

    return {
        "is_anomalous": is_anomalous,
        "anomaly_score": round(score, 6),
        "risk_note": _ANOMALY_NOTE if is_anomalous else _NORMAL_NOTE,
    }


def model_ready() -> bool:
    return MODEL_PATH.is_file()

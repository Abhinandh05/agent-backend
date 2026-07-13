"""
Load the trained customer-segmentation K-Means model and assign a segment.

Usage:
    from ml.predict_customer_segment import predict_segment
    result = predict_segment({"age": 28, "annual_income": 75, "spending_score": 80})
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "segmentation_model.pkl"

_artifact: dict[str, Any] | None = None

# Accept common aliases from API / agents / callers
_FIELD_ALIASES = {
    "Age": ("age", "Age"),
    "Annual_Income": (
        "annual_income",
        "Annual_Income",
        "annualIncome",
        "Annual Income",
        "Annual Income (k$)",
        "income",
    ),
    "Spending_Score": (
        "spending_score",
        "Spending_Score",
        "spendingScore",
        "Spending Score",
        "Spending Score (1-100)",
        "spending",
    ),
}


def _load_artifact() -> dict[str, Any]:
    """Load the joblib bundle once at first use (module-level cache)."""
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_customer_segments"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _extract_features(customer: dict, feature_columns: list[str]) -> pd.DataFrame:
    """Build a one-row DataFrame in training column order from a free-form dict."""
    values: dict[str, float] = {}
    missing: list[str] = []
    for col in feature_columns:
        aliases = _FIELD_ALIASES.get(col, (col, col.lower()))
        found = None
        for key in aliases:
            if key in customer:
                found = customer[key]
                break
        # Case-insensitive fallback
        if found is None:
            lower = {str(k).lower(): v for k, v in customer.items()}
            for key in aliases:
                if key.lower() in lower:
                    found = lower[key.lower()]
                    break
        if found is None:
            missing.append(col)
        else:
            values[col] = float(found)
    if missing:
        raise ValueError(
            f"Missing required fields: {missing}. "
            "Pass age, annual_income, and spending_score."
        )
    return pd.DataFrame([values], columns=feature_columns)


def predict_segment(customer: dict) -> dict:
    """
    Assign a customer to a K-Means segment.

    Parameters
    ----------
    customer : dict
        {"age": int, "annual_income": float, "spending_score": float}
        (aliases like Age / Annual Income (k$) also accepted)

    Returns
    -------
    dict with keys:
        segment : str  — human-readable business label
        cluster_id : int
        profile_note : str
    """
    artifact = _load_artifact()
    model = artifact["model"]
    scaler = artifact["scaler"]
    cluster_labels: dict = artifact["cluster_labels"]
    feature_columns: list[str] = artifact["feature_columns"]
    profiles: dict = artifact.get("cluster_profiles", {})

    X = _extract_features(customer, feature_columns)
    # Must use the SAME fitted scaler as training — raw Age/Income/Score
    # would not match the scaled space the centroids live in.
    X_scaled = scaler.transform(X)
    cluster_id = int(model.predict(X_scaled)[0])

    # cluster_labels keys may be int (from training) or str (after some loaders)
    segment = cluster_labels.get(cluster_id) or cluster_labels.get(str(cluster_id))
    if segment is None:
        segment = f"Cluster {cluster_id}"

    profile = profiles.get(str(cluster_id), {})
    if profile:
        profile_note = (
            f"This customer fits the '{segment}' profile: "
            f"cluster means ≈ age {profile.get('mean_age')}, "
            f"income {profile.get('mean_annual_income')}, "
            f"spending score {profile.get('mean_spending_score')}."
        )
    else:
        profile_note = f"This customer fits the '{segment}' profile."

    return {
        "segment": segment,
        "cluster_id": cluster_id,
        "profile_note": profile_note,
    }


def model_ready() -> bool:
    """True if the .pkl artifact exists on disk."""
    return MODEL_PATH.is_file()

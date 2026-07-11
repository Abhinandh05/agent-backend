"""
Load the trained churn model and predict for a single customer dict.

Usage:
    from ml.predict_churn import predict_churn
    result = predict_churn({"tenure": 2, "Contract": "Month-to-month", ...})

# Future enhancement: per-prediction SHAP values for true local explanations.
# Today we surface global RandomForest feature importances as `top_factors`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "churn_model.pkl"

_artifact: dict[str, Any] | None = None


def _load_artifact() -> dict[str, Any]:
    """Load the joblib bundle once at first use (module-level cache)."""
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_churn_model"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _preprocess(customer: dict, columns: list[str]) -> pd.DataFrame:
    """
    Apply the SAME one-hot / column alignment used in training.

    Critical: train and predict must share identical feature columns (order +
    names). If a category value was never seen in training (or is missing from
    this customer), get_dummies won't create that column — we reindex to the
    saved `columns` list and fill missing with 0. Feeding a differently shaped
    matrix is a common silent bug that corrupts RandomForest predictions.
    """
    row = pd.DataFrame([customer])

    # Drop ID / label if the caller accidentally included them
    row = row.drop(columns=["customerID", "Churn"], errors="ignore")

    if "TotalCharges" in row.columns:
        row["TotalCharges"] = pd.to_numeric(row["TotalCharges"], errors="coerce").fillna(0)

    cat_cols = row.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        row = pd.get_dummies(row, columns=cat_cols, drop_first=False)

    # Align to training columns — missing → 0, extra → dropped
    row = row.reindex(columns=columns, fill_value=0)
    for col in row.columns:
        row[col] = pd.to_numeric(row[col], errors="coerce").fillna(0)
    return row


def predict_churn(customer: dict) -> dict:
    """
    Predict churn for one customer.

    Parameters
    ----------
    customer : dict
        Raw features using original CSV column names, e.g.
        {"tenure": 12, "MonthlyCharges": 70.5, "Contract": "Month-to-month", ...}

    Returns
    -------
    dict with keys:
        churn_prediction : "Yes" | "No"
        churn_probability : float in [0, 1]  (P(Churn=Yes))
        top_factors : list of {feature, importance} from global RF importances
    """
    artifact = _load_artifact()
    model = artifact["model"]
    columns = artifact["columns"]
    label_map = artifact.get("label_map", {0: "No", 1: "Yes"})

    X = _preprocess(customer, columns)
    proba = float(model.predict_proba(X)[0][1])  # P(class=1 / Yes)
    pred_class = int(model.predict(X)[0])

    # Global feature importances (not per-row SHAP — see module docstring)
    importances = getattr(model, "feature_importances_", None)
    top_factors: list[dict] = []
    if importances is not None:
        pairs = sorted(
            zip(columns, importances),
            key=lambda t: t[1],
            reverse=True,
        )[:5]
        top_factors = [
            {"feature": name, "importance": round(float(score), 4)}
            for name, score in pairs
        ]

    return {
        "churn_prediction": label_map.get(pred_class, str(pred_class)),
        "churn_probability": round(proba, 4),
        "top_factors": top_factors,
    }


def model_ready() -> bool:
    """True if the .pkl artifact exists on disk."""
    return MODEL_PATH.is_file()

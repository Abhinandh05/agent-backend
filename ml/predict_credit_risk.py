"""
Load the trained credit-risk model and score one loan applicant.

Mirrors ml/predict_churn.py for consistency across the codebase.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "credit_risk_model.pkl"

_artifact: dict[str, Any] | None = None


def _load_artifact() -> dict[str, Any]:
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_credit_risk_model"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _preprocess(applicant: dict, columns: list[str], id_cols: list[str], label_col: str) -> pd.DataFrame:
    """
    Same get_dummies + column reindex pattern as churn.

    Mismatched train/predict columns silently break RandomForest — always
    align to the saved `columns` list from training.
    """
    row = pd.DataFrame([applicant])
    drop_cols = list(id_cols) + [label_col, "Loan_Status", "loan_status", "default"]
    row = row.drop(columns=[c for c in drop_cols if c in row.columns], errors="ignore")

    for col in row.columns:
        if pd.api.types.is_numeric_dtype(row[col]) or str(row[col].dtype).startswith("float"):
            row[col] = pd.to_numeric(row[col], errors="coerce").fillna(0)
        else:
            # try numeric coercion for fields sent as strings
            coerced = pd.to_numeric(row[col], errors="coerce")
            if not coerced.isna().all():
                row[col] = coerced.fillna(0)

    cat_cols = row.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        row = pd.get_dummies(row, columns=cat_cols, drop_first=False)

    row = row.reindex(columns=columns, fill_value=0)
    for col in row.columns:
        row[col] = pd.to_numeric(row[col], errors="coerce").fillna(0)
    return row


def predict_credit_risk(applicant: dict) -> dict:
    """
    Predict loan approval / credit risk for one applicant.

    Returns
    -------
    {
      "risk_prediction": "Approve" | "Reject",
      "risk_probability": float,   # P(Approve)
      "top_factors": [{"feature": str, "importance": float}, ...]
    }
    """
    artifact = _load_artifact()
    model = artifact["model"]
    columns = artifact["columns"]
    label_map = artifact.get("label_map", {0: "Reject", 1: "Approve"})
    id_cols = artifact.get("id_cols", [])
    label_col = artifact.get("label_col", "Loan_Status")

    X = _preprocess(applicant, columns, id_cols, label_col)
    proba_approve = float(model.predict_proba(X)[0][1])
    pred_class = int(model.predict(X)[0])

    importances = getattr(model, "feature_importances_", None)
    top_factors: list[dict] = []
    if importances is not None:
        pairs = sorted(zip(columns, importances), key=lambda t: t[1], reverse=True)[:5]
        top_factors = [
            {"feature": name, "importance": round(float(score), 4)}
            for name, score in pairs
        ]

    return {
        "risk_prediction": label_map.get(pred_class, str(pred_class)),
        "risk_probability": round(proba_approve, 4),
        "top_factors": top_factors,
    }


def model_ready() -> bool:
    return MODEL_PATH.is_file()

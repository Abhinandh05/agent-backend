"""
Load the trained sales-forecast model and predict for a feature dict.

Usage:
    from ml.predict_sales_forecast import predict_sales
    result = predict_sales({"year": 2017, "month": 11, "Category": "Technology", ...})
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "sales_forecast_model.pkl"

_artifact: dict[str, Any] | None = None

CONFIDENCE_NOTE = (
    "estimate based on historical patterns; wider ranges expected further into the future."
)


def _load_artifact() -> dict[str, Any]:
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_sales_forecast_model"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _preprocess(features: dict, columns: list[str], cat_cols: list[str]) -> pd.DataFrame:
    """
    Align caller features to the training column layout (get_dummies + reindex).

    Accepts either:
      - calendar fields: year, month, day_of_week, quarter (+ optional Category/Region)
      - or a date string / datetime under keys like Order Date / date — we derive
        calendar fields automatically when year/month are missing.
    """
    row = dict(features)

    # Derive calendar features from a date if the caller passed one
    date_keys = ["Order Date", "order_date", "date", "Date", "forecast_date"]
    has_calendar = all(k in row for k in ("year", "month"))
    if not has_calendar:
        date_val = None
        for k in date_keys:
            if k in row and row[k] is not None:
                date_val = row.pop(k)
                break
        if date_val is not None:
            ts = pd.to_datetime(date_val, errors="coerce")
            if pd.isna(ts):
                raise ValueError(f"Could not parse date value: {date_val!r}")
            row.setdefault("year", int(ts.year))
            row.setdefault("month", int(ts.month))
            row.setdefault("day_of_week", int(ts.dayofweek))
            row.setdefault("quarter", int(ts.quarter))

    # Defaults for missing calendar fields (mid-week, mid-year-ish)
    row.setdefault("year", 2017)
    row.setdefault("month", 6)
    row.setdefault("day_of_week", 2)
    row.setdefault("quarter", (int(row["month"]) - 1) // 3 + 1)

    df = pd.DataFrame([row])
    present_cats = [c for c in cat_cols if c in df.columns]
    # Also one-hot any leftover object columns the caller sent
    extra_obj = [
        c
        for c in df.select_dtypes(include=["object", "category"]).columns
        if c not in present_cats
    ]
    encode_cols = present_cats + extra_obj
    if encode_cols:
        df = pd.get_dummies(df, columns=encode_cols, drop_first=False)

    df = df.reindex(columns=columns, fill_value=0)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def predict_sales(features: dict) -> dict:
    """
    Predict sales/revenue for one feature set.

    Returns
    -------
    {
      "predicted_sales": float,
      "confidence_note": str,
    }
    """
    artifact = _load_artifact()
    model = artifact["model"]
    columns = artifact["columns"]
    cat_cols = artifact.get("cat_cols", [])

    X = _preprocess(features, columns, cat_cols)
    pred = float(model.predict(X)[0])
    # Sales shouldn't be negative for this use case
    pred = max(0.0, pred)

    return {
        "predicted_sales": round(pred, 2),
        "confidence_note": CONFIDENCE_NOTE,
    }


def model_ready() -> bool:
    return MODEL_PATH.is_file()

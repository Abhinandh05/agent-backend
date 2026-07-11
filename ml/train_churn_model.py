"""
Train a Customer Churn RandomForest on the Telco Customer Churn dataset.

Usage (from the backend root, venv active):
    python -m ml.train_churn_model

Requires: data/telco_churn.csv (download manually from Kaggle — see README).
Trains on CPU in well under a minute for ~7k rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib

# Non-interactive backend so training works on headless / no-display machines
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "telco_churn.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "churn_model.pkl"
IMPORTANCE_CHART = MODELS_DIR / "feature_importance.png"

# Columns we never feed as features
ID_COL = "customerID"
LABEL_COL = "Churn"
# Known numeric columns in the Telco dataset
NUMERIC_COLS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Download the Telco Customer Churn CSV from:\n"
            "  https://www.kaggle.com/datasets/blastchar/telco-customer-churn\n"
            "Then place/rename it exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def load_and_clean(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """
    Load CSV, clean TotalCharges blanks, encode categoricals, return X, y.

    TotalCharges quirk: a handful of rows have blank strings (new customers with
    tenure=0). We coerce to numeric and DROP those rows rather than impute —
    there are very few of them (~11), RandomForest doesn't need them, and dropping
    avoids inventing fake charge values that could skew the model.
    """
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")

    # Coerce TotalCharges; blanks → NaN
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["TotalCharges"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped} row(s) with blank/invalid TotalCharges")

    # Label: Yes → 1, No → 0
    y = (df[LABEL_COL].astype(str).str.strip().str.lower() == "yes").astype(int)
    X = df.drop(columns=[LABEL_COL, ID_COL], errors="ignore")

    # One-hot encode all remaining object/category columns with get_dummies.
    # Choice: get_dummies is simple and matches what we store as `columns`
    # for predict-time alignment (no separate OneHotEncoder object needed).
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    X = pd.get_dummies(X, columns=cat_cols, drop_first=False)

    # Ensure numeric dtypes
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    return X, y


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_and_clean(DATA_PATH)
    feature_columns = list(X.columns)

    # Stratified 80/20 so both classes appear in train and test
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    print(f"Train size={len(X_train)}, Test size={len(X_test)}")
    print(f"Churn rate (train)={y_train.mean():.3f}, (test)={y_test.mean():.3f}")

    # RandomForest: no feature scaling needed, handles mixed types after OHE,
    # class_weight='balanced' counters the ~26% churn minority class.
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n=== Test-set evaluation ===")
    print(classification_report(y_test, y_pred, target_names=["No Churn", "Churn"]))
    print("Confusion matrix [[TN FP],[FN TP]]:")
    print(confusion_matrix(y_test, y_pred))

    # Top-10 feature importance chart (business-friendly story)
    importances = pd.Series(model.feature_importances_, index=feature_columns)
    top10 = importances.nlargest(10).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    top10.plot(kind="barh", ax=ax, color="#3b82f6")
    ax.set_title("Top 10 Feature Importances — Churn Model")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(IMPORTANCE_CHART, dpi=120)
    plt.close(fig)
    print(f"\nSaved feature importance chart → {IMPORTANCE_CHART}")

    # Bundle model + column layout so predict_churn applies identical encoding.
    # Mismatched train/predict columns is a very common production bug.
    artifact = {
        "model": model,
        "columns": feature_columns,
        "label_map": {0: "No", 1: "Yes"},
        "raw_feature_hints": {
            "numeric": NUMERIC_COLS,
            "dropped": [ID_COL, LABEL_COL],
        },
    }
    joblib.dump(artifact, MODEL_PATH)

    acc = (y_pred == y_test).mean()
    print("\n=== Training complete ===")
    print(f"Accuracy: {acc:.4f}")
    print(f"Model saved to: {MODEL_PATH}")
    print("Trained on CPU only — typically seconds to ~1 minute on this dataset.")
    return artifact


def main() -> int:
    try:
        train()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

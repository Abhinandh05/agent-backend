"""
Train a Loan/Credit Risk RandomForest on data/loan_data.csv.

Usage (from backend root, venv active):
    python -m ml.train_credit_risk_model

Column names vary across Kaggle loan datasets — this script prints headers and
auto-detects the label / ID columns instead of hardcoding one schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "loan_data.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "credit_risk_model.pkl"
IMPORTANCE_CHART = MODELS_DIR / "credit_feature_importance.png"

# Candidate names across common Kaggle loan / credit datasets
LABEL_CANDIDATES = [
    "Loan_Status",
    "loan_status",
    "LoanStatus",
    "default",
    "Default",
    "Defaulted",
    "loan_default",
    "Risk",
    "credit_risk",
    "Credit_Risk",
]
ID_CANDIDATES = ["Loan_ID", "loan_id", "id", "ID", "Applicant_ID"]

# Values that mean "approve / good / no default" → class 1 (Approve)
POSITIVE_LABELS = {"y", "yes", "approve", "approved", "good", "0", "false", "n", "no"}
# For datasets where 1 = defaulted / rejected
DEFAULT_IS_ONE_LABELS = {"default", "defaulted", "loan_default", "risk", "credit_risk"}


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Download a free loan / credit-risk CSV from Kaggle, e.g.:\n"
            "  https://www.kaggle.com/datasets/altruistdelhite04/loan-prediction-problem-dataset\n"
            "  (or search: 'loan prediction' / 'loan default prediction')\n"
            "Then place/rename it exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def _detect_label_column(columns: list[str]) -> str:
    lower_map = {c.lower(): c for c in columns}
    for cand in LABEL_CANDIDATES:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise ValueError(
        "Could not auto-detect the label column. "
        f"Columns found: {columns}\n"
        f"Expected one of: {LABEL_CANDIDATES}"
    )


def _detect_id_columns(columns: list[str]) -> list[str]:
    found = []
    lower_map = {c.lower(): c for c in columns}
    for cand in ID_CANDIDATES:
        if cand in columns:
            found.append(cand)
        elif cand.lower() in lower_map:
            found.append(lower_map[cand.lower()])
    return list(dict.fromkeys(found))  # unique, order preserved


def _encode_label(series: pd.Series, label_col: str) -> tuple[pd.Series, dict]:
    """
    Map raw labels → 0/1 and return human-readable label_map.

    Convention for the API:
      class 1 → "Approve" (loan OK / not defaulted)
      class 0 → "Reject"
    """
    raw = series.astype(str).str.strip()
    unique = sorted(raw.unique().tolist())
    print(f"Label column '{label_col}' unique values: {unique}")

    # Binary numeric already?
    if set(unique).issubset({"0", "1"}):
        # If column name suggests "default", 1 = bad → flip to Approve=not default
        if label_col.lower() in {c.lower() for c in DEFAULT_IS_ONE_LABELS}:
            y = (raw != "1").astype(int)  # 1 → Reject(0), 0 → Approve(1)
        else:
            # Assume 1 = approved / good (common in some cleaned sets)
            y = (raw == "1").astype(int)
        return y, {0: "Reject", 1: "Approve"}

    # Y/N or Yes/No style (Dream Housing Loan_Status)
    lowered = raw.str.lower()
    if set(lowered.unique()).issubset({"y", "n", "yes", "no"}):
        y = lowered.isin(["y", "yes"]).astype(int)
        return y, {0: "Reject", 1: "Approve"}

    # Approve/Reject style
    if any("approv" in v.lower() or "reject" in v.lower() for v in unique):
        y = lowered.str.contains("approv").astype(int)
        return y, {0: "Reject", 1: "Approve"}

    # Fallback: first unique → 0, second → 1 (document it)
    mapping = {unique[0]: 0, unique[1]: 1} if len(unique) >= 2 else {unique[0]: 0}
    print(f"Fallback label mapping: {mapping}")
    y = raw.map(mapping).astype(int)
    return y, {0: "Reject", 1: "Approve"}


def load_and_clean(path: Path) -> tuple[pd.DataFrame, pd.Series, dict]:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")
    print(f"CSV columns: {list(df.columns)}")

    label_col = _detect_label_column(list(df.columns))
    id_cols = _detect_id_columns(list(df.columns))
    print(f"Detected label column: {label_col}")
    print(f"Detected ID column(s) to drop: {id_cols}")

    y, label_map = _encode_label(df[label_col], label_col)
    X = df.drop(columns=[label_col] + id_cols, errors="ignore")

    # Imputation strategy:
    # - Numeric: median (robust to outliers common in income / loan amount)
    # - Categorical: mode (most frequent category; keeps RF happy without inventing
    #   new levels). Loan datasets often miss Credit_History / LoanAmount / Self_Employed.
    for col in X.columns:
        if pd.api.types.is_numeric_dtype(X[col]):
            if X[col].isna().any():
                median = X[col].median()
                X[col] = X[col].fillna(median)
                print(f"  Imputed numeric '{col}' with median={median}")
        else:
            # Coerce blank strings to NaN then fill with mode
            X[col] = X[col].replace(r"^\s*$", np.nan, regex=True)
            if X[col].isna().any():
                mode = X[col].mode(dropna=True)
                fill = mode.iloc[0] if len(mode) else "Unknown"
                X[col] = X[col].fillna(fill)
                print(f"  Imputed categorical '{col}' with mode={fill!r}")

    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    # get_dummies — same approach as churn model for train/serve consistency
    X = pd.get_dummies(X, columns=cat_cols, drop_first=False)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    meta = {
        "label_col": label_col,
        "id_cols": id_cols,
        "label_map": label_map,
    }
    return X, y, meta


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, meta = load_and_clean(DATA_PATH)
    feature_columns = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train size={len(X_train)}, Test size={len(X_test)}")
    print(f"Approve rate (train)={y_train.mean():.3f}, (test)={y_test.mean():.3f}")

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n=== Test-set evaluation ===")
    print(
        classification_report(
            y_test, y_pred, target_names=["Reject", "Approve"]
        )
    )
    print("Confusion matrix [[TN FP],[FN TP]]:")
    print(confusion_matrix(y_test, y_pred))

    importances = pd.Series(model.feature_importances_, index=feature_columns)
    top10 = importances.nlargest(10).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    top10.plot(kind="barh", ax=ax, color="#10b981")
    ax.set_title("Top 10 Feature Importances — Credit Risk Model")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(IMPORTANCE_CHART, dpi=120)
    plt.close(fig)
    print(f"\nSaved feature importance chart → {IMPORTANCE_CHART}")

    artifact = {
        "model": model,
        "columns": feature_columns,
        "label_map": meta["label_map"],
        "label_col": meta["label_col"],
        "id_cols": meta["id_cols"],
    }
    joblib.dump(artifact, MODEL_PATH)

    acc = (y_pred == y_test).mean()
    print("\n=== Training complete ===")
    print(f"Accuracy: {acc:.4f}")
    print(f"Model saved to: {MODEL_PATH}")
    print("Trained on CPU only — typically seconds on this dataset size.")
    return artifact


def main() -> int:
    try:
        train()
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Train an IsolationForest fraud / anomaly detector on data/fraud_transactions.csv.

Usage (from the backend root, venv active):
    python -m ml.train_fraud_detector

Why IsolationForest (not a classifier): fraud is extremely rare (<1%). Standard
supervised classifiers struggle with that imbalance and need many labeled fraud
examples. IsolationForest is unsupervised anomaly detection — it flags
transactions whose pattern looks unusual relative to the majority, using a
contamination rate instead of balanced labels. We still evaluate against the
Class column when present (this Kaggle set includes it for research), but a
true unsupervised deployment would not have those labels at inference time.
CPU-only; no deep learning.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "fraud_transactions.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "fraud_detector.pkl"

# Typical Kaggle credit-card fraud columns; Time is optional (not used for scoring)
FEATURE_PREFIXES = ("V",)  # V1..V28 PCA features
EXTRA_FEATURES = ("Amount",)
LABEL_CANDIDATES = ["Class", "class", "Fraud", "fraud", "is_fraud", "label"]


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Download the Credit Card Fraud Detection CSV from Kaggle:\n"
            "  https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud\n"
            "Search Kaggle for: \"Credit Card Fraud Detection\"\n"
            "Then place/rename it exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def _detect_label_column(columns: list[str]) -> str | None:
    lower_map = {c.lower().strip(): c for c in columns}
    for cand in LABEL_CANDIDATES:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _resolve_feature_columns(columns: list[str]) -> list[str]:
    """
    Prefer V1..V28 + Amount (standard anonymized credit-card fraud schema).
    Fall back to all numeric columns except Time / label if naming differs.
    """
    cols = list(columns)
    v_cols = sorted(
        [c for c in cols if re_match_v(c)],
        key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or "0"),
    )
    amount = None
    for c in cols:
        if c.lower() == "amount":
            amount = c
            break
    if v_cols and amount:
        return v_cols + [amount]

    # Fallback: numeric-ish columns excluding Time / Class
    skip = {c.lower() for c in LABEL_CANDIDATES} | {"time", "id", "index"}
    features = [c for c in cols if c.lower() not in skip]
    if not features:
        raise ValueError(f"No usable feature columns found. Columns: {columns}")
    return features


def re_match_v(name: str) -> bool:
    n = name.strip()
    if len(n) < 2 or not n.upper().startswith("V"):
        return False
    return n[1:].isdigit()


def _coerce_class(series: pd.Series) -> pd.Series:
    """Handle Class as int, float, or quoted strings like '0'/'1' (OpenML export)."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace("'", "", regex=False)
        .str.replace('"', "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0).astype(int)


def load_features(path: Path) -> tuple[pd.DataFrame, pd.Series | None, list[str]]:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")
    print(f"Actual column names: {list(df.columns)}")

    label_col = _detect_label_column(list(df.columns))
    feature_cols = _resolve_feature_columns(list(df.columns))
    print(f"Detected label column: {label_col}")
    print(f"Using {len(feature_cols)} feature columns: {feature_cols[:5]}...{feature_cols[-2:]}")

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    y = _coerce_class(df[label_col]) if label_col else None
    if y is not None:
        fraud_rate = float((y == 1).mean())
        print(f"Fraud rate (Class==1): {fraud_rate:.6f} ({int((y == 1).sum())} / {len(y)})")
    return X, y, feature_cols


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, feature_cols = load_features(DATA_PATH)

    # Contamination = expected fraction of anomalies. Set from the real fraud
    # rate in this dataset rather than a hardcoded guess — IsolationForest uses
    # this to decide how many points to flag as outliers. Clamped to sklearn's
    # valid range (0, 0.5].
    if y is not None:
        fraud_rate = float((y == 1).mean())
        contamination = float(np.clip(fraud_rate, 0.0001, 0.5))
    else:
        contamination = 0.01
        print("No Class column — defaulting contamination=0.01")
    print(f"IsolationForest contamination={contamination:.6f}")

    # Scale features: IsolationForest is density/path-length based; Amount and
    # PCA components live on different scales. Same reasoning as K-Means —
    # unscaled Amount would dominate anomaly scoring.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # IsolationForest: predict → -1 anomaly, 1 normal. Convert to 1=fraud, 0=normal.
    raw_pred = model.predict(X_scaled)
    y_hat = (raw_pred == -1).astype(int)
    scores = model.decision_function(X_scaled)  # higher = more normal

    if y is not None:
        # Labels exist here only for a sanity-check evaluation. In a true
        # unsupervised deployment you would NOT have Class to compare against —
        # you would review flagged transactions manually / via rules.
        print("\n=== Evaluation vs true Class (research sanity-check only) ===")
        print(
            "Note: IsolationForest did not train on Class; we compare flags "
            "to labels afterward to see real-world recall/precision."
        )
        prec = precision_score(y, y_hat, zero_division=0)
        rec = recall_score(y, y_hat, zero_division=0)
        print(f"Precision (flagged that are fraud): {prec:.4f}")
        print(f"Recall (fraud caught):              {rec:.4f}")
        print(
            classification_report(
                y, y_hat, target_names=["normal", "fraud"], zero_division=0
            )
        )
        print("Confusion matrix [[TN FP],[FN TP]]:")
        print(confusion_matrix(y, y_hat))

    artifact = {
        "model": model,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "contamination": contamination,
    }
    joblib.dump(artifact, MODEL_PATH)

    print("\n=== Training complete ===")
    print(f"Anomalies flagged on training data: {int(y_hat.sum())} / {len(y_hat)}")
    print(f"Model saved to: {MODEL_PATH}")
    print("Trained on CPU only — may take a minute on ~280k rows.")
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

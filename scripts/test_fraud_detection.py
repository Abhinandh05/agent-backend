"""
Sanity-check the fraud detector with real rows from the dataset (if present).

Usage (from backend root, after training):
    python -m scripts.test_fraud_detection
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_fraud import MODEL_PATH, check_transaction, model_ready

DATA_PATH = ROOT / "data" / "fraud_transactions.csv"


def _coerce_class(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace("'", "", regex=False)
        .str.replace('"', "", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0).astype(int)


def _pick_examples() -> list[dict]:
    """Pull 1 normal + 1 fraud row from the CSV when available."""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Place fraud_transactions.csv first."
        )

    # Read only what we need; full CSV is ~150MB / 280k rows
    df = pd.read_csv(DATA_PATH)
    label_col = "Class" if "Class" in df.columns else None
    if label_col is None:
        raise ValueError(f"No Class column in {DATA_PATH}; columns={list(df.columns)}")

    y = _coerce_class(df[label_col])
    feature_cols = [c for c in df.columns if c != label_col and c.lower() != "time"]

    normal_idx = y[y == 0].index[0]
    fraud_idx = y[y == 1].index[0]

    examples = []
    for name, idx in (
        ("Likely normal (Class=0 from dataset)", normal_idx),
        ("Likely fraud (Class=1 from dataset)", fraud_idx),
    ):
        row = df.loc[idx, feature_cols]
        features = {c: float(row[c]) for c in feature_cols}
        examples.append({"name": name, "features": features, "true_class": int(y.loc[idx])})
    return examples


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_fraud_detector"
        )
        return 1

    try:
        examples = _pick_examples()
    except Exception as exc:
        print(f"ERROR loading dataset examples: {exc}")
        return 1

    print("=== Fraud detection smoke test ===\n")
    print(f"Model: {MODEL_PATH}\n")
    for ex in examples:
        result = check_transaction(ex["features"])
        print(f"→ {ex['name']} (true Class={ex['true_class']})")
        print(f"  Amount={ex['features'].get('Amount')}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

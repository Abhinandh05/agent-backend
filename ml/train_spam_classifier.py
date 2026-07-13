"""
Train a spam / ham text classifier on data/spam_dataset.csv.

Usage (from the backend root, venv active):
    python -m ml.train_spam_classifier

This is the project's first NLP model: it learns from raw text via TF-IDF,
unlike churn / credit / sales / segmentation which use numeric tabular features.
CPU-only; Multinomial Naive Bayes is fast and a strong classic baseline for spam.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "spam_dataset.csv"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODELS_DIR / "spam_classifier.pkl"

# Common header names across Kaggle SMS spam CSVs
LABEL_CANDIDATES = ["label", "v1", "Category", "category", "class", "Class", "target"]
TEXT_CANDIDATES = ["text", "v2", "message", "Message", "sms", "SMS", "content", "body"]


def _require_dataset() -> Path:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}\n\n"
            "Download the SMS Spam Collection (or Spam Text Message Classification)\n"
            "CSV from Kaggle, e.g.:\n"
            "  https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset\n"
            "  https://www.kaggle.com/datasets/team-ai/spam-text-message-classification\n"
            "Then place/rename it exactly to:\n"
            f"  {DATA_PATH}\n"
        )
    return DATA_PATH


def _resolve_column(columns: list[str], candidates: list[str], role: str) -> str:
    lower_map = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise ValueError(
        f"Could not find a {role} column. Actual columns: {columns}\n"
        f"Tried: {candidates}"
    )


def _clean_text(text: str) -> str:
    """
    Minimal cleaning only: lowercase + collapse whitespace.

    We intentionally do NOT strip punctuation, stem, or remove stopwords here.
    TF-IDF already down-weights very common terms and turns token counts into
    useful sparse features; heavy cleaning often removes signal (e.g. "FREE!!!")
    that helps spam detection. Keep preprocessing light and let the vectorizer work.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _normalize_label(raw: str) -> int:
    """Map spam/ham (or 1/0) → 1=spam, 0=ham."""
    v = str(raw).strip().lower()
    if v in ("spam", "1", "yes", "true"):
        return 1
    if v in ("ham", "0", "no", "false", "legit", "legitimate"):
        return 0
    raise ValueError(f"Unrecognized label value: {raw!r}")


def load_and_prepare(path: Path) -> tuple[pd.Series, pd.Series]:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows × {len(df.columns)} columns from {path}")
    print(f"Actual column names: {list(df.columns)}")

    label_col = _resolve_column(list(df.columns), LABEL_CANDIDATES, "label")
    text_col = _resolve_column(list(df.columns), TEXT_CANDIDATES, "text")
    print(f"Using label column: {label_col!r}, text column: {text_col!r}")

    # Rename internally to consistent names for the rest of the pipeline
    work = df[[label_col, text_col]].rename(columns={label_col: "label", text_col: "text"})
    work = work.dropna(subset=["text", "label"])
    work["text"] = work["text"].map(_clean_text)
    work = work[work["text"].str.len() > 0]
    work["label"] = work["label"].map(_normalize_label)

    print("Label distribution (0=ham, 1=spam):")
    print(work["label"].value_counts().sort_index())
    return work["text"], work["label"]


def train() -> dict:
    _require_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    texts, labels = load_and_prepare(DATA_PATH)

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    print(f"Train size={len(X_train)}, Test size={len(X_test)}")

    # Fit the vectorizer on TRAINING text only.
    # Fitting on the full corpus (including test) would leak information: the
    # IDF weights would "see" words that only appear in the held-out set, which
    # inflates metrics and does not reflect real deployment (where future
    # messages are unseen). Always fit transformers on train, transform test.
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=2,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # MultinomialNB: classic, fast, and traditionally very strong for spam-style
    # bag-of-words / TF-IDF text classification. LogisticRegression is a solid
    # alternative; NB is simpler and typically enough for this baseline.
    model = MultinomialNB(alpha=0.1)
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    print("\n=== Test-set evaluation ===")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1:        {f1:.4f}")
    print(
        classification_report(
            y_test, y_pred, target_names=["ham", "spam"], zero_division=0
        )
    )
    print("Confusion matrix [[TN FP],[FN TP]]:")
    print(confusion_matrix(y_test, y_pred))

    # Bundle model + fitted vectorizer — prediction must reuse the same vocab/IDF.
    artifact = {
        "model": model,
        "vectorizer": vectorizer,
        "label_map": {0: "ham", 1: "spam"},
    }
    joblib.dump(artifact, MODEL_PATH)

    print("\n=== Training complete ===")
    print(f"Model saved to: {MODEL_PATH}")
    print("Trained on CPU only — typically a few seconds on ~5k messages.")
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

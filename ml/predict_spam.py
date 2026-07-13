"""
Load the trained spam classifier and score one message.

Mirrors ml/predict_churn.py / predict_credit_risk.py for consistency.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import joblib

MODEL_PATH = Path(__file__).resolve().parent / "models" / "spam_classifier.pkl"

_artifact: dict[str, Any] | None = None


def _load_artifact() -> dict[str, Any]:
    global _artifact
    if _artifact is not None:
        return _artifact
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}.\n"
            "Run training first:\n"
            "  python -m ml.train_spam_classifier"
        )
    _artifact = joblib.load(MODEL_PATH)
    return _artifact


def _clean_text(text: str) -> str:
    """Same light cleaning as training (lowercase + collapse whitespace)."""
    if text is None:
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def classify_message(text: str) -> dict:
    """
    Classify a single message as spam or ham.

    Returns
    -------
    {
      "is_spam": bool,
      "confidence": float,   # P(predicted class)
      "label": "spam" | "ham"
    }
    """
    artifact = _load_artifact()
    model = artifact["model"]
    vectorizer = artifact["vectorizer"]
    label_map = artifact.get("label_map", {0: "ham", 1: "spam"})

    cleaned = _clean_text(text)
    X = vectorizer.transform([cleaned])
    pred = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]
    confidence = float(proba[pred])
    label = label_map.get(pred, str(pred))

    return {
        "is_spam": bool(pred == 1),
        "confidence": round(confidence, 4),
        "label": label,
    }


def model_ready() -> bool:
    return MODEL_PATH.is_file()

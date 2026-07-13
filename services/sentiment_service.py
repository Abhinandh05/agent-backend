"""
Pre-trained HuggingFace sentiment analysis for Email Agent tone checks.

Uses distilbert-base-uncased-finetuned-sst-2-english — inference only
(no training). Separate from the scikit-learn churn/credit models we train.

First call downloads ~260MB of model weights (needs internet once).
"""
from __future__ import annotations

from typing import Optional

# Explicit model for clarity/reproducibility (pipeline default is the same).
_MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
# DistilBERT max is 512 tokens; leave headroom. Truncation is ONLY for the
# tone check — the actual email body sent to the user is never truncated.
_MAX_CHARS_APPROX = 2000  # ~500 tokens for typical English prose

_pipeline = None


class SentimentModelError(RuntimeError):
    """Raised when the HuggingFace sentiment pipeline cannot be loaded."""


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import pipeline
    except Exception as exc:
        raise SentimentModelError(
            "Failed to import transformers. "
            f"Underlying error: {exc}. "
            "Try: pip install transformers torch "
            "(tip: pip install torch --index-url "
            "https://download.pytorch.org/whl/cpu for a smaller CPU-only build)."
        ) from exc

    try:
        _pipeline = pipeline(
            "sentiment-analysis",
            model=_MODEL_NAME,
            truncation=True,
        )
    except Exception as exc:
        raise SentimentModelError(
            f"Failed to download/load '{_MODEL_NAME}'. "
            "Check your internet connection on the first run "
            "(the model is ~260MB), then retry."
        ) from exc
    return _pipeline


def analyze_sentiment(text: str) -> dict:
    """
    Analyze tone of drafted email text.

    Returns:
        {
            "label": "POSITIVE" | "NEGATIVE",
            "confidence": float,  # 0–1
            "tone_warning": str | None,
            "truncated": bool,  # True if input was shortened for the check only
        }
    """
    raw = (text or "").strip()
    if not raw:
        return {
            "label": "POSITIVE",
            "confidence": 0.0,
            "tone_warning": None,
            "truncated": False,
        }

    truncated = False
    analysis_text = raw
    # Truncate by character approx for the tone check only — safe because
    # this never alters the email content returned to the user / SendGrid.
    if len(analysis_text) > _MAX_CHARS_APPROX:
        analysis_text = analysis_text[:_MAX_CHARS_APPROX]
        truncated = True

    clf = _load_pipeline()
    result = clf(analysis_text)[0]
    label = str(result.get("label", "")).upper()
    confidence = float(result.get("score", 0.0))

    tone_warning: Optional[str] = None
    if label == "NEGATIVE" and confidence > 0.7:
        pct = int(round(confidence * 100))
        tone_warning = (
            f"This email reads as quite negative in tone ({pct}% confidence). "
            "You may want to review the wording before sending."
        )
        if truncated:
            tone_warning += (
                " (Tone was checked on the first portion of a long email.)"
            )
    elif truncated and tone_warning is None:
        # Still surface truncation so long-email results aren't silently partial
        pass

    out = {
        "label": label if label in ("POSITIVE", "NEGATIVE") else label,
        "confidence": confidence,
        "tone_warning": tone_warning,
        "truncated": truncated,
    }
    if truncated and tone_warning is None:
        # Non-warning note kept out of tone_warning; callers can read truncated.
        pass
    return out

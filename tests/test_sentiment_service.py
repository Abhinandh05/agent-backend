"""Tests for services/sentiment_service.py (Day 14 tone analysis).

Choice: run against the real HuggingFace DistilBERT model when it is
already cached (or downloadable). The model is small/fast (~260MB once,
inference <<1s). We skip gracefully when transformers/torch are missing
or the model cannot load (offline CI without cache) so the suite stays green.
"""
from __future__ import annotations

import pytest

try:
    from services.sentiment_service import SentimentModelError, analyze_sentiment

    try:
        # Warm the pipeline once; skip the whole module if load fails.
        analyze_sentiment("warmup")
        _MODEL_OK = True
        _SKIP_REASON = ""
    except SentimentModelError as exc:
        _MODEL_OK = False
        _SKIP_REASON = str(exc)
    except Exception as exc:  # noqa: BLE001 — any load failure → skip
        _MODEL_OK = False
        _SKIP_REASON = f"Sentiment model unavailable: {exc}"
except Exception as exc:  # noqa: BLE001
    _MODEL_OK = False
    _SKIP_REASON = f"Cannot import sentiment_service: {exc}"

    def analyze_sentiment(text: str):  # type: ignore[misc]
        raise RuntimeError("unreachable")


pytestmark = pytest.mark.skipif(not _MODEL_OK, reason=_SKIP_REASON)


def test_positive_sentiment():
    result = analyze_sentiment("Thank you so much, this is wonderful news!")
    assert result["label"] == "POSITIVE"
    assert result["confidence"] > 0.7
    assert result["tone_warning"] is None


def test_negative_sentiment_with_warning():
    result = analyze_sentiment(
        "This is unacceptable and I am very disappointed."
    )
    assert result["label"] == "NEGATIVE"
    assert result["confidence"] > 0.7
    assert result["tone_warning"] is not None
    assert "negative" in result["tone_warning"].lower()


def test_empty_text():
    result = analyze_sentiment("   ")
    assert result["label"] == "POSITIVE"
    assert result["tone_warning"] is None
    assert result["truncated"] is False


def test_long_text_sets_truncated_flag():
    long_body = ("This is a fine update. " * 400).strip()
    result = analyze_sentiment(long_body)
    assert result["truncated"] is True
    assert "label" in result
    assert "confidence" in result

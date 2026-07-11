"""
Local embeddings via sentence-transformers (all-MiniLM-L6-v2).

This model produces 384-dimensional vectors — relevant for Day 9+ when
configuring collection dimensions (Chroma infers this automatically).

No API key required. First run downloads ~80MB of model weights.
"""
from __future__ import annotations

_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingModelError(RuntimeError):
    """Raised when the sentence-transformers model cannot be loaded."""


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        # ImportError OR version/check failures from transformers deps
        raise EmbeddingModelError(
            "Failed to import sentence-transformers / transformers. "
            f"Underlying error: {exc}. "
            "Try: pip install 'numpy>=1.26.4,<2' 'scipy>=1.11,<1.14' "
            "'scikit-learn>=1.4,<1.6' sentence-transformers"
        ) from exc

    try:
        # Load once at module level (via this singleton) — do not reload per request.
        _model = SentenceTransformer(_MODEL_NAME)
    except Exception as exc:
        raise EmbeddingModelError(
            f"Failed to download/load '{_MODEL_NAME}'. "
            "Check your internet connection on the first run "
            "(the model is ~80MB), then retry."
        ) from exc
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single string → 384-float vector."""
    model = _load_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed many strings → list of 384-float vectors."""
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]

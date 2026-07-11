"""Unit tests for Day 8 vectorstore helpers (fast — model is mocked)."""
from unittest.mock import MagicMock, patch

import numpy as np

from vectorstore.chunking import split_text


def test_split_text_produces_multiple_chunks():
    # ~1200 chars → with chunk_size=200 should yield several chunks
    text = ("Quarterly earnings rose sharply. " * 40).strip()
    chunks = split_text(text, chunk_size=200, overlap=40)
    assert len(chunks) >= 4
    assert all(isinstance(c, str) and c for c in chunks)
    assert all(len(c) <= 240 for c in chunks)  # soft upper bound with overlap


def test_split_text_empty():
    assert split_text("") == []
    assert split_text("   ") == []


def test_embed_text_returns_384_floats():
    fake_vector = np.random.rand(384).astype(np.float32)

    mock_model = MagicMock()
    mock_model.encode.return_value = fake_vector

    with patch("vectorstore.embeddings._model", mock_model):
        from vectorstore.embeddings import embed_text

        result = embed_text("What were the earnings?")

    assert isinstance(result, list)
    assert len(result) == 384
    assert all(isinstance(x, float) for x in result)
    mock_model.encode.assert_called_once()


def test_embed_batch_returns_list_of_384():
    fake_batch = np.random.rand(2, 384).astype(np.float32)
    mock_model = MagicMock()
    mock_model.encode.return_value = fake_batch

    with patch("vectorstore.embeddings._model", mock_model):
        from vectorstore.embeddings import embed_batch

        result = embed_batch(["a", "b"])

    assert len(result) == 2
    assert all(len(v) == 384 for v in result)

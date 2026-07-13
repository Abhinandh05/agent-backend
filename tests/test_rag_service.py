"""Tests for services.rag_service — embeddings / Chroma / LLM mocked."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.rag_service import NO_CONTEXT_ANSWER, rag_query_sync


@patch("services.rag_service.ask_llm_sync")
@patch("services.rag_service.chroma_query")
@patch("services.rag_service.embed_text")
def test_rag_query_zero_chunks_skips_llm(mock_embed, mock_chroma, mock_llm):
    mock_embed.return_value = [0.1] * 8
    mock_chroma.return_value = []

    result = rag_query_sync("What were Q3 earnings?", user_id=42, top_k=5)

    mock_embed.assert_called_once()
    mock_chroma.assert_called_once_with(mock_embed.return_value, user_id=42, top_k=5)
    mock_llm.assert_not_called()
    assert result["chunks_found"] == 0
    assert result["sources"] == []
    assert "couldn't find anything relevant" in result["answer"].lower()
    assert result["answer"] == NO_CONTEXT_ANSWER


@patch("services.rag_service.ask_llm_sync")
@patch("services.rag_service.chroma_query")
@patch("services.rag_service.embed_text")
def test_rag_query_with_matches_calls_llm(mock_embed, mock_chroma, mock_llm):
    mock_embed.return_value = [0.2] * 8
    mock_chroma.return_value = [
        {
            "id": "doc1_chunk0",
            "document": "Q3 revenue grew 12 percent.",
            "metadata": {"filename": "earnings.txt", "user_id": 7, "document_id": 1},
            "distance": 0.1,
        }
    ]
    mock_llm.return_value = "Revenue grew 12% in Q3."

    result = rag_query_sync("How did revenue do?", user_id=7, top_k=5)

    mock_llm.assert_called_once()
    prompt = mock_llm.call_args[0][0]
    assert "Q3 revenue grew 12 percent" in prompt
    assert "earnings.txt" in prompt
    assert result["chunks_found"] == 1
    assert result["answer"] == "Revenue grew 12% in Q3."
    assert result["sources"][0]["filename"] == "earnings.txt"

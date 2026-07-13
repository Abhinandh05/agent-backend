"""
RAG query pipeline: embed question → Chroma (user-filtered) → Groq answer.

Security: every Chroma query MUST filter by user_id so one tenant never
sees another tenant's document chunks.
"""
from __future__ import annotations

import asyncio
from typing import Any

from services.llm_service import ask_llm_sync
from vectorstore.client import query as chroma_query
from vectorstore.embeddings import embed_text

NO_CONTEXT_ANSWER = (
    "I couldn't find anything relevant in your uploaded documents. "
    "Upload and index a document first, or try a different question."
)


def _build_prompt(question: str, context: str) -> str:
    return (
        "Use the following document excerpts to answer the question. "
        "If the excerpts don't contain relevant information, say so clearly "
        "rather than guessing.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )


def _format_sources(matches: list[dict]) -> list[dict]:
    sources: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for m in matches:
        meta = m.get("metadata") or {}
        filename = str(meta.get("filename") or "unknown")
        text = (m.get("document") or "").strip()
        preview = text[:200] + ("…" if len(text) > 200 else "")
        key = (filename, preview)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"filename": filename, "chunk_preview": preview})
    return sources


def rag_query_sync(question: str, user_id: int, top_k: int = 5) -> dict[str, Any]:
    """
    Synchronous RAG core (embeddings + Chroma + Groq are all blocking).

    Returns {"answer", "sources", "chunks_found"}.
    """
    q = (question or "").strip()
    if not q:
        return {
            "answer": NO_CONTEXT_ANSWER,
            "sources": [],
            "chunks_found": 0,
        }

    # CRITICAL: always pass user_id into Chroma — never query the whole collection.
    embedding = embed_text(q)
    matches = chroma_query(embedding, user_id=int(user_id), top_k=top_k)

    if not matches:
        # Do NOT call the LLM with empty context — that invites hallucination.
        return {
            "answer": NO_CONTEXT_ANSWER,
            "sources": [],
            "chunks_found": 0,
        }

    context_parts: list[str] = []
    for i, m in enumerate(matches, start=1):
        meta = m.get("metadata") or {}
        filename = meta.get("filename") or "unknown"
        text = (m.get("document") or "").strip()
        context_parts.append(f"[{i}] Source: {filename}\n{text}")

    context = "\n\n".join(context_parts)
    prompt = _build_prompt(q, context)
    answer = ask_llm_sync(prompt)

    return {
        "answer": answer,
        "sources": _format_sources(matches),
        "chunks_found": len(matches),
    }


async def rag_query(question: str, user_id: int, top_k: int = 5) -> dict[str, Any]:
    """Async entrypoint for FastAPI — offloads blocking work to a thread."""
    return await asyncio.to_thread(rag_query_sync, question, user_id, top_k)

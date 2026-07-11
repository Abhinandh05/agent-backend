"""
Standalone Day 8 smoke test for chunk → embed → store → query.

Usage (from the backend root, with venv active):
    python -m scripts.test_vectorstore

First run downloads the sentence-transformers model (~80MB) — needs internet once.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vectorstore.chunking import split_text
from vectorstore.embeddings import embed_batch, embed_text, EmbeddingModelError
from vectorstore.client import add_chunks, query


SAMPLE_TEXT = (
    "Aurora Dynamics reported strong quarterly earnings for Q1 2026. "
    "Revenue reached $48.2 million, up 22% year-over-year, driven by "
    "enterprise software subscriptions and consulting services. "
    "Operating margin improved to 18%, and the company guided full-year "
    "revenue between $200 and $215 million. Management highlighted growth "
    "in the Asia-Pacific region as a key contributor to the beat."
)

QUERY = "What were the earnings?"


def main() -> int:
    print("=== Day 8 Vector Store Smoke Test ===\n")
    print("1) Chunking sample text…")
    chunks = split_text(SAMPLE_TEXT, chunk_size=200, overlap=40)
    print(f"   → {len(chunks)} chunk(s)")
    for i, c in enumerate(chunks):
        print(f"   [{i}] {c[:80]}{'…' if len(c) > 80 else ''}")

    print("\n2) Embedding chunks (first run may download ~80MB model)…")
    try:
        embeddings = embed_batch(chunks)
    except EmbeddingModelError as exc:
        print(f"\nERROR: {exc}")
        return 1

    print(f"   → embedding dim = {len(embeddings[0])}")

    run_id = uuid.uuid4().hex[:8]
    ids = [f"demo-{run_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {"user_id": 1, "source": "aurora_q1_earnings", "chunk_index": i}
        for i in range(len(chunks))
    ]

    print("\n3) Storing in Chroma (user_id=1)…")
    add_chunks(chunks, embeddings, metadatas, ids)
    print("   → stored")

    print(f'\n4) Querying: "{QUERY}"')
    try:
        q_emb = embed_text(QUERY)
    except EmbeddingModelError as exc:
        print(f"\nERROR: {exc}")
        return 1

    matches = query(q_emb, user_id=1, top_k=3)
    if not matches:
        print("   No matches found.")
        return 1

    print(f"   Top {len(matches)} match(es):\n")
    for i, m in enumerate(matches, start=1):
        distance = m.get("distance")
        # Cosine distance → rough similarity for display
        similarity = (1.0 - distance) if distance is not None else None
        print(f"   #{i} id={m['id']}")
        print(f"      distance={distance:.4f}  similarity≈{similarity:.4f}")
        print(f"      text: {m['document']}\n")

    print("=== Vector store pipeline OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

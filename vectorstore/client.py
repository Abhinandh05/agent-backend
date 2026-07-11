"""
Chroma persistent client for document embeddings.

Data is stored under backend/chroma_data/ (gitignored).
No Docker or external vector DB process is required.
"""
from pathlib import Path
import chromadb
from chromadb.config import Settings

# Persist next to the backend package root: agent-backend/chroma_data/
CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma_data"
COLLECTION_NAME = "documents"

_client = None
_collection = None


def get_client():
    """Return a singleton PersistentClient writing to chroma_data/."""
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    """Create or get the shared 'documents' collection."""
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    """Insert text chunks + embeddings into the documents collection."""
    if not chunks:
        return
    collection = get_collection()
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )


def query(
    query_embedding: list[float],
    user_id: int,
    top_k: int = 5,
) -> list[dict]:
    """
    Similarity search filtered to a single user's documents.

    Returns a list of dicts: {id, document, metadata, distance}.
    Chroma cosine distance: lower is more similar (0 = identical).
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"],
    )

    matches: list[dict] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, doc_id in enumerate(ids):
        matches.append(
            {
                "id": doc_id,
                "document": documents[i] if i < len(documents) else None,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )
    return matches


def delete_by_document_id(document_id: int) -> None:
    """
    Remove all Chroma chunks whose metadata.document_id matches.

    Used when a user deletes an uploaded Document row.
    """
    collection = get_collection()
    collection.delete(where={"document_id": int(document_id)})

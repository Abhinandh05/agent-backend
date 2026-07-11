"""
Text chunking for RAG (Day 9+).

Uses langchain-text-splitters' RecursiveCharacterTextSplitter — lightweight,
no full LangChain stack required. Character-based split with overlap matches
the Day 8 guide and keeps chunks coherent across sentence boundaries.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    Defaults: chunk_size=500 characters, overlap=50 characters.
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]

"""
Document ingestion: parse → chunk → embed → Chroma.

Reuses Day 8 vectorstore helpers (split_text, embed_batch, add_chunks).
OCR / scanned-PDF support (pytesseract + Tesseract binary) is a future
enhancement — skipped today to avoid system package installs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from models import Document
from vectorstore.chunking import split_text
from vectorstore.client import add_chunks
from vectorstore.embeddings import embed_batch

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}


def extract_text(file_path: str, file_type: str) -> str:
    """
    Dispatch to the right parser based on extension / file_type.

    file_type should be the extension including the leading dot, e.g. '.pdf'.
    """
    path = Path(file_path)
    ext = (file_type or path.suffix).lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    if ext == ".pdf":
        return _extract_pdf(path)
    if ext == ".docx":
        return _extract_docx(path)
    if ext == ".xlsx":
        return _extract_tabular(path, kind="xlsx")
    if ext == ".csv":
        return _extract_tabular(path, kind="csv")
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    raise ValueError(
        f"Unsupported file type '{ext}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def _extract_pdf(path: Path) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(path: Path) -> str:
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paras)


def _extract_tabular(path: Path, kind: str) -> str:
    """
    Convert spreadsheet / CSV rows to plain text for embedding.

    Choice: one line per row as `col=value | col=value | ...` rather than a
    markdown table. Chunkers split cleanly between lines, and each row stays
    a searchable unit (tables often break mid-row across chunk boundaries).
    """
    if kind == "csv":
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin-1")
    else:
        df = pd.read_excel(path, engine="openpyxl")

    if df.empty:
        return ""

    cols = [str(c) for c in df.columns]
    lines: list[str] = []
    for _, row in df.iterrows():
        parts = [f"{c}={row[c]}" for c in cols]
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def process_document(document_id: int, db: Session) -> None:
    """
    Full pipeline for one Document row. Never raises to the caller —
    failures are recorded on the Document row as status='failed'.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        return

    doc.status = "processing"
    doc.error_message = None
    doc.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        text = extract_text(doc.file_path, doc.file_type)
        if not text or not text.strip():
            raise ValueError("No extractable text found in the uploaded file.")

        chunks = split_text(text)
        if not chunks:
            raise ValueError("Text extracted but produced zero chunks.")

        embeddings = embed_batch(chunks)
        ids = [f"doc{doc.id}_chunk{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "user_id": int(doc.user_id),
                "document_id": int(doc.id),
                "filename": str(doc.filename),
                "chunk_index": int(i),
            }
            for i in range(len(chunks))
        ]
        add_chunks(chunks, embeddings, metadatas, ids)

        doc.status = "indexed"
        doc.chunk_count = len(chunks)
        doc.error_message = None
        doc.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        # Re-load in case rollback detached the instance
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is not None:
            doc.status = "failed"
            doc.error_message = str(exc)[:2000]
            doc.updated_at = datetime.now(timezone.utc)
            db.commit()


def process_document_job(document_id: int) -> None:
    """BackgroundTasks entrypoint — opens its own DB session."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        process_document(document_id, db)
    finally:
        db.close()

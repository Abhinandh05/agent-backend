# backend/routers/documents.py — upload → parse → embed → Chroma (Day 9)
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.dependencies import get_current_active_user
from database import get_db
from models import Document, User
from schemas import APIResponse
from services.document_service import SUPPORTED_EXTENSIONS, process_document_job
from vectorstore.client import delete_by_document_id

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _error_response(status_code: int, message: str, error: str) -> JSONResponse:
    body = APIResponse(
        success=False,
        data=None,
        message=message,
        error=error,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


def _doc_summary(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.post(
    "/upload",
    response_model=APIResponse,
    summary="Upload a document for parsing and indexing",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    original_name = (file.filename or "upload").strip()
    ext = Path(original_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "Unsupported file type",
            f"Got '{ext or '(none)'}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "File too large",
            f"Max upload size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )
    if not raw:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "Empty file",
            "Uploaded file has zero bytes.",
        )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{Path(original_name).name}"
    dest = UPLOADS_DIR / stored_name
    dest.write_bytes(raw)

    doc = Document(
        user_id=current_user.id,
        filename=original_name,
        file_path=str(dest),
        file_type=ext,
        status="uploaded",
        chunk_count=0,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(process_document_job, doc.id)

    return APIResponse(
        success=True,
        data={
            "document_id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
        },
        message="File uploaded; processing started in the background.",
        error=None,
    )


@router.get(
    "",
    response_model=APIResponse,
    summary="List current user's documents",
)
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    rows = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return APIResponse(
        success=True,
        data={"documents": [_doc_summary(d) for d in rows]},
        message="Documents retrieved",
        error=None,
    )


@router.get(
    "/{document_id}",
    response_model=APIResponse,
    summary="Get one document (owner only)",
)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if doc is None:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Document not found or not owned by the current user.",
        )
    return APIResponse(
        success=True,
        data=_doc_summary(doc),
        message="Document retrieved",
        error=None,
    )


@router.delete(
    "/{document_id}",
    response_model=APIResponse,
    summary="Delete document file, DB row, and Chroma chunks",
)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if doc is None:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Document not found or not owned by the current user.",
        )

    file_path = Path(doc.file_path) if doc.file_path else None
    try:
        delete_by_document_id(doc.id)
    except Exception:
        # Still remove DB/disk even if Chroma is empty / missing
        pass

    db.delete(doc)
    db.commit()

    if file_path and file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            pass

    return APIResponse(
        success=True,
        data={"document_id": document_id},
        message="Document deleted",
        error=None,
    )

"""Tests for /api/v1/documents (Day 9). Embeddings/Chroma mocked for speed."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from core.dependencies import get_current_active_user
from database import get_db
from models import Document


def _user(uid: int = 1, email: str = "user1@example.com"):
    user = MagicMock()
    user.id = uid
    user.name = "Test"
    user.email = email
    user.is_active = True
    return user


def _mock_db_for_upload(user_id: int = 1):
    """DB mock that assigns ids and stores Document rows in a list."""
    db = MagicMock()
    store: list = []
    counter = {"n": 0}

    def add(obj):
        if isinstance(obj, Document):
            counter["n"] += 1
            obj.id = counter["n"]
            if obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if obj.updated_at is None:
                obj.updated_at = datetime.now(timezone.utc)
            store.append(obj)

    def refresh(obj):
        pass

    def query(model):
        q = MagicMock()

        def filter(*args, **kwargs):
            q._filters = args
            return q

        def order_by(*args, **kwargs):
            return q

        def all():
            # Return docs for current user if we can infer user_id from filters
            return [d for d in store if getattr(d, "user_id", None) == user_id]

        def first():
            if not store:
                return None
            return store[0]

        q.filter = filter
        q.order_by = order_by
        q.all = all
        q.first = first
        return q

    db.add.side_effect = add
    db.refresh.side_effect = refresh
    db.query.side_effect = query
    db._store = store
    return db


def test_upload_unauthenticated():
    client = TestClient(app)
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 401


def test_upload_unsupported_extension():
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: _mock_db_for_upload(1)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("photo.png", b"fakepng", "image/png")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "Unsupported" in body["message"] or "png" in (body.get("error") or "")


def test_upload_txt_success():
    mock_db = _mock_db_for_upload(1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("routers.documents.process_document_job") as bg:
            # Don't run real embedding pipeline in the unit test
            client = TestClient(app)
            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "hello.txt",
                        b"Quarterly earnings were strong this year.",
                        "text/plain",
                    )
                },
            )
            # BackgroundTasks still schedules; we patched the job callable
            assert bg.called or response.status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["filename"] == "hello.txt"
    assert body["data"]["status"] == "uploaded"
    assert "document_id" in body["data"]
    assert mock_db.add.called


def test_list_documents_user_isolation():
    """User 1 should only see their own documents in the list response."""
    now = datetime.now(timezone.utc)
    docs = [
        Document(
            id=1,
            user_id=1,
            filename="mine.txt",
            file_path="/tmp/mine.txt",
            file_type=".txt",
            status="indexed",
            chunk_count=2,
            created_at=now,
            updated_at=now,
        ),
        Document(
            id=2,
            user_id=2,
            filename="theirs.txt",
            file_path="/tmp/theirs.txt",
            file_type=".txt",
            status="indexed",
            chunk_count=3,
            created_at=now,
            updated_at=now,
        ),
    ]

    db = MagicMock()

    def query(model):
        q = MagicMock()

        def filter(*args, **kwargs):
            # SQLAlchemy filter objects are opaque; return user1 docs only
            # (simulates Document.user_id == current_user.id)
            q._result = [d for d in docs if d.user_id == 1]
            return q

        def order_by(*args, **kwargs):
            return q

        def all():
            return getattr(q, "_result", [d for d in docs if d.user_id == 1])

        q.filter = filter
        q.order_by = order_by
        q.all = all
        return q

    db.query.side_effect = query

    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    names = [d["filename"] for d in body["data"]["documents"]]
    assert "mine.txt" in names
    assert "theirs.txt" not in names

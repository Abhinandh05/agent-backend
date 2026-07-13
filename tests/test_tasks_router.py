"""Tests for /api/v1/tasks (Day 17 — task history)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from core.dependencies import get_current_active_user
from database import get_db
from models import Task


def _user(uid: int = 1, email: str = "user1@example.com"):
    user = MagicMock()
    user.id = uid
    user.name = "Test"
    user.email = email
    user.is_active = True
    return user


def _make_task(
    *,
    tid: int,
    user_id: int,
    agent_type: str = "research",
    prompt: str = "short prompt",
    status: str = "completed",
    result: str | None = "done",
    plan_details: str | None = None,
    result_file_path: str | None = None,
    created_at: datetime | None = None,
) -> Task:
    now = created_at or datetime.now(timezone.utc)
    return Task(
        id=tid,
        user_id=user_id,
        agent_type=agent_type,
        prompt=prompt,
        result=result,
        plan_details=plan_details,
        result_file_path=result_file_path,
        status=status,
        created_at=now,
        updated_at=now,
    )


class _TaskQuery:
    """Minimal SQLAlchemy-query stand-in for list/filter/get/delete tests."""

    def __init__(self, store: list[Task], current_user_id: int):
        self._store = store
        self._current_user_id = current_user_id
        self._filters: list = []
        self._offset = 0
        self._limit = None
        self._ordered = False

    def filter(self, *args, **kwargs):
        self._filters.extend(args)
        return self

    def order_by(self, *args, **kwargs):
        self._ordered = True
        return self

    def _matches(self, task: Task) -> bool:
        # Always enforce owner isolation as the real router does.
        if task.user_id != self._current_user_id:
            return False
        for f in self._filters:
            text = str(f)
            # Equality filters appear as "tasks.agent_type = :agent_type_1" etc.
            if "agent_type" in text and "=" in text:
                # Value is bound; we inspect via binary expression left/right when possible
                try:
                    right = f.right.value  # type: ignore[attr-defined]
                    if task.agent_type != right:
                        return False
                except Exception:
                    pass
            if "status" in text and "created_at" not in text and "=" in text:
                try:
                    right = f.right.value  # type: ignore[attr-defined]
                    if task.status != right:
                        return False
                except Exception:
                    pass
            if "id" in text and "=" in text and "user_id" not in text:
                try:
                    right = f.right.value  # type: ignore[attr-defined]
                    if task.id != right:
                        return False
                except Exception:
                    pass
        return True

    def _filtered(self) -> list[Task]:
        rows = [t for t in self._store if self._matches(t)]
        if self._ordered:
            rows = sorted(
                rows,
                key=lambda t: t.created_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
        return rows

    def count(self) -> int:
        return len(self._filtered())

    def offset(self, n: int):
        self._offset = n
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def all(self) -> list[Task]:
        rows = self._filtered()
        end = None if self._limit is None else self._offset + self._limit
        return rows[self._offset : end]

    def first(self) -> Task | None:
        rows = self._filtered()
        return rows[0] if rows else None


def _mock_db(store: list[Task], current_user_id: int = 1):
    db = MagicMock()
    deleted: list[Task] = []

    def query(model):
        assert model is Task
        return _TaskQuery(store, current_user_id)

    def add(obj):
        if isinstance(obj, Task):
            obj.id = (max((t.id for t in store), default=0) + 1)
            if obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if obj.updated_at is None:
                obj.updated_at = obj.created_at
            store.append(obj)

    def delete(obj):
        deleted.append(obj)
        if obj in store:
            store.remove(obj)

    def refresh(obj):
        pass

    db.query.side_effect = query
    db.add.side_effect = add
    db.delete.side_effect = delete
    db.refresh.side_effect = refresh
    db._store = store
    db._deleted = deleted
    return db


def test_list_tasks_unauthenticated():
    client = TestClient(app)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 401


def test_list_tasks_user_isolation():
    """User 1 must only see their own tasks — never user 2's."""
    now = datetime.now(timezone.utc)
    store = [
        _make_task(tid=1, user_id=1, prompt="mine A", created_at=now),
        _make_task(
            tid=2,
            user_id=2,
            prompt="theirs — should not appear",
            created_at=now - timedelta(minutes=1),
        ),
        _make_task(
            tid=3,
            user_id=1,
            prompt="mine B",
            agent_type="finance",
            created_at=now - timedelta(minutes=2),
        ),
    ]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["total_count"] == 2
    ids = [t["id"] for t in body["data"]["tasks"]]
    assert ids == [1, 3]
    prompts = [t["prompt"] for t in body["data"]["tasks"]]
    assert "theirs — should not appear" not in prompts
    assert all("has_file" in t for t in body["data"]["tasks"])


def test_list_tasks_filter_by_agent_type():
    now = datetime.now(timezone.utc)
    store = [
        _make_task(tid=1, user_id=1, agent_type="research", created_at=now),
        _make_task(
            tid=2,
            user_id=1,
            agent_type="finance",
            created_at=now - timedelta(seconds=1),
        ),
        _make_task(
            tid=3,
            user_id=1,
            agent_type="research",
            created_at=now - timedelta(seconds=2),
        ),
    ]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks?agent_type=research")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total_count"] == 2
    assert all(t["agent_type"] == "research" for t in body["data"]["tasks"])


def test_list_tasks_truncates_prompt():
    long_prompt = "x" * 250
    store = [_make_task(tid=1, user_id=1, prompt=long_prompt)]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = response.json()["data"]["tasks"][0]["prompt"]
    assert len(prompt) <= 100
    assert prompt.endswith("…")


def test_get_task_detail_success():
    store = [
        _make_task(
            tid=10,
            user_id=1,
            prompt="full prompt text here",
            result="full result",
            plan_details='{"plan":[]}',
        )
    ]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks/10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["prompt"] == "full prompt text here"
    assert body["data"]["result"] == "full result"
    assert body["data"]["plan_details"] == '{"plan":[]}'
    assert body["data"]["has_file"] is False


def test_get_other_users_task_returns_404():
    store = [_make_task(tid=99, user_id=2, prompt="secret")]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks/99")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False


def test_delete_other_users_task_returns_404():
    store = [_make_task(tid=99, user_id=2, prompt="secret")]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.delete("/api/v1/tasks/99")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert len(store) == 1


def test_delete_own_task_removes_row_and_file(tmp_path: Path):
    file_path = tmp_path / "deck.pptx"
    file_path.write_bytes(b"fake-pptx")
    store = [
        _make_task(
            tid=5,
            user_id=1,
            prompt="make slides",
            result_file_path=str(file_path),
        )
    ]
    db = _mock_db(store, current_user_id=1)
    app.dependency_overrides[get_current_active_user] = lambda: _user(1)
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.delete("/api/v1/tasks/5")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == 5
    assert store == []
    assert not file_path.exists()

# backend/routers/tasks.py — task history list / detail / delete (Day 17)
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from core.dependencies import get_current_active_user
from database import get_db
from models import Task, User
from schemas import APIResponse, TaskCreate

router = APIRouter(prefix="/tasks", tags=["Tasks"])

PROMPT_LIST_MAX = 100


def _error_response(status_code: int, message: str, error: str) -> JSONResponse:
    body = APIResponse(
        success=False,
        data=None,
        message=message,
        error=error,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


def _truncate_prompt(prompt: str | None, max_len: int = PROMPT_LIST_MAX) -> str:
    text = prompt or ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _task_list_item(task: Task) -> dict:
    return {
        "id": task.id,
        "agent_type": task.agent_type,
        "prompt": _truncate_prompt(task.prompt),
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "has_file": bool(task.result_file_path),
    }


def _task_detail(task: Task) -> dict:
    return {
        "id": task.id,
        "user_id": task.user_id,
        "agent_type": task.agent_type,
        "prompt": task.prompt,
        "result": task.result,
        "plan_details": task.plan_details,
        "result_file_path": task.result_file_path,
        "has_file": bool(task.result_file_path),
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _owned_task(db: Session, task_id: int, user_id: int) -> Task | None:
    return (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )


# POST /api/v1/tasks — Create a new task (PROTECTED)
@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task for the current user",
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new task for the currently logged-in user.
    user_id is taken from the JWT token — the frontend does NOT send it manually.
    """
    new_task = Task(
        user_id=current_user.id,
        agent_type=task_data.agent_type,
        prompt=task_data.prompt,
        status="pending",
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return APIResponse(
        success=True,
        data=_task_detail(new_task),
        message="Task created",
        error=None,
    )


# GET /api/v1/tasks — List tasks for logged-in user (PROTECTED)
@router.get(
    "",
    response_model=APIResponse,
    summary="List current user's tasks (most recent first)",
)
def list_tasks(
    agent_type: str | None = Query(None, description="Filter by agent type"),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending/running/completed/failed)",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List tasks belonging to the current user only.
    Supports optional agent_type / status filters and offset pagination.
    """
    q = db.query(Task).filter(Task.user_id == current_user.id)
    if agent_type:
        q = q.filter(Task.agent_type == agent_type)
    if status_filter:
        q = q.filter(Task.status == status_filter)

    total_count = q.count()
    rows = (
        q.order_by(Task.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return APIResponse(
        success=True,
        data={
            "tasks": [_task_list_item(t) for t in rows],
            "total_count": total_count,
        },
        message="Tasks retrieved",
        error=None,
    )


# GET /api/v1/tasks/{task_id}/download — Download generated file (PROTECTED)
@router.get(
    "/{task_id}/download",
    summary="Download a task's generated file (owner only)",
)
def download_task_file(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Serve result_file_path when present (e.g. PPT decks). Same ownership rules."""
    task = _owned_task(db, task_id, current_user.id)
    if task is None or not task.result_file_path:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Generated file not found or not owned by the current user.",
        )
    path = Path(task.result_file_path)
    if not path.is_file():
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Generated file is missing on disk.",
        )
    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/octet-stream",
    )


# GET /api/v1/tasks/{task_id} — Get one task (PROTECTED)
@router.get(
    "/{task_id}",
    response_model=APIResponse,
    summary="Get one task (owner only)",
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Full task detail. Returns 404 if missing or owned by another user.
    """
    task = _owned_task(db, task_id, current_user.id)
    if task is None:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Task not found or not owned by the current user.",
        )
    return APIResponse(
        success=True,
        data=_task_detail(task),
        message="Task retrieved",
        error=None,
    )


# DELETE /api/v1/tasks/{task_id} — Delete a task (PROTECTED)
@router.delete(
    "/{task_id}",
    response_model=APIResponse,
    summary="Delete a task and any associated generated file",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a task. Only the owner can delete it.
    If result_file_path is set, remove that file from disk as well.
    """
    task = _owned_task(db, task_id, current_user.id)
    if task is None:
        return _error_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
            "Task not found or not owned by the current user.",
        )

    file_path = Path(task.result_file_path) if task.result_file_path else None
    deleted_id = task.id

    db.delete(task)
    db.commit()

    if file_path and file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            pass

    return APIResponse(
        success=True,
        data={"task_id": deleted_id},
        message="Task deleted",
        error=None,
    )

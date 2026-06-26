# backend/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Task, User
from schemas import TaskCreate, TaskResponse
from core.dependencies import get_current_active_user
from typing import List

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# POST /api/v1/tasks — Create a new task (PROTECTED)
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)  # JWT auth
):
    """
    Create a new task for the currently logged-in user.
    user_id is taken from the JWT token — the frontend does NOT send it manually.
    """
    new_task = Task(
        user_id=current_user.id,    # From JWT token — secure!
        agent_type=task_data.agent_type,
        prompt=task_data.prompt,
        status="pending"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


# GET /api/v1/tasks — List tasks for logged-in user (PROTECTED)
@router.get("/", response_model=List[TaskResponse])
def get_tasks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)  # JWT auth
):
    """
    List all tasks belonging to the currently logged-in user.
    Users can only see their own tasks — enforced by filtering on current_user.id.
    """
    tasks = (
        db.query(Task)
        .filter(Task.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return tasks


# GET /api/v1/tasks/{task_id} — Get one task (PROTECTED)
@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)  # JWT auth
):
    """
    Get a single task by ID.
    Returns 404 if the task doesn't exist OR belongs to a different user.
    (This prevents users from guessing other users' task IDs.)
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    return task


# DELETE /api/v1/tasks/{task_id} — Delete a task (PROTECTED)
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)  # JWT auth
):
    """
    Delete a task. Only the task owner can delete it.
    Returns 204 No Content on success (no body).
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    db.delete(task)
    db.commit()

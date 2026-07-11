# backend/routers/agents.py
import asyncio
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from database import get_db
from models import Task, User
from schemas import APIResponse, ResearchRequest
from core.dependencies import get_current_active_user

router = APIRouter()

RESEARCH_TIMEOUT_SECONDS = 90


def _error_response(status_code: int, message: str, error: str) -> JSONResponse:
    """Return the standard APIResponse shape with a non-2xx status code."""
    body = APIResponse(
        success=False,
        data=None,
        message=message,
        error=error,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


@router.post(
    "/research",
    response_model=APIResponse,
    summary="Run the Research Agent on a topic",
)
async def research_agent(
    body: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Authenticated endpoint that runs the Day 5 Research Agent.

    - Creates a Task row (status=running) before kickoff
    - Runs sync `run_research()` in a threadpool so the event loop is not blocked
    - Enforces a 90s timeout (504 on timeout)
    - Updates the Task to completed/failed when finished
    """
    # Lazy import so FastAPI can boot even if CrewAI deps are mid-install
    from agents.research_agent import run_research

    topic = body.topic.strip()
    if len(topic) < 3:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "Topic must be at least 3 characters after trimming whitespace.",
        )

    task = Task(
        user_id=current_user.id,
        agent_type="research",
        prompt=topic,
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        result = await asyncio.wait_for(
            run_in_threadpool(run_research, topic),
            timeout=RESEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        task.status = "failed"
        task.result = "Research timed out after 90 seconds."
        db.commit()
        return _error_response(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Research timed out",
            "Research is taking longer than expected — please try again.",
        )
    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        db.commit()
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Research failed",
            f"Upstream agent error: {exc}",
        )

    task.status = "completed"
    task.result = result
    db.commit()

    return APIResponse(
        success=True,
        data={"result": result, "task_id": task.id},
        message="Research completed",
        error=None,
    )

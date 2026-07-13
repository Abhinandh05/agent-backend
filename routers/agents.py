# backend/routers/agents.py
import asyncio
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from database import get_db
from models import Task, User
from schemas import (
    APIResponse,
    ResearchRequest,
    FinanceRequest,
    AnalyticsRequest,
    CodingRequest,
)
from core.dependencies import get_current_active_user

router = APIRouter()

AGENT_TIMEOUT_SECONDS = 90
CODING_TIMEOUT_SECONDS = 120


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
    """Authenticated Research Agent endpoint."""
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
            run_in_threadpool(run_research, topic, current_user.id),
            timeout=AGENT_TIMEOUT_SECONDS,
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


@router.post(
    "/finance",
    response_model=APIResponse,
    summary="Run the Finance Agent (LLM + credit-risk tool)",
)
async def finance_agent(
    body: FinanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated Finance Agent — same pattern as /research."""
    from agents.finance_agent import run_finance_analysis

    request = body.request.strip()
    if len(request) < 3:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "Request must be at least 3 characters after trimming whitespace.",
        )

    task = Task(
        user_id=current_user.id,
        agent_type="finance",
        prompt=request,
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        result = await asyncio.wait_for(
            run_in_threadpool(run_finance_analysis, request),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        task.status = "failed"
        task.result = "Finance analysis timed out after 90 seconds."
        db.commit()
        return _error_response(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Finance analysis timed out",
            "Finance analysis is taking longer than expected — please try again.",
        )
    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        db.commit()
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Finance analysis failed",
            f"Upstream agent error: {exc}",
        )

    task.status = "completed"
    task.result = result
    db.commit()

    return APIResponse(
        success=True,
        data={"result": result, "task_id": task.id},
        message="Finance analysis completed",
        error=None,
    )


@router.post(
    "/analytics",
    response_model=APIResponse,
    summary="Run the Analytics Agent (LLM + churn + sales-forecast tools)",
)
async def analytics_agent(
    body: AnalyticsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated Analytics Agent — same pattern as /research and /finance."""
    from agents.analytics_agent import run_analytics

    request = body.request.strip()
    if len(request) < 3:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "Request must be at least 3 characters after trimming whitespace.",
        )

    task = Task(
        user_id=current_user.id,
        agent_type="analytics",
        prompt=request,
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        result = await asyncio.wait_for(
            run_in_threadpool(run_analytics, request),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        task.status = "failed"
        task.result = "Analytics timed out after 90 seconds."
        db.commit()
        return _error_response(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Analytics timed out",
            "Analytics is taking longer than expected — please try again.",
        )
    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        db.commit()
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Analytics failed",
            f"Upstream agent error: {exc}",
        )

    task.status = "completed"
    task.result = result
    db.commit()

    return APIResponse(
        success=True,
        data={"result": result, "task_id": task.id},
        message="Analytics completed",
        error=None,
    )


@router.post(
    "/coding",
    response_model=APIResponse,
    summary="Run the Coding Agent (LLM + local Python sandbox)",
)
async def coding_agent(
    body: CodingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Authenticated Coding Agent — longer timeout to allow sandbox runs."""
    from agents.coding_agent import run_coding_task

    request = body.request.strip()
    if len(request) < 3:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "Request must be at least 3 characters after trimming whitespace.",
        )

    task = Task(
        user_id=current_user.id,
        agent_type="coding",
        prompt=request,
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        result = await asyncio.wait_for(
            run_in_threadpool(run_coding_task, request),
            timeout=CODING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        task.status = "failed"
        task.result = "Coding task timed out after 120 seconds."
        db.commit()
        return _error_response(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Coding timed out",
            "Coding is taking longer than expected — please try again.",
        )
    except Exception as exc:
        task.status = "failed"
        task.result = str(exc)
        db.commit()
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Coding failed",
            f"Upstream agent error: {exc}",
        )

    task.status = "completed"
    task.result = result
    db.commit()

    return APIResponse(
        success=True,
        data={"result": result, "task_id": task.id},
        message="Coding completed",
        error=None,
    )

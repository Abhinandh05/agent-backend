"""
Direct tool endpoints (no LLM) — Day 13 code execution and similar helpers.

POST /api/v1/tools/execute-code uses the beginner-safe subprocess sandbox.
See tools/code_execution_tool.py for honest security limitations.
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from schemas import APIResponse, ExecuteCodeRequest
from core.dependencies import get_current_active_user
from models import User

router = APIRouter(prefix="/tools", tags=["tools"])


def _error_response(status_code: int, message: str, error: str) -> JSONResponse:
    body = APIResponse(
        success=False,
        data=None,
        message=message,
        error=error,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


@router.post(
    "/execute-code",
    response_model=APIResponse,
    summary="Run Python code in the local beginner-safe sandbox (no LLM)",
)
async def execute_code(
    body: ExecuteCodeRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Instant code run for frontend "Run code" / quick testing.

    Not a hardened security boundary — process isolation + timeout only.
    """
    from tools.code_execution_tool import execute_python_code

    code = body.code.strip()
    if not code:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "code must not be empty after trimming whitespace.",
        )

    try:
        result = execute_python_code(code)
    except Exception as exc:
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Code execution failed",
            str(exc),
        )

    return APIResponse(
        success=True,
        data=result,
        message="Code execution completed",
        error=None,
    )

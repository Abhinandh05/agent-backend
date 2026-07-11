# backend/routers/ml.py — direct ML prediction endpoints (no LLM)
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from schemas import (
    APIResponse,
    CreditRiskRequest,
    ChurnRequest,
    SalesForecastRequest,
)
from core.dependencies import get_current_active_user
from models import User

router = APIRouter(prefix="/ml", tags=["ml"])


def _error_response(status_code: int, message: str, error: str) -> JSONResponse:
    body = APIResponse(
        success=False,
        data=None,
        message=message,
        error=error,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=body)


@router.post(
    "/credit-risk",
    response_model=APIResponse,
    summary="Direct credit-risk prediction (no LLM)",
)
async def credit_risk_predict(
    body: CreditRiskRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Instant numeric prediction from the trained RandomForest.
    Use this when the frontend only needs Approve/Reject + probability
    without waiting on an LLM call.
    """
    from ml.predict_credit_risk import predict_credit_risk

    if not body.applicant:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "applicant object must not be empty.",
        )

    try:
        result = predict_credit_risk(body.applicant)
    except FileNotFoundError as exc:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Model not ready",
            str(exc),
        )
    except Exception as exc:
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Prediction failed",
            str(exc),
        )

    return APIResponse(
        success=True,
        data=result,
        message="Credit risk prediction completed",
        error=None,
    )


@router.post(
    "/churn",
    response_model=APIResponse,
    summary="Direct churn prediction (no LLM)",
)
async def churn_predict(
    body: ChurnRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Instant Yes/No + probability from the trained churn RandomForest."""
    from ml.predict_churn import predict_churn

    if not body.customer:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "customer object must not be empty.",
        )

    try:
        result = predict_churn(body.customer)
    except FileNotFoundError as exc:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Model not ready",
            str(exc),
        )
    except Exception as exc:
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Prediction failed",
            str(exc),
        )

    return APIResponse(
        success=True,
        data=result,
        message="Churn prediction completed",
        error=None,
    )


@router.post(
    "/sales-forecast",
    response_model=APIResponse,
    summary="Direct sales-forecast prediction (no LLM)",
)
async def sales_forecast_predict(
    body: SalesForecastRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Instant predicted_sales from the trained sales RandomForestRegressor."""
    from ml.predict_sales_forecast import predict_sales

    if not body.features:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "features object must not be empty.",
        )

    try:
        result = predict_sales(body.features)
    except FileNotFoundError as exc:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Model not ready",
            str(exc),
        )
    except Exception as exc:
        return _error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Prediction failed",
            str(exc),
        )

    return APIResponse(
        success=True,
        data=result,
        message="Sales forecast completed",
        error=None,
    )

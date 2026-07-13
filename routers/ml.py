# backend/routers/ml.py — direct ML prediction endpoints (no LLM)
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from schemas import (
    APIResponse,
    CreditRiskRequest,
    ChurnRequest,
    SalesForecastRequest,
    CustomerSegmentRequest,
    SpamCheckRequest,
    FraudCheckRequest,
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


@router.post(
    "/customer-segment",
    response_model=APIResponse,
    summary="Direct customer-segment prediction (no LLM)",
)
async def customer_segment_predict(
    body: CustomerSegmentRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Instant segment label from the trained unsupervised K-Means model."""
    from ml.predict_customer_segment import predict_segment

    if not body.customer:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "customer object must not be empty.",
        )

    try:
        result = predict_segment(body.customer)
    except FileNotFoundError as exc:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Model not ready",
            str(exc),
        )
    except ValueError as exc:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
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
        message="Customer segmentation completed",
        error=None,
    )


@router.post(
    "/spam-check",
    response_model=APIResponse,
    summary="Direct spam/ham text classification (no LLM)",
)
async def spam_check(
    body: SpamCheckRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Instant spam/ham label from the trained TF-IDF + MultinomialNB model."""
    from ml.predict_spam import classify_message

    if not body.text or not body.text.strip():
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "text must not be empty.",
        )

    try:
        result = classify_message(body.text)
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
        message="Spam check completed",
        error=None,
    )


@router.post(
    "/fraud-check",
    response_model=APIResponse,
    summary="Direct fraud / anomaly check (no LLM)",
)
async def fraud_check(
    body: FraudCheckRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Instant anomaly flag from the trained IsolationForest model."""
    from ml.predict_fraud import check_transaction

    if not body.features:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
            "features object must not be empty.",
        )

    try:
        result = check_transaction(body.features)
    except FileNotFoundError as exc:
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Model not ready",
            str(exc),
        )
    except ValueError as exc:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation failed",
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
        message="Fraud check completed",
        error=None,
    )

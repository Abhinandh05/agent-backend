# backend/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# ══════════════════════════════════════════════════
# USER SCHEMAS
# ══════════════════════════════════════════════════

class UserCreate(BaseModel):
    """Data required to register a new user."""
    name: str
    second_name: str
    email: EmailStr       # Pydantic validates it looks like a real email
    password: str


class UserResponse(BaseModel):
    """Data returned about a user — NEVER includes the password."""
    id: int
    name: str
    second_name: Optional[str] = None
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Optional fields to update on a user profile."""
    name: Optional[str] = None
    second_name: Optional[str] = None
    email: Optional[EmailStr] = None


# ══════════════════════════════════════════════════
# AUTH SCHEMAS
# ══════════════════════════════════════════════════

class LoginRequest(BaseModel):
    """Body for POST /auth/login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response returned after successful login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse     # Return the user object too so the frontend doesn't need a second call


class TokenData(BaseModel):
    """Payload stored inside the JWT token."""
    user_id: Optional[int] = None


# ══════════════════════════════════════════════════
# TASK SCHEMAS
# ══════════════════════════════════════════════════

class TaskCreate(BaseModel):
    """Data required to create a new task."""
    agent_type: str
    prompt: str


class TaskResponse(BaseModel):
    """Data returned about a task."""
    id: int
    user_id: int
    agent_type: str
    prompt: str
    result: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════
# AGENT SCHEMAS
# ══════════════════════════════════════════════════

class ResearchRequest(BaseModel):
    """Body for POST /api/v1/agents/research"""
    topic: str = Field(..., min_length=3, max_length=500)


class FinanceRequest(BaseModel):
    """Body for POST /api/v1/agents/finance"""
    request: str = Field(..., min_length=3, max_length=2000)


class CreditRiskRequest(BaseModel):
    """
    Body for POST /api/v1/ml/credit-risk.

    Accepts any applicant fields as a free-form dict matching the loan CSV
    columns (schema varies by Kaggle dataset).
    """
    applicant: dict = Field(
        ...,
        description="Applicant feature dict matching loan_data.csv columns",
    )


class AnalyticsRequest(BaseModel):
    """Body for POST /api/v1/agents/analytics"""
    request: str = Field(..., min_length=3, max_length=2000)


class CodingRequest(BaseModel):
    """Body for POST /api/v1/agents/coding"""
    request: str = Field(..., min_length=3, max_length=5000)


class EmailRequest(BaseModel):
    """Body for POST /api/v1/agents/email (draft)."""
    request: str = Field(..., min_length=3, max_length=5000)
    recipient_hint: Optional[str] = Field(None, max_length=500)
    tone: Optional[str] = Field(None, max_length=200)


class EmailSendRequest(BaseModel):
    """Body for POST /api/v1/agents/email/send (optional SendGrid)."""
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=50000)


class ExecuteCodeRequest(BaseModel):
    """Body for POST /api/v1/tools/execute-code (no LLM)."""
    code: str = Field(..., min_length=1, max_length=20000)


class ChurnRequest(BaseModel):
    """
    Body for POST /api/v1/ml/churn.

    Free-form customer dict matching telco_churn.csv columns.
    """
    customer: dict = Field(
        ...,
        description="Customer feature dict matching telco_churn.csv columns",
    )


class SalesForecastRequest(BaseModel):
    """
    Body for POST /api/v1/ml/sales-forecast.

    Calendar + optional Category/Region/Segment, or a date field.
    """
    features: dict = Field(
        ...,
        description="Forecast features: year/month/... or Order Date + Category/Region",
    )


class DocumentQueryRequest(BaseModel):
    """Body for POST /api/v1/documents/query (RAG)."""
    question: str = Field(..., min_length=3, max_length=2000)


# ══════════════════════════════════════════════════
# STANDARD API RESPONSE WRAPPER
# ══════════════════════════════════════════════════

class APIResponse(BaseModel):
    """
    Standard wrapper for all API responses.
    Use this so the frontend always gets a consistent shape.

    Success:  {"success": true,  "data": {...}, "message": "Done",  "error": null}
    Failure:  {"success": false, "data": null,  "message": "Failed", "error": "reason"}
    """
    success: bool
    data: Optional[dict] = None
    message: str = ""
    error: Optional[str] = None

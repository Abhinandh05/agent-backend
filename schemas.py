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

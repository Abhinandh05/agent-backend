# backend/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# --- USER SCHEMAS ---

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

# --- TASK SCHEMAS ---

class TaskCreate(BaseModel):
    agent_type: str
    prompt: str

class TaskResponse(BaseModel):
    id: int
    agent_type: str
    prompt: str
    result: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

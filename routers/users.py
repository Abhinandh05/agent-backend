# backend/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserResponse, UserUpdate
from core.dependencies import get_current_active_user
from typing import List

router = APIRouter(prefix="/users", tags=["Users"])


# GET /api/v1/users/me — Alias for auth/me (PROTECTED)
@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_active_user)):
    """Get the current user's profile. Same as GET /auth/me."""
    return current_user


# PATCH /api/v1/users/me — Update own profile (PROTECTED)
@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update the current user's name or email.
    Only fields provided in the request body are updated (partial update).
    """
    if update_data.name is not None:
        current_user.name = update_data.name

    if update_data.email is not None:
        # Check new email is not already taken by someone else
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already in use by another account."
            )
        current_user.email = update_data.email

    db.commit()
    db.refresh(current_user)
    return current_user


# GET /api/v1/users/{user_id} — Get any user by ID (PROTECTED)
@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a user by their ID.
    Requires a valid JWT token (any logged-in user can look up another user's profile).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return user

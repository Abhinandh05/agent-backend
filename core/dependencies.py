# backend/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
from core.security import decode_access_token

# OAuth2PasswordBearer tells FastAPI:
# "Look for a Bearer token in the Authorization header"
# tokenUrl is the login endpoint that issues tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency — extracts and verifies the JWT token from the request.
    Injects the logged-in User object into any route that uses Depends(get_current_user).

    Raises 401 if:
    - No token provided
    - Token is invalid or expired
    - User ID in token does not exist in the database
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user_id from the "sub" field
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Look up the user in the database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    # Check if account is still active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Convenience dependency — same as get_current_user but explicitly named.
    Use this in routes to make it obvious the route requires an active logged-in user.
    """
    return current_user

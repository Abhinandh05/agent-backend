# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, UserResponse, LoginRequest, TokenResponse
from core.security import hash_password, verify_password, create_access_token
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────────
# POST /api/v1/auth/register — Create a new account
# ──────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Checks the email is not already taken
    - Hashes the password with bcrypt (NEVER stores plain text)
    - Creates the user record in the database
    - Returns the new user (without the password)
    """
    # 1. Check email is not already registered
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # 2. Hash the password — NEVER store plain passwords
    hashed = hash_password(user_data.password)

    # 3. Create the user record
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed      # Store the bcrypt hash, not the password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Refresh to get the auto-assigned id and created_at

    return new_user


# ──────────────────────────────────────────────────
# POST /api/v1/auth/login — Log in and get a JWT token
# ──────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive a JWT access token"
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.

    - Looks up the user by email
    - Verifies the password against the stored bcrypt hash
    - Creates a JWT token containing the user's ID
    - Returns the token and user details

    The frontend stores this token and sends it in every future request
    as: Authorization: Bearer <token>
    """
    # 1. Find the user by email
    user = db.query(User).filter(User.email == login_data.email).first()

    # 2. Check user exists AND password is correct
    # We check both in the same block to avoid revealing whether the email exists
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact support."
        )

    # 4. Create the JWT token
    # "sub" (subject) is the standard JWT field for the user identifier
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


# ──────────────────────────────────────────────────
# GET /api/v1/auth/me — Get the current logged-in user
# ──────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently logged-in user's profile"
)
def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Returns the profile of the currently logged-in user.

    This route is PROTECTED — it requires a valid JWT token in the header.
    FastAPI injects `current_user` automatically via the get_current_active_user dependency.

    Test this by:
    1. First login at POST /auth/login to get a token
    2. Click 'Authorize' in /docs and paste the token
    3. Then call this endpoint — it returns your user details
    """
    return current_user


# ──────────────────────────────────────────────────
# POST /api/v1/auth/logout — Client-side logout
# ──────────────────────────────────────────────────
@router.post(
    "/logout",
    summary="Logout (client-side token deletion)"
)
def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint.

    JWT tokens are stateless — the server cannot invalidate them.
    The correct approach is to delete the token on the CLIENT side (clear from localStorage/cookie).

    This endpoint confirms the user is logged in and returns a success message.
    The frontend should delete the token after calling this.

    For true server-side invalidation, implement a token blacklist in Redis (Day 27).
    """
    return {
        "message": f"Goodbye {current_user.name}! Token deleted on your client.",
        "success": True
    }

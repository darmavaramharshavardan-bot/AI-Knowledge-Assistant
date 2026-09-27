from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)


# Create authentication router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    """

    # 1. Check if email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # 2. Hash the password
    password_hash = hash_password(
        request.password
    )

    # 3. Create new user
    user = User(
        email=request.email,
        password_hash=password_hash
    )

    # 4. Save user to database
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5. Return safe information
    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email
    }


@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login an existing user and return a JWT token.
    """

    # 1. Find user by email
    user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    # 2. Check whether user exists
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # 3. Verify password
    password_valid = verify_password(
        request.password,
        user.password_hash
    )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # 4. Create JWT access token
    access_token = create_access_token(
        user.id
    )

    # 5. Return token
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
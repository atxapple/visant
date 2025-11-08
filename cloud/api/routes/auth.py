"""Authentication endpoints for user signup, login, and session management."""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from cloud.api.database import get_db, Organization, User
from cloud.api.auth.supabase_client import create_supabase_user, sign_in_with_password
from cloud.api.auth.dependencies import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Request/Response Models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "secure_password_123"
            }
        }


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "secure_password_123"
            }
        }


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
    organization: Optional[dict] = None  # Optional for simplified UI


class UserMeResponse(BaseModel):
    id: str
    email: str
    role: str
    organization: dict
    created_at: datetime
    last_login_at: Optional[datetime]


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user account and organization.

    This endpoint:
    1. Creates a new organization
    2. Creates a user in Supabase Auth
    3. Links the user to the organization in our database
    4. Returns JWT tokens for immediate login

    **Note**: For the MVP, the first user in an org is automatically an admin.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    try:
        # Step 1: Create user in Supabase Auth
        supabase_user = create_supabase_user(request.email, request.password)

        # Step 2: Create organization with auto-generated name
        # Extract username from email for workspace name
        email_username = request.email.split('@')[0]
        org_name = f"{email_username}'s Workspace"

        org = Organization(
            id=uuid.uuid4(),
            name=org_name,
            created_at=datetime.utcnow()
        )
        db.add(org)
        db.flush()  # Get org.id without committing

        # Step 3: Create user in our database
        user = User(
            id=uuid.uuid4(),
            email=request.email,
            org_id=org.id,
            supabase_user_id=uuid.UUID(supabase_user["id"]) if isinstance(supabase_user["id"], str) else supabase_user["id"],
            role="admin",  # First user is admin
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.refresh(org)

        # Step 4: Sign in to get tokens
        auth_result = sign_in_with_password(request.email, request.password)

        return {
            "access_token": auth_result["access_token"],
            "refresh_token": auth_result["refresh_token"],
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
            }
            # Organization not included for simplified UI
            # Available via /v1/auth/me endpoint if needed
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns JWT access token and refresh token.
    The access token should be included in subsequent requests as:
    `Authorization: Bearer <access_token>`
    """
    try:
        # Step 1: Authenticate with Supabase
        auth_result = sign_in_with_password(request.email, request.password)

        # Step 2: Get user from our database
        user = db.query(User).filter(
            User.supabase_user_id == auth_result["user"]["id"]
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database. Please contact support."
            )

        # Update last login
        user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        return {
            "access_token": auth_result["access_token"],
            "refresh_token": auth_result["refresh_token"],
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
            }
            # Organization not included for simplified UI
            # Available via /v1/auth/me endpoint if needed
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserMeResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information.

    Requires valid JWT token in Authorization header.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "organization": {
            "id": str(current_user.organization.id),
            "name": current_user.organization.name,
        },
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout (placeholder for now).

    In a full implementation, this would invalidate the refresh token.
    For now, clients should simply discard their tokens on logout.
    """
    # TODO: Invalidate refresh token in Supabase
    # For now, client-side logout (discard tokens) is sufficient
    return None

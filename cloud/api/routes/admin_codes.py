"""Admin endpoints for activation code management."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from cloud.api.database import get_db
from cloud.api.database.models import ActivationCode, CodeRedemption, User
from cloud.api.auth.dependencies import get_admin_user

router = APIRouter(prefix="/v1/admin/activation-codes", tags=["Admin - Activation Codes"])


# Request/Response Models
class ActivationCodeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Activation code (will be uppercased)")
    description: Optional[str] = Field(None, max_length=255)
    benefit_type: str = Field(..., description="Type: free_months, device_slots, trial_extension")
    benefit_value: int = Field(..., gt=0, description="Numeric value of benefit")
    max_uses: Optional[int] = Field(None, ge=1, description="Max uses (null = unlimited)")
    valid_until: Optional[datetime] = Field(None, description="Expiration date (null = never expires)")
    one_per_user: bool = Field(True, description="Can only be used once per user")


class ActivationCodeUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=255)
    max_uses: Optional[int] = Field(None, ge=1)
    valid_until: Optional[datetime] = None
    active: Optional[bool] = None


class RedemptionInfo(BaseModel):
    org_id: str
    user_email: str
    device_id: Optional[str]
    redeemed_at: datetime
    benefit_applied: Optional[str]


class ActivationCodeResponse(BaseModel):
    code: str
    description: Optional[str]
    benefit_type: str
    benefit_value: int
    max_uses: Optional[int]
    uses_count: int
    valid_from: datetime
    valid_until: Optional[datetime]
    active: bool
    one_per_user: bool
    created_at: datetime
    # Computed fields
    is_expired: bool
    remaining_uses: Optional[int]  # null if unlimited


class ActivationCodeDetail(ActivationCodeResponse):
    redemptions: List[RedemptionInfo]


class ActivationCodeListResponse(BaseModel):
    codes: List[ActivationCodeResponse]
    total: int


# === ENDPOINTS ===

@router.get("", response_model=ActivationCodeListResponse)
def list_activation_codes(
    active_only: bool = Query(False, description="Filter to active codes only"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all activation codes (Admin only).

    **Authentication**: Requires user JWT token.

    **TODO**: Add admin role check in production.
    """
    # Query activation codes
    query = db.query(ActivationCode)

    if active_only:
        query = query.filter(ActivationCode.active == True)

    codes = query.order_by(ActivationCode.created_at.desc()).all()

    # Build response with computed fields
    now = datetime.now(timezone.utc)
    response_codes = []

    for code in codes:
        is_expired = code.valid_until is not None and code.valid_until < now
        remaining_uses = None
        if code.max_uses is not None:
            remaining_uses = max(0, code.max_uses - code.uses_count)

        response_codes.append({
            "code": code.code,
            "description": code.description,
            "benefit_type": code.benefit_type,
            "benefit_value": code.benefit_value,
            "max_uses": code.max_uses,
            "uses_count": code.uses_count,
            "valid_from": code.valid_from,
            "valid_until": code.valid_until,
            "active": code.active,
            "one_per_user": code.one_per_user,
            "created_at": code.created_at,
            "is_expired": is_expired,
            "remaining_uses": remaining_uses
        })

    return {
        "codes": response_codes,
        "total": len(response_codes)
    }


@router.post("", response_model=ActivationCodeResponse, status_code=status.HTTP_201_CREATED)
def create_activation_code(
    request: ActivationCodeCreate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new activation code (Admin only).

    **Authentication**: Requires user JWT token.

    **Validation**:
    - Code must be unique (case-insensitive)
    - Benefit type must be valid
    - Benefit value must be positive

    **TODO**: Add admin role check in production.
    """
    # Normalize code to uppercase
    code_upper = request.code.upper().strip()

    # Validate benefit type
    valid_types = ["free_months", "device_slots", "trial_extension", "discount_percent"]
    if request.benefit_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid benefit_type. Must be one of: {', '.join(valid_types)}"
        )

    # Check for duplicate code
    existing = db.query(ActivationCode).filter(
        func.upper(ActivationCode.code) == code_upper
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Activation code '{code_upper}' already exists"
        )

    # Create activation code
    now = datetime.now(timezone.utc)
    activation_code = ActivationCode(
        code=code_upper,
        description=request.description,
        benefit_type=request.benefit_type,
        benefit_value=request.benefit_value,
        max_uses=request.max_uses,
        valid_from=now,
        valid_until=request.valid_until,
        active=True,
        one_per_user=request.one_per_user,
        created_by_user_id=user.id,
        created_at=now
    )

    db.add(activation_code)
    db.commit()
    db.refresh(activation_code)

    # Build response
    is_expired = activation_code.valid_until is not None and activation_code.valid_until < now
    remaining_uses = None
    if activation_code.max_uses is not None:
        remaining_uses = activation_code.max_uses

    return {
        "code": activation_code.code,
        "description": activation_code.description,
        "benefit_type": activation_code.benefit_type,
        "benefit_value": activation_code.benefit_value,
        "max_uses": activation_code.max_uses,
        "uses_count": activation_code.uses_count,
        "valid_from": activation_code.valid_from,
        "valid_until": activation_code.valid_until,
        "active": activation_code.active,
        "one_per_user": activation_code.one_per_user,
        "created_at": activation_code.created_at,
        "is_expired": is_expired,
        "remaining_uses": remaining_uses
    }


@router.get("/{code}", response_model=ActivationCodeDetail)
def get_activation_code(
    code: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get activation code details with redemption history (Admin only).

    **Authentication**: Requires user JWT token.

    **TODO**: Add admin role check in production.
    """
    code_upper = code.upper().strip()

    activation_code = db.query(ActivationCode).filter(
        func.upper(ActivationCode.code) == code_upper
    ).first()

    if not activation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation code '{code_upper}' not found"
        )

    # Get redemptions with user email
    redemptions = db.query(
        CodeRedemption, User.email
    ).join(
        User, CodeRedemption.user_id == User.id
    ).filter(
        CodeRedemption.code == activation_code.code
    ).order_by(
        CodeRedemption.redeemed_at.desc()
    ).all()

    redemption_list = [
        {
            "org_id": str(redemption.org_id),
            "user_email": email,
            "device_id": redemption.device_id,
            "redeemed_at": redemption.redeemed_at,
            "benefit_applied": redemption.benefit_applied
        }
        for redemption, email in redemptions
    ]

    # Build response
    now = datetime.now(timezone.utc)
    is_expired = activation_code.valid_until is not None and activation_code.valid_until < now
    remaining_uses = None
    if activation_code.max_uses is not None:
        remaining_uses = max(0, activation_code.max_uses - activation_code.uses_count)

    return {
        "code": activation_code.code,
        "description": activation_code.description,
        "benefit_type": activation_code.benefit_type,
        "benefit_value": activation_code.benefit_value,
        "max_uses": activation_code.max_uses,
        "uses_count": activation_code.uses_count,
        "valid_from": activation_code.valid_from,
        "valid_until": activation_code.valid_until,
        "active": activation_code.active,
        "one_per_user": activation_code.one_per_user,
        "created_at": activation_code.created_at,
        "is_expired": is_expired,
        "remaining_uses": remaining_uses,
        "redemptions": redemption_list
    }


@router.put("/{code}", response_model=ActivationCodeResponse)
def update_activation_code(
    code: str,
    request: ActivationCodeUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update activation code (Admin only).

    **Authentication**: Requires user JWT token.

    **Updatable fields**: description, max_uses, valid_until, active status

    **Non-updatable**: code, benefit_type, benefit_value (would break existing redemptions)

    **TODO**: Add admin role check in production.
    """
    code_upper = code.upper().strip()

    activation_code = db.query(ActivationCode).filter(
        func.upper(ActivationCode.code) == code_upper
    ).first()

    if not activation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation code '{code_upper}' not found"
        )

    # Update fields if provided
    if request.description is not None:
        activation_code.description = request.description

    if request.max_uses is not None:
        activation_code.max_uses = request.max_uses

    if request.valid_until is not None:
        activation_code.valid_until = request.valid_until

    if request.active is not None:
        activation_code.active = request.active

    db.commit()
    db.refresh(activation_code)

    # Build response
    now = datetime.now(timezone.utc)
    is_expired = activation_code.valid_until is not None and activation_code.valid_until < now
    remaining_uses = None
    if activation_code.max_uses is not None:
        remaining_uses = max(0, activation_code.max_uses - activation_code.uses_count)

    return {
        "code": activation_code.code,
        "description": activation_code.description,
        "benefit_type": activation_code.benefit_type,
        "benefit_value": activation_code.benefit_value,
        "max_uses": activation_code.max_uses,
        "uses_count": activation_code.uses_count,
        "valid_from": activation_code.valid_from,
        "valid_until": activation_code.valid_until,
        "active": activation_code.active,
        "one_per_user": activation_code.one_per_user,
        "created_at": activation_code.created_at,
        "is_expired": is_expired,
        "remaining_uses": remaining_uses
    }


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activation_code(
    code: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete activation code (Admin only).

    **Authentication**: Requires user JWT token.

    **Restriction**: Can only delete codes that have never been used (uses_count = 0).

    For codes that have been used, use deactivation (set active=False) instead.

    **TODO**: Add admin role check in production.
    """
    code_upper = code.upper().strip()

    activation_code = db.query(ActivationCode).filter(
        func.upper(ActivationCode.code) == code_upper
    ).first()

    if not activation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Activation code '{code_upper}' not found"
        )

    # Check if code has been used
    if activation_code.uses_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete code that has been used {activation_code.uses_count} times. Deactivate instead."
        )

    db.delete(activation_code)
    db.commit()

    return None

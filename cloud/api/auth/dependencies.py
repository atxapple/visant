"""FastAPI dependencies for authentication and authorization."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from cloud.api.database import get_db, User, Organization, Device
from cloud.api.auth.middleware import verify_jwt_token, extract_token_from_header


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @app.get("/endpoint")
        def endpoint(user: User = Depends(get_current_user)):
            ...

    Args:
        authorization: Authorization header with Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token invalid or user not found
    """
    # Extract and verify JWT token
    token = extract_token_from_header(authorization)
    payload = verify_jwt_token(token)

    # Get user from database
    user = db.query(User).filter(
        User.supabase_user_id == payload["user_id"]
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in database"
        )

    # Update last login timestamp
    from datetime import datetime
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return user


def get_current_org(
    user: User = Depends(get_current_user)
) -> Organization:
    """
    FastAPI dependency to get current user's organization.

    Usage:
        @app.get("/endpoint")
        def endpoint(org: Organization = Depends(get_current_org)):
            ...

    Args:
        user: Current authenticated user

    Returns:
        Organization object

    Raises:
        HTTPException: If organization not found
    """
    if not user.organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return user.organization


def verify_device_by_id(
    device_id: str,
    db: Session = Depends(get_db)
) -> Device:
    """
    FastAPI dependency to verify device by device_id only (no API key required).

    This simpler authentication method is suitable for headless IoT cameras where:
    - Device ID is unique and pre-assigned during manufacturing
    - Physical device security is the primary protection
    - Devices cannot be easily reconfigured

    Security validations:
    - Device must exist in database
    - Device must be activated (status="active")
    - Device must belong to an active organization

    Usage:
        @app.post("/v1/captures")
        def upload_capture(
            request: CaptureUploadRequest,
            device: Device = Depends(lambda: verify_device_by_id(request.device_id))
        ):
            ...

    Args:
        device_id: Device identifier from request body
        db: Database session

    Returns:
        Device object if all validations pass

    Raises:
        HTTPException: If device not found, not activated, or org inactive
    """
    # Look up device by device_id
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found"
        )

    # Verify device is activated
    if device.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device is {device.status}. Only active devices can upload captures."
        )

    # Verify device belongs to an organization
    if not device.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not assigned to any organization. Activate device first."
        )

    # Verify organization exists and is active
    org = db.query(Organization).filter(Organization.id == device.org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device organization not found"
        )

    # Update device last_seen timestamp
    from datetime import datetime
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    return device


def require_org_ownership(
    resource_org_id,
    current_org: Organization = Depends(get_current_org)
):
    """
    Verify that current user's organization owns the resource.

    Usage:
        @app.get("/v1/devices/{device_id}")
        def get_device(
            device_id: str,
            org: Organization = Depends(get_current_org),
            db: Session = Depends(get_db)
        ):
            device = db.query(Device).filter_by(device_id=device_id).first()
            require_org_ownership(device.org_id, org)
            return device

    Args:
        resource_org_id: Organization ID of the resource
        current_org: Current user's organization

    Raises:
        HTTPException: If org IDs don't match
    """
    if str(resource_org_id) != str(current_org.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )

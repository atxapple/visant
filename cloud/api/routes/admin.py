"""Admin API routes for user, device, and image management."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud.api.database import get_db, User, Device, Capture, Organization
from cloud.api.auth.dependencies import get_current_user
from cloud.api.storage.config import UPLOADS_DIR

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


# ====================
# Response Models
# ====================

class UserListItem(BaseModel):
    id: str
    email: str
    name: Optional[str]
    org_id: str
    org_name: str
    role: str
    created_at: datetime
    last_login_at: Optional[datetime]


class DeviceListItem(BaseModel):
    device_id: str
    friendly_name: Optional[str]
    org_id: str
    org_name: str
    status: str
    device_version: Optional[str]
    created_at: datetime
    last_seen_at: Optional[datetime]


class CaptureListItem(BaseModel):
    record_id: str
    device_id: str
    org_id: str
    org_name: str
    state: Optional[str]
    evaluation_status: str
    captured_at: datetime
    file_size_mb: Optional[float]


class StorageStats(BaseModel):
    total_captures: int
    total_size_mb: float
    by_org: List[dict]
    by_state: List[dict]


class PruneRequest(BaseModel):
    before_date: Optional[str] = None  # ISO 8601 date string
    state: Optional[str] = None  # normal, abnormal, uncertain
    org_id: Optional[str] = None
    limit: Optional[int] = None  # Max number to delete


class PruneResponse(BaseModel):
    deleted_count: int
    freed_space_mb: float


# ====================
# USER MANAGEMENT
# ====================

@router.get("/users", response_model=List[UserListItem])
def list_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all users across all organizations.
    """
    users = db.query(User, Organization.name).join(
        Organization, User.org_id == Organization.id
    ).order_by(User.created_at.desc()).limit(limit).offset(offset).all()

    return [
        UserListItem(
            id=str(user.id),
            email=user.email,
            name=user.name,
            org_id=str(user.org_id),
            org_name=org_name,
            role=user.role,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )
        for user, org_name in users
    ]


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user.

    Cannot delete yourself.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete yourself"
        )

    db.delete(user)
    db.commit()

    return {"message": f"User {user.email} deleted successfully"}


# ====================
# DEVICE MANAGEMENT
# ====================

@router.get("/devices", response_model=List[DeviceListItem])
def list_devices(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all devices across all organizations.

    Admin-only endpoint. Supports filtering by status.
    """
    query = db.query(Device, Organization.name).join(
        Organization, Device.org_id == Organization.id
    )

    if status_filter:
        query = query.filter(Device.status == status_filter)

    devices = query.order_by(Device.created_at.desc()).limit(limit).offset(offset).all()

    return [
        DeviceListItem(
            device_id=device.device_id,
            friendly_name=device.friendly_name,
            org_id=str(device.org_id),
            org_name=org_name,
            status=device.status,
            device_version=device.device_version,
            created_at=device.created_at,
            last_seen_at=device.last_seen_at
        )
        for device, org_name in devices
    ]


@router.delete("/devices/{device_id}")
def delete_device(
    device_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a device and all its captures.

    Admin-only endpoint. Also deletes all associated captures and files.
    """
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Get captures to delete files
    captures = db.query(Capture).filter(Capture.device_id == device_id).all()

    deleted_files = 0
    freed_space = 0

    for capture in captures:
        # Delete image files
        if capture.image_path:
            image_file = UPLOADS_DIR / capture.image_path
            if image_file.exists():
                freed_space += image_file.stat().st_size
                image_file.unlink()
                deleted_files += 1

        # Delete thumbnail files
        if capture.thumbnail_path:
            thumb_file = UPLOADS_DIR / capture.thumbnail_path
            if thumb_file.exists():
                freed_space += thumb_file.stat().st_size
                thumb_file.unlink()
                deleted_files += 1

    # Delete database records (cascade will handle captures)
    db.delete(device)
    db.commit()

    return {
        "message": f"Device {device_id} deleted successfully",
        "deleted_captures": len(captures),
        "deleted_files": deleted_files,
        "freed_space_mb": round(freed_space / (1024 * 1024), 2)
    }


# ====================
# CAPTURE MANAGEMENT
# ====================

@router.get("/captures", response_model=List[CaptureListItem])
def list_captures(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    state: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all captures across all organizations.

    Admin-only endpoint. Supports filtering by state and organization.
    """
    query = db.query(Capture, Organization.name).join(
        Organization, Capture.org_id == Organization.id
    )

    if state:
        query = query.filter(Capture.state == state)

    if org_id:
        query = query.filter(Capture.org_id == org_id)

    captures = query.order_by(Capture.captured_at.desc()).limit(limit).offset(offset).all()

    result = []
    for capture, org_name in captures:
        # Calculate file size
        file_size_mb = None
        if capture.image_path:
            image_file = UPLOADS_DIR / capture.image_path
            if image_file.exists():
                file_size_mb = round(image_file.stat().st_size / (1024 * 1024), 3)

        result.append(CaptureListItem(
            record_id=capture.record_id,
            device_id=capture.device_id,
            org_id=str(capture.org_id),
            org_name=org_name,
            state=capture.state,
            evaluation_status=capture.evaluation_status,
            captured_at=capture.captured_at,
            file_size_mb=file_size_mb
        ))

    return result


@router.delete("/captures/{record_id}")
def delete_capture(
    record_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a single capture and its files.

    Admin-only endpoint.
    """
    capture = db.query(Capture).filter(Capture.record_id == record_id).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    freed_space = 0

    # Delete image file
    if capture.image_path:
        image_file = UPLOADS_DIR / capture.image_path
        if image_file.exists():
            freed_space += image_file.stat().st_size
            image_file.unlink()

    # Delete thumbnail file
    if capture.thumbnail_path:
        thumb_file = UPLOADS_DIR / capture.thumbnail_path
        if thumb_file.exists():
            freed_space += thumb_file.stat().st_size
            thumb_file.unlink()

    db.delete(capture)
    db.commit()

    return {
        "message": "Capture deleted successfully",
        "freed_space_mb": round(freed_space / (1024 * 1024), 3)
    }


# ====================
# STORAGE PRUNING
# ====================

@router.post("/captures/prune", response_model=PruneResponse)
def prune_captures(
    request: PruneRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk delete captures based on filters.

    Admin-only endpoint. Use with caution!

    Filters:
    - before_date: Delete captures before this date (ISO 8601)
    - state: Delete captures with specific state (normal, abnormal, uncertain)
    - org_id: Delete captures from specific organization
    - limit: Maximum number of captures to delete
    """
    query = db.query(Capture)

    if request.before_date:
        before_dt = datetime.fromisoformat(request.before_date.replace('Z', '+00:00'))
        query = query.filter(Capture.captured_at < before_dt)

    if request.state:
        query = query.filter(Capture.state == request.state)

    if request.org_id:
        query = query.filter(Capture.org_id == request.org_id)

    # Apply limit
    if request.limit:
        captures = query.order_by(Capture.captured_at.asc()).limit(request.limit).all()
    else:
        captures = query.all()

    deleted_count = 0
    freed_space = 0

    for capture in captures:
        # Delete image file
        if capture.image_path:
            image_file = UPLOADS_DIR / capture.image_path
            if image_file.exists():
                freed_space += image_file.stat().st_size
                image_file.unlink()

        # Delete thumbnail file
        if capture.thumbnail_path:
            thumb_file = UPLOADS_DIR / capture.thumbnail_path
            if thumb_file.exists():
                freed_space += thumb_file.stat().st_size
                thumb_file.unlink()

        db.delete(capture)
        deleted_count += 1

    db.commit()

    return PruneResponse(
        deleted_count=deleted_count,
        freed_space_mb=round(freed_space / (1024 * 1024), 2)
    )


@router.get("/storage/stats", response_model=StorageStats)
def get_storage_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get storage usage statistics.

    Admin-only endpoint.
    """
    # Total captures
    total_captures = db.query(func.count(Capture.record_id)).scalar()

    # Calculate total size by iterating through files
    total_size = 0
    all_captures = db.query(Capture).all()

    for capture in all_captures:
        if capture.image_path:
            image_file = UPLOADS_DIR / capture.image_path
            if image_file.exists():
                total_size += image_file.stat().st_size

        if capture.thumbnail_path:
            thumb_file = UPLOADS_DIR / capture.thumbnail_path
            if thumb_file.exists():
                total_size += thumb_file.stat().st_size

    # By organization
    by_org = db.query(
        Organization.name,
        func.count(Capture.record_id).label('count')
    ).join(
        Capture, Organization.id == Capture.org_id
    ).group_by(Organization.name).all()

    # By state
    by_state = db.query(
        Capture.state,
        func.count(Capture.record_id).label('count')
    ).group_by(Capture.state).all()

    return StorageStats(
        total_captures=total_captures,
        total_size_mb=round(total_size / (1024 * 1024), 2),
        by_org=[{"org_name": org_name, "count": count} for org_name, count in by_org],
        by_state=[{"state": state or "null", "count": count} for state, count in by_state]
    )

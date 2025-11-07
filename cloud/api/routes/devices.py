"""Device management and provisioning endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud.api.database import get_db, Device, Organization, User
from cloud.api.auth.dependencies import get_current_org, get_current_user, generate_device_api_key

router = APIRouter(prefix="/v1/devices", tags=["Devices"])


# Request/Response Models
class DeviceCreateRequest(BaseModel):
    device_id: str
    friendly_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "floor-01-cam",
                "friendly_name": "Floor 1 Camera"
            }
        }


class DeviceResponse(BaseModel):
    device_id: str
    friendly_name: Optional[str]
    status: str
    created_at: datetime
    last_seen_at: Optional[datetime]
    device_version: Optional[str]
    organization: dict


class DeviceCreateResponse(DeviceResponse):
    api_key: str  # Only returned on creation


class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    total: int


@router.post("", response_model=DeviceCreateResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    request: DeviceCreateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a new device (camera) for the organization.

    This endpoint:
    1. Generates a secure API key for the device
    2. Creates the device record
    3. Returns the API key (SAVE THIS - it won't be shown again!)

    **Important**: The device API key is only returned once.
    Store it securely and configure your device to use it.

    Devices use this API key in the Authorization header:
    `Authorization: Bearer <device_api_key>`
    """
    # Check if device_id already exists
    existing_device = db.query(Device).filter(
        Device.device_id == request.device_id
    ).first()

    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device with ID '{request.device_id}' already exists"
        )

    # Generate secure API key
    api_key = generate_device_api_key()

    # Create device
    device = Device(
        device_id=request.device_id,
        org_id=org.id,
        friendly_name=request.friendly_name or request.device_id.replace('-', ' ').title(),
        api_key=api_key,
        status="active",
        created_at=datetime.utcnow()
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "device_id": device.device_id,
        "friendly_name": device.friendly_name,
        "status": device.status,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
        "device_version": device.device_version,
        "api_key": api_key,  # Only shown once!
        "organization": {
            "id": str(org.id),
            "name": org.name,
        }
    }


@router.get("", response_model=DeviceListResponse)
def list_devices(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    List all devices for the current organization.

    Returns devices sorted by creation date (newest first).
    """
    devices = db.query(Device).filter(
        Device.org_id == org.id
    ).order_by(Device.created_at.desc()).all()

    return {
        "devices": [
            {
                "device_id": d.device_id,
                "friendly_name": d.friendly_name,
                "status": d.status,
                "created_at": d.created_at,
                "last_seen_at": d.last_seen_at,
                "device_version": d.device_version,
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                }
            }
            for d in devices
        ],
        "total": len(devices)
    }


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Get details for a specific device."""
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id  # Ensure user owns this device
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    return {
        "device_id": device.device_id,
        "friendly_name": device.friendly_name,
        "status": device.status,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
        "device_version": device.device_version,
        "organization": {
            "id": str(org.id),
            "name": org.name,
        }
    }


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: str,
    friendly_name: Optional[str] = None,
    status: Optional[str] = None,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Update device settings.

    Can update:
    - friendly_name: Display name for the device
    - status: 'active' or 'inactive'
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Update fields if provided
    if friendly_name is not None:
        device.friendly_name = friendly_name

    if status is not None:
        if status not in ["active", "inactive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'active' or 'inactive'"
            )
        device.status = status

    db.commit()
    db.refresh(device)

    return {
        "device_id": device.device_id,
        "friendly_name": device.friendly_name,
        "status": device.status,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
        "device_version": device.device_version,
        "organization": {
            "id": str(org.id),
            "name": org.name,
        }
    }


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Delete a device.

    **Warning**: This will also delete all captures associated with this device!
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    db.delete(device)
    db.commit()

    return None

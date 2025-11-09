"""Device management and provisioning endpoints."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from cloud.api.database import get_db, Device, Organization, User
from cloud.api.database.models import ActivationCode, CodeRedemption
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


# New models for device validation and activation
class DeviceValidationRequest(BaseModel):
    device_id: str


class DeviceValidationResponse(BaseModel):
    device_id: str
    status: str  # "available", "already_activated_by_you", etc.
    can_activate: bool
    message: str


class DeviceActivationRequest(BaseModel):
    device_id: str
    friendly_name: Optional[str] = None
    activation_code: Optional[str] = None  # Optional activation code


class CodeBenefitResponse(BaseModel):
    code: str
    benefit: str
    expires_at: Optional[datetime] = None


class DeviceActivationResponse(BaseModel):
    device_id: str
    friendly_name: str
    api_key: str  # ONE TIME ONLY
    status: str
    activated_at: datetime
    code_benefit: Optional[CodeBenefitResponse] = None
    organization: dict


# Device Configuration Models
class TriggerConfig(BaseModel):
    """Trigger configuration for device."""
    enabled: bool = False
    interval_seconds: int = 10
    digital_input_enabled: bool = False


class NotificationConfig(BaseModel):
    """Notification configuration for device."""
    email_enabled: bool = True
    email_addresses: List[str] = []
    email_cooldown_minutes: int = 10
    digital_output_enabled: bool = False


class DeviceConfig(BaseModel):
    """Complete device configuration."""
    normal_description: Optional[str] = None
    trigger: Optional[TriggerConfig] = None
    notification: Optional[NotificationConfig] = None


class DeviceConfigResponse(BaseModel):
    """Response for device config endpoints."""
    device_id: str
    config: dict  # Will contain DeviceConfig data as dict
    last_updated: Optional[str] = None


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
        created_at=datetime.now(timezone.utc)
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
            "name": org.name,
        }
    }


# === DEVICE VALIDATION AND ACTIVATION (must come before /{device_id} wildcard) ===

@router.post("/validate", response_model=DeviceValidationResponse)
def validate_device(
    request: DeviceValidationRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate device ID before activation.

    This endpoint checks:
    1. Device ID exists in database
    2. Device not already activated
    3. Device ID format is correct

    Does NOT check subscription status (that happens at activation).

    Use this to provide immediate feedback before asking for payment.
    """
    import re

    # Validate format (5 uppercase alphanumeric characters)
    if not re.match(r'^[A-Z0-9]{5}$', request.device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format. Must be 5 uppercase alphanumeric characters."
        )

    # Look up device
    device = db.query(Device).filter(
        Device.device_id == request.device_id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device ID not found. Please check the ID on your camera sticker."
        )

    # Check if already activated
    if device.org_id is not None:
        # Already activated by some organization
        if device.org_id == org.id:
            # User trying to re-activate their own device
            return DeviceValidationResponse(
                device_id=device.device_id,
                status="already_activated_by_you",
                can_activate=False,
                message=f"This device is already activated as '{device.friendly_name}'"
            )
        else:
            # Activated by different organization
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device already activated by another user. Contact support@visant.com if this is your device."
            )

    # Device available!
    return DeviceValidationResponse(
        device_id=device.device_id,
        status="available",
        can_activate=True,
        message="Device ready to activate"
    )


def validate_and_apply_activation_code(
    code: str,
    org: Organization,
    user: User,
    device_id: str,
    db: Session
) -> Dict:
    """
    Validate activation code and apply benefits.

    Returns:
        Dict with code, benefit description, and expiration

    Raises:
        HTTPException if code invalid/expired/used
    """
    # Look up code
    activation_code = db.query(ActivationCode).filter(
        ActivationCode.code == code.upper()
    ).first()

    if not activation_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activation code not found"
        )

    if not activation_code.active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Activation code is no longer active"
        )

    # Check expiration
    now = datetime.now(timezone.utc)

    # Make database datetimes timezone-aware for comparison
    if activation_code.valid_from:
        valid_from = activation_code.valid_from.replace(tzinfo=timezone.utc) if activation_code.valid_from.tzinfo is None else activation_code.valid_from
        if now < valid_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation code not yet valid"
            )

    if activation_code.valid_until:
        valid_until = activation_code.valid_until.replace(tzinfo=timezone.utc) if activation_code.valid_until.tzinfo is None else activation_code.valid_until
        if now > valid_until:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Activation code expired"
            )

    # Check usage limit
    if activation_code.max_uses:
        if activation_code.uses_count >= activation_code.max_uses:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Activation code usage limit reached"
            )

    # Check if user already used this code
    if activation_code.one_per_user:
        existing = db.query(CodeRedemption).filter(
            CodeRedemption.code == code.upper(),
            CodeRedemption.org_id == org.id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already used this activation code"
            )

    # Apply benefits based on type
    benefit_description = ""
    benefit_expires_at = None

    if activation_code.benefit_type == "free_months":
        months = activation_code.benefit_value
        benefit_expires_at = now + timedelta(days=30 * months)

        # Grant subscription until expiry
        if not org.subscription_status or org.subscription_status == "free":
            org.subscription_status = "active"
            org.subscription_plan_id = "starter"  # Default to starter
            org.allowed_devices = 1

        # Extend subscription end date
        org.code_benefit_ends_at = benefit_expires_at

        benefit_description = f"{months} months free subscription"

    elif activation_code.benefit_type == "device_slots":
        slots = activation_code.benefit_value
        org.code_granted_devices += slots
        org.allowed_devices += slots
        benefit_description = f"{slots} additional device slots"

    elif activation_code.benefit_type == "trial_extension":
        days = activation_code.benefit_value
        benefit_expires_at = now + timedelta(days=days)
        benefit_description = f"{days} days trial extension"

    # Record redemption
    redemption = CodeRedemption(
        code=activation_code.code,
        org_id=org.id,
        user_id=user.id,
        device_id=device_id,
        benefit_applied=benefit_description,
        benefit_expires_at=benefit_expires_at
    )

    # Increment usage count
    activation_code.uses_count += 1

    db.add(redemption)

    return {
        "code": activation_code.code,
        "benefit": benefit_description,
        "expires_at": benefit_expires_at.isoformat() if benefit_expires_at else None
    }


@router.post("/activate", response_model=DeviceActivationResponse)
def activate_device(
    request: DeviceActivationRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate device with optional activation code.

    Authorization options:
    1. Valid activation code (no payment required)
    2. Active subscription (Phase 7 - payment)

    If neither, returns 402 Payment Required.

    **Important**: The device API key is only returned once during activation.
    Store it securely and configure your device to use it.
    """
    # 1. Validate device exists and available
    device = db.query(Device).filter(
        Device.device_id == request.device_id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    if device.org_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already activated"
        )

    # 2. Check authorization (subscription OR activation code)
    has_subscription = org.subscription_status == "active"
    has_code = request.activation_code is not None

    code_benefit = None

    if has_code:
        # Validate and apply activation code
        code_benefit = validate_and_apply_activation_code(
            code=request.activation_code,
            org=org,
            user=user,
            device_id=request.device_id,
            db=db
        )
        # Code is valid, grants benefits

    elif has_subscription:
        # Check device limit
        if org.active_devices_count >= org.allowed_devices:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Device limit reached ({org.allowed_devices}). Upgrade plan or use activation code."
            )

    else:
        # No subscription and no code
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Please subscribe or use an activation code to activate devices"
        )

    # 3. Activate device
    device.org_id = org.id
    device.activated_by_user_id = user.id
    device.activated_at = datetime.now(timezone.utc)
    device.status = "active"
    device.friendly_name = request.friendly_name or request.device_id.replace('-', ' ').title()
    device.api_key = generate_device_api_key()

    # 4. Update organization counts
    org.active_devices_count += 1

    db.commit()
    db.refresh(device)
    db.refresh(org)

    # 5. Return response
    response = {
        "device_id": device.device_id,
        "friendly_name": device.friendly_name,
        "api_key": device.api_key,
        "status": device.status,
        "activated_at": device.activated_at,
        "organization": {
            "name": org.name,
        }
    }

    if code_benefit:
        response["code_benefit"] = CodeBenefitResponse(
            code=code_benefit["code"],
            benefit=code_benefit["benefit"],
            expires_at=code_benefit["expires_at"]
        )

    return response


# === DEVICE CRUD OPERATIONS ===

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


# Device Configuration Endpoints (MUST be before wildcard routes)
@router.get("/{device_id}/config", response_model=DeviceConfigResponse)
def get_device_config(
    device_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Get device configuration.

    Returns the device's complete config including:
    - normal_description: AI classification reference
    - trigger: Recurring trigger settings
    - notification: Email notification settings

    If no config has been saved, returns default values.
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id,
        Device.status == "active"
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Return config (defaults to empty dict if not set)
    config = device.config or {}

    # Ensure config has default structure
    if "trigger" not in config:
        config["trigger"] = {"enabled": False, "interval_seconds": 10, "digital_input_enabled": False}
    if "notification" not in config:
        config["notification"] = {"email_enabled": True, "email_addresses": [], "email_cooldown_minutes": 10, "digital_output_enabled": False}

    return {
        "device_id": device.device_id,
        "config": config,
        "last_updated": None  # TODO: Add updated_at field to Device model for config tracking
    }


@router.put("/{device_id}/config", response_model=DeviceConfigResponse)
def update_device_config(
    device_id: str,
    config: DeviceConfig,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Update device configuration.

    Accepts partial updates - only provided fields will be updated.
    Existing config is merged with new values.

    Examples:
    - Update only normal description: {"normal_description": "..."}
    - Update only trigger: {"trigger": {"enabled": true, "interval_seconds": 15}}
    - Update multiple: {"normal_description": "...", "trigger": {...}, "notification": {...}}
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id,
        Device.status == "active"
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Get current config or initialize empty dict
    current_config = device.config or {}

    # Update config with new values (only fields that were provided)
    config_update = config.dict(exclude_unset=True)

    # Merge top-level fields
    if "normal_description" in config_update:
        current_config["normal_description"] = config_update["normal_description"]

    # Merge trigger config
    if "trigger" in config_update and config_update["trigger"] is not None:
        if "trigger" not in current_config:
            current_config["trigger"] = {}
        current_config["trigger"].update(config_update["trigger"])

    # Merge notification config
    if "notification" in config_update and config_update["notification"] is not None:
        if "notification" not in current_config:
            current_config["notification"] = {}
        current_config["notification"].update(config_update["notification"])

    # Save updated config
    device.config = current_config
    flag_modified(device, 'config')  # Mark JSON column as modified for SQLAlchemy

    db.commit()
    db.refresh(device)

    return {
        "device_id": device.device_id,
        "config": device.config,
        "last_updated": None  # TODO: Add updated_at field to Device model for config tracking
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



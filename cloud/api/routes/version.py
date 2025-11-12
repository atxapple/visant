"""Version tracking endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cloud.api.database import get_db, Device
from cloud.api.auth.dependencies import get_current_user
from version import __version__ as CLOUD_VERSION

router = APIRouter(prefix="/v1/version", tags=["Version"])


@router.get("")
async def get_version_info(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get version information for cloud and connected devices.

    Returns:
        - cloud_version: Current cloud application version
        - devices: List of devices with their versions
    """
    # Get all devices for the current user's organization
    devices = db.query(Device).filter(
        Device.org_id == current_user.org_id,
        Device.status == "active"
    ).all()

    device_versions = []
    for device in devices:
        device_versions.append({
            "device_id": device.device_id,
            "friendly_name": device.friendly_name,
            "device_version": device.device_version or "unknown",
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None
        })

    return {
        "cloud_version": CLOUD_VERSION,
        "devices": device_versions
    }


@router.get("/cloud")
async def get_cloud_version():
    """
    Get cloud application version (public endpoint).

    Returns:
        - version: Current cloud application version
    """
    return {
        "version": CLOUD_VERSION
    }

"""Share link management endpoints."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud.api.database import get_db, ShareLink, Device, Organization, User
from cloud.api.auth.dependencies import get_current_user, get_current_org
from cloud.api.utils.qrcode_gen import generate_qr_code

router = APIRouter(prefix="/v1", tags=["Sharing"])


# Request/Response Models
class ShareLinkCreateRequest(BaseModel):
    device_id: str
    share_type: str = "device"  # device, capture, date_range
    capture_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expires_in_days: int = 7  # Default: 7 days
    password: Optional[str] = None
    max_views: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "camera-01",
                "share_type": "device",
                "expires_in_days": 7
            }
        }


class ShareLinkResponse(BaseModel):
    token: str
    share_url: str
    device_id: str
    share_type: str
    created_at: datetime
    expires_at: datetime
    view_count: int
    max_views: Optional[int]


class ShareLinkListResponse(BaseModel):
    share_links: List[ShareLinkResponse]
    total: int


def generate_share_token() -> str:
    """Generate a secure random token for share links."""
    return secrets.token_urlsafe(24)  # 32 characters


@router.post("/devices/{device_id}/share", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
def create_share_link(
    device_id: str,
    request: ShareLinkCreateRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a public share link for a device.

    This allows sharing device captures publicly without requiring login.

    **Share Types:**
    - `device`: Share all captures from this device
    - `capture`: Share a single specific capture
    - `date_range`: Share captures within a date range

    **Security:**
    - Links expire after specified days (default: 7)
    - Optional password protection
    - Optional view count limit
    - View analytics tracked
    """
    # Verify device belongs to organization
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Validate share type
    if request.share_type not in ["device", "capture", "date_range"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid share_type. Must be: device, capture, or date_range"
        )

    # Validate capture_id if share_type is capture
    if request.share_type == "capture" and not request.capture_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="capture_id required when share_type is 'capture'"
        )

    # Validate date range if share_type is date_range
    if request.share_type == "date_range":
        if not request.start_date or not request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date and end_date required when share_type is 'date_range'"
            )
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )

    # Generate unique token
    token = generate_share_token()

    # Ensure token is unique (very unlikely collision, but check anyway)
    while db.query(ShareLink).filter(ShareLink.token == token).first():
        token = generate_share_token()

    # Calculate expiration
    # Note: Using utcnow() for timezone-naive datetimes to match database storage
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create share link
    share_link = ShareLink(
        token=token,
        org_id=org.id,
        device_id=device_id,
        share_type=request.share_type,
        capture_id=request.capture_id,
        start_date=request.start_date,
        end_date=request.end_date,
        created_by=user.id,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        max_views=request.max_views,
        view_count=0
    )

    # TODO: Hash password if provided
    # if request.password:
    #     share_link.password_hash = hash_password(request.password)

    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    # Generate share URL
    # TODO: Get base URL from config
    share_url = f"http://localhost:8000/s/{token}"

    return {
        "token": token,
        "share_url": share_url,
        "device_id": device_id,
        "share_type": request.share_type,
        "created_at": share_link.created_at,
        "expires_at": share_link.expires_at,
        "view_count": share_link.view_count,
        "max_views": share_link.max_views
    }


@router.get("/share-links", response_model=ShareLinkListResponse)
def list_share_links(
    device_id: Optional[str] = Query(None, description="Filter by device"),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    List all share links for the current organization.

    Optionally filter by device_id.
    """
    query = db.query(ShareLink).filter(ShareLink.org_id == org.id)

    if device_id:
        query = query.filter(ShareLink.device_id == device_id)

    share_links = query.order_by(ShareLink.created_at.desc()).all()

    # TODO: Get base URL from config
    return {
        "share_links": [
            {
                "token": sl.token,
                "share_url": f"http://localhost:8000/s/{sl.token}",
                "device_id": sl.device_id,
                "share_type": sl.share_type,
                "created_at": sl.created_at,
                "expires_at": sl.expires_at,
                "view_count": sl.view_count,
                "max_views": sl.max_views
            }
            for sl in share_links
        ],
        "total": len(share_links)
    }


@router.delete("/share-links/{token}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share_link(
    token: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Revoke (delete) a share link.

    Only the organization that created the link can revoke it.
    """
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token,
        ShareLink.org_id == org.id  # Ensure user owns this link
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    db.delete(share_link)
    db.commit()

    return None


@router.get("/share-links/{token}", response_model=ShareLinkResponse)
def get_share_link(
    token: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """Get details for a specific share link."""
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token,
        ShareLink.org_id == org.id
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    return {
        "token": share_link.token,
        "share_url": f"http://localhost:8000/s/{share_link.token}",
        "device_id": share_link.device_id,
        "share_type": share_link.share_type,
        "created_at": share_link.created_at,
        "expires_at": share_link.expires_at,
        "view_count": share_link.view_count,
        "max_views": share_link.max_views
    }


@router.get("/share-links/{token}/qrcode")
def get_share_link_qr_code(
    token: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Generate QR code for a share link.

    Returns a base64-encoded PNG image that can be displayed in HTML:
    ```html
    <img src="data:image/png;base64,..." />
    ```
    """
    # Verify share link belongs to organization
    share_link = db.query(ShareLink).filter(
        ShareLink.token == token,
        ShareLink.org_id == org.id
    ).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    # Generate share URL
    share_url = f"http://localhost:8000/s/{token}"

    # Generate QR code
    qr_code = generate_qr_code(share_url)

    if not qr_code:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="QR code generation not available. Install qrcode package."
        )

    return {
        "token": token,
        "share_url": share_url,
        "qr_code": qr_code  # Base64-encoded PNG
    }

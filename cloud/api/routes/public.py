"""Public gallery endpoints (no authentication required)."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from cloud.api.database import get_db, ShareLink, Device, Capture, Organization, AlertDefinition
from cloud.api.storage.presigned import generate_presigned_url
from fastapi import Depends
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Public"])

# Path to camera dashboard template
CAMERA_DASHBOARD_HTML = Path(__file__).parent.parent.parent / "web" / "templates" / "camera_dashboard.html"

# Response Models
class PublicCaptureResponse(BaseModel):
    record_id: str
    captured_at: datetime
    state: str
    score: Optional[float]
    reason: Optional[str]
    image_url: str  # Pre-signed S3 URL
    thumbnail_url: Optional[str]


class PublicGalleryResponse(BaseModel):
    device_name: str
    organization_name: str
    captures: List[PublicCaptureResponse]
    total: int
    share_type: str
    expires_at: datetime


class UpdatePromptRequest(BaseModel):
    description: str


@router.get("/s/{token}", response_class=HTMLResponse)
async def public_gallery_html(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public gallery page - renders same UI as authenticated camera dashboard.
    """
    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        return HTMLResponse(
            content="<h1>Share Link Not Found</h1><p>This share link does not exist or has been revoked.</p>",
            status_code=404
        )

    # Check if expired
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if share_link.expires_at < current_time:
        return HTMLResponse(
            content=f"<h1>Share Link Expired</h1><p>This share link expired on {share_link.expires_at.strftime('%Y-%m-%d %H:%M')} UTC.</p>",
            status_code=410
        )

    # Check view limit
    if share_link.max_views and share_link.view_count >= share_link.max_views:
        return HTMLResponse(
            content="<h1>View Limit Reached</h1><p>This share link has reached its maximum view limit.</p>",
            status_code=410
        )

    # Increment view count
    share_link.view_count += 1
    share_link.last_viewed_at = current_time
    db.commit()

    # Get device and organization info
    device = db.query(Device).filter(Device.device_id == share_link.device_id).first()
    org = db.query(Organization).filter(Organization.id == share_link.org_id).first()

    # Read the HTML template
    html_content = CAMERA_DASHBOARD_HTML.read_text(encoding="utf-8")

    # Replace Jinja2 template variables with actual values
    replacements = {
        "{{ 'true' if is_public_share else 'false' }}": "true",
        "{% if is_public_share %}": "<!-- PUBLIC_SHARE_START -->",
        "{% else %}": "<!-- PUBLIC_SHARE_ELSE -->",
        "{% endif %}": "<!-- PUBLIC_SHARE_END -->",
        "{{ device_name }}": device.friendly_name if device else "Unknown Device",
        "{{ organization_name }}": org.name if org else "Unknown Organization",
        "{{ share_expires_at }}": share_link.expires_at.strftime('%Y-%m-%d %H:%M UTC'),
        "{{ share_token if is_public_share else '' }}": token,
        "{{ 'true' if (is_public_share and allow_edit_prompt) else 'false' }}": "true" if share_link.allow_edit_prompt else "false",
        '{% if not is_public_share or (is_public_share and allow_edit_prompt) %}': "<!-- SETTINGS_START -->" if share_link.allow_edit_prompt else "<!-- SETTINGS_SKIP ",
        "{% if is_public_share %}ALERT CONDITION{% else %}CAMERA SETTINGS{% endif %}": "ALERT CONDITION" if share_link.allow_edit_prompt else "",
        "{% if not is_public_share %}": "<!-- AUTH_ONLY_START ",
        '{{ device_id }}': share_link.device_id,
        "{{ 'true' if is_public_share else 'false' }}": "true",
    }

    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    return HTMLResponse(content=html_content)


@router.get("/api/s/{token}", response_model=PublicGalleryResponse)
def public_gallery_api(
    token: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Public gallery API endpoint - JSON response.

    This allows building custom frontends on top of shared data.
    No authentication required.
    """
    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    # Check if expired
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if share_link.expires_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )

    # Check view limit
    if share_link.max_views and share_link.view_count >= share_link.max_views:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link view limit reached"
        )

    # Increment view count
    share_link.view_count += 1
    share_link.last_viewed_at = current_time
    db.commit()

    # Get device and organization info
    device = db.query(Device).filter(Device.device_id == share_link.device_id).first()
    org = db.query(Organization).filter(Organization.id == share_link.org_id).first()

    # Get captures based on share type
    # Only show completed evaluations in public API
    captures_query = db.query(Capture).filter(
        Capture.device_id == share_link.device_id,
        Capture.org_id == share_link.org_id,
        Capture.evaluation_status == "completed"  # Filter out pending/processing
    )

    if share_link.share_type == "capture":
        captures_query = captures_query.filter(Capture.record_id == share_link.capture_id)
    elif share_link.share_type == "date_range":
        captures_query = captures_query.filter(
            and_(
                Capture.captured_at >= share_link.start_date,
                Capture.captured_at <= share_link.end_date
            )
        )

    # Count total
    total = captures_query.count()

    # Get paginated results
    captures = captures_query.order_by(
        Capture.captured_at.desc()
    ).limit(limit).offset(offset).all()

    # Format response with pre-signed URLs
    captures_data = []
    for c in captures:
        # Generate pre-signed URLs (1 hour expiry)
        image_url = generate_presigned_url(c.s3_image_key, expiration=3600) if c.s3_image_key else None
        thumbnail_url = generate_presigned_url(c.s3_thumbnail_key, expiration=3600) if c.s3_thumbnail_key else None

        captures_data.append({
            "record_id": c.record_id,
            "captured_at": c.captured_at,
            "state": c.state,
            "score": c.score,
            "reason": c.reason,
            "image_url": image_url or f"https://placeholder.com/image/{c.record_id}",
            "thumbnail_url": thumbnail_url
        })

    return {
        "device_name": device.friendly_name if device else "Unknown Device",
        "organization_name": org.name if org else "Unknown Organization",
        "captures": captures_data,
        "total": total,
        "share_type": share_link.share_type,
        "expires_at": share_link.expires_at
    }


@router.post("/s/{token}/update-prompt")
async def update_prompt_via_share(
    token: str,
    payload: UpdatePromptRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update alert definition (prompt) via public share link.

    Only works if the share link has allow_edit_prompt=True.
    """
    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    # Check if expired
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if share_link.expires_at < current_time:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )

    # Check if prompt editing is allowed
    if not share_link.allow_edit_prompt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This share link does not allow prompt editing"
        )

    description = payload.description.strip()
    device_id = share_link.device_id

    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    logger.info(
        "Updating alert definition via share link %s for device %s: description_length=%d",
        token,
        device_id,
        len(description),
    )

    # Get current max version for this device
    max_version_row = db.query(AlertDefinition).filter(
        AlertDefinition.device_id == device_id
    ).order_by(AlertDefinition.version.desc()).first()

    new_version = (max_version_row.version + 1) if max_version_row else 1

    # Mark all existing definitions for this device as inactive
    db.query(AlertDefinition).filter(
        AlertDefinition.device_id == device_id
    ).update({"is_active": False})

    # Create new alert definition
    # Track that this was created via public share
    created_by = f"share:{token}"

    new_definition = AlertDefinition(
        id=uuid.uuid4(),
        device_id=device_id,
        version=new_version,
        description=description,
        created_at=datetime.now(timezone.utc),
        created_by=created_by,
        is_active=True
    )

    db.add(new_definition)
    db.commit()
    db.refresh(new_definition)

    # Update cache
    definition_cache = getattr(request.app.state, 'device_definitions', {})
    definition_cache[device_id] = (new_definition.id, description)
    request.app.state.device_definitions = definition_cache

    # Update classifier if available
    classifier = getattr(request.app.state, "classifier", None)
    if classifier:
        try:
            from cloud.web.routes import _apply_normal_description
            _apply_normal_description(classifier, description)
            logger.info("Updated classifier with new definition for device %s", device_id)
        except Exception as exc:
            logger.warning("Failed to update classifier: %s", exc)

    # Clear similarity cache for this device
    service = getattr(request.app.state, "service", None)
    if service is not None and hasattr(service, "similarity_cache"):
        similarity_cache = getattr(service, "similarity_cache", None)
        if similarity_cache is not None and hasattr(similarity_cache, "clear_device"):
            try:
                similarity_cache.clear_device(device_id)
                logger.info(
                    "Cleared similarity cache for device %s after definition update",
                    device_id
                )
            except Exception as exc:
                logger.warning("Failed to clear device similarity cache: %s", exc)

    return {
        "success": True,
        "definition_id": str(new_definition.id),
        "device_id": device_id,
        "version": new_version,
        "description": description,
        "created_at": new_definition.created_at.isoformat()
    }

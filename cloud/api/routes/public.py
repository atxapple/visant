"""Public gallery endpoints (no authentication required)."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from cloud.api.database import get_db, ShareLink, Device, Capture, Organization
from cloud.api.storage.presigned import generate_presigned_url
from fastapi import Depends

router = APIRouter(tags=["Public"])


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


@router.get("/s/{token}", response_class=HTMLResponse)
async def public_gallery_html(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public gallery page - HTML view.

    This is the viral growth page that anyone can access without login.
    """
    # For now, return a simple HTML page
    # TODO: Create proper Jinja2 template

    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Link Not Found</title></head>
                <body>
                    <h1>Share Link Not Found</h1>
                    <p>This share link does not exist or has been revoked.</p>
                </body>
            </html>
            """,
            status_code=404
        )

    # Check if expired
    # Note: Database stores UTC times as timezone-naive, so use utcnow() for comparison
    if share_link.expires_at < datetime.utcnow():
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Link Expired</title></head>
                <body>
                    <h1>Share Link Expired</h1>
                    <p>This share link expired on {share_link.expires_at.strftime('%Y-%m-%d %H:%M')} UTC.</p>
                </body>
            </html>
            """,
            status_code=410
        )

    # Check view limit
    if share_link.max_views and share_link.view_count >= share_link.max_views:
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>View Limit Reached</title></head>
                <body>
                    <h1>View Limit Reached</h1>
                    <p>This share link has reached its maximum view limit.</p>
                </body>
            </html>
            """,
            status_code=410
        )

    # Increment view count
    share_link.view_count += 1
    share_link.last_viewed_at = datetime.utcnow()
    db.commit()

    # Get device and organization info
    device = db.query(Device).filter(Device.device_id == share_link.device_id).first()
    org = db.query(Organization).filter(Organization.id == share_link.org_id).first()

    # Get captures based on share type
    # Only show completed evaluations in public gallery
    captures_query = db.query(Capture).filter(
        Capture.device_id == share_link.device_id,
        Capture.org_id == share_link.org_id,
        Capture.evaluation_status == "completed"  # Filter out pending/processing captures
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

    captures = captures_query.order_by(Capture.captured_at.desc()).limit(50).all()

    # Generate simple HTML gallery
    captures_html = ""
    if captures:
        for capture in captures:
            # Generate pre-signed URL for image (1 hour expiry)
            image_url = None
            if capture.s3_image_key:
                image_url = generate_presigned_url(capture.s3_image_key, expiration=3600)

            # Generate thumbnail URL
            thumbnail_url = None
            if capture.s3_thumbnail_key:
                thumbnail_url = generate_presigned_url(capture.s3_thumbnail_key, expiration=3600)

            # Use thumbnail if available, otherwise full image
            display_url = thumbnail_url or image_url

            captures_html += f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin: 10px; border-radius: 8px;">
                {f'<img src="{display_url}" style="max-width: 100%; height: auto; border-radius: 4px; margin-bottom: 10px;" />' if display_url else ''}
                <p><strong>Captured:</strong> {capture.captured_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>State:</strong> <span style="color: {'green' if capture.state == 'normal' else 'red'};">{capture.state}</span></p>
                <p><strong>Score:</strong> {capture.score or 'N/A'}</p>
                {f'<p><strong>Reason:</strong> {capture.reason}</p>' if capture.reason else ''}
            </div>
            """
    else:
        captures_html = "<p>No captures available yet.</p>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{device.friendly_name if device else 'Device'} - {org.name if org else 'Organization'}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .cta {{
                background: #007bff;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                text-decoration: none;
                display: inline-block;
                margin-top: 10px;
            }}
            .cta:hover {{
                background: #0056b3;
            }}
            .gallery {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                color: #666;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{device.friendly_name if device else 'Device Gallery'}</h1>
            <p style="color: #666;">{org.name if org else 'Organization'}</p>
            <p style="font-size: 14px; color: #999;">
                Shared via Visant • Expires: {share_link.expires_at.strftime('%Y-%m-%d %H:%M')} UTC
            </p>
            <a href="http://localhost:8000/docs" class="cta">
                🚀 Get Visant for Your Cameras
            </a>
        </div>

        <div class="gallery">
            <h2>Recent Captures ({len(captures)})</h2>
            {captures_html}
        </div>

        <div class="footer">
            <p>Powered by <strong>Visant</strong> - AI-Powered Camera Monitoring</p>
            <p>
                <a href="http://localhost:8000/docs">Sign Up Free</a> •
                <a href="http://localhost:8000/docs">Learn More</a>
            </p>
        </div>
    </body>
    </html>
    """

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
    if share_link.expires_at < datetime.now(timezone.utc):
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
    share_link.last_viewed_at = datetime.utcnow()
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

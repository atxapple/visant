"""Capture upload and management endpoints."""

import uuid
import base64
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud.api.database import get_db, Capture, Device, Organization
from cloud.api.auth.dependencies import verify_device_by_id, get_current_org
from cloud.api.service import InferenceService
from cloud.api.workers.ai_evaluator import evaluate_capture_async
from cloud.datalake.storage import _generate_thumbnail

router = APIRouter(prefix="/v1/captures", tags=["Captures"])

# Storage configuration
from cloud.api.storage.config import UPLOADS_DIR


def save_capture_image(org_id: str, device_id: str, record_id: str, image_bytes: bytes) -> tuple[str, Optional[str]]:
    """
    Save capture image and thumbnail to local filesystem.

    Storage structure:
    - Image: uploads/{org_id}/devices/{device_id}/captures/{record_id}.jpg
    - Thumbnail: uploads/{org_id}/devices/{device_id}/captures/{record_id}_thumb.jpg

    Returns:
        Tuple of (image_path, thumbnail_path) where thumbnail_path is None if generation failed.
    """
    # Create directory structure
    device_dir = UPLOADS_DIR / str(org_id) / "devices" / device_id / "captures"
    device_dir.mkdir(parents=True, exist_ok=True)

    # Save full image
    image_path = device_dir / f"{record_id}.jpg"
    image_path.write_bytes(image_bytes)

    # Generate and save thumbnail
    thumbnail_path = None
    try:
        thumbnail_bytes = _generate_thumbnail(image_bytes, max_size=(400, 300), quality=85)
        thumb_path = device_dir / f"{record_id}_thumb.jpg"
        thumb_path.write_bytes(thumbnail_bytes)
        thumbnail_path = str(thumb_path.relative_to(UPLOADS_DIR))
    except Exception as e:
        # Log warning but don't fail the upload
        print(f"Warning: Failed to generate thumbnail for {record_id}: {e}")

    # Return relative paths from uploads root
    return str(image_path.relative_to(UPLOADS_DIR)), thumbnail_path


# Request/Response Models
class CaptureUploadRequest(BaseModel):
    """Capture metadata for upload (Cloud AI - no state/score/reason from device)."""
    device_id: str
    captured_at: datetime
    image_base64: str  # Base64-encoded image for Cloud AI evaluation
    trigger_id: Optional[str] = None  # NEW: Cloud-managed trigger ID
    trigger_label: Optional[str] = None  # Legacy: device-generated label
    metadata: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "camera-01",
                "captured_at": "2025-11-07T12:00:00Z",
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "trigger_id": "sched_camera-01_20251107_120000_123456",
                "trigger_label": "motion_detected",
                "metadata": {"temperature": 22.5}
            }
        }


class CaptureResponse(BaseModel):
    record_id: str
    device_id: str
    captured_at: datetime
    ingested_at: datetime
    evaluation_status: str  # pending, processing, completed, failed
    state: Optional[str]  # null until evaluation completes
    score: Optional[float]
    reason: Optional[str]
    evaluated_at: Optional[datetime]
    image_stored: bool
    thumbnail_stored: bool


class CaptureListResponse(BaseModel):
    captures: List[CaptureResponse]
    total: int


@router.post("", response_model=CaptureResponse, status_code=status.HTTP_201_CREATED)
async def upload_capture(
    request: CaptureUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Upload a new capture from a device (Cloud AI - async evaluation).

    **Authentication**: Device ID only (no API key required).

    Security validations:
    - Device must exist in database
    - Device must be activated (status="active")
    - Device must belong to an active organization

    **Process (Cloud AI)**:
    1. Validates device_id from request
    2. Decodes image from base64
    3. Creates capture record with evaluation_status="pending"
    4. Triggers background AI evaluation
    5. Returns immediately with record_id (device should poll for results)

    **Device Flow**:
    1. Upload image + metadata → Get record_id, status="pending"
    2. Poll GET /v1/captures/{record_id}/status until status="completed"
    3. Get final state/score/reason from poll response

    **Device Authentication**:
    No Authorization header required. Device is validated by device_id in request body.
    ```json
    {
      "device_id": "TEST1",
      "captured_at": "2025-11-08T12:00:00Z",
      "image_base64": "...",
      "trigger_label": "motion"
    }
    ```
    """
    # Validate device by device_id
    device = verify_device_by_id(request.device_id, db)

    # Decode image from base64
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}"
        )

    # Generate unique record_id
    record_id = f"{device.device_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Create capture record with pending evaluation
    # Get the current alert definition from cache
    from cloud.api.server import get_alert_definition_cache

    definition_cache = get_alert_definition_cache()
    alert_definition_id = None
    if device.device_id in definition_cache:
        alert_definition_id, _ = definition_cache[device.device_id]

    capture = Capture(
        record_id=record_id,
        org_id=device.org_id,  # Automatically set from device's org
        device_id=device.device_id,
        captured_at=request.captured_at,
        ingested_at=datetime.now(timezone.utc),
        trigger_label=request.trigger_label,
        capture_metadata=request.metadata or {},
        # Link to alert definition that was active when capture was created
        alert_definition_id=alert_definition_id,
        # Cloud AI fields - initially null/pending
        evaluation_status="pending",
        state=None,  # Will be set by Cloud AI
        score=None,
        reason=None,
        evaluated_at=None,
        # Image storage
        image_stored=True,  # We have the image bytes (not in S3 yet, but available)
        thumbnail_stored=False
    )

    db.add(capture)
    db.commit()
    db.refresh(capture)

    # Save image and thumbnail to local filesystem
    try:
        image_path, thumbnail_path = save_capture_image(
            org_id=str(device.org_id),
            device_id=device.device_id,
            record_id=record_id,
            image_bytes=image_bytes
        )

        # Update capture with image and thumbnail paths
        capture.s3_image_key = image_path
        capture.image_stored = True

        if thumbnail_path:
            capture.s3_thumbnail_key = thumbnail_path
            capture.thumbnail_stored = True

        db.commit()
        db.refresh(capture)
    except Exception as e:
        # Log error but don't fail the upload (evaluation can still proceed)
        print(f"Warning: Failed to save image to disk: {e}")
        capture.image_stored = False
        capture.thumbnail_stored = False
        db.commit()

    # Update device last_seen_at
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    # Get global InferenceService instance (set by test_auth_server.py or main server)
    # This is a workaround for dependency injection - in production use proper DI
    import cloud.api.routes.captures as captures_module
    inference_service = getattr(captures_module, 'global_inference_service', None)

    if inference_service is None:
        # Fallback: try to initialize with defaults (may not work without proper setup)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="InferenceService not initialized. Server configuration error."
        )

    # Mark trigger as executed if trigger_id provided (cloud-managed triggers)
    if request.trigger_id:
        try:
            # Get trigger scheduler from app state to mark trigger executed
            from cloud.api.server import get_trigger_scheduler
            trigger_scheduler = get_trigger_scheduler()
            if trigger_scheduler:
                trigger_scheduler.mark_trigger_executed(request.trigger_id, record_id, db)
        except Exception as e:
            # Log error but don't fail the upload
            print(f"Warning: Failed to mark trigger {request.trigger_id} as executed: {e}")

    # Trigger async AI evaluation in background
    # Note: Background task creates its own DB session (request session will be closed)
    background_tasks.add_task(
        evaluate_capture_async,
        record_id=record_id,
        image_bytes=image_bytes,
        inference_service=inference_service
    )

    return {
        "record_id": capture.record_id,
        "device_id": capture.device_id,
        "captured_at": capture.captured_at,
        "ingested_at": capture.ingested_at,
        "evaluation_status": capture.evaluation_status,
        "state": capture.state,  # None initially
        "score": capture.score,  # None initially
        "reason": capture.reason,  # None initially
        "evaluated_at": capture.evaluated_at,  # None initially
        "image_stored": capture.image_stored,
        "thumbnail_stored": capture.thumbnail_stored
    }


@router.get("", response_model=CaptureListResponse)
def list_captures(
    device_id: Optional[str] = Query(None, description="Filter by device"),
    state: Optional[str] = Query(None, description="Filter by state (normal, alert, uncertain)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    List captures for the authenticated user's organization.

    **Authentication**: Requires user JWT token.

    Returns captures filtered by organization, optionally by device and state.
    """
    # Base query - filter by organization
    query = db.query(Capture).filter(Capture.org_id == org.id)

    # Apply optional filters
    if device_id:
        query = query.filter(Capture.device_id == device_id)

    if state:
        if state not in ["normal", "alert", "uncertain"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state. Must be: normal, alert, or uncertain"
            )
        query = query.filter(Capture.state == state)

    # Count total
    total = query.count()

    # Get paginated results
    captures = query.order_by(
        Capture.captured_at.desc()
    ).limit(limit).offset(offset).all()

    return {
        "captures": [
            {
                "record_id": c.record_id,
                "device_id": c.device_id,
                "captured_at": c.captured_at,
                "ingested_at": c.ingested_at,
                "evaluation_status": c.evaluation_status,
                "state": c.state,
                "score": c.score,
                "reason": c.reason,
                "evaluated_at": c.evaluated_at,
                "image_stored": c.image_stored,
                "thumbnail_stored": c.thumbnail_stored
            }
            for c in captures
        ],
        "total": total
    }


@router.get("/{record_id}", response_model=CaptureResponse)
def get_capture(
    record_id: str,
    device_id: Optional[str] = Query(None, description="Device ID for authentication (no API key required)"),
    db: Session = Depends(get_db)
):
    """
    Get details for a specific capture.

    **Authentication**: Device ID only (from query parameter).

    Only returns captures from the authenticated device's organization.

    Usage:
        GET /v1/captures/{record_id}?device_id=TEST2
    """
    # Validate device by device_id if provided
    if device_id:
        device = verify_device_by_id(device_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="device_id query parameter required"
        )

    capture = db.query(Capture).filter(
        Capture.record_id == record_id,
        Capture.org_id == device.org_id  # Ensure org isolation
    ).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    return {
        "record_id": capture.record_id,
        "device_id": capture.device_id,
        "captured_at": capture.captured_at,
        "ingested_at": capture.ingested_at,
        "evaluation_status": capture.evaluation_status,
        "state": capture.state,
        "score": capture.score,
        "reason": capture.reason,
        "evaluated_at": capture.evaluated_at,
        "image_stored": capture.image_stored,
        "thumbnail_stored": capture.thumbnail_stored
    }


@router.get("/{record_id}/status", response_model=CaptureResponse)
def get_capture_status(
    record_id: str,
    device_id: Optional[str] = Query(None, description="Device ID for authentication (no API key required)"),
    db: Session = Depends(get_db)
):
    """
    Poll for capture evaluation status (for Cloud AI async flow).

    **Authentication**: Device ID only (from query parameter).

    **Device Polling Loop**:
    ```python
    # 1. Upload capture
    response = upload_capture(...)
    record_id = response["record_id"]

    # 2. Poll until evaluation completes
    while True:
        status = get_capture_status(record_id, device_id="TEST2")
        if status["evaluation_status"] == "completed":
            print(f"Result: {status['state']} ({status['score']})")
            break
        elif status["evaluation_status"] == "failed":
            print(f"Evaluation failed: {status['reason']}")
            break
        time.sleep(1)  # Wait 1 second before polling again
    ```

    **Returns**: Same as GET /{record_id} - full capture details with evaluation status

    Usage:
        GET /v1/captures/{record_id}/status?device_id=TEST2
    """
    # Validate device by device_id if provided
    if device_id:
        device = verify_device_by_id(device_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="device_id query parameter required"
        )

    capture = db.query(Capture).filter(
        Capture.record_id == record_id,
        Capture.org_id == device.org_id
    ).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    return {
        "record_id": capture.record_id,
        "device_id": capture.device_id,
        "captured_at": capture.captured_at,
        "ingested_at": capture.ingested_at,
        "evaluation_status": capture.evaluation_status,
        "state": capture.state,
        "score": capture.score,
        "reason": capture.reason,
        "evaluated_at": capture.evaluated_at,
        "image_stored": capture.image_stored,
        "thumbnail_stored": capture.thumbnail_stored
    }


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_capture(
    record_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Delete a capture.

    **Authentication**: Requires user JWT token.

    Only allows deleting captures from the authenticated user's organization.
    """
    capture = db.query(Capture).filter(
        Capture.record_id == record_id,
        Capture.org_id == org.id
    ).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    # TODO: Delete S3 images if they exist

    db.delete(capture)
    db.commit()

    return None


@router.post("/{record_id}/image", status_code=status.HTTP_200_OK)
async def upload_capture_image(
    record_id: str,
    image: UploadFile = File(...),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Upload image for a capture.

    **Authentication**: Requires user JWT token.

    **Process**:
    1. Validates capture belongs to user's org
    2. Uploads image to S3 (or local storage for dev)
    3. Updates capture.image_stored = True
    4. Returns S3 key

    **Future Enhancement**: Generate thumbnail automatically
    """
    # Verify capture exists and belongs to org
    capture = db.query(Capture).filter(
        Capture.record_id == record_id,
        Capture.org_id == org.id
    ).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    # TODO: Upload to S3
    # For now, just mark as stored
    # s3_key = f"{device.org_id}/devices/{device.device_id}/captures/{record_id}.jpg"
    # upload_to_s3(image, s3_key)

    # Update capture
    capture.image_stored = True
    # capture.s3_image_key = s3_key
    db.commit()

    return {
        "record_id": record_id,
        "image_stored": True,
        "message": "Image upload endpoint ready. S3 integration pending."
    }


@router.get("/{record_id}/thumbnail")
def get_capture_thumbnail(
    record_id: str,
    device_id: Optional[str] = Query(None, description="Device ID for authentication (no API key required)"),
    db: Session = Depends(get_db)
):
    """
    Get thumbnail image for a capture.

    **Authentication**: Device ID only (from query parameter).

    Returns the thumbnail image file (JPEG) if available.
    Falls back to generating thumbnail from full image if thumbnail file is missing.

    Usage:
        GET /v1/captures/{record_id}/thumbnail?device_id=TEST2
    """
    from fastapi.responses import FileResponse, Response

    # Validate device by device_id if provided
    if device_id:
        device = verify_device_by_id(device_id, db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="device_id query parameter required"
        )

    # Get capture
    capture = db.query(Capture).filter(
        Capture.record_id == record_id,
        Capture.org_id == device.org_id  # Ensure org isolation
    ).first()

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture not found"
        )

    # Check if thumbnail exists
    if capture.thumbnail_stored and capture.s3_thumbnail_key:
        thumbnail_path = UPLOADS_DIR / capture.s3_thumbnail_key

        if thumbnail_path.exists():
            return FileResponse(
                thumbnail_path,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=31536000"}  # 1 year cache
            )

    # Fallback: Generate thumbnail from full image on-demand
    if capture.image_stored and capture.s3_image_key:
        image_path = UPLOADS_DIR / capture.s3_image_key

        if image_path.exists():
            try:
                image_bytes = image_path.read_bytes()
                thumbnail_bytes = _generate_thumbnail(image_bytes, max_size=(400, 300), quality=85)

                return Response(
                    content=thumbnail_bytes,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000"}  # 1 year cache
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate thumbnail: {str(e)}"
                )

    # No image available
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Thumbnail not available"
    )

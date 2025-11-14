from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, List, Optional, Sequence, Set

from fastapi import APIRouter, HTTPException, Query, Request, Header, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import jwt
import os

from ..api.database import get_db
from ..api.email_service import create_sendgrid_service
from ..api.notification_settings import NotificationSettings, save_notification_settings
from ..api.persistent_config import update_trigger_config, update_active_normal_description
from .preferences import (
    CAPTURE_LIMIT_DEFAULT,
    CAPTURE_LIMIT_MAX,
    DEFAULT_CAPTURE_STATES,
    CaptureFilterPreferences,
    UIPreferences,
    load_preferences,
    save_preferences,
)
from .capture_utils import (
    CaptureSummary,
    find_capture_image,
    load_capture_summary,
    parse_capture_timestamp,
)
from version import __version__ as CLOUD_VERSION


logger = logging.getLogger(__name__)

router = APIRouter(tags=["ui"])

LOGIN_HTML = Path(__file__).parent / "templates" / "login.html"
SIGNUP_HTML = Path(__file__).parent / "templates" / "signup.html"
FORGOT_PASSWORD_HTML = Path(__file__).parent / "templates" / "forgot-password.html"
RESET_PASSWORD_HTML = Path(__file__).parent / "templates" / "reset-password.html"
CAMERAS_HTML = Path(__file__).parent / "templates" / "cameras.html"
CAMERA_DASHBOARD_HTML = Path(__file__).parent / "templates" / "camera_dashboard.html"
SHARES_HTML = Path(__file__).parent / "templates" / "shares.html"
DEVICES_HTML = Path(__file__).parent / "templates" / "devices.html"
SETTINGS_HTML = Path(__file__).parent / "templates" / "settings.html"
ADMIN_DEVICES_HTML = Path(__file__).parent / "templates" / "admin_devices.html"
ADMIN_CODES_HTML = Path(__file__).parent / "templates" / "admin_codes.html"
ADMIN_HTML = Path(__file__).parent / "templates" / "admin.html"
TIME_LOG_HTML = Path(__file__).parent / "templates" / "time_log.html"

# JWT verification for UI routes (optional - can be disabled for now)
# Set SUPABASE_JWT_SECRET environment variable to enable authentication
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


def verify_jwt_token(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Verify JWT token from Authorization header.
    Returns None if auth is disabled or token is invalid.
    """
    if not SUPABASE_JWT_SECRET:
        # Auth disabled - allow access
        return None

    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        # Verify and decode JWT
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Supabase doesn't use aud claim
        )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


MIN_TRIGGER_INTERVAL_SECONDS = 7.0


class NormalDescriptionPayload(BaseModel):
    description: str = Field(
        default="", description="Updated normal environment description"
    )
    device_id: str = Field(
        description="Device ID for which this definition applies"
    )


class TriggerConfigPayload(BaseModel):
    enabled: bool
    interval_seconds: Optional[float] = Field(
        default=None,
        ge=MIN_TRIGGER_INTERVAL_SECONDS,
        description="Interval in seconds",
    )


class NotificationSettingsPayload(BaseModel):
    email_enabled: bool
    email_recipients: List[str] = Field(
        default_factory=list, description="Notification email recipients"
    )
    email_cooldown_minutes: float = Field(
        default=10.0,
        ge=0.0,
        description="Minutes to wait before another abnormal alert",
    )


class PreferencesPayload(UIPreferences):
    capture_filters: CaptureFilterPreferences = Field(
        default_factory=CaptureFilterPreferences
    )


_ALLOWED_CAPTURE_STATES: Set[str] = set(DEFAULT_CAPTURE_STATES)
_MAX_CAPTURE_LIMIT = CAPTURE_LIMIT_MAX
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _serialize_capture_summary(summary: CaptureSummary, request: Request) -> dict[str, Any]:
    image_url = None
    download_url = None
    thumbnail_url = None
    if summary.image_available and summary.image_path is not None:
        image_route = request.url_for("serve_capture_image", record_id=summary.record_id)
        image_url = image_route.path or str(image_route)
        download_url = f"{image_url}?download=1"
        # Thumbnail URL (uses API endpoint)
        thumbnail_url = f"/v1/captures/{summary.record_id}/thumbnail"
    return {
        "record_id": summary.record_id,
        "captured_at": summary.captured_at,
        "ingested_at": summary.ingested_at,
        "state": summary.state,
        "score": summary.score,
        "reason": summary.reason,
        "trigger_label": summary.trigger_label,
        "normal_description_file": summary.normal_description_file,
        "image_available": summary.image_available,
        "image_url": image_url,
        "thumbnail_url": thumbnail_url,
        "download_url": download_url,
        "agent_details": summary.agent_details,
    }


def _get_preferences(request: Request) -> UIPreferences:
    prefs = getattr(request.app.state, "ui_preferences", None)
    if isinstance(prefs, UIPreferences):
        return prefs
    path = _preferences_path(request)
    prefs = load_preferences(path)
    request.app.state.ui_preferences = prefs
    return prefs


def _preferences_path(request: Request) -> Path:
    path = getattr(request.app.state, "ui_preferences_path", None)
    if path is None:
        path = Path("config/ui_preferences.json")
        request.app.state.ui_preferences_path = path
    return Path(path)


@router.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    """Login page - no authentication required."""
    if not LOGIN_HTML.exists():
        raise HTTPException(status_code=500, detail="Login template missing")
    return HTMLResponse(LOGIN_HTML.read_text(encoding="utf-8"))


@router.get("/signup", response_class=HTMLResponse)
async def signup_page() -> HTMLResponse:
    """Signup page - no authentication required."""
    if not SIGNUP_HTML.exists():
        raise HTTPException(status_code=500, detail="Signup template missing")
    return HTMLResponse(SIGNUP_HTML.read_text(encoding="utf-8"))


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page() -> HTMLResponse:
    """Forgot password page - enter email to receive reset instructions."""
    if not FORGOT_PASSWORD_HTML.exists():
        raise HTTPException(status_code=500, detail="Forgot password template missing")
    return HTMLResponse(FORGOT_PASSWORD_HTML.read_text(encoding="utf-8"))


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page() -> HTMLResponse:
    """Password reset page - accessed via email link."""
    if not RESET_PASSWORD_HTML.exists():
        raise HTTPException(status_code=500, detail="Reset password template missing")
    return HTMLResponse(RESET_PASSWORD_HTML.read_text(encoding="utf-8"))


@router.get("/ui/shares", response_class=HTMLResponse)
async def shares_page() -> HTMLResponse:
    """Share links management page."""
    if not SHARES_HTML.exists():
        raise HTTPException(status_code=500, detail="Shares template missing")
    return HTMLResponse(SHARES_HTML.read_text(encoding="utf-8"))


@router.get("/ui/devices", response_class=HTMLResponse)
async def devices_page() -> HTMLResponse:
    """Device management page."""
    if not DEVICES_HTML.exists():
        raise HTTPException(status_code=500, detail="Devices template missing")
    return HTMLResponse(DEVICES_HTML.read_text(encoding="utf-8"))


@router.get("/ui/profile/settings", response_class=HTMLResponse)
async def settings_page() -> HTMLResponse:
    """User profile settings page."""
    if not SETTINGS_HTML.exists():
        raise HTTPException(status_code=500, detail="Settings template missing")
    return HTMLResponse(SETTINGS_HTML.read_text(encoding="utf-8"))


@router.get("/ui/cameras", response_class=HTMLResponse)
async def cameras_page() -> HTMLResponse:
    """Camera selection page - shows grid of user's cameras."""
    if not CAMERAS_HTML.exists():
        raise HTTPException(status_code=500, detail="Cameras template missing")
    return HTMLResponse(CAMERAS_HTML.read_text(encoding="utf-8"))


@router.get("/ui/admin", response_class=HTMLResponse)
async def admin_page() -> HTMLResponse:
    """Admin page - comprehensive management interface."""
    if not ADMIN_HTML.exists():
        raise HTTPException(status_code=500, detail="Admin template missing")
    return HTMLResponse(ADMIN_HTML.read_text(encoding="utf-8"))


@router.get("/ui/admin/devices", response_class=HTMLResponse)
async def admin_devices_page() -> HTMLResponse:
    """Admin page - device manufacturing and management."""
    if not ADMIN_DEVICES_HTML.exists():
        raise HTTPException(status_code=500, detail="Admin devices template missing")
    return HTMLResponse(ADMIN_DEVICES_HTML.read_text(encoding="utf-8"))


@router.get("/ui/admin/codes", response_class=HTMLResponse)
async def admin_codes_page() -> HTMLResponse:
    """Admin page - activation code management."""
    if not ADMIN_CODES_HTML.exists():
        raise HTTPException(status_code=500, detail="Admin codes template missing")
    return HTMLResponse(ADMIN_CODES_HTML.read_text(encoding="utf-8"))


@router.get("/ui/camera/{device_id}", response_class=HTMLResponse)
async def camera_dashboard_page(device_id: str) -> HTMLResponse:
    """Individual camera dashboard - shows camera details and captures."""
    if not CAMERA_DASHBOARD_HTML.exists():
        raise HTTPException(status_code=500, detail="Camera dashboard template missing")
    return HTMLResponse(CAMERA_DASHBOARD_HTML.read_text(encoding="utf-8"))


@router.get("/ui", response_class=RedirectResponse)
async def ui_root() -> RedirectResponse:
    """
    Redirect to cameras page - the old single-device dashboard (/ui) has been replaced
    by the modern multi-device architecture (/ui/cameras).
    """
    return RedirectResponse(url="/ui/cameras", status_code=301)


@router.get("/static/js/{file_name}")
async def serve_static_js(file_name: str) -> FileResponse:
    """Serve static JavaScript files."""
    # Security: only allow .js files and sanitize filename
    if not file_name.endswith(".js"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    safe_filename = Path(file_name).name
    if safe_filename != file_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    static_dir = Path(__file__).parent / "static" / "js"
    file_path = static_dir / safe_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/javascript")


@router.get("/favicon.ico")
async def favicon_fallback() -> FileResponse:
    """Fallback route for browsers requesting /favicon.ico directly."""
    static_dir = Path(__file__).parent / "static"
    favicon_path = static_dir / "favicon.png"
    if not favicon_path.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    return FileResponse(favicon_path, media_type="image/png")


@router.get("/ui/state")
async def ui_state(request: Request) -> dict[str, Any]:
    config_state = getattr(request.app.state, "trigger_config", None)
    enabled = getattr(config_state, "enabled", False)
    interval = getattr(config_state, "interval_seconds", None)
    normal_description: str = getattr(request.app.state, "normal_description", "")
    classifier = getattr(request.app.state, "classifier", None)
    classifier_name = classifier.__class__.__name__ if classifier else "unknown"

    # Debug: Check what description the classifier actually has
    classifier_description = None
    if classifier and hasattr(classifier, "normal_description"):
        classifier_description = getattr(classifier, "normal_description", None)
    elif classifier and hasattr(classifier, "primary"):
        # ConsensusClassifier case
        primary = getattr(classifier, "primary", None)
        if primary and hasattr(primary, "normal_description"):
            classifier_description = getattr(primary, "normal_description", None)
    device_id = getattr(request.app.state, "device_id", "ui-device")
    manual_counter = getattr(request.app.state, "manual_trigger_counter", 0)
    last_seen = getattr(request.app.state, "device_last_seen", None)
    last_ip = getattr(request.app.state, "device_last_ip", None)
    ttl_seconds = float(getattr(request.app.state, "device_status_ttl", 30.0))
    now = datetime.now(timezone.utc)
    connected = False
    last_seen_iso: str | None = None
    if isinstance(last_seen, datetime):
        if now - last_seen <= timedelta(seconds=ttl_seconds):
            connected = True
        last_seen_iso = last_seen.isoformat()
    notification_settings: NotificationSettings = getattr(
        request.app.state, "notification_settings", NotificationSettings()
    )
    notifications_payload = {
        "email": {
            "enabled": bool(notification_settings.email.enabled),
            "recipients": list(notification_settings.email.recipients),
            "cooldown_minutes": float(
                notification_settings.email.abnormal_cooldown_minutes
            ),
        }
    }
    dedupe_settings = {
        "enabled": bool(getattr(request.app.state, "dedupe_enabled", False)),
        "threshold": int(getattr(request.app.state, "dedupe_threshold", 3)),
        "keep_every": int(getattr(request.app.state, "dedupe_keep_every", 5)),
    }
    # Get version information
    device_versions = getattr(request.app.state, "device_versions", {})
    device_version = device_versions.get(device_id, None)
    return {
        "normal_description": normal_description,
        "normal_description_file": getattr(
            request.app.state, "normal_description_file", None
        ),
        "classifier": classifier_name,
        "classifier_description": classifier_description,  # Debug field
        "device_id": device_id,
        "manual_trigger_counter": manual_counter,
        "trigger": {
            "enabled": enabled,
            "interval_seconds": interval,
        },
        "device_status": {
            "connected": connected,
            "last_seen": last_seen_iso,
            "ip": last_ip,
            "ttl_seconds": ttl_seconds,
        },
        "notifications": notifications_payload,
        "dedupe": dedupe_settings,
        "version": {
            "cloud": CLOUD_VERSION,
            "device": device_version,
        },
    }


@router.get("/ui/preferences")
async def get_ui_preferences(request: Request) -> dict[str, Any]:
    prefs = _get_preferences(request)
    return prefs.model_dump()


@router.post("/ui/preferences")
async def set_ui_preferences(
    payload: PreferencesPayload, request: Request
) -> dict[str, Any]:
    preferences = UIPreferences(**payload.model_dump())
    request.app.state.ui_preferences = preferences
    path = _preferences_path(request)
    try:
        save_preferences(path, preferences)
    except Exception as exc:
        logger.error("Failed to save UI preferences to %s: %s", path, exc)
        raise HTTPException(status_code=500, detail="Failed to save preferences") from exc
    return preferences.model_dump()


@router.post("/ui/normal-description")
async def update_normal_description(
    payload: NormalDescriptionPayload,
    request: Request,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Save alert definition for a specific device."""
    from cloud.api.database import AlertDefinition, Device

    description = payload.description.strip()
    device_id = payload.device_id

    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    logger.info(
        "Saving alert definition for device %s: description_length=%d",
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
    # TODO: Get actual user email/name from authentication
    created_by = "admin@visant.ai"  # Placeholder until auth is fully implemented

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

    # Update classifier if this is the active/displayed device
    classifier = getattr(request.app.state, "classifier", None)
    if classifier:
        _apply_normal_description(classifier, description)
        logger.info("Updated classifier with new definition for device %s", device_id)

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
        "definition_id": str(new_definition.id),
        "device_id": device_id,
        "version": new_version,
        "description": description,
        "created_at": new_definition.created_at.isoformat(),
        "created_by": created_by
    }


@router.post("/ui/trigger")
async def update_trigger(
    payload: TriggerConfigPayload, request: Request
) -> dict[str, Any]:
    config_state = getattr(request.app.state, "trigger_config", None)

    if payload.enabled and (
        payload.interval_seconds is None
        or payload.interval_seconds < MIN_TRIGGER_INTERVAL_SECONDS
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Interval must be at least {MIN_TRIGGER_INTERVAL_SECONDS:.0f} seconds",
        )

    if hasattr(config_state, "enabled"):
        config_state.enabled = payload.enabled
        config_state.interval_seconds = (
            payload.interval_seconds if payload.enabled else None
        )
        enabled = config_state.enabled
        interval = config_state.interval_seconds
    else:
        config_state = {
            "enabled": payload.enabled,
            "interval_seconds": payload.interval_seconds if payload.enabled else None,
        }
        request.app.state.trigger_config = config_state
        enabled = config_state["enabled"]
        interval = config_state["interval_seconds"]

    # Persist trigger configuration to survive Railway deployments
    server_config_path = getattr(request.app.state, "server_config_path", None)
    if server_config_path:
        try:
            update_trigger_config(
                server_config_path,
                enabled=enabled,
                interval_seconds=interval,
            )
        except OSError as exc:
            logger.error(
                "Failed to persist trigger config to %s: %s", server_config_path, exc
            )
            # Don't fail the request - configuration is already updated in memory

    return {
        "trigger": {
            "enabled": enabled,
            "interval_seconds": interval,
        }
    }


@router.post("/ui/notifications")
async def update_notifications(
    payload: NotificationSettingsPayload, request: Request
) -> dict[str, Any]:
    recipients = [
        value.strip() for value in payload.email_recipients if isinstance(value, str)
    ]
    recipients = [value for value in recipients if value]

    if payload.email_enabled and not recipients:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one email recipient to enable notifications.",
        )

    invalid = [value for value in recipients if not _EMAIL_PATTERN.match(value)]
    if invalid:
        human_list = ", ".join(invalid)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid email address(es): {human_list}",
        )

    settings: NotificationSettings = getattr(
        request.app.state, "notification_settings", NotificationSettings()
    )
    store_dir = getattr(request.app.state, "normal_description_store_dir", None)
    store_dir_path = (
        Path(store_dir) if store_dir else Path("config/normal_descriptions")
    )
    settings.email.enabled = payload.email_enabled
    settings.email.recipients = recipients
    settings.email.abnormal_cooldown_minutes = float(
        max(0.0, payload.email_cooldown_minutes)
    )
    sanitized = settings.sanitized()

    base_config = getattr(request.app.state, "email_base_config", None)
    if sanitized.email.enabled and not base_config:
        raise HTTPException(
            status_code=400,
            detail="SendGrid credentials are not configured; email notifications cannot be enabled.",
        )

    notifier = None
    if sanitized.email.enabled and base_config:
        try:
            notifier = create_sendgrid_service(
                api_key=base_config["api_key"],
                sender=base_config["sender"],
                recipients=sanitized.email.recipients,
                environment_label=base_config.get("environment_label"),
                description_root=store_dir_path,
                ui_base_url=base_config.get("ui_base_url"),
            )
        except Exception as exc:  # pragma: no cover - external client init
            logger.exception(
                "Failed to initialise SendGrid client during notification update: %s",
                exc,
            )
            raise HTTPException(
                status_code=500, detail="Failed to initialise SendGrid client"
            ) from exc

    config_path = getattr(request.app.state, "notification_config_path", None)
    if isinstance(config_path, Path):
        try:
            save_notification_settings(config_path, sanitized)
        except OSError as exc:  # pragma: no cover - filesystem error surfaced to client
            raise HTTPException(
                status_code=500,
                detail=f"Failed to persist notification settings: {exc}",
            ) from exc

    request.app.state.notification_settings = sanitized
    request.app.state.abnormal_notifier = notifier
    service = getattr(request.app.state, "service", None)
    if service is not None:
        service.notifier = notifier
        service.update_alert_cooldown(sanitized.email.abnormal_cooldown_minutes)

    return {
        "notifications": {
            "email": {
                "enabled": sanitized.email.enabled,
                "recipients": sanitized.email.recipients,
                "cooldown_minutes": sanitized.email.abnormal_cooldown_minutes,
            }
        }
    }


@router.get("/ui/captures")
async def list_captures(
    request: Request,
    limit: int = 12,
    state: list[str] | None = Query(default=None),
    start: str | None = Query(default=None, alias="from"),
    end: str | None = Query(default=None, alias="to"),
    authorization: Optional[str] = Header(None),
) -> List[dict[str, Any]]:
    """
    List captures from database for authenticated user's organization.

    Now queries the database Capture table instead of filesystem.
    """
    from cloud.api.database import get_db, Capture, Organization, Device
    from cloud.api.auth.dependencies import get_current_user
    from sqlalchemy.orm import Session
    from fastapi import Depends

    states, states_explicit = _normalize_state_filters(state)
    start_dt = parse_capture_timestamp(start)
    end_dt = parse_capture_timestamp(end)

    if start and start.strip() and start_dt is None:
        raise HTTPException(
            status_code=400, detail="'from' must be an ISO 8601 timestamp with timezone"
        )
    if end and end.strip() and end_dt is None:
        raise HTTPException(
            status_code=400, detail="'to' must be an ISO 8601 timestamp with timezone"
        )
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="'from' value must be before 'to'")

    clamped_limit = max(0, min(limit, _MAX_CAPTURE_LIMIT))
    if clamped_limit == 0:
        return []

    if states_explicit and states is not None and not states:
        return []

    # Get current user's organization from JWT
    # For now, return all captures (multi-tenant filtering will be added later)
    # TODO: Implement proper session-based or cookie-based auth for UI
    db = next(get_db())
    try:
        # Query all captures (temporary - should be filtered by org in production)
        query = db.query(Capture)

        # Apply state filter if provided
        if states is not None and len(states) > 0:
            query = query.filter(Capture.state.in_(states))

        # Apply time range filters
        if start_dt:
            query = query.filter(Capture.captured_at >= start_dt)
        if end_dt:
            query = query.filter(Capture.captured_at <= end_dt)

        # Order by captured_at descending and limit
        db_captures = query.order_by(Capture.captured_at.desc()).limit(clamped_limit).all()

        # Convert database captures to API response format
        captures: List[dict[str, Any]] = []
        for cap in db_captures:
            # Get device friendly name
            device_name = None
            if cap.device_id:
                device = db.query(Device).filter(Device.device_id == cap.device_id).first()
                if device:
                    device_name = device.friendly_name

            # Build image URL if image is stored
            image_url = None
            download_url = None
            thumbnail_url = None
            if cap.image_stored and cap.s3_image_key:
                image_route = request.url_for("serve_capture_image", record_id=cap.record_id)
                image_url = image_route.path or str(image_route)
                download_url = f"{image_url}?download=1"
                # Use thumbnail endpoint for efficient gallery display
                thumbnail_url = f"/v1/captures/{cap.record_id}/thumbnail"

            captures.append({
                "record_id": cap.record_id,
                "device_id": cap.device_id,
                "device_name": device_name,
                "captured_at": cap.captured_at.isoformat() if cap.captured_at else None,
                "ingested_at": cap.ingested_at.isoformat() if cap.ingested_at else None,
                "state": cap.state,
                "score": cap.score,
                "reason": cap.reason,
                "trigger_label": cap.trigger_label,
                "evaluation_status": cap.evaluation_status,
                "normal_description_file": None,  # Not used in database captures
                "image_available": cap.image_stored,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "download_url": download_url,
                "agent_details": None,  # Not used in database captures
                "metadata": cap.capture_metadata if cap.capture_metadata is not None else {},
            })

        return captures
    finally:
        db.close()


@router.get("/ui/captures/{record_id}")
async def fetch_capture_metadata(
    record_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
) -> dict[str, Any]:
    """
    Get capture metadata from database.

    Now queries the database Capture table instead of filesystem.
    """
    from cloud.api.database import get_db, Capture, Device

    # Get capture from database
    # For now, return any capture (multi-tenant filtering will be added later)
    # TODO: Implement proper session-based or cookie-based auth for UI
    db = next(get_db())
    try:
        # Query capture from database (temporary - should be filtered by org in production)
        cap = db.query(Capture).filter(
            Capture.record_id == record_id
        ).first()

        if not cap:
            raise HTTPException(status_code=404, detail="Capture not found")

        # Get device friendly name
        device_name = None
        if cap.device_id:
            device = db.query(Device).filter(Device.device_id == cap.device_id).first()
            if device:
                device_name = device.friendly_name

        # Build image URL if image is stored
        image_url = None
        download_url = None
        thumbnail_url = None
        if cap.image_stored and cap.s3_image_key:
            image_route = request.url_for("serve_capture_image", record_id=cap.record_id)
            image_url = image_route.path or str(image_route)
            download_url = f"{image_url}?download=1"
            thumbnail_url = f"/v1/captures/{cap.record_id}/thumbnail"

        return {
            "record_id": cap.record_id,
            "device_id": cap.device_id,
            "device_name": device_name,
            "captured_at": cap.captured_at.isoformat() if cap.captured_at else None,
            "ingested_at": cap.ingested_at.isoformat() if cap.ingested_at else None,
            "state": cap.state,
            "score": cap.score,
            "reason": cap.reason,
            "trigger_label": cap.trigger_label,
            "evaluation_status": cap.evaluation_status,
            "alert_definition_id": str(cap.alert_definition_id) if cap.alert_definition_id else None,
            "image_available": cap.image_stored,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "download_url": download_url,
            "agent_details": cap.agent_details if cap.agent_details is not None else None,
            "metadata": cap.capture_metadata if cap.capture_metadata is not None else {},
        }
    finally:
        db.close()


@router.get("/ui/captures/{record_id}/image")
async def serve_capture_image(
    record_id: str,
    request: Request,
    download: bool = False,
    authorization: Optional[str] = Header(None)
) -> FileResponse:
    """
    Serve capture image from local filesystem.

    Now serves from uploads directory based on database record.
    """
    from cloud.api.database import get_db, Capture

    # Get capture from database
    # For now, return any capture (multi-tenant filtering will be added later)
    # TODO: Implement proper session-based or cookie-based auth for UI
    db = next(get_db())
    try:
        # Query capture from database (temporary - should be filtered by org in production)
        cap = db.query(Capture).filter(
            Capture.record_id == record_id
        ).first()

        if not cap:
            raise HTTPException(status_code=404, detail="Capture not found")

        if not cap.image_stored or not cap.s3_image_key:
            raise HTTPException(status_code=404, detail="Capture image not available")

        # Build path to image file
        # s3_image_key stores relative path like: "c472e36a.../devices/TEST3/captures/TEST3_20251109_035751_25bdcc09.jpg"
        from cloud.api.storage.config import UPLOADS_DIR
        image_path = UPLOADS_DIR / cap.s3_image_key

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Capture image file missing")

        filename = image_path.name if download else None
        return FileResponse(
            image_path,
            filename=filename,
            headers={"Cache-Control": "public, max-age=31536000"}  # 1 year cache
        )
    finally:
        db.close()


@router.get("/ui/captures/{record_id}/thumbnail")
async def serve_capture_thumbnail(
    record_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
) -> FileResponse:
    """
    Serve capture thumbnail image from local filesystem.

    Returns thumbnail if available, otherwise generates on-demand from full image.
    """
    from cloud.api.database import get_db, Capture
    from cloud.datalake.storage import _generate_thumbnail
    from fastapi.responses import Response

    # Get capture from database
    db = next(get_db())
    try:
        cap = db.query(Capture).filter(
            Capture.record_id == record_id
        ).first()

        if not cap:
            raise HTTPException(status_code=404, detail="Capture not found")

        from cloud.api.storage.config import UPLOADS_DIR

        # Try to serve pre-generated thumbnail first
        if cap.thumbnail_stored and cap.s3_thumbnail_key:
            thumbnail_path = UPLOADS_DIR / cap.s3_thumbnail_key

            if thumbnail_path.exists():
                return FileResponse(
                    thumbnail_path,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000"}  # 1 year cache
                )

        # Fallback: Generate thumbnail from full image on-demand
        if cap.image_stored and cap.s3_image_key:
            image_path = UPLOADS_DIR / cap.s3_image_key

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
                    # Log error and return 500
                    print(f"Error generating thumbnail for {record_id}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to generate thumbnail")

        # No image available
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    finally:
        db.close()


@router.get("/ui/alert-definitions/{definition_id}")
async def fetch_alert_definition(definition_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Fetch alert definition by ID from database."""
    from cloud.api.database import AlertDefinition

    try:
        definition_uuid = uuid.UUID(definition_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid definition ID format")

    definition = db.query(AlertDefinition).filter(AlertDefinition.id == definition_uuid).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Alert definition not found")

    return {
        "id": str(definition.id),
        "device_id": definition.device_id,
        "version": definition.version,
        "description": definition.description,
        "created_at": definition.created_at.isoformat(),
        "created_by": definition.created_by,
        "is_active": definition.is_active
    }


def _collect_recent_captures(
    root: Path,
    limit: int,
    *,
    states: Set[str] | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    exclude_ids: Set[str] | None = None,
) -> List[CaptureSummary]:
    if limit <= 0:
        return []

    json_files = sorted(
        root.glob("**/*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    matches: list[tuple[datetime, CaptureSummary]] = []

    for path in json_files:
        if len(matches) >= limit:
            break

        summary = load_capture_summary(path)
        if summary is None:
            continue

        if exclude_ids and summary.record_id in exclude_ids:
            continue

        if states is not None and summary.state not in states:
            continue

        captured_at_dt = summary.captured_at_dt
        if start is not None and (captured_at_dt is None or captured_at_dt < start):
            continue
        if end is not None and (captured_at_dt is None or captured_at_dt > end):
            continue

        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        fallback_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        sort_key = captured_at_dt or fallback_dt

        matches.append((sort_key, summary))

    matches.sort(key=lambda item: item[0], reverse=True)
    return [summary for _, summary in matches[:limit]]


def _normalize_state_filters(
    values: Sequence[str] | None,
) -> tuple[Set[str] | None, bool]:
    if values is None:
        return None, False

    normalized = [str(value).strip().lower() for value in values if value is not None]
    valid = {value for value in normalized if value in _ALLOWED_CAPTURE_STATES}
    if valid:
        return valid, True

    if normalized:
        return set(), True

    return set(), True


def _find_capture_json(root: Path, record_id: str) -> Optional[Path]:
    pattern = f"**/{record_id}.json"
    for path in root.glob(pattern):
        if path.is_file():
            return path
    return None


def _apply_normal_description(classifier: Any, description: str) -> None:
    if classifier is None:
        return
    visited: set[int] = set()

    def _walk(target: Any) -> None:
        if target is None:
            return
        identifier = id(target)
        if identifier in visited:
            return
        visited.add(identifier)
        if hasattr(target, "normal_description"):
            setattr(target, "normal_description", description)
        for attr in ("primary", "secondary"):
            child = getattr(target, attr, None)
            _walk(child)

    _walk(classifier)


# Timing Debug Endpoints

TIME_LOG_HTML = Path(__file__).parent / "templates" / "time_log.html"


@router.get("/ui/time_log", response_class=HTMLResponse)
def time_log_page() -> HTMLResponse:
    """Serve the timing debug HTML page."""
    if not TIME_LOG_HTML.exists():
        raise HTTPException(status_code=404, detail="Timing debug page not found")
    return HTMLResponse(content=TIME_LOG_HTML.read_text(encoding="utf-8"))


@router.get("/ui/time_log/data")
def get_timing_data(request: Request) -> dict[str, Any]:
    """
    Get timing statistics and recent capture timings.
    Returns 404 if timing debug is not enabled.
    """
    if not request.app.state.timing_debug_enabled:
        raise HTTPException(
            status_code=404,
            detail="Timing debug is not enabled. Set ENABLE_TIMING_DEBUG=true to enable."
        )

    timing_stats = request.app.state.timing_stats
    if not timing_stats:
        raise HTTPException(
            status_code=404,
            detail="Timing stats not available"
        )

    return {
        "enabled": True,
        "recent_captures": timing_stats.get_recent(limit=20),
        "statistics": timing_stats.compute_statistics(),
    }


@router.post("/ui/time_log/clear")
def clear_timing_data(request: Request) -> dict[str, str]:
    """
    Clear all stored timing data.
    Returns 404 if timing debug is not enabled.
    """
    if not request.app.state.timing_debug_enabled:
        raise HTTPException(
            status_code=404,
            detail="Timing debug is not enabled"
        )

    timing_stats = request.app.state.timing_stats
    if timing_stats:
        timing_stats.clear()

    return {"status": "cleared"}


__all__ = ["router"]

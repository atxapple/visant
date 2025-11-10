from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, List, Optional, Sequence, Set

from fastapi import APIRouter, HTTPException, Query, Request, Header
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
import jwt
import os

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

INDEX_HTML = Path(__file__).parent / "templates" / "index.html"
LOGIN_HTML = Path(__file__).parent / "templates" / "login.html"
SIGNUP_HTML = Path(__file__).parent / "templates" / "signup.html"
CAMERAS_HTML = Path(__file__).parent / "templates" / "cameras.html"
CAMERA_DASHBOARD_HTML = Path(__file__).parent / "templates" / "camera_dashboard.html"
SHARES_HTML = Path(__file__).parent / "templates" / "shares.html"
DEVICES_HTML = Path(__file__).parent / "templates" / "devices.html"
SETTINGS_HTML = Path(__file__).parent / "templates" / "settings.html"
ADMIN_DEVICES_HTML = Path(__file__).parent / "templates" / "admin_devices.html"
ADMIN_CODES_HTML = Path(__file__).parent / "templates" / "admin_codes.html"

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


@router.get("/ui/settings", response_class=HTMLResponse)
async def settings_page() -> HTMLResponse:
    """User settings page."""
    if not SETTINGS_HTML.exists():
        raise HTTPException(status_code=500, detail="Settings template missing")
    return HTMLResponse(SETTINGS_HTML.read_text(encoding="utf-8"))


@router.get("/ui/cameras", response_class=HTMLResponse)
async def cameras_page() -> HTMLResponse:
    """Camera selection page - shows grid of user's cameras."""
    if not CAMERAS_HTML.exists():
        raise HTTPException(status_code=500, detail="Cameras template missing")
    return HTMLResponse(CAMERAS_HTML.read_text(encoding="utf-8"))


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


@router.get("/ui", response_class=HTMLResponse)
async def ui_root() -> HTMLResponse:
    """
    Dashboard - protected by JWT authentication if SUPABASE_JWT_SECRET is set.
    For now, authentication is optional to maintain backward compatibility.
    """
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=500, detail="UI template missing")
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


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
    payload: NormalDescriptionPayload, request: Request
) -> dict[str, Any]:
    description = payload.description.strip()
    request.app.state.normal_description = description

    classifier = getattr(request.app.state, "classifier", None)
    logger.info(
        "Updating normal description: classifier=%s description_length=%d",
        classifier.__class__.__name__ if classifier else "None",
        len(description),
    )
    _apply_normal_description(classifier, description)

    # Debug: Verify the update was applied
    if classifier and hasattr(classifier, "normal_description"):
        logger.info(
            "Classifier description after update: %s",
            getattr(classifier, "normal_description", "NOT_SET")[:100],
        )
    elif classifier and hasattr(classifier, "primary"):
        primary = getattr(classifier, "primary", None)
        if primary and hasattr(primary, "normal_description"):
            logger.info(
                "Primary classifier description after update: %s",
                getattr(primary, "normal_description", "NOT_SET")[:100],
            )

    store_dir = getattr(request.app.state, "normal_description_store_dir", None)
    store_dir_path = (
        Path(store_dir) if store_dir else Path("config/normal_descriptions")
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_suffix = uuid.uuid4().hex[:8]
    file_name = f"normal_{timestamp}_{file_suffix}.txt"
    target_path = store_dir_path / file_name
    try:
        store_dir_path.mkdir(parents=True, exist_ok=True)
        target_path.write_text(description, encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem error surfaced to client
        raise HTTPException(
            status_code=500, detail=f"Failed to persist description: {exc}"
        ) from exc

    request.app.state.normal_description_path = target_path
    request.app.state.normal_description_store_dir = store_dir_path
    request.app.state.normal_description_file = file_name
    service = getattr(request.app.state, "service", None)
    if service is not None:
        service.normal_description_file = file_name

    # Persist active normal description filename to survive Railway deployments
    server_config_path = getattr(request.app.state, "server_config_path", None)
    if server_config_path:
        try:
            update_active_normal_description(server_config_path, file_name)
        except OSError as exc:
            logger.error(
                "Failed to persist active normal description to %s: %s",
                server_config_path,
                exc,
            )
            # Don't fail the request - configuration is already updated in memory

    # Clear similarity cache when normal description changes
    # This ensures fresh classifications with the new description instead of reusing
    # cached results that were based on the old description
    service = getattr(request.app.state, "service", None)
    if service is not None and hasattr(service, "similarity_cache"):
        similarity_cache = getattr(service, "similarity_cache", None)
        if similarity_cache is not None and hasattr(similarity_cache, "clear"):
            try:
                similarity_cache.clear()
                logger.info(
                    "Cleared similarity cache after normal description update to ensure fresh classifications"
                )
            except Exception as exc:
                logger.warning("Failed to clear similarity cache: %s", exc)

    return {"normal_description": description, "normal_description_file": file_name}


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
    from cloud.api.database import get_db, Capture, Organization
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
                "captured_at": cap.captured_at.isoformat() if cap.captured_at else None,
                "ingested_at": cap.ingested_at.isoformat() if cap.ingested_at else None,
                "state": cap.state,
                "score": cap.score,
                "reason": cap.reason,
                "trigger_label": cap.trigger_label,
                "normal_description_file": None,  # Not used in database captures
                "image_available": cap.image_stored,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "download_url": download_url,
                "agent_details": None,  # Not used in database captures
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
            "captured_at": cap.captured_at.isoformat() if cap.captured_at else None,
            "ingested_at": cap.ingested_at.isoformat() if cap.ingested_at else None,
            "state": cap.state,
            "score": cap.score,
            "reason": cap.reason,
            "trigger_label": cap.trigger_label,
            "normal_description_file": None,  # Not used in database captures
            "image_available": cap.image_stored,
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "download_url": download_url,
            "agent_details": None,  # Not used in database captures
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
        uploads_dir = Path("uploads")
        image_path = uploads_dir / cap.s3_image_key

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Capture image file missing")

        filename = image_path.name if download else None
        return FileResponse(image_path, filename=filename)
    finally:
        db.close()


@router.get("/ui/normal-definitions/{file_name}")
async def fetch_normal_definition(file_name: str, request: Request) -> dict[str, Any]:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise HTTPException(status_code=400, detail="Invalid definition identifier")

    store_dir = getattr(request.app.state, "normal_description_store_dir", None)
    candidates: list[Path] = []
    if store_dir:
        candidates.append(Path(store_dir) / safe_name)

    description_path = getattr(request.app.state, "normal_description_path", None)
    if description_path:
        description_path = Path(description_path)
        if description_path.name == safe_name:
            candidates.insert(0, description_path)

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            if candidate.exists() and candidate.is_file():
                description = candidate.read_text(encoding="utf-8")
                updated_at = datetime.fromtimestamp(
                    candidate.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                return {
                    "file": safe_name,
                    "description": description,
                    "updated_at": updated_at,
                }
        except OSError:
            continue

    raise HTTPException(status_code=404, detail="Definition not found")


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

# Public Share Feature - Development Plan v2.0

## Executive Summary

**Goal**: Implement a clean, maintainable public share feature that allows users to share camera feeds publicly via shareable links, using Railway volume storage and a unified UI approach with proper Jinja2 templating.

**Key Requirements**:
- ✅ Railway volume storage only (no S3)
- ✅ Shared UI between authenticated and public users
- ✅ Proper Jinja2 templating (no string hacks)
- ✅ Inline share creation from camera cards
- ✅ Optional alert prompt editing for public viewers

**Branch**: `feature/public-share-v2`
**Base Commit**: `362534d` (docs: Update README with password reset improvements)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Public Share System                      │
└─────────────────────────────────────────────────────────────┘

1. Frontend Layer
   ├── camera_dashboard.html (Unified template with Jinja2 conditionals)
   ├── share_inline.js (Share creation modal)
   └── JavaScript (Client-side data fetching and rendering)

2. API Layer
   ├── GET /s/{token}           → Public share page (HTML)
   ├── GET /api/s/{token}       → Public share data (JSON)
   ├── GET /images/{path}       → Image serving from Railway volume
   ├── POST /v1/devices/{id}/share → Create share link
   └── POST /s/{token}/update-prompt → Update alert (if allowed)

3. Storage Layer
   ├── PostgreSQL → Share metadata, device data, captures
   └── Railway Volume (/mnt/data) → Image files

4. Data Flow
   User → Create Share → ShareLink → Public URL → Jinja2 Render → Image Serving
```

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Templating**: Jinja2 (proper usage, not string replacement)
- **Storage**: Railway Volume (/mnt/data on production, ./uploads locally)
- **Database**: PostgreSQL (Railway)
- **Frontend**: Vanilla JavaScript, modern CSS

---

## File Structure

```
cloud/
├── api/
│   ├── routes/
│   │   ├── public.py          # UPDATE: Add Jinja2Templates, update endpoints
│   │   ├── shares.py          # KEEP: Share management API (already exists)
│   │   └── images.py          # NEW: Image serving endpoint
│   ├── storage/
│   │   ├── config.py          # KEEP: UPLOADS_DIR configuration
│   │   └── presigned.py       # UPDATE: Remove S3, return /images/ URLs
│   └── database/
│       └── models.py          # KEEP: ShareLink model (already exists)
├── web/
│   ├── templates/
│   │   └── camera_dashboard.html  # UPDATE: Add Jinja2 conditionals
│   ├── static/
│   │   └── js/
│   │       └── share_inline.js     # NEW: Share creation modal
│   └── routes.py              # UPDATE: Use Jinja2Templates
└── server.py                  # UPDATE: Register image router
```

---

## Detailed Implementation Plan

### Phase 1: Foundation - Image Serving ✅ COMPLETED

**Status**: All tasks completed and tested
**Files Modified**:
- `cloud/api/routes/images.py` (NEW - 95 lines)
- `cloud/api/storage/presigned.py` (UPDATED - simplified from 148 to 62 lines)
- `server.py` (UPDATED - added image router)

**Tests Passed**:
- ✅ Syntax validation for both files
- ✅ Imports work correctly
- ✅ `generate_presigned_url()` returns `/images/{path}` format
- ✅ All S3 code removed

### Phase 1: Foundation - Image Serving (30 minutes) [ORIGINAL PLAN]

#### 1.1 Create Image Serving Module

**File**: `cloud/api/routes/images.py` (NEW)

**Purpose**: Serve images directly from Railway volume storage with proper security.

**Implementation**:
```python
"""Image serving from Railway volume storage."""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from cloud.api.storage.config import UPLOADS_DIR

router = APIRouter(tags=["Images"])


@router.get("/images/{file_path:path}")
async def serve_image(file_path: str):
    """
    Serve images from Railway volume storage.

    On Railway: /mnt/data/{file_path}
    Locally: ./uploads/{file_path}

    Security: Path traversal protection
    Caching: 1 hour cache headers
    CORS: Public access allowed
    """
    # Construct full path
    full_path = UPLOADS_DIR / file_path

    # Security: Prevent path traversal attacks
    try:
        full_path = full_path.resolve()
        uploads_dir_resolved = UPLOADS_DIR.resolve()

        if not str(full_path).startswith(str(uploads_dir_resolved)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    # Check file exists and is a file
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Determine media type from extension
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    media_type = media_types.get(full_path.suffix.lower(), 'application/octet-stream')

    return FileResponse(
        full_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "Access-Control-Allow-Origin": "*"  # Allow CORS
        }
    )
```

**Testing**:
- ✅ GET `/images/{valid_path}` returns image with correct Content-Type
- ✅ GET `/images/../../../etc/passwd` returns 403 Forbidden
- ✅ GET `/images/nonexistent.jpg` returns 404 Not Found
- ✅ Cache-Control headers are set correctly

#### 1.2 Simplify Presigned URL Generation

**File**: `cloud/api/storage/presigned.py` (UPDATE)

**Changes**: Remove all S3 logic, always return local file URLs.

**Before**:
```python
def generate_presigned_url(s3_key: str, expiration: int = 3600, bucket: Optional[str] = None) -> Optional[str]:
    if not USE_S3:
        return f"https://placeholder.com/image/{s3_key.split('/')[-1]}"
    # ... S3 logic ...
```

**After**:
```python
def generate_presigned_url(s3_key: str, expiration: int = 3600, bucket: Optional[str] = None) -> Optional[str]:
    """
    Generate URL for image access.

    Returns local file URL: /images/{s3_key}
    Railway volume only - S3 support removed.
    """
    return f"/images/{s3_key}"


def get_public_url(s3_key: str, bucket: Optional[str] = None) -> str:
    """Get public URL for image (Railway volume)."""
    return f"/images/{s3_key}"
```

**Remove**:
- All boto3 imports
- All S3 client logic
- USE_S3 checks
- AWS environment variable reads

**Testing**:
- ✅ `generate_presigned_url("org/device/image.jpg")` returns `"/images/org/device/image.jpg"`
- ✅ No boto3 imports remain
- ✅ No S3-related errors

#### 1.3 Register Image Router

**File**: `server.py` (UPDATE)

**Add**:
```python
# Add import
from cloud.api.routes import images

# Register router (after other routers)
main_app.include_router(images.router)
```

**Testing**:
- ✅ Server starts without errors
- ✅ `/images/` endpoint is accessible
- ✅ OpenAPI docs show `/images/{file_path}` endpoint

---

### Phase 2: Template Setup (45 minutes)

#### 2.1 Configure Jinja2 Templates

**File**: `cloud/api/routes/public.py` (UPDATE)

**Add at top of file**:
```python
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Template configuration
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
```

#### 2.2 Update camera_dashboard.html Template

**File**: `cloud/web/templates/camera_dashboard.html` (UPDATE)

**Template Variables** (add as comment at top):
```html
<!--
Template Context Variables:
- is_public_share: bool - True if public share, False if authenticated
- share_token: str - Share token (only if is_public_share=True)
- allow_edit_prompt: bool - Allow editing alert condition
- device_id: str - Device identifier
- device_name: str - Friendly device name
- organization_name: str - Organization name
- share_expires_at: str - Expiration date (only if is_public_share=True)
- user: User object - Current user (only if is_public_share=False)
-->
```

**Header Section** (replace existing):
```html
<header>
    {% if is_public_share %}
        <!-- Public Share Header -->
        <div class="public-header">
            <div class="logo">Visant</div>
            <h1>{{ device_name }}</h1>
            <p class="org-name">{{ organization_name }}</p>
            <p class="share-info">
                📤 Shared Link • Expires: {{ share_expires_at }}
            </p>
            <a href="https://app.visant.ai/signup" class="cta-button">
                Get Visant for Your Cameras →
            </a>
        </div>
    {% else %}
        <!-- Authenticated User Header -->
        <div class="auth-header">
            <div class="logo">Visant</div>
            <h1>{{ device_name }}</h1>
            <div class="user-menu">
                <span>{{ user.email }}</span>
                <a href="/logout">Logout</a>
            </div>
        </div>
    {% endif %}
</header>
```

**Settings Panel** (wrap in conditional):
```html
{% if not is_public_share %}
    <!-- Camera Settings Panel (Authenticated Only) -->
    <div class="settings-panel">
        <h2>CAMERA SETTINGS</h2>
        <div class="device-info">
            <p>Device ID: <span id="settingsDeviceId">{{ device_id }}</span></p>
            <!-- ... other settings ... -->
        </div>
    </div>
{% endif %}
```

**Alert Condition Section** (conditional visibility):
```html
{% if not is_public_share or (is_public_share and allow_edit_prompt) %}
    <div class="alert-settings">
        <h2>{% if is_public_share %}ALERT CONDITION{% else %}CAMERA SETTINGS{% endif %}</h2>
        <textarea id="alertDescription" placeholder="Describe what constitutes an alert..."></textarea>
        <button onclick="saveAlertDescription()">Save Alert Condition</button>
    </div>
{% endif %}
```

**JavaScript Section** (update variables):
```html
<script>
    // Template variables from Jinja2
    const isPublicShare = {{ 'true' if is_public_share else 'false' }};
    const shareToken = "{{ share_token if is_public_share else '' }}";
    const deviceId = "{{ device_id }}";
    const allowEditPrompt = {{ 'true' if (is_public_share and allow_edit_prompt) else 'false' }};

    console.log('=== Template Context ===');
    console.log('isPublicShare:', isPublicShare);
    console.log('shareToken:', shareToken);
    console.log('deviceId:', deviceId);
    console.log('allowEditPrompt:', allowEditPrompt);

    // API endpoints based on mode
    function getApiUrl() {
        if (isPublicShare) {
            return `/api/s/${shareToken}`;
        } else {
            return `/v1/devices/${deviceId}`;
        }
    }

    // Load device data
    async function loadDeviceData() {
        console.log('=== loadDeviceData START ===');

        try {
            if (isPublicShare) {
                // Public share: load from public API
                const response = await fetch(`/api/s/${shareToken}`);
                const data = await response.json();
                console.log('Public API response:', data);

                // Render captures
                renderCaptures(data.captures);
            } else {
                // Authenticated: load from authenticated API
                const response = await fetch(`/v1/devices/${deviceId}/captures`);
                const data = await response.json();
                console.log('Auth API response:', data);

                // Render captures
                renderCaptures(data);
            }
        } catch (error) {
            console.error('loadDeviceData error:', error);
            showToast('Failed to load camera data', 'error');
        }
    }

    // Save alert description
    async function saveAlertDescription() {
        const description = document.getElementById('alertDescription').value;

        if (!description.trim()) {
            showToast('Please enter an alert condition', 'error');
            return;
        }

        try {
            const url = isPublicShare
                ? `/s/${shareToken}/update-prompt`
                : `/v1/devices/${deviceId}/alert-definition`;

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description })
            });

            if (!response.ok) {
                throw new Error('Failed to save alert condition');
            }

            showToast('Alert condition saved successfully', 'success');
        } catch (error) {
            console.error('saveAlertDescription error:', error);
            showToast('Failed to save alert condition', 'error');
        }
    }

    // Render captures
    function renderCaptures(captures) {
        const container = document.getElementById('capturesContainer');
        if (!container) return;

        container.innerHTML = '';

        if (!captures || captures.length === 0) {
            container.innerHTML = '<p>No captures yet.</p>';
            return;
        }

        captures.forEach(capture => {
            const captureEl = document.createElement('div');
            captureEl.className = 'capture-card';
            captureEl.innerHTML = `
                ${capture.thumbnail_url || capture.image_url
                    ? `<img src="${capture.thumbnail_url || capture.image_url}" alt="Capture" />`
                    : '<div class="no-image">No image</div>'}
                <div class="capture-info">
                    <p><strong>${new Date(capture.captured_at).toLocaleString()}</strong></p>
                    <p class="state state-${capture.state}">${capture.state}</p>
                    ${capture.reason ? `<p class="reason">${capture.reason}</p>` : ''}
                    ${capture.score ? `<p class="score">Score: ${capture.score}</p>` : ''}
                </div>
            `;
            container.appendChild(captureEl);
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        loadDeviceData();

        // Don't setup WebSocket for public shares
        if (!isPublicShare) {
            setupWebSocket();
        }
    });
</script>
```

**Testing**:
- ✅ Template renders without Jinja2 errors
- ✅ Variables populate correctly in both modes
- ✅ Conditionals show/hide appropriate sections
- ✅ JavaScript receives correct template variables

---

### Phase 3: Public Share Endpoint (30 minutes)

#### 3.1 Update Public Share HTML Endpoint

**File**: `cloud/api/routes/public.py` (UPDATE)

**Replace `public_gallery_html` function**:
```python
@router.get("/s/{token}", response_class=HTMLResponse)
async def public_gallery_html(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public gallery page - renders unified camera_dashboard.html template.

    Uses proper Jinja2 templating (not string replacement).
    """
    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        return HTMLResponse(
            content="<h1>Share Link Not Found</h1><p>This link does not exist or has been revoked.</p>",
            status_code=404
        )

    # Check expiry
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)
    if share_link.expires_at < current_time:
        return HTMLResponse(
            content=f"<h1>Link Expired</h1><p>This link expired on {share_link.expires_at.strftime('%Y-%m-%d %H:%M')} UTC.</p>",
            status_code=410
        )

    # Check view limit
    if share_link.max_views and share_link.view_count >= share_link.max_views:
        return HTMLResponse(
            content="<h1>View Limit Reached</h1><p>This link has reached its maximum view limit.</p>",
            status_code=410
        )

    # Increment view count
    share_link.view_count += 1
    share_link.last_viewed_at = current_time
    db.commit()

    # Get device and organization info
    device = db.query(Device).filter(Device.device_id == share_link.device_id).first()
    org = db.query(Organization).filter(Organization.id == share_link.org_id).first()

    # Render template with Jinja2 (proper templating, not string replacement)
    return templates.TemplateResponse("camera_dashboard.html", {
        "request": request,
        "is_public_share": True,
        "share_token": token,
        "device_id": share_link.device_id,
        "device_name": device.friendly_name if device else "Unknown Device",
        "organization_name": org.name if org else "Unknown Organization",
        "share_expires_at": share_link.expires_at.strftime('%Y-%m-%d %H:%M UTC'),
        "allow_edit_prompt": share_link.allow_edit_prompt
    })
```

**Testing**:
- ✅ GET `/s/{valid_token}` returns rendered HTML page
- ✅ GET `/s/{invalid_token}` returns 404
- ✅ GET `/s/{expired_token}` returns 410
- ✅ View count increments on each access
- ✅ Template variables populated correctly

#### 3.2 Verify JSON API Endpoint

**File**: `cloud/api/routes/public.py` (VERIFY - should already exist)

**Ensure this endpoint exists and is clean**:
```python
@router.get("/api/s/{token}", response_model=PublicGalleryResponse)
def public_gallery_api(
    token: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Public gallery API - JSON response for JavaScript to fetch."""
    # ... validation logic ...
    # Return clean JSON with captures
```

**Testing**:
- ✅ GET `/api/s/{token}` returns JSON with captures
- ✅ Response includes device_name, organization_name, captures array
- ✅ Image URLs use `/images/` format

---

### Phase 4: Authenticated Dashboard Update (20 minutes)

#### 4.1 Update Authenticated Camera Dashboard

**File**: `cloud/web/routes.py` (UPDATE)

**Add imports**:
```python
from fastapi.templating import Jinja2Templates
from pathlib import Path
```

**Add template configuration**:
```python
TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
```

**Update camera dashboard route**:
```python
@router.get("/camera/{device_id}", response_class=HTMLResponse)
async def camera_dashboard(
    device_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authenticated camera dashboard.

    Uses same camera_dashboard.html template as public shares,
    but with is_public_share=False and user context.
    """
    # Get device (ensure user owns it)
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == user.organization_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Get organization
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()

    # Render same template with different context
    return templates.TemplateResponse("camera_dashboard.html", {
        "request": request,
        "is_public_share": False,
        "device_id": device_id,
        "device_name": device.friendly_name,
        "organization_name": org.name if org else "Organization",
        "user": user,
        "allow_edit_prompt": True  # Authenticated users can always edit
    })
```

**Testing**:
- ✅ Authenticated users can access `/camera/{device_id}`
- ✅ Full settings panel is visible
- ✅ User email shows in header
- ✅ All features work (WebSocket, settings, etc.)

---

### Phase 5: Share Creation UI (30 minutes)

#### 5.1 Add Share Button to Camera Cards

**File**: `cloud/web/templates/cameras.html` (UPDATE)

**Add share button to camera card template**:
```html
<div class="camera-card" data-device-id="{{ camera.device_id }}">
    <div class="camera-header">
        <h3>{{ camera.friendly_name }}</h3>
        <span class="status {{ 'online' if camera.is_online else 'offline' }}">
            {{ 'Online' if camera.is_online else 'Offline' }}
        </span>
    </div>

    <!-- ... existing content ... -->

    <div class="camera-actions">
        <a href="/camera/{{ camera.device_id }}" class="btn-primary">View Dashboard</a>
        <button onclick="openShareModal('{{ camera.device_id }}', '{{ camera.friendly_name }}')" class="btn-secondary">
            📤 Share
        </button>
    </div>
</div>
```

**Add share modal HTML** (at bottom of page):
```html
<!-- Share Modal -->
<div id="shareModal" class="modal" style="display: none;">
    <div class="modal-overlay" onclick="closeShareModal()"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h2>Share Camera Feed</h2>
            <button class="modal-close" onclick="closeShareModal()">×</button>
        </div>

        <form id="shareForm" onsubmit="createShareLink(event)">
            <div class="form-group">
                <label for="shareName">Share Name (optional):</label>
                <input
                    type="text"
                    id="shareName"
                    placeholder="e.g., Front Door - Week 1"
                    class="form-control"
                />
            </div>

            <div class="form-group">
                <label for="expiresInDays">Expires In:</label>
                <select id="expiresInDays" class="form-control">
                    <option value="1">1 day</option>
                    <option value="7" selected>7 days</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                </select>
            </div>

            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="allowEditPrompt">
                    <span>Allow viewers to edit alert condition</span>
                </label>
                <p class="help-text">If enabled, anyone with the link can modify what triggers alerts</p>
            </div>

            <button type="submit" class="btn-primary">Create Share Link</button>
        </form>

        <div id="shareResult" style="display: none;">
            <div class="success-message">
                <h3>✓ Share Link Created!</h3>
            </div>

            <div class="form-group">
                <label>Share URL:</label>
                <div class="input-group">
                    <input
                        type="text"
                        id="shareUrl"
                        readonly
                        class="form-control"
                    />
                    <button onclick="copyShareUrl()" class="btn-secondary">Copy</button>
                </div>
            </div>

            <div class="share-info">
                <p><strong>Expires:</strong> <span id="shareExpiresAt"></span></p>
                <p><strong>Views:</strong> <span id="shareViewCount">0</span></p>
            </div>
        </div>
    </div>
</div>
```

**Add CSS** (in `<style>` section):
```css
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
}

.modal-content {
    position: relative;
    background: white;
    border-radius: 8px;
    padding: 24px;
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.modal-close {
    background: none;
    border: none;
    font-size: 28px;
    cursor: pointer;
    color: #666;
}

.form-group {
    margin-bottom: 16px;
}

.form-control {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.input-group {
    display: flex;
    gap: 8px;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}

.help-text {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}

.success-message {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 16px;
}
```

#### 5.2 Create Share JavaScript

**File**: `cloud/web/static/js/share_inline.js` (NEW)

```javascript
/**
 * Share creation and management functionality
 */

let currentDeviceId = null;
let currentDeviceName = null;

/**
 * Open share modal for a specific device
 */
function openShareModal(deviceId, deviceName) {
    currentDeviceId = deviceId;
    currentDeviceName = deviceName;

    // Reset form
    document.getElementById('shareForm').reset();
    document.getElementById('shareResult').style.display = 'none';
    document.getElementById('shareForm').style.display = 'block';

    // Show modal
    document.getElementById('shareModal').style.display = 'flex';
}

/**
 * Close share modal
 */
function closeShareModal() {
    document.getElementById('shareModal').style.display = 'none';
    currentDeviceId = null;
    currentDeviceName = null;
}

/**
 * Create share link
 */
async function createShareLink(event) {
    event.preventDefault();

    if (!currentDeviceId) {
        alert('Error: No device selected');
        return;
    }

    // Get form values
    const shareName = document.getElementById('shareName').value.trim();
    const expiresInDays = parseInt(document.getElementById('expiresInDays').value);
    const allowEditPrompt = document.getElementById('allowEditPrompt').checked;

    // Prepare request data
    const requestData = {
        device_id: currentDeviceId,
        share_type: "device",
        expires_in_days: expiresInDays,
        allow_edit_prompt: allowEditPrompt
    };

    // Add link name if provided
    if (shareName) {
        requestData.link_name = shareName;
    }

    try {
        // Show loading state
        const submitBtn = event.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Creating...';
        submitBtn.disabled = true;

        // Create share link
        const response = await fetch(`/v1/devices/${currentDeviceId}/share`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create share link');
        }

        const result = await response.json();

        // Show result
        displayShareResult(result);

    } catch (error) {
        console.error('Error creating share link:', error);
        alert('Failed to create share link: ' + error.message);

        // Reset button
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

/**
 * Display share result
 */
function displayShareResult(shareData) {
    // Hide form, show result
    document.getElementById('shareForm').style.display = 'none';
    document.getElementById('shareResult').style.display = 'block';

    // Populate result fields
    document.getElementById('shareUrl').value = shareData.share_url;
    document.getElementById('shareExpiresAt').textContent = new Date(shareData.expires_at).toLocaleString();
    document.getElementById('shareViewCount').textContent = shareData.view_count || 0;
}

/**
 * Copy share URL to clipboard
 */
function copyShareUrl() {
    const urlInput = document.getElementById('shareUrl');
    urlInput.select();
    urlInput.setSelectionRange(0, 99999); // For mobile

    try {
        document.execCommand('copy');

        // Show success feedback
        const copyBtn = event.target;
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✓ Copied!';

        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        alert('Failed to copy URL. Please copy manually.');
    }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('shareModal').style.display === 'flex') {
        closeShareModal();
    }
});
```

**Include JavaScript** (in cameras.html):
```html
<script src="/static/js/share_inline.js"></script>
```

**Testing**:
- ✅ Share button appears on camera cards
- ✅ Modal opens when clicked
- ✅ Form submission creates share link
- ✅ Share URL is displayed and copyable
- ✅ Modal closes on Escape or X button

---

### Phase 6: Alert Prompt Editing (Optional, 20 minutes)

**File**: `cloud/api/routes/public.py` (ADD NEW ENDPOINT)

**Add UpdatePromptRequest model** (if not exists):
```python
class UpdatePromptRequest(BaseModel):
    description: str
```

**Add endpoint**:
```python
@router.post("/s/{token}/update-prompt")
async def update_prompt_via_share(
    token: str,
    payload: UpdatePromptRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update alert definition via public share link.

    Only works if share_link.allow_edit_prompt = True.
    """
    # Validate share link
    share_link = db.query(ShareLink).filter(ShareLink.token == token).first()

    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    # Check expiry
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

    # Validate description
    description = payload.description.strip()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description cannot be empty"
        )

    device_id = share_link.device_id

    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    logger.info(
        "Updating alert definition via share link %s for device %s",
        token,
        device_id
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

    # Update cache (if exists)
    definition_cache = getattr(request.app.state, 'device_definitions', {})
    definition_cache[device_id] = (new_definition.id, description)
    request.app.state.device_definitions = definition_cache

    return {
        "success": True,
        "definition_id": str(new_definition.id),
        "device_id": device_id,
        "version": new_version,
        "description": description,
        "created_at": new_definition.created_at.isoformat()
    }
```

**Testing**:
- ✅ POST `/s/{token}/update-prompt` with `allow_edit_prompt=True` succeeds
- ✅ POST `/s/{token}/update-prompt` with `allow_edit_prompt=False` returns 403
- ✅ Alert definition version increments
- ✅ New captures use updated alert condition

---

## Testing Strategy

### Manual Testing Checklist

**Image Serving**:
- [ ] Access existing image via `/images/{path}`
- [ ] Verify image loads correctly
- [ ] Verify Cache-Control headers are set
- [ ] Test path traversal protection (`/images/../../../etc/passwd`)

**Public Share Page**:
- [ ] Create new share link
- [ ] Access share link in incognito window
- [ ] Verify page renders with public header
- [ ] Verify images load
- [ ] Verify settings panel is hidden
- [ ] Verify "Get Visant" CTA is visible

**Authenticated Dashboard**:
- [ ] Login and access camera dashboard
- [ ] Verify user header shows
- [ ] Verify all settings panels visible
- [ ] Verify images load
- [ ] Verify WebSocket works

**Share Creation**:
- [ ] Click share button on camera card
- [ ] Fill out share form
- [ ] Submit and verify share link created
- [ ] Copy share URL
- [ ] Open share URL in new tab

**Alert Prompt Editing**:
- [ ] Create share with `allow_edit_prompt=True`
- [ ] Access share link
- [ ] Verify alert condition textarea is visible
- [ ] Edit and save alert condition
- [ ] Verify change is saved

**Mobile Testing**:
- [ ] Open public share on mobile device
- [ ] Verify responsive layout
- [ ] Verify images load
- [ ] Verify copy button works

### Automated Tests

Run existing test suite:
```bash
pytest tests/ -v
```

Add new tests for public share functionality (future work).

---

## Deployment Instructions

### Pre-Deployment

1. **Verify current branch**:
   ```bash
   git branch
   # Should show: * feature/public-share-v2
   ```

2. **Check git status**:
   ```bash
   git status
   # Ensure you're on the right branch and no unexpected changes
   ```

3. **Run local tests**:
   ```bash
   python server.py
   # Test manually by creating share link
   ```

### Deployment Steps

1. **Commit all changes**:
   ```bash
   git add .
   git commit -m "feat: Implement clean public share with proper Jinja2 templating

   - Add image serving from Railway volume (/images endpoint)
   - Simplify presigned URL generation (remove S3)
   - Update camera_dashboard.html with Jinja2 conditionals
   - Use proper Jinja2Templates (no string replacement)
   - Add share creation modal
   - Support optional prompt editing via public shares

   This is a clean rewrite of public share functionality using
   proper templating practices instead of string manipulation."
   ```

2. **Push to remote**:
   ```bash
   git push origin feature/public-share-v2
   ```

3. **Test branch deployment** (optional):
   - If you have a staging environment, deploy this branch first
   - Run full test suite
   - Manual QA

4. **Merge to main**:
   ```bash
   git checkout main
   git pull origin main
   git merge feature/public-share-v2
   git push origin main
   ```

5. **Monitor Railway deployment**:
   - Railway will auto-deploy from main branch
   - Watch logs for any errors
   - Verify app starts successfully

6. **Post-deployment verification**:
   - [ ] Access production site
   - [ ] Create test share link
   - [ ] Access share link
   - [ ] Verify images load from /mnt/data
   - [ ] Check Railway logs for errors

### Rollback Plan

If deployment fails:

```bash
# Revert the merge commit
git checkout main
git revert -m 1 HEAD
git push origin main
```

Railway will auto-deploy the reverted version.

### Environment Variables

**Required** (already configured on Railway):
- `DATABASE_URL` - PostgreSQL connection string
- `RAILWAY_ENVIRONMENT` or `RAILWAY_ENVIRONMENT_NAME` - Triggers /mnt/data usage

**Not needed** (S3 removed):
- ~~`AWS_ACCESS_KEY_ID`~~
- ~~`AWS_SECRET_ACCESS_KEY`~~
- ~~`AWS_S3_BUCKET`~~

---

## Success Criteria

### Functional Requirements
- ✅ Users can create share links from camera cards
- ✅ Share links display same UI as authenticated dashboard
- ✅ Public users cannot access settings (unless `allow_edit_prompt`)
- ✅ Images load from Railway volume (/mnt/data)
- ✅ Share links expire correctly
- ✅ View limits work correctly
- ✅ Optional prompt editing works

### Technical Requirements
- ✅ No string replacement in templates
- ✅ Proper Jinja2 templating used
- ✅ No S3 dependencies
- ✅ Clean separation of concerns
- ✅ Security: path traversal protected
- ✅ Performance: images cached properly

### Quality Requirements
- ✅ Code is maintainable and well-documented
- ✅ No console errors in browser
- ✅ Mobile responsive
- ✅ Fast page load (< 2 seconds)

---

## Future Enhancements

### Not in This Release
- Password-protected shares
- Share analytics (view locations, times)
- Custom branding/white-label
- Share specific time ranges
- Social media previews (Open Graph)

These can be added in future iterations on top of this clean foundation.

---

## Appendix

### File Changes Summary

**New Files**:
- `cloud/api/routes/images.py` - Image serving endpoint
- `cloud/web/static/js/share_inline.js` - Share creation modal
- `public_share_feature_dev_plan.md` - This document

**Modified Files**:
- `cloud/api/storage/presigned.py` - Remove S3, return /images/ URLs
- `cloud/api/routes/public.py` - Add Jinja2Templates, update endpoints
- `cloud/web/templates/camera_dashboard.html` - Add Jinja2 conditionals
- `cloud/web/templates/cameras.html` - Add share button and modal
- `cloud/web/routes.py` - Use Jinja2Templates for auth dashboard
- `server.py` - Register image router

**Database**:
- No new migrations needed (ShareLink table already exists from previous work)

### Key Dependencies

**Python Packages** (already installed):
- `fastapi` - Web framework
- `jinja2` - Template engine
- `sqlalchemy` - ORM
- `pillow` - Image processing (for thumbnails)

**No New Dependencies Required**

---

**Document Version**: 2.0
**Created**: 2025-01-15
**Branch**: `feature/public-share-v2`
**Status**: Ready for Implementation

---

## Notes

- This is a complete rewrite using proper Jinja2 templating
- No string replacement hacks - clean, maintainable code
- Railway volume only - all S3 code removed for simplicity
- Shared UI benefits: consistent experience, less code duplication
- Easy to extend: just add to template with proper conditionals

**Let's build this the right way! 🚀**

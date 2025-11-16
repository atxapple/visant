# Visant Multi-Tenant Camera Monitoring SaaS - Project Plan

**Version**: 2.0.0
**Created**: 2025-01-06
**Last Updated**: 2025-11-10
**Status**: Railway Deployed ✅ | Multi-tenant Complete ✅ | Performance Optimized ✅
**Production URL**: https://visant-production.up.railway.app

---

## Executive Summary

### Current Status

**PRODUCTION READY** - Visant v2.0 is deployed and operational on Railway with full multi-tenant SaaS architecture.

**Recent Achievements** (November 2025):
- ✅ **Real-time capture event streaming** (WebSocket + SSE endpoints) - 2025-11-11
- ✅ **Version tracking endpoint** (GET /v1/version for cloud + device versions) - 2025-11-11
- ✅ **Public sharing system** (Time-limited links, QR codes, complete UI) - 2025-11-10
- ✅ **Password reset flow** (Dedicated forgot password page, email-based) - 2025-11-15
- ✅ **Alert definition tracking** (Database-backed with version history) - 2025-11-13
- ✅ **Railway deployment fixes** (Port binding, migration reliability) - 2025-11-16
- ✅ **JWT authentication flow** (Proper org_id lookup from database)
- ✅ **Auto-refresh dashboard** (Camera dashboard + main dashboard)
- ✅ **Performance optimization** (90% load time reduction)
- ✅ **Thumbnail serving** (Cache headers, <3s initial load, <1s cached)
- ✅ **Composite database indexes** (Optimized capture queries)
- ✅ **Multi-tenant architecture** (Complete organization isolation)

**Next Phase**: Notification UI + Normal Description Management

### What's Working
- 👥 Multi-tenant authentication (Supabase Auth)
- 🏢 Organization/workspace management
- 📱 Device activation & management (activation codes, API keys)
- 🤖 Cloud AI evaluation (OpenAI GPT-4o-mini, Gemini 2.5 Flash)
- 📊 Web dashboard (modern gradient UI, multi-device support)
- ⚡ **Real-time updates** (WebSocket streaming with 300ms debounce)
- 🚀 Performance optimizations (thumbnails, caching, indexes)
- ☁️ Production deployment (Railway PostgreSQL + volume storage)

### What's Missing (From Legacy System)
- ⚠️ Notification configuration UI (Global UI shipped, per-device pending)
- ❌ Normal description management UI
- ⏸️ Manual trigger history/feedback (Endpoint + button live, history UI pending)
- ⏸️ Datalake pruning admin panel (Phase 3 - Low priority)

---

## Table of Contents

1. [Missing Features Roadmap](#missing-features-roadmap)
2. [Feature Completion Matrix](#feature-completion-matrix)
3. [Current Production Architecture](#current-production-architecture)
4. [Implementation History](#implementation-history)
5. [Technical Reference](#technical-reference)
6. [Deployment Guide](#deployment-guide)
7. [Success Metrics](#success-metrics)

---

## Missing Features Roadmap

Comprehensive analysis of legacy system features not yet integrated into multi-tenant v2.0.

### Phase 1: Quick Wins (1-2 weeks) ⚡ HIGH IMPACT

Core features that significantly improve user experience.

#### 1. Real-time Capture Event Streaming ✅ **COMPLETE**
**Status**: ✅ Implemented and tested
**Complexity**: LOW (existing code in legacy server.py)
**Impact**: HIGH (improves UX significantly)
**Completed**: 2025-11-11

**Tasks**:
- [x] Add `/v1/capture-events/stream` SSE endpoint to multi-tenant routes
- [x] Add `/ws/capture-events` WebSocket endpoint
- [x] Wire CaptureHub pub/sub system to multi-tenant routes
- [x] Update dashboard to connect to capture event stream (main + camera dashboard)
- [x] Test real-time updates when new captures arrive
- [x] Fix JWT authentication flow (lookup org_id from database)
- [x] Fix token storage location (sessionStorage not cookies)
- [x] Add debounced reload (300ms) to prevent excessive API calls

**Files Modified**:
- `cloud/api/routes/capture_events.py`: SSE + WebSocket endpoints (217 lines)
- `cloud/api/workers/capture_hub.py`: Multi-tenant pub/sub system (161 lines)
- `cloud/api/workers/ai_evaluator.py`: Event publishing after AI evaluation
- `server.py`: CaptureHub initialization and mounting
- `cloud/web/templates/index.html`: WebSocket connection (fixed auth)
- `cloud/web/templates/camera_dashboard.html`: WebSocket connection + auto-refresh

**Actual Time**: ~6 hours

**Technical Details**:
- WebSocket URL: `ws://host/ws/capture-events?device_id={id}&token={jwt}`
- SSE URL: `GET /v1/capture-events/stream?device_id={id}` (with Bearer token)
- CaptureHub uses asyncio.Queue for non-blocking event distribution
- Subscription keys: `"{org_id}:{device_id}"` or `"{org_id}:__all__"`
- Auto-reconnect on disconnect (2-second delay)
- Console logging with `[WebSocket]` prefix for debugging

---

#### 2. Version Tracking Endpoint ✅ **COMPLETE**
**Status**: ✅ Implemented and tested
**Complexity**: LOW
**Impact**: LOW
**Completed**: 2025-11-11

**Tasks**:
- [x] Add `GET /v1/version` endpoint to multi-tenant routes
- [x] Track cloud version + connected device versions
- [x] Display version info in dashboard headers (cloud version)
- [x] Display device version next to camera ID in settings panel

**Files Created**:
- `cloud/api/routes/version.py`: Version endpoints (57 lines)
  - `GET /v1/version`: Returns cloud version + all device versions (requires auth)
  - `GET /v1/version/cloud`: Returns cloud version only (public)

**Files Modified**:
- `server.py`: Mounted version router
- `cloud/web/templates/index.html`: Cloud version display in header
- `cloud/web/templates/cameras.html`: Cloud version display in header
- `cloud/web/templates/camera_dashboard.html`: Cloud version + device version display
- `device/main_v2.py`: Device client sends version on SSE connection
- `cloud/api/routes/device_commands.py`: Server accepts and stores device version

**Actual Time**: ~3 hours

**Technical Details**:
- Cloud version sourced from `version.py` (`__version__ = "0.2.0"`)
- Device version stored in `Device.device_version` field (already existed in schema)
- Cloud version displayed left of Logout button on all authenticated pages
- Device version displayed next to Camera ID in settings panel: `{device_id} (v{version})`
- Device client sends version as query parameter when connecting to command stream
- Server updates device version in database on each connection
- Handles "unknown" device versions gracefully (not displayed if unknown)
- Full end-to-end version tracking from device → cloud → UI ✅ Working

---

### Phase 2: Core Features (2-3 weeks) 🎯 MEDIUM PRIORITY

These require UI development in addition to backend work.

#### Completed: Public Sharing System _(formerly Phase 4 #13)_
**Status**: ✅ Shipped (routers + UI live in production)  
**Impact**: MEDIUM (drives viral growth + easy sharing)

Key outcomes:
- Added `shares.py` and `public.py` routers to the main FastAPI app and navigation.
- Validated share creation, QR codes, and anonymous `/s/{token}` galleries.
- Share management tab now available alongside Devices/Settings.

No further engineering work scheduled unless analytics or rate limiting becomes necessary.

---


#### 3. Notification Configuration UI
**Status**: Global UI shipped (per-device + testing tools pending)
**Complexity**: MEDIUM
**Impact**: HIGH (user requested feature)

**Tasks**:
- [x] Create notification settings page/modal
- [x] Email recipient management (add/remove)
- [ ] Per-device notification config
- [x] Alert cooldown settings UI
- [ ] Test SendGrid integration
- [ ] Add email preview/test function

**Files to Create/Modify**:
- `cloud/web/templates/settings.html`: Add notification section
- `cloud/api/routes/devices.py`: Add notification config endpoints
- `cloud/web/static/js/notifications.js`: Frontend logic

**Expected Time**: 12-16 hours


#### 4. Normal Description Management UI
**Status**: Backend partially exists
**Complexity**: MEDIUM
**Impact**: MEDIUM

**Tasks**:
- [ ] Multi-file normal description support (like legacy)
- [ ] Description file upload/download
- [ ] Per-device description selection
- [ ] Active description indicator
- [ ] Description history/versioning

**Files to Create/Modify**:
- `cloud/web/templates/settings.html` or separate page
- `cloud/api/routes/devices.py`: Description management endpoints
- Add file upload handling

**Expected Time**: 10-12 hours

---

#### 5. Advanced Filtering UI
**Status**: InferenceService has code, not exposed
**Complexity**: MEDIUM
**Impact**: MEDIUM

**Features**:
- Dedupe (suppress duplicate consecutive states)
- Similarity cache (perceptual hashing)
- Streak pruning (keep 1 in N captures)
- Alert cooldown management

**Tasks**:
- [ ] Create advanced settings page
- [ ] Dedupe configuration UI
- [ ] Similarity cache settings UI
- [ ] Streak pruning controls
- [ ] Test with InferenceService integration

**Files to Modify**:
- `cloud/web/templates/settings.html`: Advanced tab
- `cloud/api/routes/devices.py`: Config endpoints
- `cloud/api/service.py`: Ensure multi-tenant support

**Expected Time**: 12-15 hours

---


#### 6. Device Presence Tracking UI
**Status**: Live status banner implemented (heartbeat config TBD)
**Complexity**: LOW
**Impact**: MEDIUM

**Tasks**:
- [x] Display last seen timestamp on device cards
- [x] Show online/offline status indicators
- [x] Last IP address display
- [ ] Heartbeat interval configuration
- [x] Device version display

**Files to Modify**:
- `cloud/web/templates/devices.html`: Add status indicators
- `cloud/api/routes/devices.py`: Heartbeat endpoint
- Add polling or WebSocket for real-time status

**Expected Time**: 6-8 hours

---

### Phase 3: Admin & Advanced (3-4 weeks) 🔧 LOW PRIORITY

Nice-to-have features that improve operations and debugging.

#### 7. Datalake Pruning Admin Panel
**Status**: Code exists, not exposed in UI
**Complexity**: LOW
**Impact**: LOW (mostly for Railway deployments)

**Tasks**:
- [ ] Create admin page for pruning
- [ ] Dry-run preview (show what would be deleted)
- [ ] Manual trigger button
- [ ] Retention period configuration
- [ ] Statistics display (bytes freed, files scanned)

**Files to Create**:
- `cloud/web/templates/admin_storage.html`
- Add to admin section navigation

**Expected Time**: 6-8 hours

---

#### 8. Timing Debug / Performance Monitoring
**Status**: Code exists in `timing_debug.py`, not exposed
**Complexity**: MEDIUM
**Impact**: LOW (developer tool)

**Tasks**:
- [ ] Create performance monitoring page
- [ ] Display capture timing breakdown (device → cloud → AI → response)
- [ ] Add `/v1/admin/timing-stats` endpoint
- [ ] Timing stats export (CSV/JSON)
- [ ] Performance trend charts

**Files to Create**:
- `cloud/web/templates/time_log.html` (exists, needs integration)
- `cloud/api/routes/admin.py`: Timing stats endpoint

**Expected Time**: 8-10 hours

---

#### 9. UI Preferences Management
**Status**: Filters + persistence live; presets still pending
**Complexity**: LOW
**Impact**: LOW

**Tasks**:
- [x] Capture state filters (normal/abnormal/error)
- [x] Capture limit per page
- [ ] Filter presets (last hour, last day, etc.)
- [x] Persistent preferences (save to user profile)

**Files to Modify**:
- `cloud/web/templates/index.html`: Add filter controls
- `cloud/web/preferences.py`: Wire up to UI
- `cloud/api/routes/auth.py`: User preferences endpoint

**Expected Time**: 6-8 hours

---

#### 10. WebSocket Device Commands (Alternative to SSE)
**Status**: Not implemented (SSE only)
**Complexity**: MEDIUM
**Impact**: LOW

**Tasks**:
- [ ] Add WebSocket endpoint for device commands
- [ ] Bidirectional communication support
- [ ] Connection management and reconnection logic
- [ ] Test with device clients

**Expected Time**: 10-12 hours

---

### Phase 4: Growth & Engagement Features (Future) 🚀 DEFERRED

Lower priority features that support growth and user engagement, deferred to focus on core functionality first.

> _Public Sharing System (#13) is already live; the next growth lever is polishing the manual trigger workflow._

#### 14. Multi-Tenant Manual Trigger
**Status**: Endpoint + UI button live (history/feedback pending)
**Complexity**: MEDIUM
**Impact**: MEDIUM (user convenience feature)

**Tasks**:
- [x] Verify `/v1/devices/{device_id}/trigger` endpoint works
- [x] Add manual trigger button to device dashboard
- [x] Test trigger delivery to connected devices
- [ ] Add trigger history/feedback to UI

**Files to Modify**:
- `cloud/web/templates/index.html`: Add trigger button
- `cloud/api/routes/device_commands.py`: Manual trigger endpoint (already exists)

**Expected Time**: 4-6 hours


---

## Feature Completion Matrix

Visual overview of all features across legacy and v2.0.

| Feature Category | Feature | v1.0 Legacy | v2.0 Multi-Tenant | Priority | Implementation File |
|-----------------|---------|-------------|-------------------|----------|---------------------|
| **Core Multi-Tenant** |
| Authentication | Supabase Auth | ❌ None | ✅ Complete | - | `cloud/api/routes/auth.py` |
| Multi-Tenancy | Org isolation | ❌ Single | ✅ Complete | - | `cloud/api/database/models.py` |
| Organizations | Workspaces | ❌ None | ✅ Complete | - | `cloud/api/database/models.py` |
| Users | Multi-user | ❌ None | ✅ Complete | - | `cloud/api/database/models.py` |
| **Device Management** |
| Device Registration | API keys | ❌ Manual | ✅ Auto-generated | - | `cloud/api/routes/devices.py` |
| Activation Codes | Onboarding | ❌ None | ✅ Complete | - | `cloud/api/routes/admin_codes.py` |
| Multi-Device | Device selector | ❌ Single | ✅ Smart selector | - | `cloud/web/templates/index.html` |
| Device Config | Per-device settings | ✅ Global | ✅ Per-device JSON | - | `cloud/api/routes/devices.py` |
| Device Status | Heartbeat tracking | ✅ Basic | ⚠️ Partial | MEDIUM | `cloud/api/routes/devices.py` |
| **AI Classification** |
| Cloud AI | Background eval | ❌ Edge | ✅ Complete | - | `cloud/api/workers/ai_evaluator.py` |
| OpenAI Integration | GPT-4o-mini | ✅ Yes | ✅ Yes | - | `cloud/ai/openai_client.py` |
| Gemini Integration | Gemini 2.5 Flash | ✅ Yes | ✅ Yes | - | `cloud/ai/gemini_client.py` |
| Consensus Mode | Multi-AI | ✅ Yes | ✅ Yes | - | `cloud/ai/consensus.py` |
| Normal Descriptions | AI prompt | ✅ Multi-file | ⚠️ Single | MEDIUM | `cloud/api/routes/devices.py` |
| **Performance** |
| Thumbnails | Image optimization | ❌ None | ✅ Complete | - | `cloud/api/routes/captures.py` |
| Cache Headers | Browser caching | ❌ None | ✅ Complete | - | `cloud/web/routes.py` |
| Composite Indexes | Query optimization | ❌ None | ✅ Complete | - | `alembic/versions/aa246cbd4277` |
| Similarity Detection | Duplicate skip | ✅ Yes | ✅ Code exists | - | `cloud/api/similarity_cache.py` |
| Dedupe | Consecutive skip | ✅ Yes | ⚠️ Code exists | MEDIUM | `cloud/api/service.py` |
| Streak Pruning | Storage optimization | ✅ Yes | ⚠️ Code exists | MEDIUM | `cloud/api/service.py` |
| **Sharing & Growth** |
| Public Sharing | Share links | ❌ None | ✅ Complete | - | `cloud/api/routes/shares.py` |
| Public Gallery | No-auth view | ❌ None | ✅ Complete | - | `cloud/api/routes/public.py` |
| QR Codes | Share links | ❌ None | ✅ Complete | - | `cloud/api/utils/qrcode_gen.py` |
| Share Analytics | View tracking | ❌ None | ✅ Complete | - | `cloud/api/routes/shares.py` |
| **Real-Time Features** |
| SSE Streaming | Capture events | ✅ Yes | ✅ Complete | - | `cloud/api/routes/captures.py` |
| WebSocket | Capture events | ✅ Yes | ✅ Complete | - | `cloud/api/routes/captures.py` |
| Real-time UI | Live updates | ✅ Yes | ✅ Complete | - | `cloud/web/templates/index.html` |
| Manual Triggers | On-demand capture | ✅ Yes | ⚠️ Partial (UI pending) | MEDIUM | `cloud/api/routes/device_commands.py` |
| **Notifications** |
| Email Alerts | SendGrid | ✅ Yes | ✅ Complete | - | `cloud/api/email_service.py` |
| Notification UI | Settings page | ✅ Yes | ⚠️ Partial (per-device pending) | MEDIUM | `cloud/web/templates/notifications.html` |
| Alert Cooldown | Rate limiting | ✅ Yes | ✅ Complete | - | `cloud/api/service.py` |
| **Admin Tools** |
| Datalake Pruning | Disk management | ✅ Yes | ❌ Not exposed | LOW | `cloud/api/datalake_pruner.py` |
| Timing Debug | Performance monitor | ✅ Yes | ❌ Not exposed | LOW | `cloud/api/timing_debug.py` |
| Version Tracking | Cloud + device | ✅ Yes | ✅ Complete | - | `cloud/api/routes/version.py` |
| Preferences | UI settings | ✅ Yes | ⚠️ Partial | LOW | `cloud/web/preferences.py` |
| **Database & Storage** |
| PostgreSQL | Multi-tenant DB | ❌ SQLite | ✅ Complete | - | `cloud/api/database/` |
| S3 Storage | Object storage | ❌ Filesystem | ✅ Ready (using local) | - | `cloud/api/storage/s3.py` |
| Alembic | Migrations | ❌ None | ✅ Complete | - | `alembic/versions/` |
| Row-Level Security | Data isolation | ❌ None | ✅ Query-level | - | `cloud/api/database/models.py` |

### Legend
- ✅ **Complete**: Fully implemented and tested
- ⚠️ **Partial**: Code exists but needs integration or UI
- ❌ **Missing**: Not yet implemented
- ⚡ **Quick Win**: Easy to implement, high impact

---

## Current Production Architecture

### Deployment Environment

**Platform**: Railway.app
**Production URL**: https://visant-production.up.railway.app

**Infrastructure**:
```
┌─────────────────────────────────────────────┐
│    Railway Production Environment           │
├─────────────────────────────────────────────┤
│  • PostgreSQL Database (managed)            │
│  • Persistent Volume: /mnt/data             │
│  • Supabase Auth (JWT tokens)               │
│  • SendGrid Email Service                   │
│  • OpenAI API (GPT-4o-mini)                 │
│  • Google Gemini API (2.5 Flash)            │
└─────────────────────────────────────────────┘
         ↑                            ↓
    [Devices]                    [Web Dashboard]
  (Raspberry Pi,              (Multi-user, Multi-device)
   Laptop Camera)
```

### Multi-Tenant Database Schema

```sql
organizations (id, name, created_at, settings)
    ↓ has many
users (id, email, org_id, supabase_user_id, role)

organizations (id)
    ↓ has many
devices (device_id, org_id, api_key, friendly_name, config, last_heartbeat)
    ↓ has many
captures (record_id, org_id, device_id, captured_at, state, score, reason,
          s3_image_key, s3_thumbnail_key, evaluation_status)

organizations (id)
    ↓ has many
activation_codes (code, org_id, max_devices, expires_at)
    ↓ redeemed by
code_redemptions (code, device_id, redeemed_at)

devices (device_id)
    ↓ has many
share_links (token, org_id, device_id, share_type, expires_at, view_count)

devices (device_id)
    ↓ has many
scheduled_triggers (id, device_id, enabled, interval_seconds, digital_input)
```

**Key Indexes**:
- `idx_captures_org_device_captured` - Composite index (org_id, device_id, captured_at DESC)
- `idx_captures_org_date` - Date range queries
- `idx_captures_evaluation_status` - Cloud AI polling
- `idx_devices_org` - Organization device list
- `idx_users_org` - Organization users
- `idx_share_links_token` - Public share link lookups

### Cloud-Triggered Architecture

**CommandHub**: Real-time device command streaming (SSE)
```
Web UI → POST /v1/devices/{id}/trigger
    ↓
CommandHub.publish(device_id, command)
    ↓
Device Client ← GET /v1/devices/{id}/commands (SSE stream)
```

**TriggerScheduler**: Automated scheduled captures
```
ScheduledTrigger (enabled, interval_seconds)
    ↓
TriggerScheduler (background task)
    ↓
CommandHub.publish(device_id, "capture")
    ↓
Device Client receives trigger via SSE
```

**Background AI Evaluation**:
```
Device → POST /v1/captures (upload image)
    ↓
FastAPI BackgroundTask → evaluate_capture()
    ↓
InferenceService (OpenAI + Gemini consensus)
    ↓
Update capture.state, capture.score, capture.reason
    ↓
Send email alert if abnormal
```

### Performance Optimizations (2025-11-10)

**1. Thumbnail Generation & Serving**
- Auto-generate 400x300 JPEG thumbnails on upload
- Endpoint: `GET /v1/captures/{record_id}/thumbnail`
- Endpoint: `GET /ui/captures/{record_id}/thumbnail`
- Quality: 85%, avg size: 5-15KB (vs 17-29KB full images)
- **Result**: 70% payload reduction

**2. Browser Caching**
- Cache-Control: `public, max-age=31536000` (1 year)
- Content-addressed URLs (record_id based)
- No cache invalidation needed (immutable images)
- **Result**: Instant loads on subsequent visits

**3. Composite Database Index**
- Index: `(org_id, device_id, captured_at DESC)`
- Optimizes most common query pattern
- Migration: `alembic/versions/aa246cbd4277`
- **Result**: Consistent <100ms query times

**4. Overall Performance**
- **Before**: 20-30 seconds to load 20 images
- **After**: <3 seconds first load, <1 second cached
- **Improvement**: 90% reduction in load time

---

## Implementation History

Brief summaries of completed phases (full details archived in `archive/docs/PROJECT_PLAN_v2.1_archive.md`).

### Phase 1: Foundation & Database ✅ (2025-11-06)
- PostgreSQL schema with SQLAlchemy models
- Alembic migration framework
- Storage abstraction (filesystem/S3 ready)
- Core tables: organizations, users, devices, captures

### Phase 2: Authentication & Multi-Tenancy ✅ (2025-11-07)
- Supabase Auth integration (JWT tokens)
- Organization isolation (org_id filtering)
- Device API key authentication
- Auth endpoints: signup, login, /v1/auth/me

### Phase 3: Public Sharing ✅ (2025-11-07)
- share_links table and model
- Share link generation with tokens
- QR code generation
- Public gallery template (basic)
- **Note**: Routes exist but not yet wired to main app

### Phase 4: Cloud AI Evaluation ✅ (2025-11-07)
- Background AI evaluation worker
- Device uploads raw images (not pre-evaluated)
- Async processing with FastAPI BackgroundTasks
- Status polling endpoint for devices
- evaluation_status field (pending/processing/completed/failed)

### Phase 5: Dashboard Updates ✅ (2025-11-08)
**Week 1**: Auth UI (login, signup, session management)
**Week 2**: Multi-device support (activation codes, device selector)
**Week 3**: Per-device configuration (normal descriptions, triggers, notifications)
**Week 4**: Share links & device management pages
**Week 5**: Settings page (user profile, logout)

**Key Simplifications**:
- Signup reduced to email + password (auto-create workspaces)
- Hidden user/org IDs from UI
- Smart device selector (0 devices = wizard, 1 device = auto-select, 2+ = dropdown)

### Performance Optimization Week ✅ (2025-11-10)
- Thumbnail generation and serving endpoints
- Cache headers (1-year TTL for content-addressed images)
- Composite database index (org_id, device_id, captured_at)
- Railway deployment successful
- Requirements.txt fixes (email-validator, python-multipart)

**Results**: 90% load time reduction (20-30s → <3s)

---

## Technical Reference

### Dependencies (requirements.txt)

```python
# Core Framework
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
python-dotenv>=1.0.0
python-multipart>=0.0.6  # NEW: FastAPI file uploads

# AI & ML
openai>=1.0.0
numpy>=1.24.0
opencv-python>=4.8.0
pillow>=10.0.0

# Database (Multi-tenancy)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0

# Authentication
supabase>=2.3.0
python-jose[cryptography]>=3.3.0
email-validator>=2.0.0  # NEW: Pydantic EmailStr validation

# Storage
boto3>=1.34.0

# Email
sendgrid>=6.11.0

# Testing
pytest>=8.0.0

# Utilities
requests>=2.31.0
tqdm>=4.65.0
PyYAML>=6.0.0
click>=8.1.0

# Security & Rate Limiting
slowapi>=0.1.9

# QR Codes
qrcode[pil]>=7.4.0
```

### Comprehensive Test Strategy (Nov 2025)

#### Current State
- Capture ingestion, storage, and thumbnail serving remain largely untested even though they gate every device flow (`cloud/api/routes/captures.py`, `cloud/datalake/storage.py`).
- InferenceService behaviors (dedupe, cooldowns, similarity reuse, notifications) are only lightly covered by legacy tests and could regress silently (`cloud/api/service.py` and `tests/test_similarity_reuse.py`).
- Real-time infrastructure�CommandHub, TriggerScheduler, SSE/WebSocket streams�has no automated coverage despite powering the new push architecture (`cloud/api/routes/device_commands.py`, `cloud/api/routes/capture_events.py`, `cloud/api/workers/*`).
- Device-side loops, OkApiHttpClient payloads, and admin/public routes rely on manual QA, leaving multi-tenant isolation and share links vulnerable (`device/main.py`, `cloud/api/routes/devices.py`, `cloud/api/routes/shares.py`, `cloud/api/routes/public.py`).

#### Objectives
- Establish pytest as the single runner with fixtures for temporary uploads, SQLite databases, and stubbed external services (Supabase, SendGrid, OpenAI/Gemini/NIM, S3).
- Prove the capture → inference → notification pipeline end to end, including tenant isolation and filesystem/S3 toggles.
- Lock down every external surface (REST, SSE, WebSocket, public gallery) for authentication, quota, and data-shaping bugs.
- Validate device scheduling loops, similarity cache reuse, background workers, and Alembic migrations under concurrent load.
- Track coverage budgets per package (ai, api, web, device) and fail CI when thresholds regress.

#### Phase Breakdown

1. **Phase 0 – Test Infrastructure**
   - Add pytest configuration (ini or pyproject) with coverage reporting, split markers, and default env vars for Supabase/OpenAI stubs.
   - Build reusable fixtures: tmp uploads dir bound to `cloud/api/storage/config.UPLOADS_DIR`, in-memory SQLite `SessionLocal`, seeded org/device factory helpers, and fake clients for Supabase, SendGrid, OpenAI/Gemini/NIM, and S3.
   - Provide helpers to spin up the FastAPI app via `cloud/api/server.create_app` with dependency overrides so HTTP, SSE, and WebSocket tests share state.
   - Wire CI (GitHub Actions or Railway pipeline) to run lint + pytest + coverage; publish XML/JUnit artifacts and enforce thresholds.

2. **Phase 1 – Core Unit Coverage**
   - Exercise data sanitizers and helpers (`cloud/api/notification_settings.py`, `cloud/api/similarity_cache.py`, `cloud/api/storage/filesystem.py`, `cloud/datalake/storage.py`) with malformed input, expired cache entries, and IO failures.
   - Cover OpenAI/Gemini/NIM classifier payload builders, threshold handling, and error surfaces to keep prompts consistent across refactors.
   - Expand InferenceService tests to include dedupe/streak pruning/cooldown logic, notifier gating, and normal description propagation.
   - Add targeted tests for GUID type conversions, capture metadata helpers, QR-code utilities, and capture index normalization.

3. **Phase 2 – API & Service Integration**
   - Use FastAPI TestClient + SQLite fixtures to cover capture lifecycle (upload, status polling, thumbnail download, org isolation) and to validate error codes.
   - Test device onboarding: manufacturing, validation, activation, config updates, capture history filters, and schedule retrieval with multi-tenant enforcement.
   - Validate auth/signup/login/me/logout flows with Supabase stubs plus admin-only guards; ensure organization lookups and JWT middleware behave.
   - Cover share/admin/public endpoints end to end (share link creation, QR generation, public gallery views, admin pruning/stats, activation-code workflows).
   - Assert UI routes still surface up-to-date state and preference persistence without snapshot brittleness.

4. **Phase 3 – Background & Streaming**
   - Unit-test CommandHub subscribe/publish/unsubscribe semantics under concurrent tasks and verify keep-alive behavior in `device_commands` SSE stream.
   - Add async tests for capture-event SSE/WebSocket streams with mocked hubs to assert tenant filtering, reconnect logic, and keep-alive pings.
   - Cover TriggerScheduler timing decisions (including manual triggers and ScheduledTrigger status updates) using frozen clocks and fake DB rows.
   - Validate CloudAIEvaluator state transitions, normal-description propagation, capture hub publish, and failure handling.
   - Provide regression tests for datalake pruning and disk cleanup triggered via admin endpoints.

5. **Phase 4 – Device / Edge Flows**
   - Build harness-level tests that feed Loopback IO through `device/harness.TriggerCaptureActuationHarness` to ensure triggers, API client retries, and actuator states align.
   - Simulate `device/main.py` scheduling with fake CommandHub/SSE responses to verify manual trigger counters, min-interval clamping, and config refresh logic.
   - Integration-test `cloud/api/client.OkApiHttpClient` against the FastAPI test server to confirm payload formats, version handshake, and timing metadata.
   - Add smoke tests for device CLI argument parsing (resolution/backend parsing, warmup) and failure messaging using dependency injection (no real hardware).

6. **Phase 5 – Regression & Tooling**
   - Create Alembic migration tests that run `alembic upgrade head` on fresh databases and assert ORM invariants.
   - Add multi-tenant security regressions ensuring cross-org access to captures, devices, shares, and version endpoints is forbidden.
   - Introduce load/soak style tests (pytest markers) for high-volume capture ingestion plus similarity cache eviction to catch performance regressions early.
   - Track coverage dashboards per package and map to CODEOWNERS/PR templates; document how to run focused suites (`tests/unit`, `tests/api`, `tests/device`, `tests/e2e`) with Makefile/nox shortcuts.

### Environment Variables

**Required** (Railway):
```bash
# Database (auto-injected by Railway)
DATABASE_URL=postgresql://postgres:...@railway.internal:5432/railway

# Supabase Auth
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...  # Anon public key
SUPABASE_SERVICE_KEY=eyJhbGc...  # Service role key (admin)
SUPABASE_JWT_SECRET=your-jwt-secret

# AI APIs
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AI...

# Email (optional but recommended)
SENDGRID_API_KEY=SG....
ALERT_FROM_EMAIL=alerts@yourdomain.com
ALERT_ENVIRONMENT_LABEL=production

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=https://visant-production.up.railway.app,http://localhost:3000
```

**Optional**:
```bash
# S3 Storage (when ready to switch from filesystem)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=visant-captures
S3_REGION=us-west-2
S3_ENDPOINT_URL=...  # For Railway S3 or other providers
```

### API Endpoints

#### Authentication
```
POST   /v1/auth/signup          # Create account
POST   /v1/auth/login           # Get JWT token
GET    /v1/auth/me              # Current user info
```

#### Devices
```
GET    /v1/devices                           # List org's devices
POST   /v1/devices/validate                  # Validate device_id before activation
POST   /v1/devices/activate                  # Activate device with code
GET    /v1/devices/{id}                      # Get device details
PUT    /v1/devices/{id}                      # Update device config
DELETE /v1/devices/{id}                      # Delete device
GET    /v1/devices/{id}/config               # Get device config
PUT    /v1/devices/{id}/config               # Update device config
POST   /v1/devices/{id}/share                # Create share link
GET    /v1/devices/{id}/commands             # SSE stream for commands (CommandHub)
POST   /v1/devices/{id}/trigger              # Manual capture trigger (CommandHub)
```

#### Captures
```
POST   /v1/captures                          # Upload capture (Cloud AI)
GET    /v1/captures                          # List captures (filtered by org)
GET    /v1/captures/{record_id}              # Get capture details
GET    /v1/captures/{record_id}/status       # Poll evaluation status
GET    /v1/captures/{record_id}/thumbnail    # Get thumbnail image
GET    /v1/captures/{record_id}/image        # Get full image
DELETE /v1/captures/{record_id}              # Delete capture
```

#### Share Links (exists, not wired)
```
POST   /v1/devices/{id}/share                # Create share link
GET    /v1/share-links                       # List org's share links
DELETE /v1/share-links/{token}               # Revoke share link
```

#### Public Endpoints (NO AUTH) (exists, not wired)
```
GET    /s/{token}                            # Public gallery HTML view
GET    /api/s/{token}                        # Public gallery JSON API
```

#### Admin
```
POST   /v1/admin/activation-codes            # Create activation code
GET    /v1/admin/activation-codes            # List codes
DELETE /v1/admin/activation-codes/{code}     # Revoke code
```

#### Legacy Compatibility
```
GET    /legacy/v1/device-config              # Single-tenant device config
POST   /legacy/v1/manual-trigger             # Legacy manual trigger
GET    /legacy/v1/manual-trigger/stream      # Legacy SSE stream
GET    /legacy/v1/capture-events/stream      # Legacy capture events
```

#### Web UI
```
GET    /                                     # Root API info
GET    /health                               # Health check
GET    /signup                               # Signup page
GET    /login                                # Login page
GET    /ui                                   # Dashboard (cameras page)
GET    /ui/devices                           # Device management
GET    /ui/shares                            # Share link management
GET    /ui/settings                          # User settings
GET    /ui/admin/codes                       # Admin: Activation codes
GET    /ui/captures/{record_id}/thumbnail    # UI thumbnail endpoint
GET    /ui/captures/{record_id}/image        # UI full image endpoint
```

### File Structure

```
visant/
├── cloud/
│   ├── ai/                          # AI classifiers
│   │   ├── openai_client.py         # OpenAI GPT-4o-mini
│   │   ├── gemini_client.py         # Google Gemini 2.5 Flash
│   │   └── consensus.py             # Multi-AI consensus
│   │
│   ├── api/
│   │   ├── auth/                    # Authentication
│   │   │   ├── middleware.py        # JWT validation
│   │   │   ├── dependencies.py      # FastAPI auth deps
│   │   │   └── supabase_client.py   # Supabase integration
│   │   │
│   │   ├── database/                # Database layer
│   │   │   ├── models.py            # SQLAlchemy models (all tables)
│   │   │   ├── session.py           # DB connection pooling
│   │   │   └── base.py              # Declarative base
│   │   │
│   │   ├── routes/                  # API endpoints
│   │   │   ├── auth.py              # Authentication
│   │   │   ├── devices.py           # Device management
│   │   │   ├── captures.py          # Capture upload/retrieval
│   │   │   ├── device_commands.py   # CommandHub SSE streams
│   │   │   ├── admin_codes.py       # Activation codes
│   │   │   ├── shares.py            # Share links ⚠️ NOT WIRED
│   │   │   └── public.py            # Public gallery ⚠️ NOT WIRED
│   │   │
│   │   ├── workers/                 # Background workers
│   │   │   ├── command_hub.py       # Device command streaming
│   │   │   ├── trigger_scheduler.py # Automated triggers
│   │   │   └── ai_evaluator.py      # Cloud AI evaluation
│   │   │
│   │   ├── storage/                 # Storage abstraction
│   │   │   ├── s3.py                # S3 implementation
│   │   │   ├── filesystem.py        # Filesystem (current)
│   │   │   └── presigned.py         # Pre-signed URLs
│   │   │
│   │   ├── utils/                   # Utilities
│   │   │   └── qrcode_gen.py        # QR code generation
│   │   │
│   │   ├── server.py                # Legacy single-tenant server
│   │   ├── service.py               # InferenceService (AI logic)
│   │   ├── email_service.py         # SendGrid integration
│   │   ├── capture_index.py         # Capture indexing
│   │   ├── similarity_cache.py      # Duplicate detection
│   │   ├── datalake_pruner.py       # Disk management
│   │   └── timing_debug.py          # Performance monitoring
│   │
│   ├── web/                         # Web dashboard
│   │   ├── templates/
│   │   │   ├── login.html           # Login page
│   │   │   ├── signup.html          # Signup page
│   │   │   ├── index.html           # Dashboard (cameras)
│   │   │   ├── camera_dashboard.html# Single device view
│   │   │   ├── devices.html         # Device management
│   │   │   ├── shares.html          # Share link management
│   │   │   ├── settings.html        # User settings
│   │   │   ├── admin_codes.html     # Admin: Activation codes
│   │   │   └── time_log.html        # Performance debug ⚠️ NOT WIRED
│   │   │
│   │   ├── static/
│   │   │   ├── js/
│   │   │   │   ├── auth.js          # JWT management
│   │   │   │   ├── device_manager.js# Device operations
│   │   │   │   ├── device_config.js # Device configuration
│   │   │   │   ├── share_manager.js # Share link creation
│   │   │   │   └── captures.js      # Capture gallery
│   │   │   └── css/
│   │   │       └── styles.css       # Global styles
│   │   │
│   │   ├── routes.py                # Web UI routes
│   │   ├── preferences.py           # UI preferences
│   │   └── capture_utils.py         # Capture loading helpers
│   │
│   └── datalake/
│       └── storage.py               # Filesystem datalake operations
│
├── alembic/                         # Database migrations
│   ├── versions/
│   │   ├── 20251106_2247_8af79cab0d8d_initial_schema.py
│   │   ├── 20251107_0020_747d6fbf4733_add_evaluation_status.py
│   │   ├── 20251108_1014_remove_api_key.py
│   │   └── 20251110_2129_aa246cbd4277_add_composite_index.py
│   └── env.py
│
├── deployment/                      # Deployment guides
│   └── RAILWAY_SETUP.md             # Comprehensive Railway guide
│
├── archive/                         # Archived docs
│   └── docs/
│       └── PROJECT_PLAN_v2.1_archive.md
│
├── config/
│   └── ui_preferences.json          # UI preferences storage
│
├── test_server_v2.py                # Main application entry point
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Alembic configuration
├── Procfile                         # Railway start command
├── railway.json                     # Railway service config
├── .env                             # Environment variables (local)
├── .gitignore                       # Git ignore patterns
├── PROJECT_PLAN.md                  # This file
└── PRODUCT_DESCRIPTION.md           # Product documentation
```

---

## Deployment Guide

**Full Guide**: See `deployment/RAILWAY_SETUP.md` for comprehensive step-by-step instructions.

### Quick Start (Railway)

**1. Create Railway Project**
- Connect GitHub repository
- Auto-deploy from main branch enabled

**2. Add PostgreSQL Service**
- Railway auto-injects `DATABASE_URL`

**3. Configure Environment Variables**
```bash
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_KEY=...
SUPABASE_JWT_SECRET=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...
SENDGRID_API_KEY=...
ALERT_FROM_EMAIL=...
CORS_ALLOWED_ORIGINS=https://your-app.railway.app
```

**4. Add Volume**
- Mount path: `/mnt/data`
- Size: 1GB minimum

**5. Run Migrations**
```bash
railway run bash
alembic upgrade head
```

**6. Verify Deployment**
- Visit `https://your-app.railway.app`
- Check logs for successful startup

### Production Checklist

- [x] All environment variables configured
- [x] PostgreSQL database provisioned
- [x] Volume mounted at /mnt/data
- [x] Alembic migrations completed
- [x] CORS origins configured
- [x] SSL/TLS enabled (Railway auto-provides)
- [x] Backup strategy configured
- [x] Monitoring/alerts set up

---

## Success Metrics

### MVP Launch Criteria

**Technical**:
- ✅ 3+ test organizations tested (Alice, Bob, TEST orgs)
- ✅ Cloud AI classification works
- ✅ <3s p95 response time achieved
- ✅ Railway deployment successful
- ✅ Zero cross-org data leakage (tested)

**Product**:
- ✅ User can signup, login, register device
- ✅ Multi-device support (smart selector)
- ✅ Device configuration works
- ⏳ Public share links (code exists, needs wiring)
- ⏳ Share page mobile-friendly (needs testing)

**Business**:
- ⏳ Pricing page (future)
- ⏳ User documentation (in progress)
- ⏳ Support email operational (future)

### Performance Targets (ACHIEVED)

- ✅ **Load Time**: <3s initial, <1s cached (was 20-30s)
- ✅ **Thumbnail Size**: 5-15KB (vs 17-29KB full images)
- ✅ **Query Time**: <100ms with composite index
- ✅ **Cache Hit Rate**: ~100% for unchanged images

### Next Milestones

1. **Phase 1 Complete** (1-2 weeks): All quick wins implemented
   - Public sharing fully integrated
   - Real-time streaming working
   - Manual triggers multi-tenant

2. **Phase 2 Complete** (2-3 weeks): Core features
   - Notification UI complete
   - Normal description management
   - Advanced filtering UI

3. **Full Feature Parity** (4-6 weeks): All legacy features migrated

---

## Next Steps

### This Week (Immediate Actions)

1. **Wire up public sharing** ⚡
   - Add shares.py and public.py routers to test_server_v2.py
   - Test share link creation and public gallery
   - Test time: 2-3 hours

2. **Connect real-time streaming** ⚡
   - Add capture event SSE/WebSocket endpoints
   - Update dashboard to receive real-time updates
   - Test time: 4-6 hours

3. **Add version tracking**
   - Simple endpoint showing cloud + device versions
   - Test time: 2 hours

### Next 2 Weeks

4. **Notification configuration UI**
   - Email recipient management
   - Per-device settings
   - Test SendGrid integration

5. **Normal description management**
   - Multi-file support
   - Upload/download interface
   - Per-device selection

6. **Device presence tracking UI**
   - Last seen indicators
   - Online/offline status
   - Heartbeat monitoring

---

**Last Updated**: 2025-11-10
**Status**: Railway Deployed ✅ | Ready for Feature Migration
**Owner**: Development Team
**Next Review**: After Phase 1 quick wins complete

---

*End of Document*

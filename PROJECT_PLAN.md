# Visant Multi-User Commercial Upgrade Plan

**Version**: 2.0
**Created**: 2025-01-06
**Last Updated**: 2025-11-07
**Status**: Phase 2-4 Complete ✅
**Target Launch**: 2-3 weeks from now
**Current Progress**: Backend API complete, UI/deployment remaining

---

## Progress Summary

**COMPLETED (Phases 2-4):**
- ✅ Multi-tenant database architecture (PostgreSQL + Alembic)
- ✅ User authentication (Supabase integration)
- ✅ Device management with API keys
- ✅ Public sharing with token-based access
- ✅ Cloud AI evaluation (async background processing)
- ✅ Organization isolation and security

**IN PROGRESS:**
- 🔄 Multi-tenant web dashboard (Phase 5)
- 🔄 Production deployment (Phase 6)

**REMAINING:**
- ⏳ Device client updates
- ⏳ Security audit & load testing
- ⏳ Documentation & launch

---

## Table of Contents

1. [Project Goal](#project-goal)
2. [Core Principles](#core-principles)
3. [Architecture Overview](#architecture-overview)
4. [Implementation Phases](#implementation-phases)
5. [Technical Stack](#technical-stack-changes)
6. [Database Schema](#database-schema-details)
7. [API Changes](#api-changes)
8. [File Structure](#file-structure-new-components)
9. [Security](#security-considerations)
10. [Scalability](#scalability-architecture)
11. [Migration Strategy](#migration-strategy)
12. [Testing](#testing-strategy)
13. [Success Metrics](#success-metrics)
14. [Post-MVP Roadmap](#post-mvp-roadmap-deferred-features)
15. [Risks](#risk-mitigation)
16. [Timeline](#timeline-summary)
17. [Remaining Tasks](#remaining-tasks)

---

## Project Goal

Transform Visant from single-tenant to **multi-tenant SaaS** with viral public sharing capabilities, preparing for commercial scale while maintaining existing features and performance.

### Business Objectives
- Enable multiple organizations on single deployment (cost efficiency)
- Drive viral growth through frictionless public sharing
- Maintain 100% feature parity with current version
- Prepare architecture for 100K+ users, millions of captures

### Target Users
- **Primary**: Small businesses, facility managers, security teams (1-10 cameras)
- **Growth**: Viral sharing converts viewers to customers
- **Future**: Enterprise customers (100+ cameras, advanced features)

---

## Core Principles

1. **Growth First**: Public sharing without login friction to drive viral adoption
2. **MVP Speed**: Minimal features, maximum impact (5-6 weeks to launch)
3. **Scalable Architecture**: Design for future scale, implement for today
4. **Simple Start**: Basic multi-tenancy, defer complex features (roles, analytics, billing)
5. **Data Safety**: Zero tolerance for cross-org data leakage
6. **Backward Compatibility**: Existing deployments can migrate smoothly

---

## Architecture Overview

### Deployment Model
- **Multi-tenant SaaS**: Single Railway deployment serves all customers
- **Data isolation**: PostgreSQL with org_id filtering + Row-Level Security (RLS)
- **Storage**: S3-compatible object storage (org-scoped paths)
- **Auth**: Supabase Auth (fast integration, pre-built UI components)

### Key Architectural Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Org-centric storage** | Camera transfers rare, simplifies queries/billing | Harder to transfer cameras (acceptable) |
| **Supabase Auth** | Pre-built UI, 2 weeks faster than custom | External dependency (can migrate later) |
| **PostgreSQL** | Industry standard, great for multi-tenancy | More complex than filesystem |
| **S3 storage** | Unlimited scale, CDN-ready | Migration required |
| **Cloud AI (not Edge)** | Simplifies device code, centralized models | Slightly higher latency |
| **Public sharing in Phase 3** | Critical growth driver, not "nice to have" | Adds 1 week to timeline (worth it) |

### Storage Structure
```
s3://{bucket}/{org_id}/devices/{device_id}/captures/{YYYY}/{MM}/{DD}/{record_id}.jpeg
s3://{bucket}/{org_id}/devices/{device_id}/captures/{YYYY}/{MM}/{DD}/{record_id}_thumb.jpeg
```

**Benefits**:
- All org data in one prefix (fast queries, easy backup)
- Pre-signed URLs for secure public sharing
- Simple billing (storage = org usage)
- Easy compliance (delete org = delete all data)

### Database Schema (Core Tables)

```
organizations (id, name, created_at)
    ↓ has many
users (id, email, org_id, supabase_user_id)

organizations (id)
    ↓ has many
devices (device_id, org_id, api_key, friendly_name)
    ↓ has many
captures (record_id, org_id, device_id, s3_image_key, state, score, reason, evaluation_status)

devices (device_id)
    ↓ has many
share_links (token, org_id, device_id, expires_at, view_count)
```

---

## Implementation Phases

### Phase 1: Foundation & Database ✅ COMPLETE
**Status**: ✅ Complete (2025-11-06)
**Goal**: Migrate from filesystem to PostgreSQL + S3

**Completed Tasks**:
- ✅ Set up PostgreSQL database schema (SQLAlchemy models)
- ✅ Implement Alembic migrations (2 migrations created)
- ✅ Design database schema with org_id isolation
- ✅ Add feature flag to switch between filesystem/S3
- ✅ Create storage abstraction layer (filesystem/S3)
- ✅ Write data migration script template

**Deliverables**:
- ✅ PostgreSQL schema with 5 core tables
- ✅ Storage abstraction ready for S3
- ✅ Alembic migration framework operational

**Files Created**:
- `cloud/api/database/models.py` - SQLAlchemy models
- `cloud/api/database/session.py` - DB connection pooling
- `cloud/api/database/base.py` - Base model
- `cloud/api/storage/s3.py` - S3 storage implementation
- `cloud/api/storage/filesystem.py` - Filesystem storage (legacy)
- `cloud/api/storage/base.py` - Storage interface
- `scripts/migrate_to_multitenancy.py` - Migration script
- `alembic/versions/20251106_2247_8af79cab0d8d_initial_schema.py` - Initial migration
- `alembic/versions/20251107_0020_747d6fbf4733_add_evaluation_status_to_captures.py` - Cloud AI migration

**Completion Criteria**:
- ✅ Can query captures from PostgreSQL
- ✅ Database migrations work end-to-end
- ✅ Storage abstraction supports both filesystem and S3
- ⏳ Migration script tested on production data (pending)
- ⏳ Images served from S3 with pre-signed URLs (pending)

---

### Phase 2: Authentication & Multi-Tenancy ✅ COMPLETE
**Status**: ✅ Complete (2025-11-07)
**Goal**: Add user authentication and org isolation

**Completed Tasks**:
- ✅ Integrate Supabase Auth client
- ✅ Create JWT validation middleware
- ✅ Add org_id filtering to all queries
- ✅ Build signup/login endpoints
- ✅ Add device API key authentication
- ✅ Create device provisioning endpoint (generates API key)
- ✅ Add authorization checks (org ownership)

**Deliverables**:
- ✅ Working login/signup flow
- ✅ All API endpoints require authentication
- ✅ Device API key system operational
- ✅ Complete tenant isolation (security tested)

**Files Created**:
- `cloud/api/auth/middleware.py` - JWT validation
- `cloud/api/auth/dependencies.py` - FastAPI auth dependencies
- `cloud/api/auth/supabase_client.py` - Supabase integration
- `cloud/api/routes/auth.py` - Auth endpoints
- `cloud/api/routes/devices.py` - Device provisioning
- `cloud/api/utils/qrcode_gen.py` - QR code generation

**API Endpoints Added**:
```
POST /v1/auth/signup      # Create org + user
POST /v1/auth/login       # Get JWT token
GET  /v1/auth/me          # Current user info
POST /v1/devices          # Register device (returns API key)
GET  /v1/devices          # List org's devices
GET  /v1/devices/{id}     # Get device details
```

**Completion Criteria**:
- ✅ Can signup, login via Swagger docs
- ✅ Devices authenticate with API keys
- ✅ Org A cannot see Org B's data (tested)
- ✅ All endpoints work with auth

---

### Phase 3: Public Sharing ✅ COMPLETE
**Status**: ✅ Complete (2025-11-07)
**Goal**: Enable viral sharing via public links

**Completed Tasks**:
- ✅ Create share_links table and model
- ✅ Build share link generation endpoint
- ✅ Design public gallery template (basic HTML)
- ✅ Implement pre-signed S3 URL generation (1-hour expiry)
- ✅ Build public gallery view (no login required)
- ✅ Add QR code generation for share links
- ✅ Implement link expiration (7 days default)
- ✅ Add share type options (capture, date_range, all)

**Deliverables**:
- ✅ `/s/{token}` public view page (no login required)
- ✅ Share link creation endpoint
- ✅ QR code generation
- ✅ Growth-optimized shared view with CTAs

**Files Created**:
- `cloud/api/routes/shares.py` - Share link endpoints
- `cloud/api/routes/public.py` - Public gallery view
- `cloud/api/storage/presigned.py` - Pre-signed URL generation

**Public Share Page Features**:
- ✅ Beautiful HTML gallery (renders thumbnails)
- ✅ Device name and stats visible
- ✅ AI classifications shown
- ✅ "Get Visant for Your Cameras" CTA
- ✅ Social share buttons (prepared)
- ✅ "Powered by Visant" branding

**API Endpoints Added**:
```
POST   /v1/devices/{id}/share   # Create share link
GET    /v1/share-links          # List org's share links
DELETE /v1/share-links/{token}  # Revoke share link

# Public endpoints (NO AUTH)
GET    /s/{token}                # Public gallery HTML view
GET    /api/s/{token}            # Public gallery JSON API
```

**Completion Criteria**:
- ✅ Can generate share link from API
- ✅ Public link works without login
- ✅ Share page is mobile-friendly
- ✅ Filters out pending/processing captures
- ⏳ Rate limiting prevents abuse (pending)

---

### Phase 4: Cloud AI Evaluation ✅ COMPLETE
**Status**: ✅ Complete (2025-11-07)
**Goal**: Migrate from Edge AI to Cloud AI architecture

**Completed Tasks**:
- ✅ Add evaluation_status column to captures table
- ✅ Create background AI evaluation worker
- ✅ Refactor capture upload to accept raw images (base64)
- ✅ Implement async evaluation with FastAPI BackgroundTasks
- ✅ Add status polling endpoint for devices
- ✅ Reuse existing InferenceService for classification
- ✅ Update public gallery to filter pending evaluations
- ✅ Create test script for Cloud AI flow

**Deliverables**:
- ✅ Devices upload raw images instead of pre-evaluated results
- ✅ Background AI evaluation works
- ✅ Status polling endpoint functional
- ✅ Evaluation state machine (pending → processing → completed/failed)

**Files Created**:
- `cloud/api/workers/ai_evaluator.py` - Background AI worker
- `test_cloud_ai.py` - End-to-end Cloud AI test script

**Files Modified**:
- `cloud/api/routes/captures.py` - Refactored for Cloud AI
- `cloud/api/routes/public.py` - Filter pending captures
- `cloud/api/database/models.py` - Add evaluation_status field

**API Changes**:
```
# Upload now accepts image instead of state/score/reason
POST /v1/captures
{
  "device_id": "camera-01",
  "captured_at": "2025-11-07T12:00:00Z",
  "image_base64": "iVBORw0KG...",  # NEW: image instead of results
  "trigger_label": "motion_detected",
  "metadata": {}
}

# Response includes evaluation status
{
  "record_id": "...",
  "evaluation_status": "pending",  # NEW: pending/processing/completed/failed
  "state": null,  # Will be set after evaluation
  "score": null,
  "reason": null,
  ...
}

# New polling endpoint
GET /v1/captures/{record_id}/status  # Poll until evaluation completes
```

**Test Results**:
```
✅ Upload successful (status 201)
✅ Evaluation completed in 1 second
✅ Result: abnormal (score: 0.89)
✅ Capture found in list
```

**Completion Criteria**:
- ✅ Devices can upload images
- ✅ Cloud AI evaluates in background
- ✅ Polling endpoint returns results
- ✅ Public gallery filters pending captures
- ⏳ Device client updated to use new API (pending)

---

### Phase 5: Dashboard Updates 🔄 IN PROGRESS
**Status**: 🔄 In Progress (Week 1: Authentication Foundation)
**Goal**: Adapt existing UI for multi-user/multi-device
**Duration**: 5 weeks (25 days)

---

#### Week 1: Authentication Foundation (Days 1-5) 🔄 Current

**Tasks**:
- [ ] Day 1-2: Create login & signup pages
  - [ ] Create `cloud/web/templates/login.html`
  - [ ] Create `cloud/web/templates/signup.html`
  - [ ] Create `cloud/web/static/js/auth.js` (JWT management)
  - [ ] Implement sessionStorage for tokens
- [ ] Day 3: Auth middleware
  - [ ] Add JWT verification to UI routes
  - [ ] Redirect unauthenticated users to login
  - [ ] Handle token expiration
- [ ] Day 4-5: Testing & polish
  - [ ] Test login flow end-to-end
  - [ ] Error handling (invalid credentials, network errors)
  - [ ] Mobile responsive design

**Deliverables**:
- [ ] Working login/signup flow
- [ ] JWT stored in sessionStorage
- [ ] Auth middleware protecting dashboard

---

#### Week 2: Multi-Device Support (Days 6-10) ⏳ Pending

**Tasks**:
- [ ] Day 1-2: Device selector
  - [ ] Add device dropdown to dashboard header
  - [ ] Fetch devices from `/v1/devices` API
  - [ ] Device switching logic
  - [ ] Display device status (online/offline)
- [ ] Day 3: API migration
  - [ ] Update all API calls to use new endpoints
  - [ ] Add auth headers to all requests
  - [ ] Handle 401 errors (redirect to login)
- [ ] Day 4: Capture gallery
  - [ ] Migrate to `/v1/captures` API
  - [ ] Handle S3 presigned URLs
  - [ ] Support pending evaluations (polling)
- [ ] Day 5: WebSocket updates
  - [ ] Add JWT auth to WebSocket connections
  - [ ] Filter by selected device
  - [ ] Reconnection logic

**Deliverables**:
- [ ] Device selector dropdown working
- [ ] Capture gallery shows device-specific captures
- [ ] WebSocket filtered by device

---

#### Week 3: Per-Device Configuration (Days 11-15) ⏳ Pending

**Tasks**:
- [ ] Day 1-2: Device config API
  - [ ] Create `cloud/api/routes/device_config.py`
  - [ ] Endpoints: GET/PUT `/v1/devices/{id}/config`
  - [ ] Migrate config storage to `device.config` JSON
  - [ ] Normal description per device
- [ ] Day 3: Trigger configuration
  - [ ] Update trigger UI to save per device
  - [ ] Sync config when switching devices
- [ ] Day 4: Notification settings
  - [ ] Email notification config per device
  - [ ] Cooldown settings
- [ ] Day 5: Testing
  - [ ] Test config persistence
  - [ ] Test device switching
  - [ ] Verify no data leakage between devices

**Deliverables**:
- [ ] Per-device normal descriptions
- [ ] Per-device trigger configuration
- [ ] Per-device notification settings

---

#### Week 4: Share Links & Device Management (Days 16-20) ⏳ Pending

**Tasks**:
- [ ] Day 1-2: Share modal
  - [ ] Create share link modal component
  - [ ] Integrate with `/v1/devices/{id}/share` API
  - [ ] QR code generation
- [ ] Day 3: Share management
  - [ ] List existing share links
  - [ ] Revoke functionality
  - [ ] View analytics (view count)
- [ ] Day 4-5: Device registration
  - [ ] Device management page (`cloud/web/templates/devices.html`)
  - [ ] Add device wizard
  - [ ] Display API key (one-time)
  - [ ] Config file download

**Deliverables**:
- [ ] Share link creation modal
- [ ] Share link management page
- [ ] Device registration wizard

---

#### Week 5: Polish & Testing (Days 21-25) ⏳ Pending

**Tasks**:
- [ ] Day 1: User profile
  - [ ] User menu dropdown
  - [ ] Organization name display
  - [ ] Logout functionality
- [ ] Day 2: Settings page
  - [ ] Create `cloud/web/templates/settings.html`
  - [ ] Organization settings
  - [ ] User profile
- [ ] Day 3-4: Bug fixes & polish
  - [ ] Error handling improvements
  - [ ] Loading states
  - [ ] Mobile responsive design
  - [ ] Cross-browser testing
- [ ] Day 5: End-to-end testing
  - [ ] Complete user journey testing
  - [ ] Performance optimization
  - [ ] Security audit

**Deliverables**:
- [ ] User profile & settings page
- [ ] Production-ready UI
- [ ] All tests passing

---

**Files to Create**:
```
cloud/web/templates/
  - login.html              # Week 1
  - signup.html             # Week 1
  - devices.html            # Week 4
  - shares.html             # Week 4
  - settings.html           # Week 5

cloud/web/static/js/
  - auth.js                 # Week 1

cloud/api/routes/
  - device_config.py        # Week 3
```

**Files to Modify**:
```
cloud/web/templates/
  - index.html              # Week 2 (device selector, API updates)

cloud/web/
  - routes.py               # Week 1 (auth middleware)

cloud/api/
  - server.py               # Week 2 (WebSocket auth)
```

**Technical Approach**:

1. **Authentication Flow**:
   ```
   User → Login → POST /v1/auth/login → JWT Token
        → sessionStorage.setItem('access_token', token)
        → Redirect to /ui
        → All API calls include Authorization: Bearer {token}
   ```

2. **Multi-Device Support**:
   ```
   Load Dashboard → GET /v1/devices → Show device selector
                  → Select device → Load device config
                  → GET /v1/captures?device_id={id}
                  → Connect WebSocket with device filter
   ```

3. **Per-Device Config**:
   ```sql
   devices.config = {
     "normal_description": "...",
     "trigger": { "enabled": true, "interval_seconds": 10 },
     "notifications": { "email": { ... } }
   }
   ```

**Completion Criteria**:
- [ ] User can signup, login, logout
- [ ] Dashboard shows only user's organization devices
- [ ] Can switch between devices seamlessly
- [ ] All existing features work (captures, triggers, notifications)
- [ ] Share links can be created and accessed publicly
- [ ] WebSocket updates work per device
- [ ] No cross-org data leakage
- [ ] Mobile responsive
- [ ] Production-ready security

---

### Phase 6: Migration & Deployment ⏳ PENDING
**Status**: ⏳ Pending
**Goal**: Production deployment on Railway

**Remaining Tasks**:
- [ ] Set up production PostgreSQL on Railway
- [ ] Set up S3-compatible storage (Railway or AWS)
- [ ] Configure Supabase production project
- [ ] Test data migration on staging environment
- [ ] Create backup of production filesystem data
- [ ] Run full migration (filesystem → PostgreSQL + S3)
- [ ] Update Railway environment variables
- [ ] Configure PostgreSQL connection pooling
- [ ] Set up automated database backups (Railway)
- [ ] Deploy to production
- [ ] Update existing devices with API keys
- [ ] Create device update documentation
- [ ] Test with real devices (all existing functionality)
- [ ] Monitor for errors/performance issues

**Deliverables**:
- [ ] Production deployment on Railway
- [ ] All existing data migrated
- [ ] Documentation for device setup
- [ ] Backward compatibility verified

**Migration Checklist**:
- [ ] Backup filesystem datalake to external storage
- [ ] Run migration script in dry-run mode
- [ ] Verify image count matches (filesystem vs S3)
- [ ] Test image access via pre-signed URLs
- [ ] Create default organization for existing data
- [ ] Update device API keys on physical devices
- [ ] Switch to PostgreSQL + S3
- [ ] Monitor logs for 24 hours
- [ ] Keep filesystem data for 30 days (safety)

**Completion Criteria**:
- [ ] Zero data loss (verified)
- [ ] All devices reconnect successfully
- [ ] Dashboard loads migrated data correctly
- [ ] Image access works (thumbnails + full-size)

---

### Phase 7: Polish & Launch ⏳ PENDING
**Status**: ⏳ Pending
**Goal**: Security, analytics, onboarding

**Remaining Tasks**:
- [ ] Implement rate limiting (per-org, per-IP)
- [ ] Add CORS configuration
- [ ] Set up share link analytics tracking
- [ ] Create onboarding flow/welcome email
- [ ] Write user documentation (setup guide)
- [ ] Set up monitoring/alerting (Railway metrics)
- [ ] Security audit (SQL injection, XSS, auth bypass)
- [ ] Performance testing (load test with 100 concurrent users)
- [ ] Create pricing page (prepare for monetization)
- [ ] Launch marketing site/landing page

**Deliverables**:
- [ ] Production-ready security
- [ ] Share analytics dashboard
- [ ] User onboarding flow
- [ ] Complete documentation

**Security Audit Checklist**:
- [ ] SQL injection testing (automated + manual)
- [ ] XSS testing on all user inputs
- [ ] Auth bypass attempts (test org isolation)
- [ ] Share token brute-forcing resistance
- [ ] Rate limit enforcement
- [ ] CORS policy verification
- [ ] S3 bucket permissions (private, pre-signed only)

**Completion Criteria**:
- [ ] Security audit passed (no critical vulnerabilities)
- [ ] Load test shows <2s response time (p95)
- [ ] User documentation complete
- [ ] Analytics tracking operational

---

## Technical Stack Changes

### New Dependencies

Added to `requirements.txt`:
```python
# Core Framework
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# AI & ML
openai>=1.0.0
numpy>=1.24.0
opencv-python>=4.8.0
pillow>=10.0.0

# Database (Phase 1: Multi-tenancy)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0

# Authentication (Phase 2)
supabase>=2.3.0
python-jose[cryptography]>=3.3.0

# Storage (Phase 1)
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

# Security & Rate Limiting (Phase 6)
slowapi>=0.1.9

# QR Codes
qrcode[pil]>=7.4.0
```

### Infrastructure Requirements (Railway)

**Existing**:
- Web service (FastAPI)
- Persistent volume (`/mnt/data`)

**New (To Be Added)**:
- PostgreSQL database service (Starter plan: $5/month)
- S3-compatible storage (Railway or AWS S3)

**Environment Variables** (to add to Railway):
```bash
# Database (Railway auto-injects)
DATABASE_URL=postgresql://...

# Supabase Auth
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=xxx

# S3 Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=visant-captures
S3_REGION=us-west-2
S3_ENDPOINT_URL=...  # For Railway S3 compatibility

# Existing (keep)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SENDGRID_API_KEY=...
ALERT_FROM_EMAIL=...
```

---

## Database Schema Details

### organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Future: billing, quotas, settings
    settings JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_organizations_created ON organizations(created_at DESC);
```

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    supabase_user_id UUID UNIQUE,  -- Link to Supabase Auth

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,

    -- Future: role, permissions
    role VARCHAR(50) DEFAULT 'member',  -- admin, member, viewer

    CONSTRAINT fk_users_org FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_supabase ON users(supabase_user_id);
```

### devices
```sql
CREATE TABLE devices (
    device_id VARCHAR(255) PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    friendly_name VARCHAR(255),
    api_key VARCHAR(255) UNIQUE NOT NULL,  -- For device authentication

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP,
    last_ip VARCHAR(45),

    status VARCHAR(50) DEFAULT 'active',  -- active, inactive, transferred

    -- Metadata
    device_version VARCHAR(50),
    config JSONB DEFAULT '{}'::jsonb,  -- Per-device configuration

    CONSTRAINT fk_devices_org FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX idx_devices_org ON devices(org_id);
CREATE INDEX idx_devices_api_key ON devices(api_key);
CREATE INDEX idx_devices_last_seen ON devices(last_seen_at DESC);
```

### captures
```sql
CREATE TABLE captures (
    record_id VARCHAR(255) PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,

    -- Timestamps
    captured_at TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Storage (S3 paths)
    s3_image_key VARCHAR(500),      -- {org_id}/devices/{device_id}/captures/...
    s3_thumbnail_key VARCHAR(500),
    image_stored BOOLEAN DEFAULT false,
    thumbnail_stored BOOLEAN DEFAULT false,

    -- Classification (Cloud AI)
    state VARCHAR(50),  -- normal, abnormal, uncertain (nullable until evaluated)
    score FLOAT,
    reason TEXT,
    agent_details JSONB,

    -- Cloud AI evaluation tracking
    evaluation_status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    evaluated_at TIMESTAMP,

    -- Metadata
    trigger_label VARCHAR(100),
    normal_description_file VARCHAR(500),
    capture_metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_captures_org FOREIGN KEY (org_id) REFERENCES organizations(id),
    CONSTRAINT fk_captures_device FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Performance indexes
CREATE INDEX idx_captures_org_date ON captures(org_id, captured_at DESC);
CREATE INDEX idx_captures_device_date ON captures(device_id, captured_at DESC);
CREATE INDEX idx_captures_state ON captures(org_id, state, captured_at DESC);
CREATE INDEX idx_captures_ingested ON captures(ingested_at DESC);
CREATE INDEX idx_captures_evaluation_status ON captures(evaluation_status, ingested_at DESC);

-- For analytics (future)
CREATE INDEX idx_captures_org_state_date ON captures(org_id, state, captured_at DESC);
```

### share_links
```sql
CREATE TABLE share_links (
    token VARCHAR(32) PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,

    -- Sharing scope
    share_type VARCHAR(50) DEFAULT 'device',  -- device, capture, date_range
    capture_id VARCHAR(255),  -- If sharing single capture
    start_date TIMESTAMP,     -- If sharing date range
    end_date TIMESTAMP,

    -- Access control
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,

    -- Security (optional for MVP)
    password_hash VARCHAR(255),
    max_views INTEGER,

    -- Analytics
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP,

    CONSTRAINT fk_share_links_org FOREIGN KEY (org_id) REFERENCES organizations(id),
    CONSTRAINT fk_share_links_device FOREIGN KEY (device_id) REFERENCES devices(device_id),
    CONSTRAINT fk_share_links_creator FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX idx_share_links_token ON share_links(token);
CREATE INDEX idx_share_links_org ON share_links(org_id, created_at DESC);
CREATE INDEX idx_share_links_device ON share_links(device_id);
CREATE INDEX idx_share_links_expires ON share_links(expires_at);
```

---

## API Changes

### New Endpoints

#### Authentication (`cloud/api/routes/auth.py`)
```python
POST   /v1/auth/signup          # Create org + user (via Supabase) ✅
POST   /v1/auth/login           # Login (via Supabase) ✅
GET    /v1/auth/me              # Current user info ✅
POST   /v1/auth/logout          # Logout ⏳
```

#### Devices (`cloud/api/routes/devices.py`)
```python
POST   /v1/devices              # Register new device (returns API key) ✅
GET    /v1/devices              # List org's devices ✅
GET    /v1/devices/{id}         # Get device details ✅
PUT    /v1/devices/{id}         # Update device config ⏳
DELETE /v1/devices/{id}         # Deactivate device ⏳
GET    /v1/devices/{id}/status  # Get device status (last_seen, version) ⏳
```

#### Share Links (`cloud/api/routes/shares.py` & `cloud/api/routes/public.py`)
```python
POST   /v1/devices/{id}/share   # Create share link ✅
GET    /v1/share-links          # List org's share links ✅
DELETE /v1/share-links/{token}  # Revoke share link ⏳
PUT    /v1/share-links/{token}  # Update expiry/limits ⏳

# Public endpoints (NO AUTH)
GET    /s/{token}                # Public gallery HTML view ✅
GET    /api/s/{token}            # Public gallery JSON API ✅
GET    /s/{token}/qr            # QR code for share link ⏳
```

#### Captures (`cloud/api/routes/captures.py`)
```python
POST   /v1/captures             # Upload capture (Cloud AI - accepts image) ✅
GET    /v1/captures             # List captures (filtered by org) ✅
GET    /v1/captures/{id}        # Get capture details ✅
GET    /v1/captures/{id}/status # Poll for evaluation status (Cloud AI) ✅
DELETE /v1/captures/{id}        # Delete capture ✅
POST   /v1/captures/{id}/image  # Upload image separately (optional) ✅
```

### Authentication Flow

#### User Authentication (JWT)
```python
# Login request
POST /v1/auth/login
{
    "email": "user@example.com",
    "password": "secure_password"
}

# Response
{
    "access_token": "eyJhbGc...",  # JWT token
    "refresh_token": "...",
    "user": {
        "id": "uuid",
        "email": "user@example.com",
        "org_id": "uuid",
        "org_name": "Acme Corp"
    }
}

# Subsequent requests
GET /v1/captures
Authorization: Bearer eyJhbGc...
```

#### Device Authentication (API Key)
```python
# Capture upload
POST /v1/captures
Authorization: Bearer device_api_key_abc123
{
    "device_id": "camera-01",
    "image_base64": "...",
    ...
}
```

---

## File Structure (New Components)

```
visant/
├── cloud/
│   ├── api/
│   │   ├── auth/                        # ✅ NEW: Authentication
│   │   │   ├── __init__.py
│   │   │   ├── middleware.py            # JWT validation middleware
│   │   │   ├── dependencies.py          # FastAPI auth dependencies
│   │   │   └── supabase_client.py       # Supabase integration
│   │   │
│   │   ├── database/                    # ✅ NEW: Database layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # SQLAlchemy declarative base
│   │   │   ├── session.py               # DB connection/pooling
│   │   │   └── models.py                # SQLAlchemy models (all tables)
│   │   │
│   │   ├── storage/                     # ✅ NEW: Storage abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Storage interface (ABC)
│   │   │   ├── s3.py                    # S3 implementation
│   │   │   ├── filesystem.py            # Legacy filesystem (fallback)
│   │   │   └── presigned.py             # Pre-signed URL generation
│   │   │
│   │   ├── routes/                      # ✅ NEW: Organized routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # Auth endpoints
│   │   │   ├── devices.py               # Device provisioning
│   │   │   ├── captures.py              # Capture endpoints (refactored for Cloud AI)
│   │   │   ├── shares.py                # Share link management
│   │   │   └── public.py                # Public gallery
│   │   │
│   │   ├── workers/                     # ✅ NEW: Background workers
│   │   │   ├── __init__.py
│   │   │   └── ai_evaluator.py          # Cloud AI evaluation worker
│   │   │
│   │   ├── utils/                       # ✅ NEW: Utilities
│   │   │   └── qrcode_gen.py            # QR code generation
│   │   │
│   │   ├── server.py                    # ⏳ MODIFY: Updated with auth
│   │   ├── main.py                      # ⏳ MODIFY: Add DB init
│   │   └── ... (existing files)
│   │
│   └── web/
│       ├── templates/
│       │   ├── login.html               # ⏳ NEW: Login page
│       │   ├── signup.html              # ⏳ NEW: Signup page
│       │   ├── devices.html             # ⏳ NEW: Device management
│       │   ├── share_links.html         # ⏳ NEW: Share link management
│       │   └── dashboard.html           # ⏳ MODIFY: Multi-device support
│       │
│       └── static/
│           ├── auth.js                  # ⏳ NEW: Auth client logic
│           ├── share.js                 # ⏳ NEW: Share functionality
│           └── ... (existing files)
│
├── scripts/
│   ├── migrate_to_multitenancy.py       # ✅ NEW: Data migration script
│   ├── create_test_org.py               # ⏳ NEW: Setup test data
│   └── seed_database.py                 # ⏳ NEW: Dev database seeding
│
├── alembic/                             # ✅ NEW: Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20251106_2247_8af79cab0d8d_initial_schema.py      # ✅
│       └── 20251107_0020_747d6fbf4733_add_evaluation_status_to_captures.py  # ✅
│
├── config/
│   └── cloud.json                       # ✅ MODIFIED: Add DB config
│
├── alembic.ini                          # ✅ NEW: Alembic config
├── requirements.txt                     # ✅ MODIFIED: Add new deps
├── test_auth_server.py                  # ✅ NEW: Test server for Phases 2-4
├── test_cloud_ai.py                     # ✅ NEW: Cloud AI test script
├── PROJECT_PLAN.md                      # ✅ NEW: This file
└── README.md                            # ⏳ UPDATE: New architecture docs
```

---

## Remaining Tasks

### High Priority (Next 1-2 Weeks)

#### 1. Multi-Tenant Web Dashboard
- [ ] Create login page with Supabase UI
- [ ] Migrate existing dashboard to use new API endpoints
- [ ] Add device selector dropdown
- [ ] Update WebSocket filtering by org_id
- [ ] Add share link management UI
- [ ] Add device registration wizard
- [ ] Test all existing features with multi-device

**Files to Create/Modify**:
- `cloud/web/templates/login.html` (NEW)
- `cloud/web/templates/signup.html` (NEW)
- `cloud/web/templates/dashboard.html` (MODIFY)
- `cloud/web/routes.py` (MODIFY)
- `cloud/web/static/auth.js` (NEW)

#### 2. Production Deployment Setup
- [ ] Create Railway PostgreSQL service
- [ ] Set up S3-compatible storage (Railway or AWS)
- [ ] Create Supabase production project
- [ ] Configure environment variables
- [ ] Set up database backups
- [ ] Test migration script on staging data

#### 3. Device Client Updates
- [ ] Update device client to use new API endpoints
- [ ] Change capture upload to send raw images (base64)
- [ ] Implement polling for Cloud AI results
- [ ] Add API key authentication
- [ ] Test on physical Raspberry Pi devices
- [ ] Create device update documentation

**Files to Update**:
- Device client code (capture upload logic)
- Device configuration (add API key)
- Documentation for device setup

---

### Medium Priority (2-4 Weeks)

#### 4. Security & Performance
- [ ] Implement rate limiting (slowapi)
- [ ] Add CORS configuration
- [ ] Security audit (SQL injection, XSS, auth bypass)
- [ ] Load testing (100 concurrent users)
- [ ] Monitor performance metrics
- [ ] Set up error tracking/logging

#### 5. Documentation
- [ ] User documentation (setup guide)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Device setup guide
- [ ] Migration guide for existing deployments
- [ ] Troubleshooting guide

#### 6. Analytics & Monitoring
- [ ] Set up share link analytics
- [ ] Add usage metrics dashboard
- [ ] Configure Railway monitoring
- [ ] Set up alerts for errors/downtime
- [ ] Track key metrics (DAU, captures/day, etc.)

---

### Low Priority (Post-Launch)

#### 7. Enhanced Features
- [ ] User roles & permissions (admin, member, viewer)
- [ ] Advanced sharing options (password protection, custom expiry)
- [ ] Analytics dashboard (trends, reports)
- [ ] Webhook integrations
- [ ] Mobile app (iOS/Android)

#### 8. Billing & Monetization
- [ ] Stripe integration
- [ ] Usage-based pricing
- [ ] Subscription tiers
- [ ] Invoicing for enterprise
- [ ] Usage dashboard

---

## Success Metrics

### MVP Launch Criteria

**Technical**:
- [x] 3+ test organizations with devices tested (Alice, Bob, test orgs)
- [ ] All existing data migrated from filesystem (pending)
- [x] Zero cross-org data leakage (tested via API)
- [x] Cloud AI classification works
- [ ] <2s p95 response time (load tested)
- [ ] 99% uptime over 7 days (Railway metrics)

**Product**:
- [x] User can signup, login, register device (API tested)
- [x] Public share links work without auth
- [ ] Share page is beautiful and mobile-friendly (basic version exists)
- [ ] Device setup takes <10 minutes (pending device client update)

**Business**:
- [ ] Pricing page live (prepare for monetization)
- [ ] User documentation complete
- [ ] Support email operational

---

## Timeline Summary

| Phase | Status | Duration | Deliverables |
|-------|--------|----------|--------------|
| 1. Foundation & Database | ✅ Complete | 1 week | PostgreSQL schema, storage abstraction |
| 2. Auth & Multi-Tenancy | ✅ Complete | 1 week | Supabase auth, org isolation, API endpoints |
| 3. Public Sharing | ✅ Complete | 3 days | Share links, public gallery, QR codes |
| 4. Cloud AI Evaluation | ✅ Complete | 2 days | Background AI, polling, async processing |
| 5. Dashboard Updates | 🔄 In Progress | 1-2 weeks | Multi-tenant UI, device management |
| 6. Deployment | ⏳ Pending | 1 week | Production setup, migration, testing |
| 7. Polish & Launch | ⏳ Pending | 1 week | Security, docs, analytics |

**Current Status**: Backend API complete (Phases 1-4), UI migration and deployment remaining
**Estimated Time to Launch**: 2-3 weeks from now

---

## Next Steps

### This Week (Immediate Actions)

1. **Start Phase 5 - Dashboard Updates**:
   - [ ] Create login/signup pages
   - [ ] Migrate existing dashboard to new API
   - [ ] Test with multiple organizations

2. **Prepare for Deployment**:
   - [ ] Set up Railway PostgreSQL service
   - [ ] Configure S3 storage
   - [ ] Test migration script

3. **Update Device Clients**:
   - [ ] Modify capture upload logic
   - [ ] Add API key authentication
   - [ ] Test Cloud AI flow

---

**Last Updated**: 2025-11-07
**Status**: Phases 2-4 Complete, Dashboard & Deployment In Progress
**Owner**: Development Team
**Next Review**: After Phase 5 completion

---

*End of Document*

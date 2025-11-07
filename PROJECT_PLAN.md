# Visant Multi-User Commercial Upgrade Plan

**Version**: 1.0
**Created**: 2025-01-06
**Status**: In Progress
**Target Launch**: 6 weeks from approval

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
captures (record_id, org_id, device_id, s3_image_key, state, score, reason)

devices (device_id)
    ↓ has many
share_links (token, org_id, device_id, expires_at, view_count)
```

---

## Implementation Phases

### Phase 1: Foundation & Database (Week 1-2)
**Goal**: Migrate from filesystem to PostgreSQL + S3

**Tasks**:
- [ ] Set up PostgreSQL database (Railway service)
- [ ] Design database schema with SQLAlchemy models
- [ ] Implement Alembic migrations
- [ ] Set up S3-compatible storage (Railway or AWS)
- [ ] Write data migration script (JSON files → PostgreSQL)
- [ ] Migrate existing images to S3 (with progress tracking)
- [ ] Update storage layer to abstract filesystem/S3
- [ ] Add feature flag to switch between filesystem/S3

**Deliverables**:
- ✅ PostgreSQL schema with 5 core tables
- ✅ Migration script tested on production data
- ✅ S3 storage operational
- ✅ Feature flag to switch between filesystem/S3

**Files to Create**:
- `cloud/api/database/models.py` - SQLAlchemy models
- `cloud/api/database/session.py` - DB connection pooling
- `cloud/api/storage/s3.py` - S3 storage implementation
- `scripts/migrate_to_multitenancy.py` - Migration script
- `alembic/versions/001_initial_schema.py` - Initial migration

**Completion Criteria**:
- [ ] Can query captures from PostgreSQL instead of filesystem
- [ ] Images served from S3 with pre-signed URLs
- [ ] Migration script tested on copy of production data
- [ ] All existing tests pass with new storage backend

---

### Phase 2: Authentication & Multi-Tenancy (Week 2-3)
**Goal**: Add user authentication and org isolation

**Tasks**:
- [ ] Create Supabase project and configure
- [ ] Integrate Supabase Auth client
- [ ] Create JWT validation middleware
- [ ] Add org_id filtering to all queries
- [ ] Implement Row-Level Security (RLS) policies
- [ ] Build login/signup pages (use Supabase UI components)
- [ ] Add device API key authentication
- [ ] Create device provisioning endpoint (generates API key)
- [ ] Update all existing endpoints with auth middleware
- [ ] Add authorization checks (org ownership)

**Deliverables**:
- ✅ Working login/signup flow
- ✅ All API endpoints require authentication
- ✅ Device API key system operational
- ✅ Complete tenant isolation (security tested)

**Files to Create**:
- `cloud/api/auth/middleware.py` - JWT validation
- `cloud/api/auth/dependencies.py` - FastAPI auth dependencies
- `cloud/api/auth/supabase_client.py` - Supabase integration
- `cloud/api/routes/auth.py` - Auth endpoints
- `cloud/api/routes/devices.py` - Device provisioning
- `cloud/web/templates/login.html` - Login page
- `cloud/web/templates/signup.html` - Signup page

**API Endpoints to Add**:
```
POST /v1/auth/signup      # Create org + user
POST /v1/auth/login       # Get JWT token
GET  /v1/auth/me          # Current user info
POST /v1/devices          # Register device (returns API key)
GET  /v1/devices          # List org's devices
```

**Completion Criteria**:
- [ ] Can signup, login, access dashboard
- [ ] Devices authenticate with API keys
- [ ] Org A cannot see Org B's data (tested)
- [ ] All existing endpoints work with auth

---

### Phase 3: Public Sharing (Week 3) ⭐ **GROWTH PRIORITY**
**Goal**: Enable viral sharing via public links

**Tasks**:
- [ ] Create share_links table and model
- [ ] Build share link generation endpoint
- [ ] Design beautiful public gallery template (marketing-focused)
- [ ] Implement pre-signed S3 URL generation (1-hour expiry)
- [ ] Add "Share Camera" button to dashboard
- [ ] Build one-click copy link functionality
- [ ] Add social share buttons (SMS, Email, Twitter)
- [ ] Implement QR code generation for share links
- [ ] Create share link management UI (list, revoke)
- [ ] Implement link expiration (7 days default)
- [ ] Add rate limiting on public share endpoint

**Deliverables**:
- ✅ `/s/{token}` public view page (no login required)
- ✅ One-click share from dashboard
- ✅ Social sharing capabilities
- ✅ Growth-optimized shared view with CTAs

**Files to Create**:
- `cloud/api/routes/share_links.py` - Share link endpoints
- `cloud/web/templates/shared_camera.html` - Public gallery view
- `cloud/web/static/share.js` - Share functionality
- `cloud/api/database/models.py` - Add ShareLink model

**Public Share Page Features**:
```html
<!-- /s/{token} - The Growth Page -->
- Beautiful thumbnail grid (same UX as dashboard)
- Device name and stats (X captures, Y abnormals)
- AI classifications visible
- "Get Visant for Your Cameras" CTA prominently placed
- Social share buttons (SMS, Email, Twitter)
- QR code for in-person sharing
- "Powered by Visant" branding
```

**Completion Criteria**:
- [ ] Can generate share link from dashboard
- [ ] Public link works without login
- [ ] Share page is beautiful and mobile-friendly
- [ ] CTAs track clicks (analytics ready)
- [ ] Rate limiting prevents abuse

---

### Phase 4: Dashboard Updates (Week 3-4)
**Goal**: Adapt existing UI for multi-user/multi-device

**Tasks**:
- [ ] Add device selector/filter dropdown
- [ ] Show device status (online/offline based on last_seen)
- [ ] Build device registration wizard (step-by-step)
- [ ] Add share link management panel
- [ ] Update WebSocket to filter by org_id
- [ ] Add user profile/settings page
- [ ] Create organization settings page
- [ ] Update capture gallery to show device name
- [ ] Add device-specific configuration UI

**Deliverables**:
- ✅ Multi-device dashboard
- ✅ Device management UI
- ✅ Share link management
- ✅ User/org settings

**Files to Modify**:
- `cloud/web/templates/dashboard.html` - Add device selector
- `cloud/web/routes.py` - Update to filter by org_id
- `cloud/api/server.py` - Update WebSocket filtering

**New Features in Dashboard**:
```
┌──────────────────────────────────────┐
│  Visant | My Org                      │
│  ┌────────────┐  [+ Add Device]      │
│  │ All Devices▾│                      │
│  │ Floor 1 Cam │  🟢 Online           │
│  │ Parking Lot │  🟢 Online           │
│  │ Back Door   │  🔴 Offline (2h ago) │
│  └────────────┘                       │
│                                        │
│  Recent Captures                       │
│  [Thumbnail Grid]                      │
│                                        │
│  Share Links                           │
│  • Floor 1 Camera - Expires Jan 13    │
│    https://visant.app/s/k7mX9pQ2      │
│    [Copy] [Revoke]                     │
└──────────────────────────────────────┘
```

**Completion Criteria**:
- [ ] Can manage multiple devices from single dashboard
- [ ] Can create and revoke share links
- [ ] Device status updates in real-time
- [ ] All existing features work (triggers, config, alerts)

---

### Phase 5: Migration & Deployment (Week 4-5)
**Goal**: Production deployment on Railway

**Tasks**:
- [ ] Test data migration on staging environment
- [ ] Create backup of production filesystem data
- [ ] Run full migration (filesystem → PostgreSQL + S3)
- [ ] Update Railway environment variables
- [ ] Configure PostgreSQL connection pooling
- [ ] Set up automated database backups (Railway)
- [ ] Deploy to production with feature flag (gradual rollout)
- [ ] Create device update documentation
- [ ] Test with real devices (all existing functionality)
- [ ] Monitor for errors/performance issues

**Deliverables**:
- ✅ Production deployment on Railway
- ✅ All existing data migrated
- ✅ Documentation for device setup
- ✅ Backward compatibility verified

**Migration Checklist**:
- [ ] Backup filesystem datalake to external storage
- [ ] Run migration script in dry-run mode
- [ ] Verify image count matches (filesystem vs S3)
- [ ] Test image access via pre-signed URLs
- [ ] Create default organization for existing data
- [ ] Update device API keys on physical devices
- [ ] Switch feature flag to use PostgreSQL + S3
- [ ] Monitor logs for 24 hours
- [ ] Keep filesystem data for 30 days (safety)

**Completion Criteria**:
- [ ] Zero data loss (verified)
- [ ] All devices reconnect successfully
- [ ] Dashboard loads migrated data correctly
- [ ] Image access works (thumbnails + full-size)

---

### Phase 6: Polish & Launch (Week 5-6)
**Goal**: Security, analytics, onboarding

**Tasks**:
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
- ✅ Production-ready security
- ✅ Share analytics dashboard
- ✅ User onboarding flow
- ✅ Complete documentation

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

Add to `requirements.txt`:
```python
# Authentication
supabase>=2.3.0              # Supabase client for auth

# Database
sqlalchemy>=2.0.25           # ORM
psycopg2-binary>=2.9.9       # PostgreSQL driver
alembic>=1.13.1              # Database migrations

# Storage
boto3>=1.34.34               # S3 SDK (AWS/Railway compatible)

# Security
python-jose[cryptography]>=3.3.0  # JWT handling
slowapi>=0.1.9               # Rate limiting

# Utilities
qrcode[pil]>=7.4.2           # QR code generation
```

### Infrastructure Requirements (Railway)

**Existing**:
- Web service (FastAPI)
- Persistent volume (`/mnt/data`)

**New**:
- PostgreSQL database service (Starter plan: $5/month)
- S3-compatible storage (Railway or AWS S3)

**Environment Variables** (add to Railway):
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

    -- Classification
    state VARCHAR(50) NOT NULL,  -- normal, abnormal, uncertain
    score FLOAT,
    reason TEXT,
    agent_details JSONB,

    -- Metadata
    trigger_label VARCHAR(100),
    normal_description_file VARCHAR(500),
    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_captures_org FOREIGN KEY (org_id) REFERENCES organizations(id),
    CONSTRAINT fk_captures_device FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

-- Performance indexes
CREATE INDEX idx_captures_org_date ON captures(org_id, captured_at DESC);
CREATE INDEX idx_captures_device_date ON captures(device_id, captured_at DESC);
CREATE INDEX idx_captures_state ON captures(org_id, state, captured_at DESC);
CREATE INDEX idx_captures_ingested ON captures(ingested_at DESC);

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

### Row-Level Security (RLS) Policies

```sql
-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE captures ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;

-- Example policy (users can only see their org's data)
CREATE POLICY org_isolation ON captures
    FOR ALL
    USING (org_id = current_setting('app.current_org_id')::uuid);
```

---

## API Changes

### New Endpoints

#### Authentication (`cloud/api/routes/auth.py`)
```python
POST   /v1/auth/signup          # Create org + user (via Supabase)
POST   /v1/auth/login           # Login (via Supabase)
GET    /v1/auth/me              # Current user info
POST   /v1/auth/logout          # Logout
```

#### Organizations (`cloud/api/routes/organizations.py`)
```python
GET    /v1/organizations/{id}   # Get org details
PUT    /v1/organizations/{id}   # Update org settings
```

#### Devices (`cloud/api/routes/devices.py`)
```python
POST   /v1/devices              # Register new device (returns API key)
GET    /v1/devices              # List org's devices
GET    /v1/devices/{id}         # Get device details
PUT    /v1/devices/{id}         # Update device config
DELETE /v1/devices/{id}         # Deactivate device
GET    /v1/devices/{id}/status  # Get device status (last_seen, version)
```

#### Share Links (`cloud/api/routes/share_links.py`)
```python
POST   /v1/devices/{id}/share   # Create share link
GET    /v1/share-links          # List org's share links
GET    /v1/share-links/{token}  # Get share link details (auth required)
DELETE /v1/share-links/{token}  # Revoke share link
PUT    /v1/share-links/{token}  # Update expiry/limits

# Public endpoints (NO AUTH)
GET    /s/{token}                # Public gallery view
GET    /s/{token}/qr            # QR code for share link
GET    /s/{token}/captures      # Get captures JSON (for AJAX)
```

### Modified Endpoints (Add Auth + Filtering)

**All existing endpoints now require authentication and filter by org_id:**

```python
# Capture endpoints (cloud/api/routes/captures.py)
POST   /v1/captures             # Now requires device API key
                                # Auto-adds org_id from device
GET    /v1/captures             # Filtered by user's org_id
GET    /v1/captures/{id}        # Authorization check (org_id match)

# Device config (cloud/api/server.py)
GET    /v1/device-config        # Filtered by device's org_id
                                # Requires device API key

# Manual trigger
POST   /v1/manual-trigger       # Filtered by user's org_id
GET    /v1/manual-trigger/stream # Filtered by device's org_id

# UI endpoints (cloud/web/routes.py)
GET    /ui                      # Requires user login
GET    /ui/captures             # Filtered by user's org_id
POST   /ui/notifications        # Filtered by user's org_id
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
    "device_id": "floor-01-cam",
    "image_base64": "...",
    ...
}

# Device config polling
GET /v1/device-config?device_id_override=floor-01-cam
Authorization: Bearer device_api_key_abc123
```

---

## File Structure (New Components)

```
visant/
├── cloud/
│   ├── api/
│   │   ├── auth/                        # NEW: Authentication
│   │   │   ├── __init__.py
│   │   │   ├── middleware.py            # JWT validation middleware
│   │   │   ├── dependencies.py          # FastAPI auth dependencies
│   │   │   └── supabase_client.py       # Supabase integration
│   │   │
│   │   ├── database/                    # NEW: Database layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # SQLAlchemy declarative base
│   │   │   ├── session.py               # DB connection/pooling
│   │   │   ├── models.py                # SQLAlchemy models (all tables)
│   │   │   └── migrations/              # Alembic migrations
│   │   │       ├── env.py
│   │   │       ├── script.py.mako
│   │   │       └── versions/
│   │   │           ├── 001_initial_schema.py
│   │   │           └── 002_add_share_links.py
│   │   │
│   │   ├── storage/                     # NEW: Storage abstraction
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Storage interface (ABC)
│   │   │   ├── s3.py                    # S3 implementation
│   │   │   └── filesystem.py            # Legacy filesystem (fallback)
│   │   │
│   │   ├── routes/                      # NEW: Organized routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # Auth endpoints
│   │   │   ├── organizations.py         # Org management
│   │   │   ├── devices.py               # Device provisioning
│   │   │   ├── captures.py              # Capture endpoints (refactored)
│   │   │   └── share_links.py           # Public sharing
│   │   │
│   │   ├── server.py                    # MODIFIED: Updated with auth
│   │   ├── main.py                      # MODIFIED: Add DB init
│   │   └── ... (existing files)
│   │
│   └── web/
│       ├── templates/
│       │   ├── login.html               # NEW: Login page
│       │   ├── signup.html              # NEW: Signup page
│       │   ├── shared_camera.html       # NEW: Public share view
│       │   ├── devices.html             # NEW: Device management
│       │   ├── share_links.html         # NEW: Share link management
│       │   └── dashboard.html           # MODIFIED: Multi-device support
│       │
│       └── static/
│           ├── auth.js                  # NEW: Auth client logic
│           ├── share.js                 # NEW: Share functionality
│           └── ... (existing files)
│
├── scripts/
│   ├── migrate_to_multitenancy.py       # NEW: Data migration script
│   ├── create_test_org.py               # NEW: Setup test data
│   └── seed_database.py                 # NEW: Dev database seeding
│
├── config/
│   └── cloud.json                       # MODIFIED: Add DB config
│
├── alembic.ini                          # NEW: Alembic config
├── requirements.txt                     # MODIFIED: Add new deps
├── PROJECT_PLAN.md                      # NEW: This file
└── README.md                            # UPDATE: New architecture docs
```

---

## Security Considerations

### Authentication
- ✅ **JWT tokens** with short expiry (1 hour access, 7 day refresh)
- ✅ **Refresh token** mechanism (via Supabase)
- ✅ **Device API keys** (UUID v4, high entropy, 128-bit)
- ✅ **Password hashing** (handled by Supabase, bcrypt)
- ✅ **HTTPS only** (Railway enforces)

### Authorization
- ✅ **Row-Level Security (RLS)** in PostgreSQL
- ✅ **All queries filtered by org_id** (middleware enforced)
- ✅ **Device ownership verification** (API key → device → org)
- ✅ **Share link token validation** (crypto-secure tokens)

### Data Protection
- ✅ **HTTPS only** (Railway default, enforce redirect)
- ✅ **SQL injection protection** (SQLAlchemy parameterized queries)
- ✅ **CORS configuration** (whitelist domains)
- ✅ **Rate limiting** (per-org: 1000 req/hour, per-IP: 100 req/hour)
- ✅ **Pre-signed S3 URLs** (time-limited, 1 hour expiry)
- ✅ **Secrets in env vars** (never in code or logs)

### Public Sharing Security
- ✅ **Tokens cryptographically secure** (`secrets.token_urlsafe(24)`)
- ✅ **Rate limiting** on share endpoints (100 views/hour per IP)
- ✅ **Optional password protection** (bcrypt hashed)
- ✅ **Expiration enforcement** (7 days default, max 90 days)
- ✅ **No sensitive data** in public view (device location, org name hidden)
- ✅ **Revocation** (instant, DB-driven)

### Input Validation
- ✅ **Pydantic models** for all API inputs
- ✅ **Email validation** (regex + DNS check)
- ✅ **Image size limits** (max 10MB per capture)
- ✅ **SQL injection** (ORM prevents)
- ✅ **XSS protection** (template escaping)

### Monitoring & Auditing
- ✅ **Failed login tracking** (Supabase built-in)
- ✅ **Share link access logs** (IP, timestamp, user agent)
- ✅ **Device activity logs** (last_seen, last_ip)
- ✅ **Error logging** (sanitized, no secrets)

---

## Scalability Architecture

### Current (MVP) - Supports 1K orgs, 10K devices, 1M captures

**Database**:
- Single PostgreSQL instance (Railway Starter: 2 CPU, 8GB RAM)
- Connection pooling (SQLAlchemy: 20 connections, 10 overflow)
- Indexes on all query patterns (org_id, device_id, captured_at)

**Storage**:
- S3-compatible storage (unlimited scale)
- Pre-signed URLs (no server bandwidth consumption)
- Thumbnail generation on upload (server-side)

**API**:
- Single Railway web service (async FastAPI)
- WebSocket connection pooling
- In-memory caching (LRU cache for hot data)

---

### Future (100K orgs, 1M devices, 100M+ captures)

**Database Scaling**:
- Read replicas for dashboard queries (PostgreSQL replication)
- Partitioning captures table by org_id + date range
- Caching layer (Redis) for:
  - Recent captures (TTL: 5 minutes)
  - Device status (TTL: 30 seconds)
  - Share link metadata (TTL: until expiry)
- Archive old captures to cold storage (S3 Glacier)

**Storage Scaling**:
- CDN for thumbnails (CloudFront or Cloudflare)
- Lazy thumbnail generation (generate on first view)
- Image compression pipeline (reduce storage costs 50%)
- Multi-region S3 buckets (low latency globally)

**API Scaling**:
- Horizontal scaling (Railway auto-scaling, 2-10 instances)
- Load balancer (Railway built-in)
- Background job queue (Celery + Redis) for:
  - AI classification (async)
  - Email notifications (batched)
  - Image processing (thumbnails, compression)
- Separate worker services for heavy tasks

**Multi-Tenancy Scaling**:
- Unlimited organizations (org_id indexed)
- Isolated data per org (RLS + query filtering)
- Per-org resource limits (quotas enforced at API layer):
  - Storage: 100GB free, pay for overages
  - Captures/day: 1000 free, throttled above
  - Devices: 10 free, $5/month per additional
- Tenant-specific configuration (JSONB columns, no schema changes)

---

## Migration Strategy

### Data Migration Script (`scripts/migrate_to_multitenancy.py`)

**Purpose**: Migrate existing filesystem-based data to PostgreSQL + S3

**Steps**:

#### 1. Pre-Migration Checks
```python
- Check PostgreSQL connection
- Check S3 bucket access (write test file)
- Verify filesystem datalake readable
- Estimate migration time (based on capture count)
- Confirm user approval (interactive prompt)
```

#### 2. Create Default Organization
```python
org_name = input("Enter organization name for existing data: ")
org = Organization(name=org_name)
db.add(org)
db.commit()

# Create admin user
admin_email = input("Enter admin email: ")
admin_password = input("Enter admin password: ")
user = create_user_in_supabase(admin_email, admin_password, org.id)
```

#### 3. Scan Filesystem Datalake
```python
# Parse directory structure: /YYYY/MM/DD/{record_id}.json
capture_files = glob.glob(f"{datalake_root}/**/*.json", recursive=True)
total_captures = len(capture_files)
print(f"Found {total_captures} captures to migrate")

# Extract unique device_ids
device_ids = set()
for file in capture_files:
    metadata = json.load(file)
    device_ids.add(metadata['metadata']['device_id'])

print(f"Found {len(device_ids)} unique devices")
```

#### 4. Create Devices
```python
for device_id in device_ids:
    api_key = secrets.token_urlsafe(32)
    device = Device(
        device_id=device_id,
        org_id=org.id,
        friendly_name=device_id.replace('-', ' ').title(),
        api_key=api_key,
        status='active'
    )
    db.add(device)

    # Save API key for user
    print(f"Device: {device_id} → API Key: {api_key}")

db.commit()
```

#### 5. Upload Images to S3 & Insert Captures
```python
from tqdm import tqdm  # Progress bar

for capture_file in tqdm(capture_files, desc="Migrating captures"):
    # Parse JSON
    metadata = json.load(open(capture_file))
    record_id = metadata['record_id']
    device_id = metadata['metadata']['device_id']

    # Upload image to S3
    image_path = capture_file.replace('.json', '.jpeg')
    if os.path.exists(image_path):
        s3_image_key = f"{org.id}/devices/{device_id}/captures/{YYYY}/{MM}/{DD}/{record_id}.jpeg"
        s3_client.upload_file(image_path, bucket, s3_image_key)

    # Upload thumbnail to S3
    thumb_path = capture_file.replace('.json', '_thumb.jpeg')
    if os.path.exists(thumb_path):
        s3_thumb_key = f"{org.id}/devices/{device_id}/captures/{YYYY}/{MM}/{DD}/{record_id}_thumb.jpeg"
        s3_client.upload_file(thumb_path, bucket, s3_thumb_key)

    # Insert into PostgreSQL
    capture = Capture(
        record_id=record_id,
        org_id=org.id,
        device_id=device_id,
        captured_at=metadata['captured_at'],
        ingested_at=metadata['ingested_at'],
        s3_image_key=s3_image_key if os.path.exists(image_path) else None,
        s3_thumbnail_key=s3_thumb_key if os.path.exists(thumb_path) else None,
        image_stored=os.path.exists(image_path),
        thumbnail_stored=os.path.exists(thumb_path),
        state=metadata['classification']['state'],
        score=metadata['classification']['score'],
        reason=metadata['classification']['reason'],
        agent_details=metadata['classification'].get('agent_details'),
        trigger_label=metadata['metadata'].get('trigger_label'),
        metadata=metadata['metadata']
    )
    db.add(capture)

    # Commit in batches (every 100 captures)
    if len(db.new) >= 100:
        db.commit()

db.commit()  # Final commit
```

#### 6. Validation
```python
# Verify data integrity
db_capture_count = db.query(Capture).count()
assert db_capture_count == total_captures, "Capture count mismatch!"

# Test image access
sample_capture = db.query(Capture).first()
presigned_url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': sample_capture.s3_image_key},
    ExpiresIn=3600
)
response = requests.get(presigned_url)
assert response.status_code == 200, "Image access failed!"

print("✅ Migration complete and validated")
```

#### 7. Output Summary
```python
print("\n=== Migration Summary ===")
print(f"Organization: {org.name} ({org.id})")
print(f"Admin User: {admin_email}")
print(f"Devices: {len(device_ids)}")
print(f"Captures: {db_capture_count}")
print(f"S3 Bucket: {bucket}")
print("\n=== Next Steps ===")
print("1. Update device configuration files with new API keys:")
for device_id, api_key in device_api_keys.items():
    print(f"   {device_id}: {api_key}")
print("2. Set feature flag: STORAGE_BACKEND=s3 in Railway")
print("3. Restart server")
print("4. Test dashboard login")
print("5. Keep filesystem backup for 30 days")
```

### Safety Mechanisms

**Dry-Run Mode**:
```bash
python scripts/migrate_to_multitenancy.py --dry-run
# Simulates migration without writing to DB/S3
```

**Rollback Plan**:
```python
# If migration fails, restore from filesystem
# 1. Keep filesystem data for 30 days
# 2. Feature flag allows switching back to filesystem
# 3. PostgreSQL can be dropped and recreated
```

**Feature Flag**:
```python
# config/cloud.json
{
  "storage": {
    "backend": "filesystem",  # or "s3" after migration
    ...
  }
}

# In code
if config.storage.backend == "s3":
    storage = S3Storage()
else:
    storage = FilesystemStorage()
```

---

## Testing Strategy

### Unit Tests (`pytest`)

**Database Models** (`tests/test_models.py`):
```python
def test_organization_creation():
    org = Organization(name="Test Org")
    assert org.name == "Test Org"
    assert org.id is not None

def test_user_org_relationship():
    org = Organization(name="Test Org")
    user = User(email="test@example.com", org_id=org.id)
    assert user.organization == org
```

**Auth Middleware** (`tests/test_auth.py`):
```python
def test_jwt_validation():
    token = create_jwt_token(user_id="123", org_id="456")
    decoded = validate_jwt_token(token)
    assert decoded['user_id'] == "123"

def test_invalid_jwt_rejected():
    with pytest.raises(HTTPException):
        validate_jwt_token("invalid_token")
```

**Storage Abstraction** (`tests/test_storage.py`):
```python
def test_s3_upload():
    storage = S3Storage()
    key = storage.upload(image_bytes, "org/device/capture.jpeg")
    assert storage.exists(key)

def test_filesystem_fallback():
    storage = FilesystemStorage()
    path = storage.upload(image_bytes, "capture.jpeg")
    assert os.path.exists(path)
```

---

### Integration Tests (`tests/integration/`)

**End-to-End User Signup**:
```python
def test_user_signup_flow():
    # 1. Signup
    response = client.post("/v1/auth/signup", json={
        "email": "newuser@example.com",
        "password": "SecurePass123",
        "org_name": "New Org"
    })
    assert response.status_code == 201

    # 2. Login
    response = client.post("/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 200
    token = response.json()['access_token']

    # 3. Access dashboard
    response = client.get("/v1/captures", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
```

**Device Registration + Capture Upload**:
```python
def test_device_lifecycle():
    # 1. Register device
    response = client.post("/v1/devices", json={
        "device_id": "test-cam-01",
        "friendly_name": "Test Camera"
    }, headers=auth_headers)
    assert response.status_code == 201
    api_key = response.json()['api_key']

    # 2. Upload capture
    response = client.post("/v1/captures", json={
        "device_id": "test-cam-01",
        "image_base64": base64_image,
        ...
    }, headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200

    # 3. View in dashboard
    response = client.get("/v1/captures", headers=auth_headers)
    captures = response.json()
    assert len(captures) == 1
```

**Multi-Tenancy Isolation**:
```python
def test_org_data_isolation():
    # Create 2 orgs with devices
    org1_user = create_test_user(org_name="Org 1")
    org2_user = create_test_user(org_name="Org 2")

    org1_device = create_test_device(org1_user)
    org2_device = create_test_device(org2_user)

    # Upload captures
    org1_capture = upload_test_capture(org1_device)
    org2_capture = upload_test_capture(org2_device)

    # Org 1 user should only see their capture
    response = client.get("/v1/captures", headers=org1_user.auth_headers)
    captures = response.json()
    assert len(captures) == 1
    assert captures[0]['record_id'] == org1_capture.record_id

    # Org 2 user should only see their capture
    response = client.get("/v1/captures", headers=org2_user.auth_headers)
    captures = response.json()
    assert len(captures) == 1
    assert captures[0]['record_id'] == org2_capture.record_id
```

**Public Share Link**:
```python
def test_public_share_link():
    # 1. Create share link (authenticated)
    response = client.post(f"/v1/devices/{device_id}/share",
                          headers=auth_headers)
    assert response.status_code == 201
    share_url = response.json()['share_url']
    token = share_url.split('/')[-1]

    # 2. View public page (no auth)
    response = client.get(f"/s/{token}")
    assert response.status_code == 200
    assert "Test Device" in response.text

    # 3. Revoke link
    response = client.delete(f"/v1/share-links/{token}",
                            headers=auth_headers)
    assert response.status_code == 204

    # 4. Verify link no longer works
    response = client.get(f"/s/{token}")
    assert response.status_code == 410  # Gone
```

---

### Security Tests (`tests/security/`)

**SQL Injection Attempts**:
```python
def test_sql_injection_protection():
    # Attempt SQL injection in email field
    response = client.post("/v1/auth/login", json={
        "email": "admin' OR '1'='1",
        "password": "anything"
    })
    assert response.status_code == 401  # Not 500 (no crash)
```

**Authorization Bypass**:
```python
def test_cannot_access_other_org_data():
    # Attempt to guess other org's capture ID
    other_org_capture_id = "other-org-device_20250101_abc123"
    response = client.get(f"/v1/captures/{other_org_capture_id}",
                         headers=auth_headers)
    assert response.status_code == 404  # Not found (hides existence)
```

**Share Token Brute-Forcing**:
```python
def test_share_token_entropy():
    # Generate 10,000 tokens, verify no collisions
    tokens = [create_share_token() for _ in range(10000)]
    assert len(tokens) == len(set(tokens))  # All unique

    # Verify token length (24 chars = 144 bits entropy)
    assert all(len(t) >= 24 for t in tokens)
```

**Rate Limit Enforcement**:
```python
def test_rate_limiting():
    # Send 150 requests (over limit of 100/hour)
    for i in range(150):
        response = client.get("/s/test-token")
        if i < 100:
            assert response.status_code in [200, 404]
        else:
            assert response.status_code == 429  # Too Many Requests
```

---

### Load Tests (`locust` or `k6`)

**Concurrent Capture Uploads**:
```python
from locust import HttpUser, task, between

class DeviceUser(HttpUser):
    wait_time = between(1, 5)  # Capture every 1-5 seconds

    @task
    def upload_capture(self):
        self.client.post("/v1/captures", json={
            "device_id": f"load-test-cam-{self.user_id}",
            "image_base64": TEST_IMAGE_BASE64,
            ...
        }, headers={"Authorization": f"Bearer {self.api_key}"})

# Run: locust -f tests/load/test_captures.py --users 100 --spawn-rate 10
```

**Dashboard Page Loads**:
```python
class DashboardUser(HttpUser):
    wait_time = between(2, 10)

    @task
    def view_dashboard(self):
        self.client.get("/ui")

    @task
    def view_captures(self):
        self.client.get("/v1/captures?limit=50")

# Target: <2s p95 latency with 1000 concurrent users
```

**Viral Share Link Traffic**:
```python
class ShareLinkViewer(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_shared_camera(self):
        token = random.choice(SHARE_TOKENS)
        self.client.get(f"/s/{token}")

# Simulate viral post: 10,000 views in 1 hour
# Run: locust -f tests/load/test_share_links.py --users 200 --spawn-rate 20
```

---

## Success Metrics

### MVP Launch Criteria (Week 6)

**Technical**:
- [ ] 3+ test organizations with real devices deployed
- [ ] 100% data migrated from filesystem (verified)
- [ ] Zero cross-org data leakage (security audit passed)
- [ ] All existing features work (AI classification, alerts, real-time updates)
- [ ] <2s p95 response time (load tested)
- [ ] 99% uptime over 7 days (Railway metrics)

**Product**:
- [ ] User can signup, login, register device
- [ ] Public share links generate 10+ signups (viral proof of concept)
- [ ] Share page conversion rate >5% (views → signups)
- [ ] Device setup takes <10 minutes (timed test)

**Business**:
- [ ] Pricing page live (prepare for monetization)
- [ ] User documentation complete
- [ ] Support email operational

---

### Growth Metrics (Post-Launch)

#### Month 1
- **50+ organizations** signed up
- **200+ devices** registered
- **10K+ captures** processed
- **500+ share link views** → 25+ signups (5% conversion)

#### Month 3
- **500+ organizations**
- **2,000+ devices**
- **100K+ captures**
- **50K+ share link views** → 2,500+ signups (5% conversion)
- **10+ paying customers** (early adopters)

#### Month 6
- **2,000+ organizations**
- **10,000+ devices**
- **1M+ captures**
- **Revenue positive** (covers infrastructure + development)

---

### Key Performance Indicators (KPIs)

**Product**:
- Active organizations (DAU/MAU)
- Captures per device per day
- Abnormal detection rate
- Share link creation rate (% of users who share)

**Growth**:
- Signup conversion rate (share link view → signup)
- Viral coefficient (invites sent per user)
- Time to first capture (onboarding speed)
- Device activation rate (registered → first capture)

**Technical**:
- API response time (p50, p95, p99)
- Database query time
- S3 download speed (pre-signed URLs)
- Error rate (<0.1%)

**Business**:
- Customer Acquisition Cost (CAC)
- Monthly Recurring Revenue (MRR)
- Storage cost per org
- AI API cost per capture

---

## Post-MVP Roadmap (Deferred Features)

### Phase 7: User Roles & Permissions (Month 2)
**Goal**: Multi-user collaboration within organizations

**Features**:
- Admin, Member, Viewer roles
- Per-device access control (assign users to specific cameras)
- Audit logs (who changed what, when)
- Activity feed (recent captures, alerts, config changes)

**Use Case**: Building manager assigns floor supervisors to specific cameras

---

### Phase 8: Advanced Sharing (Month 2-3)
**Goal**: Flexible sharing for different use cases

**Features**:
- Custom share expiration dates (1 day to 90 days)
- Password-protected shares (for compliance)
- Embed widgets for websites (`<iframe>` integration)
- White-label share pages (custom branding, remove "Powered by Visant")
- Share single capture (not whole device feed)
- Share date range (e.g., "Jan 1-15 only")

**Use Case**: Contractor gets password-protected 30-day access to construction site camera

---

### Phase 9: Analytics & Reporting (Month 3)
**Goal**: Historical insights and compliance reports

**Features**:
- Dashboard metrics (captures/day, abnormal rate, uptime)
- Historical trends (anomaly patterns over time)
- Device health monitoring (offline alerts, low battery)
- Compliance reports (CSV/PDF export for audits)
- Heatmap (when anomalies occur most)
- Comparison mode (device A vs device B)

**Use Case**: Monthly security report for building management

---

### Phase 10: Integrations (Month 4)
**Goal**: Connect to existing workflows

**Features**:
- Webhooks for abnormal detections (POST to custom URL)
- Slack/Teams notifications (real-time alerts in chat)
- Zapier integration (trigger other automations)
- REST API for partners (read-only access to captures)
- IFTTT integration (consumer use cases)
- Alexa/Google Home skills ("Alexa, show me my cameras")

**Use Case**: Security team gets Slack alert when warehouse camera detects motion after hours

---

### Phase 11: Enterprise Features (Month 6+)
**Goal**: Serve large organizations (100+ cameras)

**Features**:
- SSO/SAML authentication (Okta, Azure AD)
- Advanced RBAC (custom roles, fine-grained permissions)
- Multi-region deployment (EU, APAC data residency)
- SLA guarantees (99.9% uptime, <1s API latency)
- Dedicated instances (single-tenant for compliance)
- Priority support (24/7, dedicated Slack channel)

**Use Case**: Fortune 500 company with 500 cameras across 10 facilities

---

### Phase 12: Billing & Monetization (Month 3+)
**Goal**: Revenue generation

**Features**:
- Stripe integration (credit card payments)
- Usage-based pricing (captures/month, storage GB)
- Storage quota enforcement (soft limits + overages)
- Subscription tiers:
  - **Free**: 1 device, 1000 captures/month, 7-day retention
  - **Pro** ($29/month): 10 devices, unlimited captures, 90-day retention
  - **Business** ($99/month): 50 devices, advanced features, 1-year retention
  - **Enterprise** (custom): Unlimited, dedicated instance, SLA
- Invoicing for enterprise
- Usage dashboard (show current billing cycle usage)

**Pricing Strategy**:
- Freemium model (generous free tier)
- Capture-based pricing (aligns with value)
- Storage overages ($0.10/GB/month)
- Additional devices ($5/month each)

---

### Phase 13: Mobile App (Month 6+)
**Goal**: On-the-go monitoring

**Features**:
- iOS/Android apps (React Native or Flutter)
- Push notifications for abnormal detections
- Live view (if devices support streaming)
- Manual trigger from phone
- Share links via phone (SMS, WhatsApp)
- Camera setup wizard (QR code scan)

**Use Case**: Security guard gets phone alert when camera detects anomaly

---

### Phase 14: Advanced AI Features (Month 9+)
**Goal**: Better detection, lower costs

**Features**:
- On-device AI (Raspberry Pi + TensorFlow Lite, save cloud costs)
- Custom AI models (train on customer data)
- Object detection (person, vehicle, animal)
- Face recognition (opt-in, privacy-conscious)
- License plate reading (parking lots)
- Activity recognition (walking, running, fighting)
- Anomaly prediction (detect patterns, predict issues)

**Use Case**: Retail store detects shoplifting patterns

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data loss during migration | Medium | Critical | Backup filesystem, dry-run mode, keep old data 30 days |
| PostgreSQL performance issues | Medium | High | Proper indexing, connection pooling, query optimization, load testing |
| S3 cost overruns | Medium | Medium | Image compression, thumbnail optimization, lifecycle policies (Glacier after 90 days) |
| Auth integration complexity | Low | High | Use Supabase (battle-tested), fallback to custom JWT if needed |
| Cross-org data leakage | Low | Critical | RLS policies, comprehensive security tests, bug bounty program |
| Railway downtime | Low | High | Monitor uptime, backup to AWS/GCP ready, status page |

---

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Low share link conversion | Medium | High | A/B test share page designs, optimize CTAs, user feedback sessions |
| Slow user adoption | Medium | High | Free tier, referral program, content marketing, early adopter outreach |
| Competitor launches similar feature | High | Medium | Focus on AI quality, unique UX, faster iteration, community building |
| Pricing too high/low | Medium | Medium | Start free, gather willingness-to-pay data, test pricing tiers |
| Poor user retention | Low | High | Onboarding flow, email engagement, product analytics (PostHog) |

---

### Security Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cross-org data leakage | Low | Critical | RLS policies, security audit, bug bounty, pentesting |
| Share link abuse | Medium | Low | Rate limiting, expiration, optional passwords, link revocation |
| DDoS on share links | Medium | Medium | Cloudflare, rate limiting, auto-scaling, link revocation |
| Credential stuffing attacks | High | Medium | Rate limiting, CAPTCHA on login, breach monitoring (HaveIBeenPwned API) |
| API key theft (devices) | Medium | High | Key rotation, IP whitelisting (optional), device fingerprinting |

---

### Product Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Complex onboarding | High | High | Guided setup wizard, video tutorials, live chat support |
| Poor share page UX | Medium | High | User testing, A/B testing, mobile optimization |
| Feature bloat | Medium | Medium | Strict MVP scope, defer non-essential features, user research |
| Device compatibility issues | Low | Medium | Test on multiple Pi models, fallback camera modes, diagnostics |

---

## Timeline Summary

| Phase | Duration | Start | End | Key Deliverables |
|-------|----------|-------|-----|------------------|
| 1. Foundation & Database | 1-2 weeks | Week 1 | Week 2 | PostgreSQL schema, data migration, S3 storage |
| 2. Auth & Multi-Tenancy | 1 week | Week 2 | Week 3 | Login/signup, JWT auth, org isolation |
| 3. Public Sharing | 1 week | Week 3 | Week 4 | Share links, public gallery, viral features |
| 4. Dashboard Updates | 1 week | Week 3 | Week 4 | Multi-device UI, share management |
| 5. Migration & Deployment | 1 week | Week 4 | Week 5 | Production deployment, device updates |
| 6. Polish & Launch | 1 week | Week 5 | Week 6 | Security audit, analytics, documentation |

**Total: 5-6 weeks to commercial MVP**

---

### Gantt Chart

```
Week  1    2    3    4    5    6
      |====|====|====|====|====|
Ph 1  [===========]
Ph 2       [========]
Ph 3            [========]
Ph 4            [========]
Ph 5                 [========]
Ph 6                      [========]
      |====|====|====|====|====|
      Jan  Jan  Feb  Feb  Feb  Feb
      06   13   20   27   03   10
```

**Critical Path**: Phase 1 → Phase 2 → Phase 3 (must be sequential)
**Parallel Work**: Phase 3 + Phase 4 can overlap (different team members)

---

### Weekly Milestones

**Week 1 (Jan 6-12)**:
- ✅ PostgreSQL database set up
- ✅ SQLAlchemy models complete
- ✅ S3 storage configured
- ✅ Migration script written (dry-run tested)

**Week 2 (Jan 13-19)**:
- ✅ Data migrated to PostgreSQL + S3
- ✅ Supabase Auth integrated
- ✅ JWT middleware working
- ✅ Device API key system operational

**Week 3 (Jan 20-26)**:
- ✅ Share links functional
- ✅ Public gallery page live
- ✅ Dashboard updated for multi-device
- ✅ Social share buttons working

**Week 4 (Jan 27 - Feb 2)**:
- ✅ Production deployment
- ✅ Devices updated with API keys
- ✅ All features tested end-to-end
- ✅ Migration validated

**Week 5 (Feb 3-9)**:
- ✅ Security audit passed
- ✅ Load testing complete
- ✅ Documentation finished
- ✅ Onboarding flow tested

**Week 6 (Feb 10-16)**:
- ✅ Soft launch (invite early users)
- ✅ Collect feedback
- ✅ Fix critical bugs
- ✅ **Public launch** 🚀

---

## Next Steps

### Immediate Actions (This Week)

1. **Set up Railway services**:
   - [ ] Add PostgreSQL database (Starter plan)
   - [ ] Configure S3-compatible storage
   - [ ] Add environment variables

2. **Create Supabase project**:
   - [ ] Sign up at supabase.com
   - [ ] Create new project
   - [ ] Get API keys (public, secret, JWT secret)
   - [ ] Configure email templates

3. **Begin Phase 1 implementation**:
   - [ ] Create database schema (SQLAlchemy models)
   - [ ] Set up Alembic migrations
   - [ ] Write S3 storage abstraction
   - [ ] Start migration script

4. **Review and finalize plan**:
   - [ ] Stakeholder approval
   - [ ] Budget approval (Railway costs)
   - [ ] Timeline commitment

---

### Weekly Check-ins

**Format**: 30-minute sync every Monday

**Agenda**:
1. Progress review (what shipped last week)
2. Blockers discussion (technical, product, business)
3. Next week priorities (what's critical)
4. Metrics review (if post-launch)

**Participants**: Development team, product owner, stakeholders

---

### Success Criteria for Plan Approval

- [ ] All stakeholders have reviewed
- [ ] Timeline is realistic (5-6 weeks)
- [ ] Budget approved (Railway + Supabase costs)
- [ ] Technical approach validated
- [ ] Risks understood and mitigated
- [ ] Team capacity confirmed

---

## Document Maintenance

This plan is a **living document** and will be updated throughout implementation.

**Update Triggers**:
- Architecture decisions changed
- Scope adjusted (features added/removed)
- Timeline shifts
- Blockers encountered
- Post-launch metrics available

**Update Process**:
1. Make changes to PROJECT_PLAN.md
2. Document rationale in commit message
3. Notify team in weekly check-in
4. Archive old versions (git history)

**Version History**:
- **v1.0** (2025-01-06): Initial plan, pre-implementation
- **v1.1** (TBD): Post-Phase 1 updates
- **v2.0** (TBD): Post-launch updates with metrics

---

## Appendix

### Glossary

- **Multi-tenancy**: Architecture where single app serves multiple customers (tenants) with data isolation
- **Row-Level Security (RLS)**: Database feature that filters rows based on user context
- **JWT**: JSON Web Token, standard for authentication tokens
- **Pre-signed URL**: Time-limited URL for accessing S3 objects without auth
- **Org**: Short for "organization", the tenant entity
- **Share link**: Public URL that allows viewing camera feed without login
- **Device API key**: Secret token used by devices to authenticate
- **Capture**: Single image + metadata from camera

### Abbreviations

- **MVP**: Minimum Viable Product
- **SaaS**: Software as a Service
- **S3**: Simple Storage Service (AWS object storage)
- **RLS**: Row-Level Security
- **JWT**: JSON Web Token
- **API**: Application Programming Interface
- **UI**: User Interface
- **UX**: User Experience
- **CTA**: Call to Action
- **CAC**: Customer Acquisition Cost
- **MRR**: Monthly Recurring Revenue
- **KPI**: Key Performance Indicator
- **RBAC**: Role-Based Access Control
- **SSO**: Single Sign-On
- **SAML**: Security Assertion Markup Language

### References

- [Visant GitHub Repository](https://github.com/atxapple/okmonitor) (forked from OK Monitor)
- [Supabase Documentation](https://supabase.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org)
- [PostgreSQL Multi-Tenancy Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [AWS S3 Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

---

**Last Updated**: 2025-01-06
**Status**: Awaiting Approval
**Owner**: Development Team
**Approved By**: (pending)
**Next Review**: Week 2 (post-Phase 1 completion)

---

*End of Document*

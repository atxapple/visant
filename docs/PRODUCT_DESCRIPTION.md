# Visant - Multi-Tenant Camera Monitoring SaaS

> **Vision:** Deliver a cloud-native, multi-tenant SaaS platform where lightweight edge devices continuously monitor environments, cloud AI classifies visual anomalies in real-time, and organizations manage their camera fleet through a unified web dashboard.

**Current Version:** v2.0 Multi-Tenant SaaS (November 2025)
**Deployment:** Production on Railway.app
**Architecture:** Cloud-triggered, PostgreSQL-backed, Supabase Auth

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Product Overview](#product-overview)
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Device Setup](#device-setup)
- [Current Status](#current-status)
- [Roadmap](#roadmap)

---

## Executive Summary

Visant is a **multi-tenant SaaS platform** for AI-powered visual monitoring. Organizations deploy lightweight camera devices that continuously capture images, upload them to the cloud, and receive AI classification results to detect environmental anomalies.

### What's Working Now (Production on Railway)

✅ **Multi-Tenant Architecture** - Complete organization/user isolation with PostgreSQL
✅ **Supabase Authentication** - Email/password auth with JWT tokens
✅ **Cloud-Triggered Device Management** - Real-time command streaming via SSE
✅ **AI Classification** - Dual-agent consensus (OpenAI GPT-4o-mini + Gemini 2.5 Flash)
✅ **Background Evaluation** - Asynchronous AI processing pipeline
✅ **Scheduled Triggers** - Automated capture scheduling per device
✅ **Activation Codes** - Promotional codes for device slots and trial extensions
✅ **Web Dashboard** - Device management, capture gallery, real-time updates
✅ **Performance Optimization** - Thumbnail generation, cache headers, composite indexes
✅ **Datalake Storage** - Persistent volume storage on Railway (`/mnt/data`)
✅ **Legacy Compatibility** - Mounted single-tenant server at `/legacy/*`

### What's Missing (See PROJECT_PLAN.md for details)

⚠️ **Manual Trigger UI** - Endpoint exists, UI button needed
⚠️ **Per-Device Notification UI** - Global settings complete, per-device config pending
⚠️ **Normal Description Management** - Multi-tenant version needed
⚠️ **Advanced Filtering** - Similarity detection, streak pruning (code exists, needs integration)
⚠️ **Admin Tools** - Datalake pruning UI, performance monitoring dashboard

---

## Product Overview

### Value Proposition

**For organizations:**
- Deploy camera devices to monitor environments 24/7
- Receive instant AI-powered anomaly detection
- Access captures from anywhere via web dashboard
- Share findings with stakeholders via public links
- Manage multiple devices across locations

**For end users:**
- Simple device setup with QR code activation
- No technical expertise required
- Email notifications for important events
- Mobile-friendly web interface

### Key Differentiators

1. **Cloud-Triggered Architecture** - Real-time command delivery via SSE (not device polling)
2. **Dual-Agent AI Consensus** - Combining OpenAI and Gemini for higher accuracy
3. **Multi-Tenant from Day 1** - Built for SaaS with proper data isolation
4. **Background Evaluation** - Non-blocking AI processing for fast uploads
5. **Promotional Growth** - Activation code system for trials and referrals

---

## Core Features

### 1. Multi-Tenant Organization Management

**Organizations**
- Auto-created on user signup
- Isolated data storage (captures, devices, schedules)
- Configurable device slots (expandable via activation codes)
- Default: 5 device slots, 30-day trial

**Users**
- Email/password authentication via Supabase
- JWT token-based authorization
- One organization per user (for now)
- Future: Multi-user organizations with RBAC

**Activation Codes**
- Promotional codes for device slots, free months, trial extensions
- One-time or multi-use codes
- Email domain restrictions
- Usage tracking and analytics

### 2. Device Management

**Device Registration**
- Devices manufactured with unique IDs
- QR code activation flow
- Device-to-organization pairing
- Status tracking: manufactured → active → deactivated

**Cloud-Triggered Commands** (CommandHub)
- Real-time SSE connections from devices
- Command streaming: capture, schedule updates, config changes
- Heartbeat monitoring and presence tracking
- Graceful reconnection handling

**Scheduled Triggers** (TriggerScheduler)
- Per-device capture schedules (cron-style)
- Cloud-managed scheduling (no device-side logic)
- Real-time schedule updates pushed to devices
- Timezone-aware scheduling

### 3. AI-Powered Classification

**Dual-Agent Consensus**
- **Agent1:** OpenAI GPT-4o-mini (fast, accurate, structured JSON)
- **Agent2:** Gemini 2.5 Flash (experimental, cost-effective)
- Consensus logic: highest confidence wins, flag disagreements as "uncertain"
- Detailed reasoning provided for abnormal/uncertain captures

**Background Evaluation Pipeline**
- Captures uploaded instantly (200 OK)
- AI classification runs asynchronously
- Non-blocking for device clients
- Evaluation status tracking: pending → processing → completed → failed

**Classification States**
- **Normal:** Expected environment state (green)
- **Abnormal:** Anomaly detected (red, triggers notifications)
- **Uncertain:** Low confidence or agent disagreement (yellow)

### 4. Datalake Storage

**File System Organization**
```
/mnt/data/datalake/
└── {org_id}/
    └── {device_id}/
        └── YYYY/
            └── MM/
                └── DD/
                    ├── {record_id}.jpg (full image)
                    ├── {record_id}_thumb.jpg (thumbnail)
                    └── {record_id}.json (metadata)
```

**Features**
- Organization-based partitioning
- Date-based directory structure
- Automatic thumbnail generation (400x300, 85% quality)
- Browser caching (1-year TTL for thumbnails)
- Persistent volume on Railway (`/mnt/data`)

### 5. Web Dashboard

**Authentication Pages**
- `/ui/login` - Email/password login
- `/ui/signup` - New user registration (auto-creates organization)

**Main Dashboard** (`/ui/dashboard`)
- Device overview cards
- Recent captures across all devices
- Quick actions (add device, view captures)

**Device Page** (`/ui/camera/{device_id}`)
- Device details and status
- Capture gallery with filters (state, date range, limit)
- Thumbnail grid with lazy loading
- Full-size image viewer
- Download captures

**Settings** (Coming Soon)
- Notification preferences
- Normal description editor
- Organization settings
- API key management

### 6. API Endpoints

**Authentication** (`/v1/auth/`)
- `POST /login` - User login (email/password)
- `POST /signup` - New user registration
- `POST /token/refresh` - JWT token refresh
- `GET /me` - Current user info

**Devices** (`/v1/devices/`)
- `POST /activate` - Activate device with code
- `GET /` - List organization devices
- `GET /{device_id}` - Device details
- `PUT /{device_id}` - Update device
- `DELETE /{device_id}` - Deactivate device

**Captures** (`/v1/captures`)
- `POST /` - Upload capture (multipart/form-data)
- `GET /` - List captures (filtered by device, state, date)
- `GET /{record_id}` - Capture details
- `GET /{record_id}/thumbnail` - Thumbnail JPEG

**Device Commands** (`/v1/device-commands/`)
- `GET /stream` - SSE command stream (device client)
- `POST /heartbeat` - Device heartbeat
- `POST /ack` - Command acknowledgment

**Scheduled Triggers** (`/v1/scheduled-triggers/`)
- `GET /device/{device_id}` - List device schedules
- `POST /` - Create schedule
- `PUT /{schedule_id}` - Update schedule
- `DELETE /{schedule_id}` - Delete schedule

**Admin** (`/v1/admin/`)
- `POST /codes` - Create activation code
- `GET /codes` - List codes
- `POST /codes/{code}/redeem` - Redeem code

**Legacy** (`/legacy/*`)
- Single-tenant v1.0 server mounted for backward compatibility

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Browser                          │
│                  (Vue.js Dashboard - Future)                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI Application                      │
│                   (test_server_v2.py)                       │
├─────────────────────────────────────────────────────────────┤
│  Routes:                                                    │
│  ├── /v1/auth/* (authentication.py)                        │
│  ├── /v1/devices/* (devices.py)                            │
│  ├── /v1/captures (captures.py)                            │
│  ├── /v1/device-commands/* (device_commands.py)            │
│  ├── /v1/scheduled-triggers/* (scheduled_triggers.py)      │
│  ├── /v1/admin/codes/* (admin_codes.py)                    │
│  ├── /ui/* (web_routes.py)                                 │
│  └── /legacy/* (server.py - v1.0 compatibility)            │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                  │
│  ├── CommandHub (SSE streaming to devices)                 │
│  ├── TriggerScheduler (cron-based capture scheduling)      │
│  ├── InferenceService (AI classification)                  │
│  └── BackgroundEvaluator (async AI processing)             │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
    ┌──────────▼─────────┐   ┌───────▼────────┐
    │   PostgreSQL       │   │  File System   │
    │   (Railway)        │   │   Datalake     │
    │                    │   │  (/mnt/data)   │
    │  ├── organizations │   │                │
    │  ├── users         │   │ ├── org_id/    │
    │  ├── devices       │   │    ├── device/ │
    │  ├── captures      │   │       ├── YYYY │
    │  ├── schedules     │   │          ├── MM│
    │  └── codes         │   │             └──│
    └────────────────────┘   └────────────────┘
               │
    ┌──────────▼─────────┐
    │   Supabase Auth    │
    │   (JWT tokens)     │
    └────────────────────┘
               │
    ┌──────────▼─────────┐   ┌─────────────────┐
    │   OpenAI API       │   │   Gemini API    │
    │  (GPT-4o-mini)     │   │ (2.5 Flash)     │
    └────────────────────┘   └─────────────────┘
```

### Database Schema (PostgreSQL)

**organizations**
- `id` (UUID, PK)
- `name` (VARCHAR)
- `device_slots` (INT, default: 5)
- `trial_end_date` (TIMESTAMP)
- `created_at`, `updated_at`

**users**
- `id` (UUID, PK, from Supabase)
- `email` (VARCHAR, unique)
- `org_id` (UUID, FK → organizations)
- `created_at`

**devices**
- `id` (VARCHAR, PK)
- `org_id` (UUID, FK → organizations, nullable)
- `status` (ENUM: manufactured, active, deactivated)
- `activated_at`, `deactivated_at`
- `last_seen` (TIMESTAMP)
- `created_at`, `updated_at`

**captures**
- `id` (UUID, PK)
- `record_id` (VARCHAR, unique)
- `device_id` (VARCHAR, FK → devices)
- `org_id` (UUID, FK → organizations)
- `captured_at` (TIMESTAMP)
- `trigger_label` (VARCHAR)
- `classification_state` (ENUM: normal, abnormal, uncertain, null)
- `classification_confidence` (FLOAT)
- `classification_reason` (TEXT)
- `evaluation_status` (ENUM: pending, processing, completed, failed)
- `file_path`, `thumbnail_path`, `metadata_path`
- `created_at`, `updated_at`
- **Composite Index:** `(org_id, device_id, captured_at DESC)` ✅ Performance critical!

**scheduled_triggers**
- `id` (UUID, PK)
- `device_id` (VARCHAR, FK → devices)
- `org_id` (UUID, FK → organizations)
- `trigger_label` (VARCHAR)
- `cron_expression` (VARCHAR)
- `enabled` (BOOLEAN)
- `created_at`, `updated_at`

**activation_codes**
- `code` (VARCHAR, PK)
- `description` (VARCHAR)
- `benefit_type` (ENUM: device_slots, free_months, trial_extension)
- `benefit_value` (INT)
- `max_uses` (INT, nullable)
- `uses_count` (INT, default: 0)
- `valid_from`, `valid_until` (TIMESTAMP)
- `active` (BOOLEAN)
- `one_per_user` (BOOLEAN)
- `allowed_email_domains` (JSON, array)

**code_redemptions**
- `id` (UUID, PK)
- `code` (VARCHAR, FK → activation_codes)
- `org_id` (UUID, FK → organizations)
- `redeemed_at` (TIMESTAMP)
- **Unique:** `(code, org_id)` if one_per_user=true

**share_links** (Not yet wired)
- `id` (UUID, PK)
- `token` (VARCHAR, unique)
- `device_id` (VARCHAR, FK → devices)
- `org_id` (UUID, FK → organizations)
- `share_type` (ENUM: device, single_capture)
- `capture_id` (UUID, nullable)
- `expires_at` (TIMESTAMP)
- `created_at`

---

## Data Flow

### 1. User Signup & Organization Creation

```
User → POST /v1/auth/signup (email, password)
  ↓
Supabase Auth creates user account (JWT token)
  ↓
Backend creates Organization (default: 5 slots, 30-day trial)
  ↓
User record linked to Organization
  ↓
Response: JWT token + organization_id
```

### 2. Device Activation

```
User → POST /v1/devices/activate (device_id, activation_code)
  ↓
Validate: device exists, not already activated, org has slots
  ↓
Update device: status=active, org_id=user.org_id
  ↓
Redeem activation code (if used)
  ↓
Generate QR code with device credentials
  ↓
Response: device details + QR code data
```

### 3. Device Connection & Command Streaming

```
Device → GET /v1/device-commands/stream (device_id, SSE)
  ↓
CommandHub registers device connection
  ↓
Send initial config (schedules, settings)
  ↓
Device sends periodic heartbeats
  ↓
Server pushes commands in real-time:
  - capture (trigger_label, timestamp)
  - schedule_update (new cron expressions)
  - config_update (settings changes)
  ↓
Device ACKs commands → POST /v1/device-commands/ack
```

### 4. Scheduled Capture Execution

```
TriggerScheduler (background task, runs every 60s)
  ↓
Evaluate cron expressions for all active schedules
  ↓
For each due schedule:
  ↓
  Check device is connected (last_seen < 5 min)
  ↓
  Send "capture" command via CommandHub → SSE stream
  ↓
  Device receives command, captures image, uploads
```

### 5. Capture Upload & AI Classification

```
Device → POST /v1/captures (multipart/form-data)
  - file: image.jpg
  - device_id, record_id, captured_at, trigger_label
  ↓
Validate: device belongs to organization, file is valid JPEG
  ↓
Save to datalake: /mnt/data/datalake/{org_id}/{device_id}/YYYY/MM/DD/
  ↓
Generate thumbnail (400x300, 85% quality)
  ↓
Create capture record in DB (evaluation_status=pending)
  ↓
Response: 200 OK (instant, non-blocking)
  ↓
Background Evaluator picks up pending capture
  ↓
Load normal description for organization
  ↓
Run Agent1 (OpenAI) and Agent2 (Gemini) in parallel
  ↓
Consensus logic: highest confidence wins
  ↓
Update capture record:
  - classification_state (normal/abnormal/uncertain)
  - classification_confidence
  - classification_reason
  - evaluation_status=completed
  ↓
If abnormal: Send email notification (SendGrid)
  ↓
Broadcast to dashboard via WebSocket (future)
```

### 6. Dashboard Capture Gallery

```
User → GET /ui/camera/{device_id}
  ↓
Fetch device details (validate org ownership)
  ↓
Fetch captures: SELECT * FROM captures
  WHERE org_id = ? AND device_id = ?
  ORDER BY captured_at DESC
  LIMIT 50
  ↓
Using composite index: (org_id, device_id, captured_at DESC)
  ↓
Render thumbnail grid:
  <img src="/v1/captures/{record_id}/thumbnail">
  ↓
Browser caches thumbnails (1-year TTL)
  ↓
Click thumbnail → Load full image (lazy)
```

---

## Technology Stack

### Backend

**Framework**
- FastAPI 0.100+ (async, OpenAPI docs)
- Uvicorn (ASGI server)
- Pydantic 2.0+ (data validation)

**Database**
- PostgreSQL 15+ (Railway managed)
- SQLAlchemy 2.0+ (ORM)
- Alembic 1.13+ (migrations)

**Authentication**
- Supabase Auth (JWT tokens)
- python-jose (JWT decoding)
- email-validator (Pydantic EmailStr)

**AI Services**
- OpenAI API (GPT-4o-mini, structured JSON)
- Gemini API (2.5 Flash, REST)

**Storage**
- File system datalake (Railway persistent volume)
- boto3 (future: S3 migration)

**Email**
- SendGrid (transactional alerts)

**Utilities**
- python-dotenv (environment variables)
- PyYAML (config files)
- qrcode[pil] (QR code generation)
- opencv-python (image processing)
- Pillow (thumbnail generation)

### Frontend (Current)

**Templating**
- Jinja2 (server-side rendering)
- HTML5 + vanilla JavaScript
- Bootstrap 5 (CSS framework)

### Frontend (Future)

**Framework**
- Vue.js 3 (composition API)
- TypeScript
- Vite (build tool)
- Pinia (state management)

### DevOps

**Deployment**
- Railway.app (auto-deploy from GitHub)
- Nixpacks (buildpack)
- PostgreSQL + persistent volume

**Version Control**
- Git + GitHub
- Alembic migrations in `alembic/versions/`

**Testing**
- pytest (unit tests)
- Postman/curl (API testing)

---

## Deployment

### Local Development

**1. Environment Setup**

```bash
# Clone repository
git clone https://github.com/atxapple/visant.git
cd visant

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

**2. Configure Environment Variables**

Create `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/visant

# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret

# AI APIs
OPENAI_API_KEY=sk-proj-your-key
GEMINI_API_KEY=your-gemini-key

# Email (optional)
SENDGRID_API_KEY=SG.your-key
ALERT_FROM_EMAIL=alerts@yourdomain.com
ALERT_ENVIRONMENT_LABEL=development

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

**3. Database Migration**

```bash
# Run migrations
alembic upgrade head

# Verify
alembic current
```

**4. Start Server**

```bash
python test_server_v2.py
```

Server starts on `http://localhost:8000`
- Dashboard: `http://localhost:8000/ui`
- API Docs: `http://localhost:8000/docs`

### Railway Deployment

**Prerequisites**
- Railway account (https://railway.app)
- GitHub repository connected
- PostgreSQL database provisioned
- Persistent volume mounted at `/mnt/data`

**Step-by-Step Guide**

See `deployment/RAILWAY_SETUP.md` for comprehensive instructions.

**Quick Deploy**

1. **Create Railway Project**
   - Connect GitHub repository
   - Auto-detect Python buildpack
   - Start command: `python test_server_v2.py`

2. **Add PostgreSQL Service**
   - Railway auto-injects `DATABASE_URL`

3. **Add Persistent Volume**
   - Mount path: `/mnt/data`
   - Size: 1 GB (minimum, expandable)

4. **Configure Environment Variables**
   ```
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

5. **Run Migrations**
   ```bash
   railway run bash
   alembic upgrade head
   ```

6. **Deploy**
   - Push to `main` branch
   - Railway auto-deploys
   - Monitor logs: `railway logs`

**Post-Deployment Verification**

```bash
# Health check
curl https://your-app.railway.app/

# API docs
curl https://your-app.railway.app/docs

# Login test
curl -X POST https://your-app.railway.app/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

---

## API Documentation

### Authentication Flow

**1. User Signup**
```http
POST /v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepass123"
}

→ Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "org_id": "uuid"
  }
}
```

**2. User Login**
```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepass123"
}

→ Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "org_id": "uuid"
  }
}
```

**3. Authenticated Requests**
```http
GET /v1/devices
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

→ Response: 200 OK
[
  {
    "id": "DEVICE001",
    "status": "active",
    "activated_at": "2025-11-10T12:00:00Z",
    "last_seen": "2025-11-10T14:30:00Z"
  }
]
```

### Device Management

**Activate Device**
```http
POST /v1/devices/activate
Authorization: Bearer {token}
Content-Type: application/json

{
  "device_id": "DEVICE001",
  "activation_code": "PROMO2024"  // optional
}

→ Response: 200 OK
{
  "id": "DEVICE001",
  "org_id": "uuid",
  "status": "active",
  "activated_at": "2025-11-10T12:00:00Z",
  "qr_code_data": "visant://activate?device=DEVICE001&token=..."
}
```

**List Devices**
```http
GET /v1/devices
Authorization: Bearer {token}

→ Response: 200 OK
[
  {
    "id": "DEVICE001",
    "status": "active",
    "activated_at": "2025-11-10T12:00:00Z",
    "last_seen": "2025-11-10T14:30:00Z"
  },
  {
    "id": "DEVICE002",
    "status": "manufactured",
    "activated_at": null,
    "last_seen": null
  }
]
```

### Capture Upload

**Upload Capture (Device Client)**
```http
POST /v1/captures
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="image.jpg"
Content-Type: image/jpeg

<binary JPEG data>
--boundary
Content-Disposition: form-data; name="device_id"

DEVICE001
--boundary
Content-Disposition: form-data; name="record_id"

CAP_20251110_120000_abc123
--boundary
Content-Disposition: form-data; name="captured_at"

2025-11-10T12:00:00Z
--boundary
Content-Disposition: form-data; name="trigger_label"

scheduled-hourly
--boundary--

→ Response: 200 OK
{
  "record_id": "CAP_20251110_120000_abc123",
  "message": "Capture uploaded successfully",
  "evaluation_status": "pending"
}
```

**List Captures**
```http
GET /v1/captures?device_id=DEVICE001&state=abnormal&limit=50
Authorization: Bearer {token}

→ Response: 200 OK
[
  {
    "record_id": "CAP_20251110_120000_abc123",
    "device_id": "DEVICE001",
    "captured_at": "2025-11-10T12:00:00Z",
    "classification_state": "abnormal",
    "classification_confidence": 0.92,
    "classification_reason": "Detected person in restricted area",
    "evaluation_status": "completed",
    "thumbnail_url": "/v1/captures/CAP_20251110_120000_abc123/thumbnail"
  }
]
```

**Get Thumbnail**
```http
GET /v1/captures/{record_id}/thumbnail

→ Response: 200 OK
Content-Type: image/jpeg
Cache-Control: public, max-age=31536000

<binary JPEG data>
```

### Scheduled Triggers

**Create Schedule**
```http
POST /v1/scheduled-triggers
Authorization: Bearer {token}
Content-Type: application/json

{
  "device_id": "DEVICE001",
  "trigger_label": "hourly-check",
  "cron_expression": "0 * * * *",  // Every hour
  "enabled": true
}

→ Response: 200 OK
{
  "id": "uuid",
  "device_id": "DEVICE001",
  "trigger_label": "hourly-check",
  "cron_expression": "0 * * * *",
  "enabled": true,
  "created_at": "2025-11-10T12:00:00Z"
}
```

**List Schedules**
```http
GET /v1/scheduled-triggers/device/DEVICE001
Authorization: Bearer {token}

→ Response: 200 OK
[
  {
    "id": "uuid",
    "trigger_label": "hourly-check",
    "cron_expression": "0 * * * *",
    "enabled": true
  },
  {
    "id": "uuid",
    "trigger_label": "daily-report",
    "cron_expression": "0 9 * * *",
    "enabled": true
  }
]
```

---

## Device Setup

### Device Client Configuration

**1. Install Dependencies**
```bash
pip install requests opencv-python python-dotenv
```

**2. Create `.env` on Device**
```env
DEVICE_ID=DEVICE001
CLOUD_URL=https://your-app.railway.app
```

**3. Device Client Script** (`device/main_v2.py`)

```python
import os
import time
import requests
from sseclient import SSEClient  # pip install sseclient-py

DEVICE_ID = os.getenv("DEVICE_ID")
CLOUD_URL = os.getenv("CLOUD_URL")

def connect_command_stream():
    """Connect to SSE command stream"""
    url = f"{CLOUD_URL}/v1/device-commands/stream"
    headers = {"X-Device-ID": DEVICE_ID}

    messages = SSEClient(url, headers=headers)
    for msg in messages:
        if msg.event == "command":
            handle_command(json.loads(msg.data))
        elif msg.event == "ping":
            send_heartbeat()

def handle_command(command):
    """Execute command from cloud"""
    if command["type"] == "capture":
        trigger_label = command["trigger_label"]
        capture_and_upload(trigger_label)
    elif command["type"] == "schedule_update":
        print(f"Schedule updated: {command['schedules']}")

def capture_and_upload(trigger_label):
    """Capture image and upload to cloud"""
    # Capture image with OpenCV
    import cv2
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    # Save to file
    filename = f"capture_{int(time.time())}.jpg"
    cv2.imwrite(filename, frame)

    # Upload
    record_id = f"CAP_{time.strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    url = f"{CLOUD_URL}/v1/captures"

    with open(filename, "rb") as f:
        files = {"file": f}
        data = {
            "device_id": DEVICE_ID,
            "record_id": record_id,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_label": trigger_label
        }
        response = requests.post(url, files=files, data=data)
        print(f"Upload: {response.status_code}")

    os.remove(filename)

def send_heartbeat():
    """Send heartbeat to cloud"""
    url = f"{CLOUD_URL}/v1/device-commands/heartbeat"
    data = {"device_id": DEVICE_ID}
    requests.post(url, json=data)

if __name__ == "__main__":
    print(f"Device {DEVICE_ID} connecting to {CLOUD_URL}")
    connect_command_stream()
```

**4. Run Device Client**
```bash
python device/main_v2.py
```

**Expected Output**
```
Device DEVICE001 connecting to https://your-app.railway.app
Connected to command stream
Received command: capture (trigger_label: hourly-check)
Capturing image...
Uploading capture...
Upload: 200
```

---

## Current Status

### Production Deployment (Railway)

✅ **Deployed:** https://visant-production.railway.app
✅ **Database:** PostgreSQL 15 (Railway managed)
✅ **Storage:** Persistent volume at `/mnt/data` (1 GB)
✅ **Performance:** <3s first load, <1s cached (90% improvement)
✅ **Uptime:** Auto-restart on failure (max 10 retries)

### Feature Completion

| Category | Feature | Status |
|----------|---------|--------|
| **Authentication** | Supabase JWT | ✅ Complete |
| | Email/password login | ✅ Complete |
| | User signup | ✅ Complete |
| **Multi-Tenancy** | Organizations | ✅ Complete |
| | Data isolation | ✅ Complete |
| | Device slots | ✅ Complete |
| **Device Management** | Activation codes | ✅ Complete |
| | QR code generation | ✅ Complete |
| | Device status tracking | ✅ Complete |
| **Cloud Commands** | SSE streaming | ✅ Complete |
| | Heartbeat monitoring | ✅ Complete |
| | Command ACK | ✅ Complete |
| **Scheduling** | Cron-based triggers | ✅ Complete |
| | Real-time updates | ✅ Complete |
| **AI Classification** | Dual-agent consensus | ✅ Complete |
| | Background evaluation | ✅ Complete |
| | OpenAI + Gemini | ✅ Complete |
| **Storage** | Datalake file system | ✅ Complete |
| | Thumbnail generation | ✅ Complete |
| | Cache headers | ✅ Complete |
| **Dashboard** | Login/signup pages | ✅ Complete |
| | Device list | ✅ Complete |
| | Capture gallery | ✅ Complete |
| | Thumbnail grid | ✅ Complete |
| **Performance** | Composite indexes | ✅ Complete |
| | Query optimization | ✅ Complete |
| | 90% load time reduction | ✅ Complete |
| **Sharing** | Public share links | ✅ Complete |
| | Public gallery | ✅ Complete |
| | QR code generation | ✅ Complete |
| | Share analytics | ✅ Complete |
| **Real-Time** | SSE capture events | ✅ Complete |
| | WebSocket updates | ✅ Complete |
| | Live UI updates | ✅ Complete |
| **Manual Triggers** | API endpoint | ✅ Complete |
| | UI button | ⚠️ Partial (button exists, history pending) |
| **Notifications** | Email alerts | ✅ Complete |
| | Global UI settings | ✅ Complete |
| | Per-device config | ⚠️ Partial (pending) |
| **Version Tracking** | /v1/version endpoint | ✅ Complete |
| **Admin Tools** | Datalake pruning UI | ❌ Not implemented |
| | Performance monitoring | ❌ Not implemented |

### Performance Metrics

**Database**
- Query time: <100ms (with composite index)
- Connection pool: 20 connections, 10 overflow
- Pool timeout: 30s

**Image Loading**
- Thumbnail size: 5-15 KB (vs 17-29 KB full)
- Payload reduction: 70%
- Cache TTL: 1 year
- First load: <3s for 20 images
- Cached load: <1s

**AI Classification**
- Upload response: <500ms (non-blocking)
- Evaluation time: 3-5s (background)
- Agent1 (OpenAI): ~2s
- Agent2 (Gemini): ~3s

---

## Roadmap

### Recently Completed (November 2025)

✅ **Public Sharing System** - Complete share link creation, public gallery, QR codes, analytics
✅ **Real-time Capture Streaming** - SSE/WebSocket endpoints, live UI updates
✅ **Version Tracking** - GET /v1/version endpoint with cloud + device versions
✅ **Password Reset Flow** - Dedicated forgot password page with email-based reset
✅ **Alert Definition Tracking** - Database-backed definitions with version history

### Phase 1: Quick Wins (1-2 weeks)

**Priority: HIGH**

1. **Manual Trigger UI**
   - Add trigger history view
   - Show trigger feedback in UI
   - Trigger button integration (already exists in legacy)

### Phase 2: Core Features (2-3 weeks)

**Priority: MEDIUM**

2. **Per-Device Notification UI**
   - Per-device email configuration
   - Device-specific alert settings
   - Notification preferences override

3. **Normal Description Management**
   - UI editor for "normal state" prompt
   - Per-organization customization
   - Real-time preview
   - Version history

4. **Advanced Capture Filtering**
   - Similarity detection (perceptual hash)
   - Streak pruning (delete redundant normals)
   - Deduplication logic
   - Smart datalake optimization

### Phase 3: Admin & Advanced (3-4 weeks)

**Priority: LOW**

5. **Datalake Pruning Admin Panel**
   - UI for pruning configuration
   - Manual prune trigger
   - Storage usage dashboard
   - Retention policy editor

6. **Timing Debug / Performance Monitoring**
   - Request timing logs
   - Slow query detection
   - AI latency tracking
   - Performance dashboard

7. **UI Preferences & State Filtering**
    - Save filter preferences (per user)
    - Default view settings
    - Custom date ranges
    - Favorite devices

8. **WebSocket Device Commands**
    - Two-way WebSocket for device control
    - Real-time command delivery
    - Device status updates
    - Connection monitoring

9. **Legacy Compatibility Migration**
    - Migrate remaining legacy users
    - Deprecate `/legacy/*` routes
    - Remove `cloud/api/server.py`

### Future Enhancements

**Multi-User Organizations**
- RBAC (admin, viewer, editor roles)
- User invitations
- Team management
- Audit logs

**Advanced Analytics**
- Capture trends over time
- Anomaly heatmaps
- Device uptime reports
- AI accuracy metrics

**Mobile App**
- iOS/Android native apps
- Push notifications
- Offline mode
- Camera access

**S3 Storage Migration**
- Move from file system to S3
- CDN integration (CloudFront)
- Cost optimization
- Scalability improvements

**API Rate Limiting**
- Per-organization quotas
- SlowAPI integration
- Usage analytics
- Throttling policies

---

## Repository Structure

```
visant/
├── alembic/                    # Database migrations
│   └── versions/               # Migration scripts
│       ├── 8af79cab0d8d_initial_schema.py
│       ├── 747d6fbf4733_add_evaluation_status.py
│       ├── aa246cbd4277_add_composite_index.py
│       └── db7d78dfcf08_add_alert_definitions.py
├── archive/                    # Archived files
│   ├── docs/                   # Historical documentation
│   │   ├── README.md           # Archive index
│   │   ├── CODE_REVIEW_SUMMARY_2025-11-12.md
│   │   └── PRUNING_LOGIC_REVIEW.md
│   └── scripts/                # Legacy scripts
│       └── migrate_to_volume.py
├── cloud/                      # Cloud backend
│   ├── ai/                     # AI classification
│   │   ├── openai_client.py    # Agent1 (OpenAI)
│   │   ├── gemini_client.py    # Agent2 (Gemini)
│   │   └── consensus.py        # Consensus logic
│   ├── api/                    # FastAPI application
│   │   ├── database/           # SQLAlchemy models
│   │   ├── routes/             # API endpoints
│   │   │   ├── authentication.py
│   │   │   ├── devices.py
│   │   │   ├── captures.py      # ✅ Real-time SSE/WebSocket
│   │   │   ├── device_commands.py
│   │   │   ├── scheduled_triggers.py
│   │   │   ├── admin_codes.py
│   │   │   ├── admin.py
│   │   │   ├── shares.py        # ✅ Complete
│   │   │   ├── public.py        # ✅ Complete
│   │   │   └── version.py       # ✅ Complete
│   │   ├── server.py            # Legacy v1.0 server (mounted at /legacy/*)
│   │   └── service.py           # InferenceService
│   ├── datalake/                # Storage layer
│   │   └── storage.py           # File system operations
│   └── web/                     # Web UI
│       ├── routes.py            # Dashboard routes
│       └── templates/           # Jinja2 templates
│           ├── login.html
│           ├── signup.html
│           ├── forgot_password.html
│           ├── reset_password.html
│           ├── dashboard.html
│           ├── camera.html
│           └── notifications.html
├── config/                      # Configuration files
│   ├── cloud.example.json       # Example config
│   └── normal_guidance.txt      # Normal state prompt
├── deployment/                  # Deployment guides
│   ├── RAILWAY_SETUP.md         # Railway deployment
│   └── *.md                     # Device setup guides
├── device/                      # Device client
│   └── main_v2.py               # SSE-based client
├── docs/                        # Documentation
│   ├── CHANGELOG.md             # Version history
│   ├── PROJECT_PLAN.md          # Project roadmap
│   ├── PRODUCT_DESCRIPTION.md   # This file
│   ├── RAILWAY_TESTING.md       # Railway deployment guide
│   └── VERSIONING.md            # Versioning strategy
├── scripts/                     # Utility scripts
│   ├── db/                      # Database utilities
│   │   └── migrate.py           # Alembic migration runner
│   └── dev/                     # Development tools
│       ├── check_ai_status.py
│       ├── check_captures.py
│       ├── check_device_config.py
│       └── check_railway_db.py
├── tests/                       # Test files
│   ├── test_image_route.py
│   ├── test_pruning_logic.py
│   └── test_railway_path.py
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── alembic.ini                  # Alembic configuration
├── railway.json                 # Railway deployment config
├── requirements.txt             # Python dependencies
├── server.py                    # Main entry point
└── version.py                   # Version tracking
```

---

## Support & Documentation

**Project Documentation**
- `docs/PROJECT_PLAN.md` - Detailed roadmap and implementation status
- `docs/CHANGELOG.md` - Version history and release notes
- `docs/VERSIONING.md` - Versioning strategy and workflow
- `docs/RAILWAY_TESTING.md` - Railway deployment and debugging guide
- `deployment/RAILWAY_SETUP.md` - Step-by-step Railway deployment
- `deployment/DEPLOYMENT.md` - Raspberry Pi device setup

**API Documentation**
- OpenAPI/Swagger: `https://your-app.railway.app/docs`
- ReDoc: `https://your-app.railway.app/redoc`

**Contact**
- GitHub Issues: https://github.com/atxapple/visant/issues
- Email: support@visant.app (future)

---

**Built with ❤️ for visual monitoring**

*Last Updated: November 16, 2025*
*Version: 2.0 Multi-Tenant SaaS*

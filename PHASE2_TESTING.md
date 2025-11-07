# Phase 2 Testing Guide - Authentication & Multi-Tenancy

**Status**: ✅ Implementation Complete
**Date**: 2025-01-06

---

## What We Built

### 1. Authentication Infrastructure ✅
- Supabase client integration
- JWT token validation
- FastAPI authentication dependencies
- Secure password handling

### 2. Auth Endpoints ✅
- `POST /v1/auth/signup` - Create organization + user
- `POST /v1/auth/login` - Login with email/password
- `GET /v1/auth/me` - Get current user info
- `POST /v1/auth/logout` - Logout (client-side for now)

### 3. Device Management ✅
- `POST /v1/devices` - Register device (returns API key)
- `GET /v1/devices` - List organization's devices
- `GET /v1/devices/{device_id}` - Get device details
- `PUT /v1/devices/{device_id}` - Update device
- `DELETE /v1/devices/{device_id}` - Delete device

### 4. Security Features ✅
- JWT token validation
- Device API key authentication
- Organization-scoped data access
- Password requirements (min 6 chars)

---

## Prerequisites

### 1. Supabase Project Setup

**If you haven't created a Supabase project yet:**

1. Go to https://supabase.com
2. Click "New Project"
3. Fill in:
   - Name: "Visant" (or your choice)
   - Database Password: (save this!)
   - Region: Choose closest to you
4. Wait ~2 minutes for project creation

**Get your API keys:**

1. Go to **Settings → API**
2. Copy these values to your `.env` file:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_KEY`

3. Go to **Settings → API → JWT Settings**
4. Copy **JWT Secret** → `SUPABASE_JWT_SECRET`

### 2. Update `.env` File

Your `.env` should now have:

```bash
# AI Keys (existing)
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=...

# Supabase Auth (NEW - add these)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

---

## Testing Phase 2

### Step 1: Start the Test Server

```bash
# Make sure you're in the visant directory with venv activated
cd D:\dev\visant
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Start the test server
uvicorn test_auth_server:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 2: Open API Documentation

Open your browser to: **http://localhost:8000/docs**

You'll see the interactive Swagger UI with all endpoints.

---

## Test Scenarios

### Scenario 1: Create Account (Signup)

**Using Swagger UI:**

1. Go to http://localhost:8000/docs
2. Find `POST /v1/auth/signup`
3. Click "Try it out"
4. Enter request body:
```json
{
  "email": "test@example.com",
  "password": "test123",
  "org_name": "Test Organization"
}
```
5. Click "Execute"

**Expected Response (201 Created):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "...",
  "user": {
    "id": "uuid-here",
    "email": "test@example.com",
    "role": "admin"
  },
  "organization": {
    "id": "uuid-here",
    "name": "Test Organization"
  }
}
```

**Using curl:**
```bash
curl -X POST http://localhost:8000/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "org_name": "Test Organization"
  }'
```

**Save the `access_token`** - you'll need it for authenticated requests!

---

### Scenario 2: Login

**Using Swagger UI:**

1. Find `POST /v1/auth/login`
2. Click "Try it out"
3. Enter:
```json
{
  "email": "test@example.com",
  "password": "test123"
}
```
4. Click "Execute"

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "...",
  "user": {...},
  "organization": {...}
}
```

**Using curl:**
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123"
  }'
```

---

### Scenario 3: Get Current User

**Using Swagger UI:**

1. Find `GET /v1/auth/me`
2. Click the 🔒 lock icon (Authorize button at top)
3. Enter: `Bearer <your_access_token>`
4. Click "Authorize"
5. Now click "Try it out" on `/v1/auth/me`
6. Click "Execute"

**Expected Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "test@example.com",
  "role": "admin",
  "organization": {
    "id": "uuid",
    "name": "Test Organization"
  },
  "created_at": "2025-01-06T...",
  "last_login_at": "2025-01-06T..."
}
```

**Using curl:**
```bash
curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer eyJhbGc..."
```

---

### Scenario 4: Register a Device

**Using Swagger UI:**

1. Make sure you're authorized (see Scenario 3)
2. Find `POST /v1/devices`
3. Click "Try it out"
4. Enter:
```json
{
  "device_id": "test-camera-01",
  "friendly_name": "Test Camera 1"
}
```
5. Click "Execute"

**Expected Response (201 Created):**
```json
{
  "device_id": "test-camera-01",
  "friendly_name": "Test Camera 1",
  "status": "active",
  "created_at": "2025-01-06T...",
  "last_seen_at": null,
  "device_version": null,
  "api_key": "Np5X9fK2mL8qRv3tYu7wB1cD4eF6gH0jI",  // SAVE THIS!
  "organization": {
    "id": "uuid",
    "name": "Test Organization"
  }
}
```

**⚠️ IMPORTANT**: Save the `api_key`! It's only shown once and needed for device authentication.

**Using curl:**
```bash
curl -X POST http://localhost:8000/v1/devices \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-camera-01",
    "friendly_name": "Test Camera 1"
  }'
```

---

### Scenario 5: List Devices

**Using Swagger UI:**

1. Find `GET /v1/devices`
2. Click "Try it out"
3. Click "Execute"

**Expected Response (200 OK):**
```json
{
  "devices": [
    {
      "device_id": "test-camera-01",
      "friendly_name": "Test Camera 1",
      "status": "active",
      "created_at": "2025-01-06T...",
      "last_seen_at": null,
      "device_version": null,
      "organization": {
        "id": "uuid",
        "name": "Test Organization"
      }
    }
  ],
  "total": 1
}
```

---

### Scenario 6: Multi-Tenancy Test (Create Second Org)

**Purpose**: Verify data isolation between organizations.

1. **Create second account:**
```json
POST /v1/auth/signup
{
  "email": "org2@example.com",
  "password": "test123",
  "org_name": "Second Organization"
}
```

2. **Login as org2**
3. **Try to list devices** → Should return empty array (can't see org1's devices)
4. **Register device for org2**
5. **Login as org1 again** → Should NOT see org2's device

**Expected**: Complete data isolation between organizations ✅

---

## Common Issues & Solutions

### Error: "SUPABASE_URL or SUPABASE_KEY not set"

**Fix**: Check your `.env` file has all Supabase variables set.

```bash
# Verify env vars are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))"
```

### Error: "JWT secret not configured"

**Fix**: Add `SUPABASE_JWT_SECRET` to `.env`

### Error: "User with this email already exists"

**Fix**: Either:
- Use a different email
- Or login with the existing account

### Error: "Failed to create user: User already registered"

**Fix**: The user exists in Supabase but not in your database. This can happen if:
- You ran signup twice
- Signup failed partway through

**Solution**:
```bash
# Delete the user from Supabase dashboard
# Go to: Authentication → Users → Find user → Delete
# Then try signup again
```

---

## Verification Checklist

After testing, verify:

- [ ] ✅ Can create new account (signup)
- [ ] ✅ Can login with email/password
- [ ] ✅ Receive valid JWT tokens
- [ ] ✅ Can access protected endpoints with token
- [ ] ✅ Can register devices
- [ ] ✅ Device API keys are generated
- [ ] ✅ Can list devices for organization
- [ ] ✅ Two organizations have isolated data

---

## Database Inspection

Check what was created in SQLite:

```bash
# Install sqlite3 if needed
# On Windows: Already included with Python

# Open database
sqlite3 visant_dev.db

# List tables
.tables

# Query organizations
SELECT * FROM organizations;

# Query users
SELECT id, email, org_id, role FROM users;

# Query devices
SELECT device_id, org_id, friendly_name, status FROM devices;

# Exit
.quit
```

---

## Next Steps

After Phase 2 is verified:

### Phase 3: Public Sharing (Week 3)
- Share link generation
- Public gallery view (/s/{token})
- Social share buttons
- QR codes

### Phase 4: Update Existing Endpoints (Week 3-4)
- Add auth to capture upload endpoint
- Filter captures by org_id
- Update web dashboard with login

---

## API Reference

### Authentication Headers

**User endpoints (JWT)**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Device endpoints (API Key)**:
```
Authorization: Bearer Np5X9fK2mL8qRv3tYu7wB1cD4eF6gH0jI
```

---

**Phase 2 Status**: ✅ Complete and Ready for Testing!
**Last Updated**: 2025-01-06

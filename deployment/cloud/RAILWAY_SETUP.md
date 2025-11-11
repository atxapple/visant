# Railway Deployment Guide for Visant

Complete step-by-step instructions for deploying Visant multi-tenant camera monitoring SaaS to Railway.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Phase 1: Railway Project Setup](#phase-1-railway-project-setup)
- [Phase 2: Environment Variables](#phase-2-environment-variables)
- [Phase 3: Volume Setup](#phase-3-volume-setup)
- [Phase 4: Database Migration](#phase-4-database-migration)
- [Phase 5: Deploy Application](#phase-5-deploy-application)
- [Phase 6: Post-Deployment Verification](#phase-6-post-deployment-verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting deployment, ensure you have:
- [x] Railway account (https://railway.app)
- [x] GitHub repository connected
- [x] Railway CLI installed (optional but recommended)
- [x] PostgreSQL database provisioned on Railway
- [x] Supabase project configured for authentication
- [x] SendGrid API key for email notifications
- [x] OpenAI/Gemini API keys for AI classification

---

## Phase 1: Railway Project Setup

### Step 1.1: Create New Railway Project

1. Log in to Railway dashboard: https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `visant` repository
5. Railway will detect Python and auto-configure

### Step 1.2: Enable Automatic Deployments

1. Go to **Settings** tab
2. Under **"Deployments"**, enable:
   - ✅ **Auto-deploy from main branch**
   - ✅ **Deploy on push**
3. Click **"Save Changes"**

### Step 1.3: Configure Build Settings

1. In **Settings** → **Build**:
   - **Build Command**: (leave empty - auto-detected)
   - **Start Command**: `python test_server_v2.py`
2. Verify `Procfile` exists in root directory

---

## Phase 2: Environment Variables

### Step 2.1: Add Database Configuration

1. Go to **Variables** tab
2. Click **"New Variable"**
3. Add the following variables:

```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RAILWAY_DB_HOST:PORT/railway
```

**Note:** If you already have a Railway PostgreSQL service, Railway will automatically inject `DATABASE_URL`.

### Step 2.2: Add Authentication Variables

```bash
# Supabase Authentication
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_ANON_PUBLIC_KEY
SUPABASE_SERVICE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET=YOUR_JWT_SECRET
```

### Step 2.3: Add AI Service Keys

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_KEY

# Gemini API
GEMINI_API_KEY=YOUR_GEMINI_KEY
```

### Step 2.4: Add Email Configuration

```bash
# SendGrid Email
SENDGRID_API_KEY=SG.YOUR_SENDGRID_KEY
ALERT_FROM_EMAIL=alerts@yourdomain.com
ALERT_ENVIRONMENT_LABEL=production
```

### Step 2.5: Add CORS Configuration

```bash
# CORS Origins (update with your Railway URL)
CORS_ALLOWED_ORIGINS=https://YOUR_APP.railway.app,http://localhost:3000
```

**Important:** Replace `YOUR_APP.railway.app` with your actual Railway deployment URL after first deploy.

### Step 2.6: Verify All Variables

Check that you have all required environment variables:
- ✅ `DATABASE_URL`
- ✅ `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- ✅ `OPENAI_API_KEY`
- ✅ `GEMINI_API_KEY`
- ✅ `SENDGRID_API_KEY`, `ALERT_FROM_EMAIL`
- ✅ `CORS_ALLOWED_ORIGINS`

---

## Phase 3: Volume Setup

Railway provides persistent storage through volumes.

### Step 3.1: Add Volume to Service

1. Go to your service in Railway dashboard
2. Click **"Settings"** tab
3. Scroll to **"Volumes"**
4. Click **"Add Volume"**
5. Configure:
   - **Mount Path**: `/mnt/data`
   - **Size**: 1 GB (minimum, adjust based on needs)
6. Click **"Add"**

### Step 3.2: Create Directory Structure (Post-Deployment)

After first deployment, connect to your service and create directories:

Using Railway CLI:
```bash
railway run bash

# Inside the container:
mkdir -p /mnt/data/datalake
mkdir -p /mnt/data/config

# Verify
ls -la /mnt/data
```

Or create a one-time deployment script in `scripts/setup_volume.sh`:
```bash
#!/bin/bash
mkdir -p /mnt/data/datalake
mkdir -p /mnt/data/config
echo "Volume setup complete"
```

### Step 3.3: Upload Configuration Files

Copy configuration files to `/mnt/data/config`:

**normal_guidance.txt:**
```bash
railway run bash
cat > /mnt/data/config/normal_guidance.txt << 'EOF'
Normal state guidelines:
- All expected objects are present
- Nothing is out of place
- No unusual activity
EOF
```

**notifications.json:**
```bash
cat > /mnt/data/config/notifications.json << 'EOF'
{
  "enabled": true,
  "channels": ["email"],
  "email": {
    "enabled": true,
    "recipients": []
  }
}
EOF
```

---

## Phase 4: Database Migration

### Step 4.1: Connect to Railway Shell

Using Railway CLI:
```bash
railway link
railway run bash
```

Or from Railway dashboard:
1. Go to your service
2. Click **"Shell"** tab

### Step 4.2: Run Alembic Migrations

Inside the Railway shell:
```bash
# Verify Alembic is installed
pip list | grep alembic

# Check current migration status
alembic current

# Run all pending migrations
alembic upgrade head

# Verify migration success
alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> 8af79cab0d8d, initial_schema
INFO  [alembic.runtime.migration] Running upgrade 8af79cab0d8d -> 747d6fbf4733, add_evaluation_status_to_captures
INFO  [alembic.runtime.migration] Running upgrade 747d6fbf4733 -> aa246cbd4277, add_composite_index_for_capture_queries
```

### Step 4.3: Verify Database Schema

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# List all tables
\dt

# Verify organizations table
\d organizations

# Verify captures table has composite index
\di+ idx_captures_org_device_captured

# Exit
\q
```

**Expected tables:**
- `organizations`
- `users`
- `devices`
- `captures`
- `share_links`
- `activation_codes`
- `code_redemptions`
- `scheduled_triggers`
- `alembic_version`

---

## Phase 5: Deploy Application

### Step 5.1: Trigger Deployment

**Option A - Automatic (Recommended):**
Push to main branch:
```bash
git add Procfile railway.json deployment/RAILWAY_SETUP.md
git commit -m "Add Railway deployment configuration"
git push origin main
```

Railway will automatically detect the push and deploy.

**Option B - Manual:**
1. Go to Railway dashboard
2. Click **"Deploy"** button
3. Select **"Redeploy"**

### Step 5.2: Monitor Deployment Logs

1. Go to **"Deployments"** tab
2. Click on the latest deployment
3. Watch logs for:
   ```
   ======================================================================
   Starting Visant Cloud Server v2.0 (Cloud-Triggered Architecture)
   ======================================================================

   Features enabled:
     - Web UI: Login, Dashboard, Device Management
     - CommandHub: Real-time device command streaming (SSE)
     - TriggerScheduler: Automated scheduled captures

   Starting server...
   ----------------------------------------------------------------------
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

### Step 5.3: Get Deployment URL

1. Go to **"Settings"** tab
2. Under **"Domains"**, find your Railway URL:
   - Format: `https://YOUR_APP.railway.app`
3. **Copy this URL** - you'll need it for CORS and device configuration

### Step 5.4: Update CORS Origins

1. Go back to **"Variables"** tab
2. Update `CORS_ALLOWED_ORIGINS`:
   ```
   https://YOUR_APP.railway.app,http://localhost:3000
   ```
3. **Redeploy** for changes to take effect

---

## Phase 6: Post-Deployment Verification

### Step 6.1: Test Web UI

1. Open browser to: `https://YOUR_APP.railway.app/ui`
2. Verify login page loads
3. Try signing up with a test account
4. Verify redirect to dashboard

**Expected:**
- ✅ Login page loads without errors
- ✅ Can create new account
- ✅ Dashboard shows "No devices yet"

### Step 6.2: Test API Endpoints

Using curl or Postman:

**Health Check:**
```bash
curl https://YOUR_APP.railway.app/
```

**API Docs:**
```bash
curl https://YOUR_APP.railway.app/docs
```

**Login:**
```bash
curl -X POST https://YOUR_APP.railway.app/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

### Step 6.3: Test Device Registration

1. Log in to web UI
2. Click **"Add Device"**
3. Create activation code
4. Register a test device using the code
5. Verify device appears in dashboard

### Step 6.4: Test Image Upload

Using a test device client:

```python
import requests

# Upload test capture
device_id = "YOUR_DEVICE_ID"
url = f"https://YOUR_APP.railway.app/v1/captures"

with open("test_image.jpg", "rb") as f:
    files = {"file": f}
    data = {
        "device_id": device_id,
        "record_id": "TEST_20251110_120000_abc123",
        "captured_at": "2025-11-10T12:00:00Z",
        "trigger_label": "test"
    }
    response = requests.post(url, files=files, data=data)
    print(response.status_code, response.json())
```

### Step 6.5: Verify Thumbnail Generation

1. Go to device page in UI: `https://YOUR_APP.railway.app/ui/camera/DEVICE_ID`
2. Verify thumbnail loads
3. Click thumbnail to view full image
4. Refresh page - second load should be instant (cache working)

### Step 6.6: Check Storage Volume

Connect to Railway shell:
```bash
railway run bash

# Check datalake directory
ls -lh /mnt/data/datalake/

# Check disk usage
df -h /mnt/data

# Verify thumbnails are being generated
find /mnt/data/datalake -name "*_thumb.jpg"
```

### Step 6.7: Monitor Application Logs

Watch for any errors:
```bash
railway logs
```

**Look for:**
- ✅ No database connection errors
- ✅ No file system permission errors
- ✅ Successful capture ingestion
- ✅ Thumbnail generation logs
- ✅ Background evaluation processing

---

## Troubleshooting

### Issue: Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
1. Verify `DATABASE_URL` is set correctly
2. Check PostgreSQL service is running
3. Verify database user has correct permissions
4. Check network connectivity between services

### Issue: Volume Not Writable

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/mnt/data/datalake'
```

**Solution:**
1. Verify volume is mounted at `/mnt/data`
2. Check directory permissions:
   ```bash
   railway run bash
   ls -la /mnt/data
   chmod 755 /mnt/data
   ```
3. Verify user has write access

### Issue: Thumbnails Not Loading

**Symptoms:**
- 404 errors on thumbnail URLs
- Slow image loading

**Solution:**
1. Check thumbnail endpoint is working:
   ```bash
   curl https://YOUR_APP.railway.app/ui/captures/RECORD_ID/thumbnail
   ```
2. Verify thumbnail files exist:
   ```bash
   railway run bash
   find /mnt/data/datalake -name "*_thumb.jpg"
   ```
3. Check logs for thumbnail generation errors:
   ```bash
   railway logs | grep thumbnail
   ```

### Issue: CORS Errors

**Symptoms:**
```
Access to fetch at 'https://YOUR_APP.railway.app' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solution:**
1. Update `CORS_ALLOWED_ORIGINS` environment variable
2. Include both Railway URL and localhost:
   ```
   https://YOUR_APP.railway.app,http://localhost:3000
   ```
3. Redeploy application

### Issue: Alembic Migration Failed

**Symptoms:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'XXX'
```

**Solution:**
1. Check migration history:
   ```bash
   alembic history
   ```
2. Reset to base and re-run:
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```
3. If still failing, check `alembic_version` table:
   ```sql
   SELECT * FROM alembic_version;
   ```

### Issue: Out of Disk Space

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solution:**
1. Check disk usage:
   ```bash
   railway run bash
   df -h /mnt/data
   ```
2. Increase volume size in Railway dashboard
3. Verify disk pruning is working:
   ```bash
   railway logs | grep "disk space"
   ```
4. Manually trigger pruning if needed

---

## Performance Optimization

### Enable Connection Pooling

Already configured in `config/cloud.json`:
```json
"database": {
  "pool_size": 20,
  "max_overflow": 10,
  "pool_timeout": 30
}
```

### Monitor Query Performance

Check slow queries:
```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- View slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Verify Composite Index

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE indexname = 'idx_captures_org_device_captured';
```

---

## Security Checklist

Before production launch:

- [ ] Rotate all API keys in `.env`
- [ ] Use strong PostgreSQL password
- [ ] Enable Supabase RLS policies
- [ ] Configure SendGrid domain authentication
- [ ] Set up HTTPS/TLS certificates (Railway auto-provides)
- [ ] Enable Railway secret management
- [ ] Review CORS allowed origins
- [ ] Set up database backups
- [ ] Enable Railway service replicas (high availability)
- [ ] Configure monitoring and alerts

---

## Next Steps

After successful deployment:

1. **Update Device Clients**: Configure devices to use Railway URL
2. **Test End-to-End Flow**: Complete capture → upload → evaluation → notification cycle
3. **Monitor Performance**: Use Railway metrics dashboard
4. **Set Up Alerts**: Configure alerts for errors and downtime
5. **Document Device Setup**: Update `DEVICE_CLIENT_SETUP.md` with Railway URL

---

## Support

**Railway Documentation:**
- https://docs.railway.app/

**Visant Project Documentation:**
- `PROJECT_PLAN.md` - Project roadmap
- `deployment/DEPLOYMENT.md` - Raspberry Pi device setup
- `DEVICE_CLIENT_SETUP.md` - Device client configuration

**Contact:**
- GitHub Issues: https://github.com/atxapple/visant/issues

---

**Deployment completed!** 🚀

Your Visant multi-tenant camera monitoring SaaS is now live on Railway.

# Railway Testing & Debugging Guide

**Version:** 1.0
**Last Updated:** 2025-11-13
**Purpose:** Comprehensive guide for testing, debugging, and troubleshooting Railway.app deployments

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Railway CLI Setup](#railway-cli-setup)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Log Analysis](#log-analysis)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Database Debugging](#database-debugging)
9. [Environment Variables](#environment-variables)
10. [Performance Monitoring](#performance-monitoring)
11. [Rollback Procedures](#rollback-procedures)
12. [Testing Workflows](#testing-workflows)

---

## Overview

**Railway.app** is our production deployment platform for the Visant cloud backend. This guide provides systematic procedures for:

- Deploying code changes safely
- Verifying deployments are successful
- Debugging production issues
- Analyzing logs effectively
- Rolling back failed deployments

**Production URL:** https://app.visant.ai

**Railway Project:** visant-production

---

## Pre-Deployment Checklist

Before pushing code to production, verify these items:

### 1. Local Testing

```bash
# Ensure server starts without errors
python server.py

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### 2. Version Update

```bash
# Verify version.py has been updated
cat version.py

# Should show new version (e.g., v0.2.3)
__version__ = "0.2.3"
```

### 3. Database Migrations

```bash
# Check for pending migrations
alembic current
alembic history

# If new migrations exist, test them locally first
alembic upgrade head

# Verify no errors
```

### 4. Environment Variables

```bash
# Ensure all required env vars are set in Railway dashboard
# Check: DATABASE_URL, SUPABASE_*, OPENAI_API_KEY, GEMINI_API_KEY
railway variables
```

### 5. Git Status Clean

```bash
git status

# Should show:
# On branch main
# Your branch is up to date with 'origin/main'
# nothing to commit, working tree clean
```

### 6. Commit Quality

```bash
# Review recent commits
git log --oneline -5

# Ensure commit messages are clear and include version
# Format: "v0.2.3 - Description"
```

---

## Railway CLI Setup

### Installation

```bash
# Install Railway CLI (Windows with npm)
npm install -g @railway/cli

# Or with Homebrew (Mac/Linux)
brew install railway

# Verify installation
railway --version
```

### Authentication

```bash
# Login to Railway
railway login

# This opens a browser for authentication
# After login, you should see: "Logged in as <your-email>"

# Link to project
railway link

# Select: visant-production
```

### Verify Connection

```bash
# Check current project
railway status

# Should show:
# Project: visant-production
# Environment: production
# Service: web
```

---

## Deployment Process

### Step-by-Step Deployment

#### 1. Push to GitHub

```bash
# Push changes to main branch
git push origin main

# Railway automatically deploys on push to main
```

#### 2. Monitor Deployment

```bash
# Watch deployment logs in real-time
railway logs --follow

# Or view in Railway dashboard:
# https://railway.app/project/<project-id>/deployments
```

#### 3. Check Deployment Status

```bash
# View recent deployments
railway status

# Expected output:
# Deployment Status: SUCCESS
# Build Time: 2m 15s
# Deploy Time: 45s
```

### Manual Deployment (Alternative)

```bash
# Deploy directly from local machine
railway up

# This uploads code and triggers build/deploy
# Useful for hotfixes or testing
```

---

## Post-Deployment Verification

### Verification Checklist

Run these checks **immediately** after deployment:

#### 1. Health Check

```bash
# Test API is responding
curl https://app.visant.ai/docs

# Should return 200 OK with Swagger UI
```

#### 2. Version Verification

```bash
# Check deployed version matches committed version
railway logs | grep "Visant Cloud v"

# Expected output:
# [startup] Visant Cloud v0.2.3
```

**Alternative:** Visit UI and check footer for version number.

#### 3. Database Migration Status

```bash
# Check migration logs
railway logs | grep -i "migration\|alembic"

# Expected output:
# [migrate] Starting database migrations...
# [migrate] Running upgrade -> db7d78dfcf08, add alert_definitions table
# [migrate] Database migrations completed successfully!
```

#### 4. Application Startup

```bash
# Check for startup errors
railway logs | grep -i "error\|exception\|failed" | head -20

# If empty, no errors (good!)
# If output, investigate each error
```

#### 5. Key Endpoints Test

```bash
# Test critical endpoints
curl https://app.visant.ai/v1/auth/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'

# Expected: 200 or 401 (not 500)

# Test device endpoint
curl https://app.visant.ai/v1/devices \
  -H "Authorization: Bearer <valid-token>"

# Expected: 200 with device list
```

#### 6. Database Connectivity

```bash
# Check database connection logs
railway logs | grep -i "database\|postgres\|connection"

# Expected:
# [startup] Database connection established
# [startup] PostgreSQL version: 15.3
```

---

## Log Analysis

### Accessing Logs

#### Real-Time Logs

```bash
# Stream logs as they occur
railway logs --follow

# Stop with Ctrl+C
```

#### Recent Logs

```bash
# Last 100 lines
railway logs

# Last 500 lines
railway logs --lines 500

# Last hour
railway logs --since 1h

# Last 24 hours
railway logs --since 24h
```

#### Search Logs

```bash
# Search for specific keywords
railway logs | grep "error"
railway logs | grep "500"
railway logs | grep "migration"

# Case-insensitive search
railway logs | grep -i "exception"

# Search with context (5 lines before and after)
railway logs | grep -A5 -B5 "ImportError"
```

### Log Patterns to Look For

#### Successful Startup

```
[startup] Visant Cloud v0.2.3
[startup] Environment: production
[migrate] Starting database migrations...
[migrate] Database migrations completed successfully!
[startup] Loaded 15 alert definitions into cache
[startup] Starting TriggerScheduler...
[startup] Starting CommandHub...
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

#### Migration Success

```
[migrate] Starting database migrations...
[migrate] INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
[migrate] INFO  [alembic.runtime.migration] Will assume transactional DDL.
[migrate] INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add new table
[migrate] Database migrations completed successfully!
```

#### Application Error

```
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/app/cloud/api/routes/devices.py", line 42, in get_devices
    devices = session.query(Device).filter(...)
AttributeError: 'NoneType' object has no attribute 'query'
```

**Action:** Investigate the specific file and line number.

---

## Common Issues & Solutions

### Issue 1: Deployment Shows Old Version

**Symptoms:**
- UI footer shows old version (e.g., v0.2.0 instead of v0.2.3)
- Recent changes not visible in production

**Diagnosis:**
```bash
# Check deployed version in logs
railway logs | grep "Visant Cloud v"

# Check latest commit
git log --oneline -1

# Verify push was successful
git log origin/main --oneline -1
```

**Common Causes:**
1. Browser cache (hard refresh: Ctrl+Shift+R)
2. Deployment failed silently
3. `version.py` not committed

**Solution:**
```bash
# 1. Verify version.py is committed
git show HEAD:version.py

# 2. Force redeploy
railway up

# 3. Clear browser cache and hard refresh
```

---

### Issue 2: Database Migration Errors

**Symptoms:**
- Logs show migration failures
- 500 errors on API endpoints
- "column does not exist" errors

**Example Error:**
```
[migrate] ERROR: column "alert_definition_id" does not exist
[migrate] Migration failed: (psycopg2.errors.UndefinedColumn)
```

**Diagnosis:**
```bash
# Check current migration state
railway run alembic current

# Check migration history
railway run alembic history

# View specific migration
railway run alembic show db7d78dfcf08
```

**Solution:**
```bash
# Option 1: Retry migration
railway run alembic upgrade head

# Option 2: Rollback and reapply
railway run alembic downgrade -1
railway run alembic upgrade head

# Option 3: Stamp database (if migration already applied manually)
railway run alembic stamp head
```

**Prevention:**
- Always test migrations locally first
- Review generated migrations before committing
- Never edit migration files after they've been deployed

---

### Issue 3: Environment Variable Missing

**Symptoms:**
- Logs show "KeyError" or "Environment variable X not set"
- Authentication fails
- AI evaluation returns errors

**Example Error:**
```
ERROR: Environment variable OPENAI_API_KEY not set
KeyError: 'SUPABASE_JWT_SECRET'
```

**Diagnosis:**
```bash
# List all environment variables
railway variables

# Check specific variable
railway variables | grep OPENAI_API_KEY
```

**Solution:**
```bash
# Set missing variable via CLI
railway variables set OPENAI_API_KEY=sk-...

# Or via Railway dashboard:
# 1. Go to project → Variables
# 2. Click "+ New Variable"
# 3. Enter name and value
# 4. Click "Add"
# 5. Redeploy: railway up
```

**Verification:**
```bash
# Check variable is set
railway run printenv | grep OPENAI_API_KEY

# Test in application
railway run python -c "import os; print(os.getenv('OPENAI_API_KEY', 'NOT SET'))"
```

---

### Issue 4: Import Errors

**Symptoms:**
- Logs show "ImportError" or "ModuleNotFoundError"
- Server fails to start

**Example Error:**
```
ImportError: cannot import name 'app_state' from 'cloud.api.server'
ModuleNotFoundError: No module named 'PIL'
```

**Diagnosis:**
```bash
# Check if dependency is in requirements.txt
grep PIL requirements.txt

# Check installed packages (in Railway)
railway run pip list | grep Pillow
```

**Solution for Missing Dependency:**
```bash
# Add to requirements.txt
echo "Pillow==10.0.0" >> requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Add Pillow dependency"
git push origin main
```

**Solution for Import Error:**
```bash
# Review import statement in code
# Ensure module path is correct
# Example fix:
# Wrong: from cloud.api.server import app_state
# Right: from cloud.api.server import get_alert_definition_cache
```

---

### Issue 5: 500 Internal Server Error

**Symptoms:**
- API endpoints return 500 status
- UI shows "Failed to load X"
- No specific error message to user

**Diagnosis:**
```bash
# Search logs for 500 errors and stack traces
railway logs | grep -A20 "500\|ERROR\|Exception"

# Common locations for 500 errors:
# - Database queries (null pointer, missing column)
# - File operations (permission denied, not found)
# - External API calls (timeout, auth failure)
```

**Example Analysis:**
```bash
# Log shows:
ERROR: Exception in /v1/devices endpoint
File "cloud/api/routes/devices.py", line 45
  device_config = device.normal_description_file
AttributeError: 'Device' object has no attribute 'normal_description_file'

# Problem: Code references removed database column
# Solution: Remove code that accesses normal_description_file
```

**General Solution:**
1. Identify exact error from logs
2. Locate file and line number
3. Fix code issue
4. Test locally
5. Commit with descriptive message
6. Push and verify

---

### Issue 6: Database Connection Failures

**Symptoms:**
- Logs show "could not connect to database"
- Timeouts on database queries
- "too many connections" errors

**Example Error:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
could not connect to server: Connection refused
```

**Diagnosis:**
```bash
# Check DATABASE_URL is set
railway variables | grep DATABASE_URL

# Test connection
railway run python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
print('Connection successful!')
conn.close()
"
```

**Solution:**
```bash
# Verify DATABASE_URL format
# Should be: postgresql://user:pass@host:port/dbname

# If using Railway PostgreSQL plugin:
# 1. Check plugin is attached: railway plugins
# 2. Reconnect plugin if needed
# 3. Redeploy: railway up
```

---

## Database Debugging

### Accessing Production Database

**WARNING:** Be extremely careful when accessing production database. Always use read-only queries unless absolutely necessary.

#### Via Railway CLI

```bash
# Open psql shell
railway run psql $DATABASE_URL

# Read-only query examples
SELECT * FROM devices LIMIT 10;
SELECT COUNT(*) FROM captures;
SELECT * FROM alert_definitions WHERE is_active = true;

# Exit psql
\q
```

#### Check Database Schema

```bash
# List all tables
railway run psql $DATABASE_URL -c "\dt"

# Describe table structure
railway run psql $DATABASE_URL -c "\d devices"
railway run psql $DATABASE_URL -c "\d captures"
railway run psql $DATABASE_URL -c "\d alert_definitions"
```

#### Check Migration Status

```bash
# View Alembic version table
railway run psql $DATABASE_URL -c "SELECT * FROM alembic_version;"

# Expected output:
#  version_num
# --------------
#  db7d78dfcf08
```

### Common Database Queries for Debugging

#### Check Device Count

```bash
railway run psql $DATABASE_URL -c "
SELECT
  COUNT(*) as total_devices,
  COUNT(DISTINCT org_id) as total_orgs
FROM devices;
"
```

#### Check Recent Captures

```bash
railway run psql $DATABASE_URL -c "
SELECT
  record_id,
  device_id,
  classification_state,
  evaluation_status,
  captured_at
FROM captures
ORDER BY captured_at DESC
LIMIT 10;
"
```

#### Check Alert Definitions

```bash
railway run psql $DATABASE_URL -c "
SELECT
  device_id,
  version,
  is_active,
  created_at,
  LEFT(description, 50) as description_preview
FROM alert_definitions
WHERE is_active = true
ORDER BY created_at DESC;
"
```

#### Check Failed Evaluations

```bash
railway run psql $DATABASE_URL -c "
SELECT
  record_id,
  device_id,
  evaluation_status,
  captured_at
FROM captures
WHERE evaluation_status = 'failed'
ORDER BY captured_at DESC
LIMIT 10;
"
```

---

## Environment Variables

### Required Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anon key | `eyJhbGc...` |
| `SUPABASE_JWT_SECRET` | JWT signature verification | `super-secret-key` |
| `OPENAI_API_KEY` | OpenAI API access | `sk-...` |
| `GEMINI_API_KEY` | Google Gemini API access | `AIza...` |
| `SENDGRID_API_KEY` | Email alerts (optional) | `SG....` |
| `SENDGRID_FROM_EMAIL` | Email sender (optional) | `noreply@visant.ai` |
| `STORAGE_PATH` | File storage location | `/mnt/data` |

### Verification Script

Save as `scripts/verify_env.py`:

```python
#!/usr/bin/env python
"""Verify all required environment variables are set."""
import os
import sys

REQUIRED_VARS = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_JWT_SECRET",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
]

OPTIONAL_VARS = [
    "SENDGRID_API_KEY",
    "SENDGRID_FROM_EMAIL",
    "STORAGE_PATH",
]

def main():
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            print(f"✅ {var}: SET")

    print("\nOptional variables:")
    for var in OPTIONAL_VARS:
        if not os.getenv(var):
            print(f"⚠️  {var}: NOT SET (optional)")
        else:
            print(f"✅ {var}: SET")

    if missing:
        print(f"\n❌ Missing {len(missing)} required variables")
        sys.exit(1)
    else:
        print("\n✅ All required variables set!")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Local check
python scripts/verify_env.py

# Railway check
railway run python scripts/verify_env.py
```

---

## Performance Monitoring

### Monitor Response Times

```bash
# Monitor logs for slow requests
railway logs | grep -i "slow\|timeout\|took"

# Look for patterns like:
# [perf] Request to /v1/captures took 5.2s
# [warn] Database query slow: 3.1s
```

### Monitor Memory Usage

```bash
# Railway dashboard shows memory usage
# Or query via API (if available)
railway status

# Look for:
# Memory: 256MB / 512MB (50%)
```

### Monitor Database Connections

```bash
# Check active connections
railway run psql $DATABASE_URL -c "
SELECT
  COUNT(*) as active_connections,
  state
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state;
"
```

---

## Rollback Procedures

### When to Rollback

Rollback if:
- Deployment causes 500 errors affecting users
- Database migration corrupts data
- Critical feature is broken
- Security vulnerability introduced

### Rollback Methods

#### Method 1: Revert to Previous Deployment (Railway Dashboard)

1. Go to Railway dashboard → Deployments
2. Find last successful deployment
3. Click "..." → "Redeploy"
4. Confirm redeploy

#### Method 2: Git Revert (Recommended)

```bash
# Find commit hash of last good version
git log --oneline -10

# Revert specific commit
git revert <bad-commit-hash>

# Or revert to specific commit
git reset --hard <good-commit-hash>
git push origin main --force-with-lease

# WARNING: Only use --force-with-lease if you're sure!
```

#### Method 3: Rollback Migration Only

```bash
# If only database migration is the issue
railway run alembic downgrade -1

# Or to specific version
railway run alembic downgrade <revision>
```

### Post-Rollback

After rollback:
1. Verify deployment status
2. Test critical endpoints
3. Check logs for errors
4. Notify users (if necessary)
5. Investigate root cause
6. Fix issue in separate branch
7. Test thoroughly before redeploying

---

## Testing Workflows

### Pre-Deployment Testing

```bash
# 1. Run local server
python server.py

# 2. Test in browser
# Visit: http://localhost:8000

# 3. Test API endpoints
curl http://localhost:8000/docs

# 4. Run migrations (if any)
alembic upgrade head

# 5. Check for errors in console
```

### Post-Deployment Testing

```bash
# 1. Check version deployed
railway logs | grep "Visant Cloud v"

# 2. Test homepage
curl -I https://app.visant.ai/

# 3. Test API docs
curl -I https://app.visant.ai/docs

# 4. Test device endpoint (with auth)
curl https://app.visant.ai/v1/devices \
  -H "Authorization: Bearer <token>"

# 5. Check logs for errors
railway logs | grep -i error | head -20
```

### Automated Testing (Future)

Create `scripts/test_deployment.sh`:

```bash
#!/bin/bash
# Automated deployment testing script

BASE_URL="https://app.visant.ai"

echo "Testing deployment..."

# Test 1: Homepage
echo "1. Testing homepage..."
status=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/)
if [ "$status" == "200" ]; then
  echo "✅ Homepage OK"
else
  echo "❌ Homepage failed: $status"
  exit 1
fi

# Test 2: API docs
echo "2. Testing API docs..."
status=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/docs)
if [ "$status" == "200" ]; then
  echo "✅ API docs OK"
else
  echo "❌ API docs failed: $status"
  exit 1
fi

# Test 3: Health check
echo "3. Testing health endpoint..."
status=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/health)
if [ "$status" == "200" ]; then
  echo "✅ Health check OK"
else
  echo "⚠️  Health check failed: $status (may not be implemented)"
fi

echo "✅ All tests passed!"
```

---

## Quick Reference

### Essential Commands

```bash
# Deploy
git push origin main

# View logs
railway logs --follow

# Check status
railway status

# Run command in production
railway run <command>

# Set environment variable
railway variables set KEY=value

# Database shell
railway run psql $DATABASE_URL

# Redeploy
railway up
```

### Debugging Flowchart

```
Issue Detected
    ↓
Check Railway logs
    ↓
Error found? → YES → Identify file/line → Fix code → Deploy
    ↓ NO
Check database
    ↓
Query works? → NO → Check migrations → Run alembic upgrade → Verify
    ↓ YES
Check environment variables
    ↓
All set? → NO → Set missing vars → Redeploy
    ↓ YES
Check external services (Supabase, OpenAI)
    ↓
Services OK? → NO → Contact service provider
    ↓ YES
Escalate to senior developer
```

---

## For Future AI Assistants

When debugging Railway issues, follow this systematic approach:

1. **Always start with logs**: `railway logs | grep -i error`
2. **Check version consistency**: Ensure deployed version matches expected
3. **Verify migrations**: Check Alembic version matches code
4. **Test locally first**: Never debug directly in production
5. **Document findings**: Update this guide with new issues encountered
6. **Be cautious with database**: Always use read-only queries unless necessary

**Common Pitfalls:**
- Assuming version.py was updated (always verify)
- Forgetting to check migration logs
- Not testing locally before deploying
- Missing environment variables after Railway project changes
- Not checking Railway deployment status before investigating code

---

**Maintainers:** Visant Development Team
**Last Reviewed:** 2025-11-13
**Next Review:** When new deployment patterns emerge or issues arise

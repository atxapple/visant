# Visant Versioning System

**Version:** 1.0
**Last Updated:** 2025-11-13
**Purpose:** Define the versioning strategy for Visant cloud and device components

---

## Overview

Visant uses **semantic versioning (semver)** to track releases across both cloud backend and device client components. This document defines when and how to increment version numbers, ensuring consistency and clarity for debugging, deployment, and communication.

## Semantic Versioning Format

```
MAJOR.MINOR.PATCH
```

**Example:** `0.2.2`
- `0` = MAJOR version (pre-1.0 indicates beta/development)
- `2` = MINOR version (features added)
- `2` = PATCH version (bug fixes)

### Version Components

#### MAJOR Version (X.0.0)

Increment when making **incompatible API changes** that break existing integrations:

**Examples:**
- Changing authentication mechanism (Supabase → different provider)
- Removing or renaming API endpoints (e.g., `/v1/devices` → `/v2/devices`)
- Breaking database schema changes requiring data migration
- Device protocol changes requiring device firmware updates
- Multi-tenant architecture → single-tenant (or vice versa)

**Impact:** Requires coordinated updates across cloud and device components.

**Current Status:** Version `0.x.x` indicates pre-1.0 development phase where breaking changes are expected.

#### MINOR Version (0.X.0)

Increment when adding **backwards-compatible functionality**:

**Examples:**
- New API endpoints (e.g., `/v1/admin/users`, `/v1/reports`)
- New database tables or columns (non-breaking)
- New features (alert definitions, scheduling, sharing)
- New AI classifier models (GPT-5, Claude integration)
- New web UI pages or dashboard features
- Enhanced device capabilities (new capture modes)

**Impact:** Existing integrations continue working; new features available.

**Database Migrations:** Create Alembic migrations for schema additions.

#### PATCH Version (0.0.X)

Increment when making **backwards-compatible bug fixes**:

**Examples:**
- Fix crash in image upload handler
- Correct authentication token validation logic
- Fix SSE connection timeout issues
- UI bug fixes (modal not closing, incorrect display)
- Database query optimization (no schema change)
- Documentation updates (like this file!)
- Dependency updates (security patches)

**Impact:** No behavior changes; only fixes incorrect behavior.

---

## Version File Location

### Cloud Backend

**File:** `version.py`

```python
"""Visant version information.

Version numbering follows semantic versioning (semver.org):
- MAJOR version: Incompatible API changes
- MINOR version: Backwards-compatible functionality additions
- PATCH version: Backwards-compatible bug fixes
"""

__version__ = "0.2.2"
```

**Usage in Code:**
```python
from version import __version__

print(f"Visant Cloud v{__version__}")
```

**Display Location:**
- Web UI footer: "Cloud v0.2.2"
- API `/v1/version` endpoint (planned)
- Server startup logs

### Device Client

**File:** `device_client/version.py` (same format as cloud)

**Display Location:**
- Device logs on startup
- Device registration API payload
- Device dashboard UI

---

## Versioning Workflow

### Step-by-Step Process

#### 1. Determine Version Increment

Ask these questions:

1. **Does this change break existing API contracts or device compatibility?**
   - YES → Increment MAJOR
   - NO → Continue to question 2

2. **Does this add new functionality or features?**
   - YES → Increment MINOR
   - NO → Continue to question 3

3. **Does this fix a bug or update documentation?**
   - YES → Increment PATCH
   - NO → No version change needed (internal refactoring only)

#### 2. Update `version.py`

Edit `version.py` before committing code:

```python
# Before
__version__ = "0.2.2"

# After (example: adding new feature)
__version__ = "0.3.0"
```

#### 3. Commit with Version Number

Include version in commit message:

```bash
git commit -m "v0.3.0 - Add notification preferences UI

Implement user notification settings page with email/SMS preferences.
Adds new database table notification_preferences and API endpoints.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Format:** `v{VERSION} - {Short description}`

#### 4. Create Git Tag (Release Milestones Only)

For significant releases (not every patch):

```bash
# Create annotated tag
git tag -a v0.3.0 -m "Release v0.3.0: Notification preferences"

# Push tags to remote
git push origin v0.3.0
```

**When to Tag:**
- MAJOR releases (always)
- MINOR releases (always)
- PATCH releases (only if significant bug fix or production hotfix)

#### 5. Deploy to Railway

Railway automatically deploys on push to `main`:

```bash
git push origin main
```

**Verification Steps:**
1. Check Railway deployment logs for version number
2. Visit production UI and verify footer displays new version
3. Test affected functionality

---

## Version History Tracking

### Changelog Location

**File:** `docs/CHANGELOG.md` (to be created)

**Format:**
```markdown
# Changelog

## [0.3.0] - 2025-11-13

### Added
- Notification preferences UI at `/ui/settings/notifications`
- Email/SMS toggle settings per device
- Database table `notification_preferences`

### Changed
- Alert email template now respects user preferences

### Fixed
- None

## [0.2.2] - 2025-11-13

### Fixed
- Alert definition save endpoint now correctly stores definitions
- Modal popup displays alert definition version and metadata
```

### Git Log as Changelog

For quick version history:

```bash
# View versions in git history
git log --oneline --grep="^v[0-9]"

# View changes between versions
git log v0.2.0..v0.2.2 --oneline
```

---

## Pre-1.0 Development Phase

**Current Status:** Visant is in version `0.x.x`

**Implications:**
- API may change without MAJOR version increment
- Database schema migrations may require manual intervention
- Device compatibility may break between MINOR versions
- Production deployments should be coordinated

**Graduation to v1.0.0:**

Criteria for releasing `v1.0.0`:
1. ✅ Multi-tenant architecture stable
2. ✅ Core features complete (devices, captures, AI evaluation, alerts)
3. ❌ Comprehensive test coverage (target: 80%+)
4. ❌ API documentation finalized
5. ❌ Device client auto-update mechanism
6. ❌ Production monitoring and alerting
7. ❌ Public beta with 10+ organizations

**Target Date:** Q1 2026

---

## Component Version Compatibility

### Cloud ↔ Device Compatibility Matrix

| Cloud Version | Compatible Device Versions | Notes |
|---------------|---------------------------|-------|
| 0.2.x | 0.2.0+ | SSE command protocol stable |
| 0.3.x | 0.2.0+ | Backward compatible API |
| 1.0.0 | 1.0.0+ | Breaking changes; devices must upgrade |

### Database Migration Compatibility

**Rule:** Cloud version must match database schema version.

**Verification:**
```bash
# Check current database version
alembic current

# Check pending migrations
alembic history

# Ensure match with code version
python -c "from version import __version__; print(__version__)"
```

**Railway Deployment:** Migrations run automatically via `scripts/db/migrate.py` before server starts.

---

## Version Display Guidelines

### Web UI Footer

**Location:** `cloud/web/templates/base.html` (or equivalent)

**Format:**
```html
<footer>
  <p>Cloud v{{ version }} | Device v{{ device_version }}</p>
</footer>
```

**Implementation:**
```python
from version import __version__

@router.get("/ui/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "version": __version__
    })
```

### API Version Endpoint

**Planned:** `/v1/version` endpoint

```python
from fastapi import APIRouter
from version import __version__

router = APIRouter()

@router.get("/v1/version")
async def get_version():
    return {
        "version": __version__,
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "database_version": get_alembic_version()
    }
```

### Server Startup Logs

**Current:**
```
[startup] Visant Cloud v0.2.2
[startup] Environment: production
[startup] Database version: db7d78dfcf08
```

---

## Troubleshooting Version Mismatches

### Symptom: UI shows old version

**Cause:** Browser cache or server not restarted

**Fix:**
```bash
# Local development
# 1. Restart server
Ctrl+C
python server.py

# 2. Hard refresh browser
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

### Symptom: Railway deployment shows old version

**Cause:** Deployment not completed or `version.py` not updated

**Fix:**
```bash
# Check Railway logs
railway logs

# Look for startup message with version
# If missing, redeploy:
git push origin main --force-with-lease
```

### Symptom: Database migration conflicts

**Cause:** Version mismatch between code and database schema

**Fix:**
```bash
# Check current migration
alembic current

# Check code version
python -c "from version import __version__; print(__version__)"

# If mismatch, run migrations
alembic upgrade head

# Or on Railway, redeploy (scripts/db/migrate.py runs automatically)
railway up
```

---

## Best Practices

### DO:
- ✅ Update `version.py` in the same commit as the change
- ✅ Include version number in commit message for releases
- ✅ Test deployments on Railway before merging to main
- ✅ Document breaking changes in commit message body
- ✅ Create git tags for MINOR and MAJOR releases
- ✅ Keep version in sync across related changes

### DON'T:
- ❌ Increment version for every commit (only for releases)
- ❌ Use git commit hash as version number
- ❌ Deploy to production without version increment
- ❌ Skip version increment for bug fixes ("it's just a small fix")
- ❌ Use different versions for cloud and device if they depend on each other

---

## Future Enhancements

### Planned Improvements

1. **Automated Version Bumping**
   - Script: `scripts/bump_version.py`
   - Usage: `python scripts/bump_version.py minor`
   - Auto-updates `version.py` and creates commit

2. **Version API Endpoint**
   - Endpoint: `GET /v1/version`
   - Returns: Cloud version, database version, environment

3. **Device Version Tracking**
   - Store device client version in `devices` table
   - Display in admin dashboard
   - Alert on version mismatch

4. **Changelog Generator**
   - Auto-generate `CHANGELOG.md` from git commits
   - Parse commit messages for version entries
   - Group by version and category (Added/Changed/Fixed)

5. **Pre-release Versions**
   - Format: `0.3.0-beta.1`, `1.0.0-rc.2`
   - For testing before stable release

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Railway Deployment Documentation](https://docs.railway.app/)
- [Alembic Migration Guide](https://alembic.sqlalchemy.org/)

---

**Maintainers:** Visant Development Team
**Questions:** Create an issue on GitHub or contact maintainers

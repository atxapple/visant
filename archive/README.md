# Archive Directory

This directory contains obsolete, superseded, or completed files from the Visant project. Files are archived (not deleted) to preserve project history and provide reference for past implementation approaches.

**Archived on:** 2025-11-09

---

## Directory Structure

```
archive/
├── tests/          # Obsolete test scripts
├── docs/           # Historical phase documentation
├── legacy/         # Old implementation files (filesystem-based)
└── scripts/        # One-time migration scripts
```

---

## Archived Files

### `tests/` - Obsolete Test Scripts

#### `test_auth_server.py`
- **Purpose**: Minimal FastAPI test server for Phase 2-4 development
- **Why archived**: This was a development-only server. Production uses `cloud/api/main.py` and `cloud/api/server.py`
- **Notes**: Still imported legacy `FileSystemDatalake` and `RecentCaptureIndex`
- **Superseded by**: Production server at `cloud/api/main.py`

#### `test_comprehensive.py`
- **Purpose**: Comprehensive integration test suite for Phase 5 Week 2
- **Why archived**: Phase-specific test that covered authentication, device management, activation codes
- **Notes**: 329 lines, tested static files and dashboard UI
- **Superseded by**: `test_end_to_end_device_flow.py` provides more focused E2E coverage

#### `test_device_flow.py`
- **Purpose**: Device validation and activation testing (176 lines)
- **Why archived**: Functionality covered by more comprehensive tests
- **Superseded by**: `test_end_to_end_device_flow.py`

#### `test_device_config.py`
- **Purpose**: Device configuration API endpoint testing (230 lines)
- **Why archived**: Duplicate functionality
- **Superseded by**: `test_week3_complete.py` had more comprehensive config testing

#### `test_week3_complete.py`
- **Purpose**: Complete Week 3 testing for per-device configuration (327 lines)
- **Why archived**: Phase-specific test - Week 3 completed, functionality verified
- **Notes**: Could be kept for regression testing, but integration tests now cover this

#### `test_api_call.py`
- **Purpose**: Manual API testing script with hardcoded JWT token (49 lines)
- **Why archived**: Manual testing script with hardcoded tokens from Phase 2
- **Superseded by**: Automated test suite

#### `test_routes_debug.py`
- **Purpose**: Debug script to check route registration (39 lines)
- **Why archived**: One-time debugging utility, no longer needed

#### `check_capture.py`
- **Purpose**: Database query script to check capture data (28 lines)
- **Why archived**: Manual debugging tool with hardcoded email address
- **Notes**: Used for one-time data inspection

#### `body.json`
- **Purpose**: Test fixture or example request body (36 bytes)
- **Why archived**: Sample test data, not actively used

---

### `docs/` - Historical Phase Documentation

#### `PHASE1_COMPLETE.md`
- **Purpose**: Phase 1 completion documentation from 2025-01-06
- **Why archived**: Phase 1 is complete (Phases 2-5 are now done)
- **Historical context**: Early foundation work - Alembic migrations, basic database setup

#### `PHASE2_TESTING.md`
- **Purpose**: Phase 2 testing guide with manual Supabase setup instructions
- **Why archived**: Phase 2 is complete, manual testing instructions now outdated
- **Superseded by**: Automated tests cover Phase 2 functionality

#### `GETTING_STARTED.md`
- **Purpose**: "Getting Started with Phase 1" - Alembic setup guide
- **Why archived**: Refers only to Phase 1, current setup much more advanced
- **Superseded by**: Current README.md and PROJECT_PLAN.md

#### `NEXT_STEPS.md`
- **Purpose**: "Phase 5 Week 3 - Per-Device Configuration" planning document
- **Why archived**: Week 3 completed according to git history
- **Notes**: This was forward-looking planning documentation for work now completed

#### `DEV-BRANCH.md`
- **Purpose**: Development branch workflow documentation
- **Why archived**: Development workflow may have changed since this was written
- **Notes**: Review to confirm if git workflow still matches documented approach

---

### `legacy/` - Old Implementation Files

#### `storage.py` (from `cloud/datalake/`)
- **Purpose**: `FileSystemDatalake` class for local filesystem storage
- **Why archived**: Legacy filesystem-based storage system
- **Still imported by**: `test_auth_server.py` (archived), `tests/test_similarity_reuse.py`, `tests/test_inference_notifications.py`, `cloud/api/server.py`
- **Superseded by**: Database-driven storage in `cloud/api/routes/captures.py`
- **Migration status**: Production routes use database exclusively

#### `capture_index.py` (from `cloud/api/`)
- **Purpose**: `RecentCaptureIndex` for in-memory filesystem-based capture tracking
- **Why archived**: Legacy in-memory index from filesystem era
- **Still imported by**: `test_auth_server.py` (archived), `cloud/api/server.py`
- **Superseded by**: Database queries replace in-memory indexing
- **Migration status**: Database now stores captures directly

---

### `scripts/` - One-Time Migration Scripts

#### `migrate_to_multitenancy.py`
- **Purpose**: One-time migration script from single-tenant to multi-tenant architecture
- **Why archived**: Migration completed (project is now multi-tenant)
- **Status**: Keep for reference, but migration is done
- **Notes**: Useful to review if rolling back or understanding migration approach

---

## Files KEPT in Active Project

The following files remain in the project root and are actively maintained:

### Active Test Files
- `test_end_to_end_device_flow.py` - Critical end-to-end device flow test (306 lines)
- `laptop_camera_test.py` - Webcam integration test with OpenCV (214 lines)
- `tests/` directory - Active pytest test suite with proper fixtures

### Active Scripts
- `scripts/seed_activation_codes.py` - Seed database with activation codes (dev setup)
- `scripts/seed_test_devices.py` - Seed test devices (dev setup)
- `scripts/nim_smoke_test.py` - NVIDIA NIM API smoke test

---

## Restoration

If you need to restore any archived file:

```bash
# Example: Restore a test file
git mv archive/tests/test_device_flow.py .

# Example: Restore a doc file
git mv archive/docs/PHASE2_TESTING.md .
```

---

## Cleanup Notes

**Active Code Check**: Before archiving, verified that no active production code imports these files. The only remaining imports are:
- Legacy server (`cloud/api/server.py`) still imports `storage.py` and `capture_index.py`
- Old unit tests still import `storage.py`

These legacy files will be removed once:
1. `cloud/api/server.py` is confirmed to be unused in production
2. Unit tests are updated to use database fixtures instead of filesystem

---

## Archive History

**2025-11-09**: Initial archive creation
- 9 test files archived (test scripts, debug utilities)
- 5 documentation files archived (phase-specific docs)
- 2 legacy implementation files archived (filesystem storage)
- 1 migration script archived (multi-tenancy migration)
- **Total**: 17 files archived

---

For current project documentation, see:
- `README.md` - Main project documentation
- `PROJECT_PLAN.md` - Current project plan and phase status

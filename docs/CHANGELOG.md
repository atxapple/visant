# Changelog

All notable changes to Visant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Project Organization**: Reorganized repository structure
  - Moved test files to `tests/` directory
  - Moved debug scripts to `scripts/dev/`
  - Moved database utilities to `scripts/db/`
  - Archived outdated documentation to `archive/docs/`
  - Archived legacy scripts to `archive/scripts/`

### Fixed
- **Railway Deployment**: Fixed port binding to use Railway's dynamic PORT environment variable
- **Database Migrations**: Enhanced migrate.py with comprehensive error logging and dotenv support

---

## [0.2.3] - 2025-11-15

### Added
- **Password Reset Flow**: Dedicated forgot password page with email-based reset functionality
  - New `/ui/forgot-password` page with clean UI
  - Email-based password reset link generation
  - Complete reset flow with success feedback

### Fixed
- **Railway Deployment**: Fixed production deployment crash loop
  - Corrected database migration version references
  - Fixed server port binding for Railway environment
  - Enhanced migration script error logging

---

## [0.2.2] - 2025-11-13

### Added
- **Alert Definition Tracking**: Database-backed alert definitions with version history
  - Alert definition metadata stored in captures table
  - Modal popup displays definition version and details
  - Alert definition save endpoint for persistence

### Fixed
- Alert definition save endpoint now correctly stores definitions to database

---

## [0.2.1] - 2025-11-11

### Added
- **Real-time Capture Event Streaming**: WebSocket and SSE support for live updates
  - WebSocket endpoint at `/ws/captures/{device_id}` for bi-directional communication
  - SSE endpoint at `/v1/captures/stream/{device_id}` for server-sent events
  - Real-time UI updates in dashboard when new captures arrive
  - Automatic reconnection logic for dropped connections

- **Version Tracking Endpoint**: Monitor cloud and device versions
  - New GET `/v1/version` endpoint returns cloud version, device versions, environment
  - Version information displayed in UI footer
  - Server startup logs show version number

---

## [0.2.0] - 2025-11-10

### Added
- **Public Sharing System**: Complete time-limited share link functionality
  - Create shareable links with customizable expiration (1 hour to 30 days)
  - Public gallery view at `/public/share/{share_token}` (no authentication required)
  - QR code generation for easy mobile access
  - Share analytics tracking (view counts, last accessed)
  - Share management UI in dashboard
  - Copy-to-clipboard functionality for share URLs

### Changed
- Enhanced capture thumbnails with better optimization
- Improved browser caching with proper cache headers

---

## [0.1.0] - 2025-11-01

### Added
- **Multi-Tenant Architecture**: Complete organization and user isolation
  - Supabase authentication with JWT tokens
  - Organization workspaces with multi-user support
  - Row-level security through query-level isolation
  - Activation code system for device onboarding

- **Device Management**: Auto-registration and per-device configuration
  - Auto-generated API keys for device authentication
  - Smart device selector UI for multi-device support
  - Per-device configuration (JSON-based settings)
  - Device heartbeat tracking

- **Cloud AI Classification**: Background evaluation with consensus mode
  - OpenAI GPT-4o-mini integration
  - Google Gemini 2.5 Flash integration
  - Multi-AI consensus mode for higher accuracy
  - Asynchronous background processing

- **Performance Optimizations**:
  - Thumbnail generation for faster image loading
  - Composite database indexes for query optimization
  - Similarity detection to skip duplicate captures
  - Consecutive duplicate skip (dedupe)
  - Streak pruning for storage optimization

- **Notifications**:
  - SendGrid email integration for alert notifications
  - Global notification preferences UI
  - Alert cooldown/rate limiting to prevent spam

- **Database & Storage**:
  - PostgreSQL multi-tenant database (Railway managed)
  - Alembic migrations for schema versioning
  - Persistent volume storage at `/mnt/data`
  - S3-compatible storage interface (using local filesystem)

### Changed
- Migrated from SQLite to PostgreSQL for production scalability
- Replaced edge AI with cloud-based AI evaluation for better accuracy

---

## Legend

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

---

## Version Numbering

Visant follows [Semantic Versioning](https://semver.org/):

- **MAJOR version** (X.0.0): Incompatible API changes
- **MINOR version** (0.X.0): Backwards-compatible functionality additions
- **PATCH version** (0.0.X): Backwards-compatible bug fixes

**Current Status**: Version 0.x.x indicates pre-1.0 development phase where breaking changes may occur between minor versions.

**Graduation to v1.0.0** planned for Q1 2026 with:
- ✅ Multi-tenant architecture stable
- ✅ Core features complete
- ❌ Comprehensive test coverage (target: 80%+)
- ❌ API documentation finalized
- ❌ Device client auto-update mechanism
- ❌ Production monitoring and alerting
- ❌ Public beta with 10+ organizations

---

**See also**: [VERSIONING.md](VERSIONING.md) for detailed versioning guidelines and workflows.

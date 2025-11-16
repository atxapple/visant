# Archive - Historical Documentation

This directory contains outdated or superseded documentation from previous versions of Visant. These files are preserved for historical reference but are no longer maintained.

**For current documentation, see the main `/docs` directory.**

---

## Archived Documents

### Code Reviews

**CODE_REVIEW_SUMMARY_2025-11-12.md**
- **Archived:** 2025-11-16
- **Description:** Comprehensive code review of capture processing, classification, and performance optimizations
- **Reason for Archival:** Point-in-time review completed, recommendations implemented
- **Key Topics:** Image processing pipeline, AI evaluation flow, performance bottlenecks

**PRUNING_LOGIC_REVIEW.md**
- **Archived:** 2025-11-16
- **Description:** Technical review of datalake pruning logic and storage management
- **Reason for Archival:** Review completed, logic validated and implemented
- **Key Topics:** Disk space optimization, retention policies, safe deletion logic

---

## Current Documentation

For up-to-date documentation, refer to:

- **README.md** - Main project documentation with quick start and overview
- **docs/PROJECT_PLAN.md** - Living roadmap with feature status and priorities
- **docs/VERSIONING.md** - Versioning strategy and release workflow
- **docs/CHANGELOG.md** - Version history and release notes
- **docs/ARCHITECTURE.md** - System architecture and design decisions (if exists)
- **docs/API.md** - API endpoint documentation (if exists)

---

## Why These Files Were Archived

Documentation is archived when:
1. ✅ **Review Completed:** Point-in-time code reviews that have served their purpose
2. ✅ **Superseded:** Replaced by newer, more accurate documentation
3. ✅ **Historical Context:** No longer needed for day-to-day development but useful for reference
4. ✅ **Implementation Complete:** Planning documents for features that are now fully implemented

---

## Retrieving Archived Files

All archived files are tracked in git history. To view previous versions:

```bash
# View when a file was archived
git log --follow archive/docs/FILENAME.md

# View file contents from before archival
git log -p -- archive/docs/FILENAME.md

# Restore an archived file to the main docs (if needed)
git mv archive/docs/FILENAME.md docs/FILENAME.md
```

---

**Last Updated:** 2025-11-16
**Maintained By:** Visant Development Team

# Getting Started with Phase 1

## Quick Start for Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all Phase 1 dependencies including:
- SQLAlchemy (database ORM)
- Alembic (database migrations)
- psycopg2-binary (PostgreSQL driver)
- boto3 (S3 client)
- And others...

### 2. Initialize Database (Local Development)

For local development, we'll use SQLite (no PostgreSQL needed):

```bash
# Create initial migration from models
alembic revision --autogenerate -m "Initial multi-tenant schema"

# Apply migration to create tables
alembic upgrade head
```

This creates a local `visant_dev.db` SQLite database with all tables.

### 3. Test the Database

Create a test script to verify the database works:

```python
# test_database.py
from cloud.api.database import SessionLocal, Organization, User, Device

# Create a test organization
db = SessionLocal()

org = Organization(name="Test Org")
db.add(org)
db.commit()
db.refresh(org)

print(f"✅ Created organization: {org.name} (ID: {org.id})")

# Create a test user
user = User(email="test@example.com", org_id=org.id, role="admin")
db.add(user)
db.commit()

print(f"✅ Created user: {user.email}")

# Create a test device
device = Device(
    device_id="test-cam-01",
    org_id=org.id,
    friendly_name="Test Camera",
    api_key="test-api-key-123"
)
db.add(device)
db.commit()

print(f"✅ Created device: {device.friendly_name}")

db.close()
print("\n✅ Database test complete!")
```

Run it:
```bash
python test_database.py
```

### 4. Test Storage Abstraction

```python
# test_storage.py
from cloud.api.storage import FilesystemStorage, S3Storage
import os

# Test filesystem storage
fs = FilesystemStorage(base_path="./test_data")

# Upload a test file
test_data = b"Hello, Visant!"
key = fs.upload(test_data, "test/hello.txt", content_type="text/plain")
print(f"✅ Uploaded to filesystem: {key}")

# Download it back
downloaded = fs.download("test/hello.txt")
assert downloaded == test_data
print(f"✅ Downloaded from filesystem: {downloaded.decode()}")

# Check if exists
exists = fs.exists("test/hello.txt")
print(f"✅ File exists: {exists}")

print("\n✅ Storage test complete!")
```

Run it:
```bash
python test_storage.py
```

---

## Production Setup (Railway)

### 1. Add PostgreSQL Service

In Railway dashboard:
1. Click "New" → "Database" → "PostgreSQL"
2. Railway will automatically set `DATABASE_URL` environment variable
3. No manual configuration needed!

### 2. Set Up S3 Storage

**Option A: AWS S3**
```bash
# In Railway environment variables
S3_BUCKET=visant-captures
S3_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

**Option B: Railway S3** (if available)
```bash
S3_BUCKET=visant-captures
S3_ENDPOINT_URL=https://railway-s3-endpoint.com
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### 3. Run Migrations on Railway

Railway will automatically run migrations if you add a deploy script:

**Option 1: Add to `Procfile`** (create if doesn't exist):
```
release: alembic upgrade head
web: python -m cloud.api.main
```

**Option 2: Run manually via Railway CLI**:
```bash
railway run alembic upgrade head
```

### 4. Run Data Migration

After database is set up, migrate existing filesystem data:

```bash
# SSH into Railway container or run as one-time command
python scripts/migrate_to_multitenancy.py
```

This will:
- Create a default organization
- Scan existing captures in `/mnt/data/datalake`
- Upload images to S3
- Insert metadata into PostgreSQL
- Generate device API keys

---

## Configuration

### Database Configuration

Edit `config/cloud.json`:
```json
{
  "database": {
    "url_env": "DATABASE_URL",     // Environment variable name
    "pool_size": 20,                // Max connections in pool
    "max_overflow": 10              // Extra connections if pool full
  }
}
```

### Storage Configuration

```json
{
  "storage": {
    "backend": "filesystem",        // or "s3"
    "filesystem": {
      "datalake_root": "/mnt/data/datalake"
    },
    "s3": {
      "bucket_env": "S3_BUCKET",
      "region_env": "S3_REGION",
      "endpoint_url_env": "S3_ENDPOINT_URL",
      "access_key_env": "AWS_ACCESS_KEY_ID",
      "secret_key_env": "AWS_SECRET_ACCESS_KEY"
    }
  }
}
```

To switch from filesystem to S3:
1. Change `"backend": "filesystem"` to `"backend": "s3"`
2. Set S3 environment variables
3. Restart server

---

## Common Commands

### Alembic (Database Migrations)

```bash
# Create new migration (auto-detect model changes)
alembic revision --autogenerate -m "Description"

# Create empty migration (manual)
alembic revision -m "Description"

# Apply all pending migrations
alembic upgrade head

# Upgrade by one version
alembic upgrade +1

# Downgrade by one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history --verbose
```

### Data Migration

```bash
# Dry run (test without writing)
python scripts/migrate_to_multitenancy.py --dry-run

# Run migration with filesystem storage (local testing)
python scripts/migrate_to_multitenancy.py --storage filesystem

# Run migration with S3 storage (production)
python scripts/migrate_to_multitenancy.py --storage s3
```

---

## Environment Variables Reference

### Required for Production

```bash
# Database (auto-set by Railway PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Storage (S3)
S3_BUCKET=visant-captures
S3_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Existing (keep these)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SENDGRID_API_KEY=...    # Optional
ALERT_FROM_EMAIL=...    # Optional
```

### Optional

```bash
# For Railway S3 or MinIO
S3_ENDPOINT_URL=https://...

# For development (SQLite used if not set)
# DATABASE_URL=sqlite:///./visant_dev.db
```

---

## Troubleshooting

### "No module named 'alembic'"

```bash
pip install -r requirements.txt
```

### "Can't connect to PostgreSQL"

Check `DATABASE_URL` is set:
```bash
echo $DATABASE_URL  # Linux/Mac
echo %DATABASE_URL%  # Windows
```

### "S3 bucket not found"

Check S3 environment variables:
```bash
echo $S3_BUCKET
echo $AWS_ACCESS_KEY_ID
```

### "Migration script can't find datalake"

Update source path in `scripts/migrate_to_multitenancy.py`:
```python
self.source_datalake = Path("/your/path/to/datalake")
```

---

## Next Steps

After completing Phase 1 setup:

1. **Test locally** - Verify database and storage work
2. **Deploy to Railway** - Set up PostgreSQL + S3
3. **Run migration** - Move existing data
4. **Begin Phase 2** - Authentication & multi-tenancy

See `PHASE1_COMPLETE.md` for detailed Phase 1 summary.
See `PROJECT_PLAN.md` for full roadmap.

---

## Support

- GitHub Issues: https://github.com/your-repo/visant/issues
- Documentation: See `docs/` directory
- Project Plan: `PROJECT_PLAN.md`

---

**Last Updated**: 2025-01-06
**Phase**: 1 (Foundation & Database)
**Status**: Complete ✅

# Visant

AI-powered visual monitoring platform with cloud-based anomaly detection. Multi-tenant SaaS for deploying camera devices that continuously monitor environments and send real-time alerts when anomalies are detected.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# 3. Run database migrations
alembic upgrade head

# 4. Start the server
python server.py
```

Server will be available at `http://localhost:8000`

## Technology Stack

### Backend
- **FastAPI 0.100+** - Modern async web framework
- **PostgreSQL 15+** - Primary database with SQLAlchemy 2.0+ ORM
- **Alembic 1.13+** - Database migration management
- **Supabase Auth** - JWT-based authentication

### AI/ML
- **OpenAI API** - GPT-4o-mini for image classification
- **Google Gemini API** - Gemini 2.5 Flash as secondary classifier
- **Dual-Agent Consensus** - Custom voting system combining both models
- **OpenCV + Pillow** - Image processing and thumbnail generation

### Infrastructure
- **Railway.app** - Cloud deployment platform
- **SendGrid** - Transactional email service for alerts
- **Persistent Volume** - `/mnt/data` for file storage

### Frontend
- **Jinja2 Templates** - Server-side HTML rendering
- **Vanilla JavaScript** - No framework dependencies (Vue.js planned)
- **WebSocket/SSE** - Real-time updates for captures and commands

## Project Structure

```
visant/
├── server.py                    # Main FastAPI application entry point
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Database migration configuration
├── version.py                   # Version tracking
│
├── cloud/                       # Main application code
│   ├── ai/                      # AI classifier implementations
│   │   ├── openai_client.py    # OpenAI GPT-4o-mini classifier
│   │   ├── gemini_client.py    # Google Gemini classifier
│   │   ├── consensus.py        # Dual-agent voting logic
│   │   └── simple_threshold.py # Fallback classifier
│   │
│   ├── api/                     # Backend API
│   │   ├── routes/              # REST API endpoints
│   │   │   ├── auth.py         # Authentication (signup, login)
│   │   │   ├── devices.py      # Device management
│   │   │   ├── captures.py     # Image upload/retrieval
│   │   │   ├── device_commands.py  # SSE command streaming
│   │   │   └── admin_codes.py  # Activation code management
│   │   │
│   │   ├── workers/             # Background services
│   │   │   ├── command_hub.py  # SSE device communication hub
│   │   │   ├── trigger_scheduler.py  # Automated capture scheduling
│   │   │   ├── ai_evaluator.py # Async AI classification worker
│   │   │   └── capture_hub.py  # Real-time capture event streaming
│   │   │
│   │   ├── database/            # Database models and session
│   │   │   ├── models.py       # SQLAlchemy ORM models
│   │   │   └── session.py      # Database connection
│   │   │
│   │   ├── auth/                # Authentication middleware
│   │   ├── storage/             # File storage abstraction
│   │   └── utils/               # Utilities (QR codes, etc.)
│   │
│   ├── web/                     # Web dashboard
│   │   ├── routes.py            # HTML page routes
│   │   ├── templates/           # Jinja2 HTML templates (11 pages)
│   │   └── static/              # CSS, JS, images
│   │
│   └── datalake/                # File storage operations
│
├── alembic/                     # Database migrations
│   └── versions/                # Migration files (7 migrations)
│
├── deployment/                  # Deployment guides
│   ├── cloud/                   # Railway deployment
│   └── device/                  # Raspberry Pi setup
│
├── docs/                        # Current documentation
│   ├── PROJECT_PLAN.md         # Comprehensive roadmap (1021 lines)
│   └── PRODUCT_DESCRIPTION.md  # Full product docs (1295 lines)
│
└── archive/                     # Historical code and docs
```

## Key Architecture Concepts

### Multi-Tenant Design

Every query is filtered by `org_id` to ensure complete organization isolation:

```python
# Example: Get devices for an organization
devices = session.query(Device).filter(
    Device.org_id == current_user.org_id
).all()
```

### Dual-Agent AI Consensus

Two AI models evaluate each capture independently, then reconcile:

1. **OpenAI GPT-4o-mini** - Primary classifier
2. **Google Gemini 2.5 Flash** - Secondary classifier
3. **Consensus Logic** - If they disagree → "uncertain", if they agree → use that classification

### Cloud-Triggered Devices

Devices connect via SSE (Server-Sent Events) to receive real-time commands:

```
Device → GET /v1/devices/{id}/commands (SSE stream)
        ← Server sends: {"command": "capture", "params": {...}}
Device executes command and uploads result
```

### Background AI Evaluation

Non-blocking upload flow:

1. Device uploads image → Immediate 200 OK response
2. Server saves image with `evaluation_status="pending"`
3. BackgroundTask queues AI evaluation
4. AI evaluation runs asynchronously (3-5 seconds)
5. Results saved to database with state (normal/abnormal/uncertain)

### Database Schema Overview

```
organizations (tenant root)
  ├─ users (Supabase Auth integration)
  ├─ devices (camera hardware)
  │   └─ captures (images + AI evaluation results)
  ├─ activation_codes (promotional system)
  ├─ share_links (public sharing)
  └─ scheduled_triggers (cloud-managed scheduling)
```

## Environment Variables

Required environment variables (create `.env` file):

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret

# AI Services
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Email (optional - for alerts)
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# Storage
STORAGE_PATH=/mnt/data  # Or local path for development
```

## Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- Git

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd visant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up local database
createdb visant_dev

# Configure environment
cp .env.example .env
# Edit .env with local database URL and API keys

# Run migrations
alembic upgrade head

# Start development server
python server.py
```

Server runs on `http://localhost:8000` with auto-reload enabled.

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Accessing the API

- **API Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Web Dashboard**: http://localhost:8000/

## Common Development Tasks

### Adding a New API Endpoint

1. Create or edit a route file in `cloud/api/routes/`
2. Define Pydantic request/response models
3. Add authentication decorator if needed
4. Include router in `server.py`

Example:
```python
from fastapi import APIRouter, Depends
from cloud.api.auth.middleware import get_current_user

router = APIRouter(prefix="/v1/myfeature", tags=["myfeature"])

@router.get("/")
async def list_items(current_user = Depends(get_current_user)):
    # Ensure org isolation
    items = session.query(Item).filter(
        Item.org_id == current_user.org_id
    ).all()
    return items
```

### Adding a Database Model

1. Add model class in `cloud/api/database/models.py`
2. Create migration: `alembic revision --autogenerate -m "add model name"`
3. Review generated migration in `alembic/versions/`
4. Apply: `alembic upgrade head`

### Adding an AI Classifier

1. Create new classifier in `cloud/ai/`
2. Implement `ClassifierInterface` protocol
3. Add to consensus system in `cloud/ai/consensus.py`
4. Update configuration to include new model

### Creating a Web Page

1. Add route in `cloud/web/routes.py`
2. Create template in `cloud/web/templates/`
3. Use base template for consistent layout
4. Add authentication check if needed

### Background Workers

Background services run in separate threads:

- **CommandHub** - Manages SSE connections for device commands
- **TriggerScheduler** - Executes scheduled captures
- **CaptureHub** - Streams real-time capture events to dashboard

Managed in `server.py` startup event.

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cloud --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

**Note**: Test suite needs to be re-established. Previous tests are in `archive/tests/`.

### Writing Tests

Example test structure:
```python
import pytest
from fastapi.testclient import TestClient
from server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_signup(client):
    response = client.post("/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    })
    assert response.status_code == 200
```

## Deployment

### Cloud Deployment (Railway)

Production deployment is on Railway.app. See `deployment/cloud/README.md` for detailed instructions.

**Quick deploy:**
```bash
# Railway CLI
railway login
railway link
railway up
```

Environment variables are configured in Railway dashboard.

### Device Deployment (Raspberry Pi)

See `deployment/device/README.md` for full Raspberry Pi setup instructions.

**Quick setup:**
1. Flash Raspberry Pi OS
2. Clone device client code
3. Configure systemd service for auto-start
4. Set up WiFi (comitup or manual)
5. Activate device with activation code

## API Documentation

### Authentication

All API endpoints (except auth routes) require JWT token in Authorization header:

```bash
Authorization: Bearer <jwt_token>
```

Get token from:
- `POST /v1/auth/signup` - Create account
- `POST /v1/auth/login` - Login existing user

### Key Endpoints

#### Devices
- `GET /v1/devices` - List organization's devices
- `POST /v1/devices/activate` - Activate device with code
- `PUT /v1/devices/{device_id}` - Update device config
- `GET /v1/devices/{device_id}/commands` - SSE command stream (device client)

#### Captures
- `POST /v1/captures` - Upload image (multipart/form-data)
- `GET /v1/captures` - List captures with filters
- `GET /v1/captures/{record_id}` - Get single capture
- `GET /v1/captures/{record_id}/thumbnail` - Get optimized thumbnail

#### Admin
- `GET /v1/admin/codes` - List activation codes
- `POST /v1/admin/codes` - Create activation code
- `GET /v1/admin/devices` - List all devices (admin only)

Full API documentation: http://localhost:8000/docs

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql $DATABASE_URL

# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### Migration Conflicts

```bash
# If migrations are out of sync
alembic stamp head  # Mark current state
alembic revision --autogenerate -m "sync migrations"
```

### AI Evaluation Not Working

Check logs for API key errors:
```bash
# Verify API keys are set
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY

# Check logs for detailed errors
# Look for "evaluation_status: failed" in captures
```

### Device Not Receiving Commands

1. Check device is activated: `SELECT * FROM devices WHERE device_id='...'`
2. Verify SSE connection in device logs
3. Check CommandHub is running in server logs
4. Test with manual command: Use dashboard "Test Command" button

### Image Upload Fails

1. Check storage path exists: `ls -la /mnt/data` (or configured path)
2. Verify write permissions
3. Check disk space: `df -h`
4. Review file size limits in nginx/proxy config

## Performance Optimization

### Database Indexes

Key indexes for performance:
```sql
-- Composite index for common query pattern
CREATE INDEX idx_captures_org_device_captured
ON captures(org_id, device_id, captured_at);
```

### Image Optimization

- Thumbnails generated at 400x300, 85% quality
- ~70% size reduction
- Browser caching enabled (1-year TTL)
- Reduces load time from 20-30s to <3s

### Caching Strategy

Current: Browser caching only
Planned: Redis for API response caching

## Known Issues & Limitations

### Current Limitations

1. **No test coverage** - Tests need to be re-established
2. **Filesystem storage** - Not yet migrated to S3
3. **Single-region deployment** - No CDN for images
4. **Legacy routes** - `/legacy/*` routes still mounted

### Incomplete Features

- Public sharing UI exists but not fully wired
- Manual trigger button missing in multi-tenant UI
- Notification configuration page not implemented
- Normal description management UI incomplete

See `docs/PROJECT_PLAN.md` for detailed roadmap.

## Git Workflow

### Branch Strategy

- `main` - Production-ready code
- `feature/*` - New features (e.g., `feature/camera-rename`)
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Commit Message Format

```
<type>: <subject>

<optional body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Contributing

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to public functions
- Keep functions focused and small

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with clear commits
3. Update documentation if needed
4. Test locally
5. Create PR with description of changes
6. Wait for review and CI checks

## Resources

### Documentation
- **Project Plan**: `docs/PROJECT_PLAN.md` - Comprehensive roadmap
- **Product Description**: `docs/PRODUCT_DESCRIPTION.md` - Full architecture and API docs
- **Deployment Guides**: `deployment/` - Cloud and device setup

### External Services
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Supabase Documentation](https://supabase.com/docs)
- [Railway Documentation](https://docs.railway.app/)

### Support
- GitHub Issues: Report bugs and feature requests
- Project Wiki: Additional guides and FAQs

## License

[Add license information here]

## Version History

Current version: `2.0` (Multi-tenant SaaS)

See `version.py` for version tracking and `git log` for detailed history.

---

**Last Updated**: 2025-11-12
**Maintainers**: [Add maintainer info]

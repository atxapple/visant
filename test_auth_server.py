"""
Minimal FastAPI server to test Phase 2 authentication.

Run with:
    uvicorn test_auth_server:app --reload

Then test endpoints at: http://localhost:8000/docs
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our auth routes
from cloud.api.routes.auth import router as auth_router
from cloud.api.routes.devices import router as devices_router
from cloud.api.routes.shares import router as shares_router
from cloud.api.routes.public import router as public_router
from cloud.api.routes.captures import router as captures_router

# Initialize InferenceService for Cloud AI
from cloud.api.service import InferenceService
from cloud.datalake.storage import FileSystemDatalake
from cloud.api.capture_index import RecentCaptureIndex
from cloud.ai import SimpleThresholdModel

# Create global InferenceService instance for testing
datalake = FileSystemDatalake(root=Path("./test_datalake"))
capture_index = RecentCaptureIndex(root=datalake.root)
classifier = SimpleThresholdModel()

global_inference_service = InferenceService(
    classifier=classifier,
    datalake=datalake,
    capture_index=capture_index,
    notifier=None,  # No notifications in test
    dedupe_enabled=False,
    similarity_enabled=False,
    streak_pruning_enabled=False
)

# Make it accessible to routes
import cloud.api.routes.captures as captures_module
captures_module.global_inference_service = global_inference_service

# Create FastAPI app
app = FastAPI(
    title="Visant Authentication API (Phase 4 Test)",
    description="Testing authentication, device provisioning, and capture upload",
    version="0.2.0"
)

# Add CORS middleware (for web dashboard later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(shares_router)
app.include_router(public_router)  # Public routes (no auth required)
app.include_router(captures_router)  # Capture upload (device auth)


@app.get("/")
def root():
    """Root endpoint - API info."""
    return {
        "name": "Visant API",
        "version": "0.2.0",
        "phase": "4 - Capture Upload",
        "status": "testing",
        "docs": "/docs",
        "endpoints": {
            "auth": {
                "signup": "POST /v1/auth/signup",
                "login": "POST /v1/auth/login",
                "me": "GET /v1/auth/me (requires auth)",
            },
            "devices": {
                "register": "POST /v1/devices (requires auth)",
                "list": "GET /v1/devices (requires auth)",
                "get": "GET /v1/devices/{device_id} (requires auth)",
            },
            "captures": {
                "upload": "POST /v1/captures (requires device API key)",
                "list": "GET /v1/captures (requires device API key)",
                "get": "GET /v1/captures/{record_id} (requires device API key)",
                "delete": "DELETE /v1/captures/{record_id} (requires device API key)",
                "upload_image": "POST /v1/captures/{record_id}/image (requires device API key)"
            },
            "shares": {
                "create": "POST /v1/devices/{device_id}/share (requires auth)",
                "list": "GET /v1/share-links (requires auth)",
            },
            "public": {
                "gallery_html": "GET /s/{token} (no auth)",
                "gallery_api": "GET /api/s/{token} (no auth)",
            }
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

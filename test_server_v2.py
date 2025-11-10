#!/usr/bin/env python3
"""
Test server for Cloud-Triggered Camera System v2.0

This script starts the cloud API server with:
- CommandHub for device command streaming
- TriggerScheduler for automated captures
- Device command routes (SSE streams)
"""

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("=" * 70)
    print("Starting Visant Cloud Server v2.0 (Cloud-Triggered Architecture)")
    print("=" * 70)
    print("\nFeatures enabled:")
    print("  - Web UI: Login, Dashboard, Device Management")
    print("  - CommandHub: Real-time device command streaming (SSE)")
    print("  - TriggerScheduler: Automated scheduled captures")
    print("\nWeb Interface:")
    print("  • http://localhost:8000/signup             (Create account)")
    print("  • http://localhost:8000/login              (Login)")
    print("  • http://localhost:8000/ui                 (Dashboard)")
    print("\nDevice Commands API:")
    print("  • GET  /v1/devices/{device_id}/commands    (SSE stream)")
    print("  • POST /v1/devices/{device_id}/trigger     (manual trigger)")
    print("  • GET  /v1/devices/connected               (connected devices)")
    print("\nStarting server...")
    print("-" * 70)

    # Create FastAPI app with multi-tenant architecture
    from cloud.api.database import Base, engine
    from cloud.api.server import create_app
    from cloud.api.routes import auth, devices, captures, device_commands, admin_codes
    from cloud.web import routes as web_routes
    from cloud.api.service import InferenceService
    from cloud.ai import SimpleThresholdModel
    from cloud.datalake.storage import FileSystemDatalake
    from cloud.api.capture_index import RecentCaptureIndex
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    # Initialize InferenceService for captures endpoint
    datalake = FileSystemDatalake(root=Path("uploads"))
    capture_index = RecentCaptureIndex(root=Path("uploads"))
    classifier = SimpleThresholdModel()
    inference_service = InferenceService(
        classifier=classifier,
        datalake=datalake,
        capture_index=capture_index,
        notifier=None,
        dedupe_enabled=False,
        similarity_enabled=False,
        streak_pruning_enabled=False
    )

    # Set global inference service for captures route
    import cloud.api.routes.captures as captures_module
    captures_module.global_inference_service = inference_service

    # Create main app
    main_app = FastAPI(title="Visant Cloud API v2.0", version="2.0.0")

    # Mount static files for web UI
    static_path = Path(__file__).parent / "cloud" / "web" / "static"
    main_app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Include multi-tenant routes
    main_app.include_router(auth.router)
    main_app.include_router(devices.router)
    main_app.include_router(captures.router)
    main_app.include_router(device_commands.router)  # NEW: Cloud-triggered commands
    main_app.include_router(admin_codes.router)  # Admin: Activation code management
    main_app.include_router(web_routes.router)  # Web UI routes (login, signup, dashboard)

    # Create old single-tenant app for compatibility (mounted at /legacy)
    legacy_app = create_app()

    # Get the TriggerScheduler from legacy_app to start it
    @main_app.on_event("startup")
    async def startup_trigger_scheduler():
        """Start the TriggerScheduler on main app startup."""
        trigger_scheduler = legacy_app.state.trigger_scheduler
        await trigger_scheduler.start()
        print("[startup] TriggerScheduler started successfully")

    @main_app.on_event("shutdown")
    async def shutdown_trigger_scheduler():
        """Stop the TriggerScheduler on shutdown."""
        trigger_scheduler = legacy_app.state.trigger_scheduler
        await trigger_scheduler.stop()
        print("[shutdown] TriggerScheduler stopped")

    # Mount legacy app
    main_app.mount("/legacy", legacy_app)

    @main_app.get("/health")
    def health():
        return {"status": "ok", "version": "2.0.0"}

    @main_app.get("/")
    def root():
        return {
            "service": "Visant Cloud API",
            "version": "2.0.0",
            "architecture": "cloud-triggered",
            "features": {
                "web_ui": "enabled",
                "command_hub": "enabled",
                "trigger_scheduler": "enabled",
                "multi_tenant": "enabled"
            },
            "web_interface": {
                "signup": "/signup",
                "login": "/login",
                "dashboard": "/ui",
                "devices": "/ui/devices",
                "settings": "/ui/settings"
            },
            "api_endpoints": {
                "auth": "/v1/auth/*",
                "devices": "/v1/devices/*",
                "captures": "/v1/captures/*",
                "device_commands": "/v1/devices/{device_id}/commands (SSE)",
                "legacy": "/legacy/*"
            }
        }

    # Start server
    uvicorn.run(
        main_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

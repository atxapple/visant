#!/usr/bin/env python3
"""
Visant Cloud Server - Production Entry Point

Multi-tenant SaaS platform for AI-powered visual monitoring.

This server provides:
- Multi-tenant API with organization/user isolation
- CommandHub for real-time device command streaming (SSE)
- TriggerScheduler for automated scheduled captures
- Background AI evaluation pipeline
- Web UI for dashboard and device management
- Legacy single-tenant server mounted at /legacy/*
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
# This file is at the project root
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

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
    from cloud.api.routes import auth, devices, captures, device_commands, admin_codes, capture_events, version, admin
    from cloud.web import routes as web_routes
    from cloud.api.service import InferenceService
    from cloud.api.config_loader import load_config
    from cloud.ai import (
        SimpleThresholdModel,
        OpenAIImageClassifier,
        GeminiImageClassifier,
        ConsensusClassifier,
    )
    from cloud.datalake.storage import FileSystemDatalake
    from cloud.api.capture_index import RecentCaptureIndex
    from cloud.api.workers.capture_hub import CaptureHub
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    import os

    # Load configuration from config/cloud.json
    # Use absolute path relative to project root to ensure it works on Railway
    config_path = project_root / "config" / "cloud.json"

    print(f"[config] Looking for config at: {config_path}")
    print(f"[config] Config exists: {config_path.exists()}")
    print(f"[config] Current working directory: {Path.cwd()}")

    try:
        cfg = load_config(config_path if config_path.exists() else None)
        if config_path.exists():
            print(f"[config] [OK] Loaded configuration from {config_path}")
            # Debug: Show what was actually loaded
            print(f"[config] similarity.enabled = {cfg.features.similarity.enabled}")
            print(f"[config] similarity.threshold = {cfg.features.similarity.threshold}")
            print(f"[config] similarity.expiry_minutes = {cfg.features.similarity.expiry_minutes}")
            print(f"[config] similarity.cache_path = {cfg.features.similarity.cache_path}")
        else:
            print(f"[config] ⚠ Config file not found, using defaults")
    except (TypeError, ValueError) as e:
        # Config file has incompatible format, use defaults with manual classifier config
        print(f"WARNING: Could not load config from {config_path}: {e}")
        print("Using default config...")
        cfg = load_config(None)
    except Exception as e:
        # Catch any other exceptions to see what's happening
        print(f"ERROR: Unexpected exception loading config: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("Using default config...")
        cfg = load_config(None)

    # Build classifier based on config (consensus = OpenAI + Gemini)
    def build_classifier(kind: str, role: str, normal_description: str = ""):
        if kind == "simple":
            return SimpleThresholdModel()
        if kind == "openai":
            # Try to get API key from config env var name, fallback to standard name
            api_key_env = getattr(cfg.classifier.openai, 'api_key_env', 'OPENAI_API_KEY')
            key = os.environ.get(api_key_env)
            if not key:
                print(f"WARNING: {api_key_env} not set, using SimpleThresholdModel")
                return SimpleThresholdModel()
            print(f"[OK] OpenAI API key found, initializing GPT-4o-mini classifier")
            return OpenAIImageClassifier(
                api_key=key,
                model=getattr(cfg.classifier.openai, 'model', 'gpt-4o-mini'),
                base_url=getattr(cfg.classifier.openai, 'base_url', 'https://api.openai.com/v1'),
                normal_description=normal_description,
                timeout=getattr(cfg.classifier.openai, 'timeout', 30.0),
            )
        if kind == "gemini":
            # Try to get API key from config env var name, fallback to standard name
            api_key_env = getattr(cfg.classifier.gemini, 'api_key_env', 'GEMINI_API_KEY')
            key = os.environ.get(api_key_env)
            if not key:
                print(f"WARNING: {api_key_env} not set, using SimpleThresholdModel")
                return SimpleThresholdModel()
            print(f"[OK] Gemini API key found, initializing Gemini 2.0 Flash classifier")
            return GeminiImageClassifier(
                api_key=key,
                model=getattr(cfg.classifier.gemini, 'model', 'models/gemini-2.0-flash-exp'),
                base_url=getattr(cfg.classifier.gemini, 'base_url', 'https://generativelanguage.googleapis.com/v1beta'),
                timeout=getattr(cfg.classifier.gemini, 'timeout', 30.0),
                normal_description=normal_description,
            )
        print(f"WARNING: Unsupported classifier '{kind}', using SimpleThresholdModel")
        return SimpleThresholdModel()

    # Force consensus mode (OpenAI + Gemini) - hardcoded to ensure AI evaluation works
    # If API keys are missing, build_classifier will fall back to SimpleThresholdModel
    primary_kind = "openai"
    secondary_kind = "gemini"

    # Build classifiers
    primary_classifier = build_classifier(primary_kind, "primary")
    secondary_classifier = build_classifier(secondary_kind, "secondary") if secondary_kind else None

    # Create consensus classifier if we have both
    if secondary_classifier:
        classifier = ConsensusClassifier(
            primary=primary_classifier,
            secondary=secondary_classifier,
            primary_label="OpenAI",
            secondary_label="Gemini",
        )
        print(f"Initialized ConsensusClassifier (OpenAI + Gemini)")
    else:
        classifier = primary_classifier
        print(f"Initialized {classifier.__class__.__name__}")

    # Initialize InferenceService for captures endpoint
    from cloud.api.storage.config import UPLOADS_DIR
    from cloud.api.similarity_cache import SimilarityCache

    datalake = FileSystemDatalake(root=UPLOADS_DIR)
    capture_index = RecentCaptureIndex(root=UPLOADS_DIR)

    # Initialize similarity cache if enabled
    similarity_cache = None
    if cfg.features.similarity.enabled and cfg.features.similarity.cache_path:
        similarity_cache = SimilarityCache(Path(cfg.features.similarity.cache_path))
        print(f"[OK] Similarity cache initialized: threshold={cfg.features.similarity.threshold} bits, expiry={cfg.features.similarity.expiry_minutes} min")
    else:
        print(f"[WARN] Similarity cache NOT initialized: enabled={cfg.features.similarity.enabled}, cache_path={cfg.features.similarity.cache_path}")

    # Debug: Show exact values being passed to InferenceService
    print(f"[service] Initializing InferenceService with:")
    print(f"[service]   similarity_enabled={cfg.features.similarity.enabled}")
    print(f"[service]   similarity_threshold={cfg.features.similarity.threshold}")
    print(f"[service]   similarity_expiry_minutes={cfg.features.similarity.expiry_minutes}")
    print(f"[service]   similarity_cache={'initialized' if similarity_cache else 'None'}")

    inference_service = InferenceService(
        classifier=classifier,
        datalake=datalake,
        capture_index=capture_index,
        notifier=None,
        dedupe_enabled=cfg.features.dedupe.enabled,
        dedupe_threshold=cfg.features.dedupe.threshold,
        dedupe_keep_every=cfg.features.dedupe.keep_every,
        similarity_enabled=cfg.features.similarity.enabled,
        similarity_threshold=cfg.features.similarity.threshold,
        similarity_expiry_minutes=cfg.features.similarity.expiry_minutes,
        similarity_cache=similarity_cache,
        streak_pruning_enabled=cfg.features.streak_pruning.enabled,
        streak_threshold=cfg.features.streak_pruning.threshold,
        streak_keep_every=cfg.features.streak_pruning.keep_every
    )

    # Debug: Verify what the service actually has
    print(f"[service] InferenceService initialized. Verifying:")
    print(f"[service]   service.similarity_enabled={inference_service.similarity_enabled}")
    print(f"[service]   service.similarity_threshold={inference_service.similarity_threshold}")
    print(f"[service]   service.similarity_expiry_minutes={inference_service.similarity_expiry_minutes}")
    print(f"[service]   service.similarity_cache={'present' if inference_service.similarity_cache else 'None'}")

    # Set global inference service for captures route
    import cloud.api.routes.captures as captures_module
    captures_module.global_inference_service = inference_service

    # Initialize CaptureHub for real-time event streaming
    _capture_hub = CaptureHub()

    # Register CaptureHub for global access
    from cloud.api.server import set_capture_hub
    set_capture_hub(_capture_hub)

    # Create main app
    main_app = FastAPI(title="Visant Cloud API v2.0", version="2.0.0")

    # Store inference service in app state for admin endpoint access
    main_app.state.service = inference_service

    # Set global app reference for admin routes
    from cloud.api.server import set_current_app
    set_current_app(main_app)

    # Mount static files for web UI
    static_path = project_root / "cloud" / "web" / "static"
    main_app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Include multi-tenant routes
    main_app.include_router(auth.router)
    main_app.include_router(devices.router)
    main_app.include_router(captures.router)
    main_app.include_router(device_commands.router)  # Cloud-triggered device commands (SSE)
    main_app.include_router(capture_events.router)  # Real-time capture events (SSE/WebSocket)
    main_app.include_router(admin_codes.router)  # Admin: Activation code management
    main_app.include_router(admin.router)  # Admin: System management (users, devices, captures)
    main_app.include_router(version.router)  # Version tracking
    main_app.include_router(web_routes.router)  # Web UI routes (login, signup, dashboard)

    # Create old single-tenant app for compatibility (mounted at /legacy)
    legacy_app = create_app()

    # Get the TriggerScheduler from legacy_app to start it
    @main_app.on_event("startup")
    async def startup_trigger_scheduler():
        """Start the TriggerScheduler on main app startup."""
        # Initialize alert definitions cache
        from cloud.api.database import SessionLocal, AlertDefinition
        db = SessionLocal()
        try:
            # Load all active alert definitions into cache
            active_definitions = db.query(AlertDefinition).filter(
                AlertDefinition.is_active == True
            ).all()

            device_definitions = {}
            for definition in active_definitions:
                device_definitions[definition.device_id] = (definition.id, definition.description)

            legacy_app.state.device_definitions = device_definitions
            print(f"[startup] Loaded {len(device_definitions)} alert definitions into cache")
        except Exception as e:
            print(f"[startup] Error loading alert definitions: {e}")
        finally:
            db.close()

        trigger_scheduler = legacy_app.state.trigger_scheduler
        await trigger_scheduler.start()
        print("[startup] TriggerScheduler started successfully")

        # Start background task for similarity cache flushing
        if similarity_cache is not None:
            import asyncio

            async def flush_similarity_cache_periodically():
                """Periodically flush similarity cache to disk."""
                while True:
                    try:
                        await asyncio.sleep(10)  # Flush every 10 seconds
                        if similarity_cache._dirty:
                            similarity_cache.flush()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"[similarity_cache] Error during periodic flush: {e}")

            asyncio.create_task(flush_similarity_cache_periodically())
            print("[startup] Similarity cache background flush task started")

    @main_app.on_event("shutdown")
    async def shutdown_trigger_scheduler():
        """Stop the TriggerScheduler on shutdown."""
        trigger_scheduler = legacy_app.state.trigger_scheduler
        await trigger_scheduler.stop()
        print("[shutdown] TriggerScheduler stopped")

        # Flush similarity cache on shutdown
        if similarity_cache is not None and similarity_cache._dirty:
            try:
                similarity_cache.flush()
                print("[shutdown] Similarity cache flushed to disk")
            except Exception as e:
                print(f"[shutdown] Error flushing similarity cache: {e}")

    # Mount legacy app
    main_app.mount("/legacy", legacy_app)

    @main_app.get("/health")
    def health():
        return {"status": "ok", "version": "2.0.0"}

    @main_app.get("/debug/similarity")
    def debug_similarity():
        """Debug endpoint to check similarity configuration."""
        import os
        service = getattr(main_app.state, 'service', None)

        # Check config file
        config_file_path = project_root / "config" / "cloud.json"
        config_info = {
            "config_path": str(config_file_path),
            "config_exists": config_file_path.exists(),
            "project_root": str(project_root),
            "cwd": str(Path.cwd()),
        }

        # Try to read config file if it exists
        if config_file_path.exists():
            try:
                with open(config_file_path) as f:
                    import json
                    config_data = json.load(f)
                    config_info["config_similarity"] = config_data.get("features", {}).get("similarity", {})
            except Exception as e:
                config_info["config_read_error"] = str(e)

        if service is None:
            return {
                **config_info,
                "error": "No service found in main_app.state",
                "state_keys": list(vars(main_app.state).keys()) if hasattr(main_app, 'state') else []
            }

        return {
            **config_info,
            "service_exists": True,
            "similarity_enabled": getattr(service, 'similarity_enabled', None),
            "similarity_threshold": getattr(service, 'similarity_threshold', None),
            "similarity_expiry_minutes": getattr(service, 'similarity_expiry_minutes', None),
            "similarity_cache_exists": service.similarity_cache is not None if hasattr(service, 'similarity_cache') else False,
            "cache_hits": getattr(service, 'similarity_cache_hits', None),
            "cache_misses": getattr(service, 'similarity_cache_misses', None),
        }

    @main_app.get("/debug/storage")
    def debug_storage():
        """Debug endpoint to check storage configuration and file counts."""
        import os
        from pathlib import Path

        # Show uploads directory configuration
        is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME")

        result = {
            "uploads_dir": str(UPLOADS_DIR),
            "is_railway": bool(is_railway),
            "railway_env": os.getenv("RAILWAY_ENVIRONMENT"),
            "exists": UPLOADS_DIR.exists(),
            "is_directory": UPLOADS_DIR.is_dir() if UPLOADS_DIR.exists() else False,
        }

        # Count files if directory exists
        if UPLOADS_DIR.exists() and UPLOADS_DIR.is_dir():
            try:
                # Count total files recursively
                all_files = list(UPLOADS_DIR.rglob("*"))
                image_files = list(UPLOADS_DIR.rglob("*.jpg")) + list(UPLOADS_DIR.rglob("*.jpeg")) + list(UPLOADS_DIR.rglob("*.png"))

                result["total_items"] = len(all_files)
                result["image_files"] = len(image_files)
                result["sample_paths"] = [str(p.relative_to(UPLOADS_DIR)) for p in image_files[:5]]
            except Exception as e:
                result["error"] = str(e)

        return result

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

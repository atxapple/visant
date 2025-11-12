"""Storage configuration - handles Railway volumes and local development."""

import os
from pathlib import Path


def get_uploads_dir() -> Path:
    """
    Get the uploads directory path.

    - On Railway: Uses /mnt/data (persistent volume)
    - Locally: Uses ./uploads (local development)

    Returns:
        Path to uploads directory
    """
    # Check if running on Railway (Railway sets RAILWAY_ENVIRONMENT or RAILWAY_ENVIRONMENT_NAME)
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME")

    if is_railway:
        # Use Railway volume mount point
        uploads_path = Path("/mnt/data")
    else:
        # Use local uploads directory for development
        uploads_path = Path("uploads")

    # Ensure directory exists
    uploads_path.mkdir(parents=True, exist_ok=True)

    return uploads_path


# Singleton instance
UPLOADS_DIR = get_uploads_dir()

"""Image serving from Railway volume storage."""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import logging

from cloud.api.storage.config import UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Images"])


@router.get("/images/{file_path:path}")
async def serve_image(file_path: str):
    """
    Serve images from Railway volume storage.

    On Railway: /mnt/data/{file_path}
    Locally: ./uploads/{file_path}

    Security: Path traversal protection
    Caching: 1 hour cache headers
    CORS: Public access allowed

    Args:
        file_path: Relative path to image file

    Returns:
        FileResponse with image

    Raises:
        HTTPException: 403 for path traversal attempts
        HTTPException: 404 for non-existent files
        HTTPException: 400 for invalid paths
    """
    # Construct full path
    full_path = UPLOADS_DIR / file_path

    logger.debug(f"Serving image request: {file_path}")
    logger.debug(f"Full path: {full_path}")
    logger.debug(f"UPLOADS_DIR: {UPLOADS_DIR}")

    # Security: Prevent path traversal attacks
    try:
        full_path = full_path.resolve()
        uploads_dir_resolved = UPLOADS_DIR.resolve()

        if not str(full_path).startswith(str(uploads_dir_resolved)):
            logger.warning(f"Path traversal attempt detected: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    except Exception as e:
        logger.error(f"Error resolving path: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    # Check file exists and is a file
    if not full_path.exists():
        logger.warning(f"Image not found: {full_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    if not full_path.is_file():
        logger.warning(f"Path is not a file: {full_path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    # Determine media type from extension
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    media_type = media_types.get(full_path.suffix.lower(), 'application/octet-stream')

    logger.info(f"Serving image: {file_path} (type: {media_type})")

    return FileResponse(
        full_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "Access-Control-Allow-Origin": "*"  # Allow CORS for public access
        }
    )

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from PIL import Image

try:
    _RESAMPLE = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
except AttributeError:  # pragma: no cover - Pillow < 9 fallback
    _RESAMPLE = Image.LANCZOS  # type: ignore[attr-defined]


def _generate_thumbnail(image_bytes: bytes, max_size: tuple[int, int] = (400, 300), quality: int = 85) -> bytes:
    """Generate a thumbnail from image bytes.

    Args:
        image_bytes: Original image data
        max_size: Maximum dimensions (width, height) for thumbnail
        quality: JPEG quality (0-100)

    Returns:
        Thumbnail image as JPEG bytes

    Raises:
        ValueError: If image cannot be loaded or processed
    """
    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Calculate new dimensions while preserving aspect ratio
        img.thumbnail(max_size, _RESAMPLE)

        # Save as JPEG with specified quality
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to generate thumbnail: {e}") from e


@dataclass
class CaptureRecord:
    record_id: str
    image_path: Path
    metadata_path: Path
    captured_at: datetime
    ingested_at: datetime
    metadata: Dict[str, Any]
    classification: Dict[str, Any]
    normal_description_file: str | None = None
    image_stored: bool = True
    thumbnail_path: Path | None = None
    thumbnail_stored: bool = False


class FileSystemDatalake:
    """Store captures on the local filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

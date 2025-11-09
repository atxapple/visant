from __future__ import annotations

import io
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

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

    def store_capture(
        self,
        image_bytes: bytes | None,
        metadata: Dict[str, Any],
        classification: Dict[str, Any],
        *,
        thumbnail_bytes: bytes | None = None,
        normal_description_file: str | None = None,
        store_image: bool = True,
        captured_at: datetime | None = None,
        ingested_at: datetime | None = None,
        device_id: str | None = None,
    ) -> CaptureRecord:
        ingest_time = (ingested_at or datetime.now(tz=timezone.utc)).astimezone(
            timezone.utc
        )
        capture_time = (captured_at or ingest_time).astimezone(timezone.utc)
        date_dir = self._root / capture_time.strftime("%Y/%m/%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        record_id = _build_record_id(device_id or metadata.get("device_id"), capture_time)
        image_path = date_dir / f"{record_id}.jpeg"
        thumbnail_path = date_dir / f"{record_id}_thumb.jpeg"
        metadata_path = date_dir / f"{record_id}.json"

        # Store full image
        image_stored = bool(store_image and image_bytes is not None)
        if store_image:
            if image_bytes is None:
                raise ValueError("image_bytes must be provided when store_image=True")
            image_path.write_bytes(image_bytes)

        # Generate and store thumbnail
        # If device provided thumbnail, use it (backward compatibility)
        # Otherwise, generate from full image
        thumbnail_stored = False
        if thumbnail_bytes is not None:
            # Use device-provided thumbnail
            thumbnail_path.write_bytes(thumbnail_bytes)
            thumbnail_stored = True
        elif image_bytes is not None:
            # Generate thumbnail from full image
            try:
                generated_thumbnail = _generate_thumbnail(image_bytes)
                thumbnail_path.write_bytes(generated_thumbnail)
                thumbnail_stored = True
            except ValueError as e:
                # Log error but don't fail the entire capture
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to generate thumbnail for %s: %s", record_id, e
                )

        payload = {
            "record_id": record_id,
            "captured_at": capture_time.isoformat(),
            "ingested_at": ingest_time.isoformat(),
            "metadata": metadata,
            "classification": classification,
            "normal_description_file": normal_description_file,
            "image_stored": image_stored,
            "image_filename": image_path.name if image_stored else None,
            "thumbnail_stored": thumbnail_stored,
            "thumbnail_filename": thumbnail_path.name if thumbnail_stored else None,
        }
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return CaptureRecord(
            record_id=record_id,
            image_path=image_path,
            metadata_path=metadata_path,
            captured_at=capture_time,
            ingested_at=ingest_time,
            metadata=metadata,
            classification=classification,
            normal_description_file=normal_description_file,
            image_stored=image_stored,
            thumbnail_path=thumbnail_path if thumbnail_stored else None,
            thumbnail_stored=thumbnail_stored,
        )


def _build_record_id(device_label: Optional[str], capture_time: datetime) -> str:
    label = str(device_label or "device").strip().lower()
    sanitized = re.sub(r"[^a-z0-9]+", "-", label)
    sanitized = sanitized.strip("-") or "device"
    if len(sanitized) > 48:
        sanitized = sanitized[:48].rstrip("-") or "device"
    timestamp_fragment = capture_time.strftime("%Y%m%dT%H%M%S%fZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{sanitized}_{timestamp_fragment}_{suffix}"


__all__ = ["CaptureRecord", "FileSystemDatalake"]

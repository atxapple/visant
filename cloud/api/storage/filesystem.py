"""Filesystem storage backend (legacy, for backward compatibility)."""

import os
from pathlib import Path
from typing import Optional
from cloud.api.storage.base import StorageBackend


class FilesystemStorage(StorageBackend):
    """Filesystem-based storage (original Visant implementation)."""

    def __init__(self, base_path: str = "/mnt/data/datalake"):
        """
        Initialize filesystem storage.

        Args:
            base_path: Root directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(self, file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """Upload file to filesystem."""
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_data)

        return key

    def download(self, key: str) -> bytes:
        """Download file from filesystem."""
        file_path = self.base_path / key

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        with open(file_path, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        """Check if file exists."""
        file_path = self.base_path / key
        return file_path.exists()

    def delete(self, key: str) -> bool:
        """Delete file from filesystem."""
        file_path = self.base_path / key

        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get file path (filesystem doesn't support URLs).

        For filesystem storage, returns the local file path.
        In production, this should be served via FastAPI endpoint.
        """
        return str(self.base_path / key)

    def list_keys(self, prefix: str) -> list[str]:
        """List all keys with given prefix."""
        prefix_path = self.base_path / prefix

        if not prefix_path.exists():
            return []

        keys = []
        for file_path in prefix_path.rglob("*"):
            if file_path.is_file():
                # Get relative path from base_path
                relative_path = file_path.relative_to(self.base_path)
                keys.append(str(relative_path))

        return keys

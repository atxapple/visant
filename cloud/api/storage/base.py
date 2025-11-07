"""Base storage interface for abstracting filesystem vs S3."""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO
from datetime import datetime


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def upload(self, file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """
        Upload file to storage.

        Args:
            file_data: Binary file data
            key: Storage key/path
            content_type: MIME type

        Returns:
            Storage key where file was saved
        """
        pass

    @abstractmethod
    def download(self, key: str) -> bytes:
        """
        Download file from storage.

        Args:
            key: Storage key/path

        Returns:
            Binary file data
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            key: Storage key/path

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete file from storage.

        Args:
            key: Storage key/path

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get URL for accessing file (pre-signed for S3, file path for filesystem).

        Args:
            key: Storage key/path
            expires_in: URL expiration in seconds (for S3 pre-signed URLs)

        Returns:
            Accessible URL
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]:
        """
        List all keys with given prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            List of matching keys
        """
        pass

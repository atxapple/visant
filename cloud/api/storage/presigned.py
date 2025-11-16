"""URL generation for Railway volume storage.

S3 support removed - using local file serving instead.
Images are served from Railway volume at /mnt/data (or ./uploads locally).
"""

from typing import Optional


def generate_presigned_url(
    s3_key: str,
    expiration: int = 3600,
    bucket: Optional[str] = None
) -> Optional[str]:
    """
    Generate URL for image access.

    Returns local file URL that will be served by /images endpoint.
    Railway volume only - S3 support removed for simplicity.

    Args:
        s3_key: File path (kept as 's3_key' for backwards compatibility)
        expiration: Ignored (kept for API compatibility)
        bucket: Ignored (kept for API compatibility)

    Returns:
        Local file URL: /images/{s3_key}
    """
    return f"/images/{s3_key}"


def generate_presigned_upload_url(
    s3_key: str,
    expiration: int = 3600,
    bucket: Optional[str] = None,
    content_type: str = "image/jpeg"
) -> Optional[str]:
    """
    Generate URL for uploading.

    Note: This function is no longer used with Railway volume storage.
    Kept for backwards compatibility.

    Returns:
        None (uploads are handled differently with Railway volume)
    """
    return None


def get_public_url(s3_key: str, bucket: Optional[str] = None) -> str:
    """
    Get public URL for image (Railway volume).

    Args:
        s3_key: File path (kept as 's3_key' for backwards compatibility)
        bucket: Ignored (kept for API compatibility)

    Returns:
        Local file URL: /images/{s3_key}
    """
    return f"/images/{s3_key}"

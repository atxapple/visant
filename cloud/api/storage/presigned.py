"""Pre-signed URL generation for S3 storage."""

import os
from datetime import timedelta
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    print("WARNING: boto3 not installed. S3 features will be limited.")


# S3 Configuration from environment
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# For local development/testing without S3
USE_S3 = AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET


def get_s3_client():
    """Get configured S3 client."""
    if not S3_AVAILABLE:
        return None

    if not USE_S3:
        return None

    try:
        return boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
    except Exception as e:
        print(f"ERROR: Failed to create S3 client: {e}")
        return None


def generate_presigned_url(
    s3_key: str,
    expiration: int = 3600,
    bucket: Optional[str] = None
) -> Optional[str]:
    """
    Generate a pre-signed URL for S3 object.

    Args:
        s3_key: S3 object key (path)
        expiration: URL expiration in seconds (default: 1 hour)
        bucket: S3 bucket name (defaults to AWS_S3_BUCKET)

    Returns:
        Pre-signed URL or None if S3 not configured
    """
    if not USE_S3:
        # Return placeholder for development
        return f"https://placeholder.com/image/{s3_key.split('/')[-1]}"

    s3_client = get_s3_client()
    if not s3_client:
        return None

    bucket_name = bucket or AWS_S3_BUCKET

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"ERROR: Failed to generate pre-signed URL: {e}")
        return None


def generate_presigned_upload_url(
    s3_key: str,
    expiration: int = 3600,
    bucket: Optional[str] = None,
    content_type: str = "image/jpeg"
) -> Optional[str]:
    """
    Generate a pre-signed URL for uploading to S3.

    Args:
        s3_key: S3 object key (path)
        expiration: URL expiration in seconds (default: 1 hour)
        bucket: S3 bucket name (defaults to AWS_S3_BUCKET)
        content_type: MIME type of file being uploaded

    Returns:
        Pre-signed upload URL or None if S3 not configured
    """
    if not USE_S3:
        return None

    s3_client = get_s3_client()
    if not s3_client:
        return None

    bucket_name = bucket or AWS_S3_BUCKET

    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"ERROR: Failed to generate pre-signed upload URL: {e}")
        return None


def get_public_url(s3_key: str, bucket: Optional[str] = None) -> str:
    """
    Get public URL for S3 object (for public buckets).

    For development without S3, returns placeholder.

    Args:
        s3_key: S3 object key (path)
        bucket: S3 bucket name (defaults to AWS_S3_BUCKET)

    Returns:
        Public URL or placeholder
    """
    if not USE_S3:
        return f"https://placeholder.com/image/{s3_key.split('/')[-1]}"

    bucket_name = bucket or AWS_S3_BUCKET
    return f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

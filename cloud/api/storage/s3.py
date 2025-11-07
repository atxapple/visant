"""S3 storage backend for scalable cloud storage."""

import os
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from cloud.api.storage.base import StorageBackend


class S3Storage(StorageBackend):
    """S3-compatible storage backend (AWS S3, Railway S3, MinIO, etc.)."""

    def __init__(
        self,
        bucket: str,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            region: AWS region (e.g., "us-west-2")
            endpoint_url: Custom endpoint URL (for Railway S3, MinIO, etc.)
            access_key_id: AWS access key ID (or from env AWS_ACCESS_KEY_ID)
            secret_access_key: AWS secret key (or from env AWS_SECRET_ACCESS_KEY)
        """
        self.bucket = bucket
        self.region = region or os.getenv("S3_REGION", "us-west-2")

        # Initialize boto3 client
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=endpoint_url or os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        # Verify bucket exists (or create it)
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    if self.region == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.bucket)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    print(f"✅ Created S3 bucket: {self.bucket}")
                except ClientError as create_error:
                    print(f"⚠️  Failed to create bucket {self.bucket}: {create_error}")
            else:
                print(f"⚠️  S3 bucket access error: {e}")

    def upload(self, file_data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """Upload file to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )
            return key
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {e}")

    def download(self, key: str) -> bytes:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {key}")
            raise RuntimeError(f"Failed to download from S3: {e}")

    def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise RuntimeError(f"Failed to check S3 object: {e}")

    def delete(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            print(f"⚠️  Failed to delete from S3: {e}")
            return False

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate pre-signed URL for accessing S3 object.

        Args:
            key: S3 object key
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Pre-signed URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate pre-signed URL: {e}")

    def list_keys(self, prefix: str) -> list[str]:
        """List all keys with given prefix."""
        try:
            keys = []
            paginator = self.s3_client.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        keys.append(obj["Key"])

            return keys
        except ClientError as e:
            print(f"⚠️  Failed to list S3 objects: {e}")
            return []

    def copy(self, source_key: str, dest_key: str) -> str:
        """
        Copy object within S3 bucket.

        Args:
            source_key: Source object key
            dest_key: Destination object key

        Returns:
            Destination key
        """
        try:
            copy_source = {"Bucket": self.bucket, "Key": source_key}
            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=self.bucket, Key=dest_key
            )
            return dest_key
        except ClientError as e:
            raise RuntimeError(f"Failed to copy S3 object: {e}")

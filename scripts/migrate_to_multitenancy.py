"""
Data migration script: Filesystem → PostgreSQL + S3

This script migrates existing Visant data from filesystem-based storage
to the multi-tenant PostgreSQL + S3 architecture.

Usage:
    python scripts/migrate_to_multitenancy.py --dry-run    # Test without writing
    python scripts/migrate_to_multitenancy.py              # Run migration
"""

import os
import sys
import json
import glob
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from tqdm import tqdm
from sqlalchemy.orm import Session
from cloud.api.database import (
    SessionLocal, engine, Base,
    Organization, User, Device, Capture
)
from cloud.api.storage import FilesystemStorage, S3Storage


class MigrationScript:
    """Handles migration from filesystem to database + S3."""

    def __init__(self, dry_run: bool = False, storage_backend: str = "s3"):
        self.dry_run = dry_run
        self.storage_backend = storage_backend
        self.db: Optional[Session] = None
        self.org: Optional[Organization] = None
        self.device_api_keys = {}

        # Initialize storage
        if storage_backend == "s3":
            bucket = os.getenv("S3_BUCKET")
            if not bucket:
                raise ValueError("S3_BUCKET environment variable required for S3 migration")
            self.storage = S3Storage(bucket=bucket)
            print(f"✅ Using S3 storage (bucket: {bucket})")
        else:
            # Filesystem (for testing)
            self.storage = FilesystemStorage()
            print(f"✅ Using filesystem storage")

        # Source filesystem datalake
        self.source_datalake = Path("/mnt/data/datalake")
        if not self.source_datalake.exists():
            # Try local path for development
            self.source_datalake = Path("./data/datalake")
            if not self.source_datalake.exists():
                raise FileNotFoundError(f"Source datalake not found at {self.source_datalake}")

        print(f"📂 Source datalake: {self.source_datalake}")

    def run(self):
        """Execute the full migration."""
        print("\n" + "=" * 60)
        print("   Visant Multi-Tenancy Migration")
        print("=" * 60)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No data will be written\n")
        else:
            confirm = input("\n⚠️  This will migrate data to database. Continue? (yes/no): ")
            if confirm.lower() != "yes":
                print("Migration cancelled.")
                return

        # Step 1: Initialize database
        if not self.dry_run:
            print("\n[1/6] Initializing database...")
            Base.metadata.create_all(bind=engine)
            self.db = SessionLocal()
            print("✅ Database initialized")
        else:
            print("\n[1/6] ✓ Database initialization (skipped - dry run)")

        # Step 2: Create default organization
        print("\n[2/6] Creating default organization...")
        self.create_default_organization()

        # Step 3: Scan filesystem
        print("\n[3/6] Scanning filesystem datalake...")
        capture_files = self.scan_filesystem()
        print(f"✅ Found {len(capture_files)} captures")

        # Step 4: Create devices
        print("\n[4/6] Creating devices...")
        device_ids = self.extract_device_ids(capture_files)
        self.create_devices(device_ids)

        # Step 5: Migrate captures
        print("\n[5/6] Migrating captures...")
        self.migrate_captures(capture_files)

        # Step 6: Validation
        print("\n[6/6] Validation...")
        self.validate_migration(len(capture_files))

        # Output summary
        self.print_summary()

        if not self.dry_run and self.db:
            self.db.close()

    def create_default_organization(self):
        """Create default organization for existing data."""
        if self.dry_run:
            self.org = Organization(
                name="Default Organization (dry run)",
                created_at=datetime.utcnow()
            )
            print(f"✓ Would create organization: {self.org.name}")
            return

        org_name = input("Enter organization name for existing data [Default Org]: ") or "Default Org"

        self.org = Organization(
            name=org_name,
            created_at=datetime.utcnow()
        )
        self.db.add(self.org)
        self.db.commit()
        self.db.refresh(self.org)

        print(f"✅ Created organization: {self.org.name} (ID: {self.org.id})")

        # Create admin user
        admin_email = input("Enter admin email: ")
        if admin_email:
            admin_user = User(
                email=admin_email,
                org_id=self.org.id,
                role="admin",
                created_at=datetime.utcnow()
            )
            self.db.add(admin_user)
            self.db.commit()
            print(f"✅ Created admin user: {admin_email}")

    def scan_filesystem(self) -> list[Path]:
        """Scan filesystem for JSON capture files."""
        pattern = str(self.source_datalake / "**" / "*.json")
        capture_files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        return sorted(capture_files)

    def extract_device_ids(self, capture_files: list[Path]) -> set[str]:
        """Extract unique device IDs from captures."""
        device_ids = set()

        for file_path in tqdm(capture_files, desc="Extracting device IDs"):
            try:
                with open(file_path) as f:
                    metadata = json.load(f)
                device_id = metadata.get("metadata", {}).get("device_id")
                if device_id:
                    device_ids.add(device_id)
            except Exception as e:
                print(f"⚠️  Error reading {file_path}: {e}")

        return device_ids

    def create_devices(self, device_ids: set[str]):
        """Create device records."""
        for device_id in tqdm(sorted(device_ids), desc="Creating devices"):
            api_key = secrets.token_urlsafe(32)
            self.device_api_keys[device_id] = api_key

            if self.dry_run:
                print(f"✓ Would create device: {device_id}")
                continue

            friendly_name = device_id.replace('-', ' ').replace('_', ' ').title()

            device = Device(
                device_id=device_id,
                org_id=self.org.id,
                friendly_name=friendly_name,
                api_key=api_key,
                status="active",
                created_at=datetime.utcnow()
            )
            self.db.add(device)

        if not self.dry_run:
            self.db.commit()
            print(f"✅ Created {len(device_ids)} devices")

    def migrate_captures(self, capture_files: list[Path]):
        """Migrate captures to database + S3."""
        batch_size = 100
        batch = []

        for file_path in tqdm(capture_files, desc="Migrating captures"):
            try:
                # Parse JSON metadata
                with open(file_path) as f:
                    metadata = json.load(f)

                record_id = metadata["record_id"]
                device_id = metadata["metadata"]["device_id"]

                # Extract date components from captured_at
                captured_at_str = metadata["captured_at"]
                captured_at = datetime.fromisoformat(captured_at_str.replace('Z', '+00:00'))
                year = captured_at.strftime("%Y")
                month = captured_at.strftime("%m")
                day = captured_at.strftime("%d")

                # Upload image to S3
                s3_image_key = None
                image_stored = False
                image_path = file_path.parent / f"{record_id}.jpeg"

                if image_path.exists():
                    if not self.dry_run:
                        s3_image_key = f"{self.org.id}/devices/{device_id}/captures/{year}/{month}/{day}/{record_id}.jpeg"
                        with open(image_path, "rb") as img_file:
                            self.storage.upload(img_file.read(), s3_image_key)
                        image_stored = True
                    else:
                        s3_image_key = f"<org_id>/devices/{device_id}/captures/{year}/{month}/{day}/{record_id}.jpeg"
                        image_stored = True

                # Upload thumbnail to S3
                s3_thumbnail_key = None
                thumbnail_stored = False
                thumb_path = file_path.parent / f"{record_id}_thumb.jpeg"

                if thumb_path.exists():
                    if not self.dry_run:
                        s3_thumbnail_key = f"{self.org.id}/devices/{device_id}/captures/{year}/{month}/{day}/{record_id}_thumb.jpeg"
                        with open(thumb_path, "rb") as thumb_file:
                            self.storage.upload(thumb_file.read(), s3_thumbnail_key)
                        thumbnail_stored = True
                    else:
                        s3_thumbnail_key = f"<org_id>/devices/{device_id}/captures/{year}/{month}/{day}/{record_id}_thumb.jpeg"
                        thumbnail_stored = True

                # Create capture record
                if not self.dry_run:
                    capture = Capture(
                        record_id=record_id,
                        org_id=self.org.id,
                        device_id=device_id,
                        captured_at=captured_at,
                        ingested_at=datetime.fromisoformat(metadata["ingested_at"].replace('Z', '+00:00')),
                        s3_image_key=s3_image_key,
                        s3_thumbnail_key=s3_thumbnail_key,
                        image_stored=image_stored,
                        thumbnail_stored=thumbnail_stored,
                        state=metadata["classification"]["state"],
                        score=metadata["classification"].get("score"),
                        reason=metadata["classification"].get("reason"),
                        agent_details=metadata["classification"].get("agent_details"),
                        trigger_label=metadata["metadata"].get("trigger_label"),
                        normal_description_file=metadata.get("normal_description_file"),
                        capture_metadata=metadata["metadata"]
                    )
                    batch.append(capture)

                    # Commit in batches
                    if len(batch) >= batch_size:
                        self.db.bulk_save_objects(batch)
                        self.db.commit()
                        batch = []

            except Exception as e:
                print(f"\n⚠️  Error migrating {file_path}: {e}")

        # Commit remaining batch
        if not self.dry_run and batch:
            self.db.bulk_save_objects(batch)
            self.db.commit()

    def validate_migration(self, expected_count: int):
        """Validate migration results."""
        if self.dry_run:
            print("✓ Validation (skipped - dry run)")
            return

        # Check capture count
        actual_count = self.db.query(Capture).count()

        if actual_count == expected_count:
            print(f"✅ Capture count matches: {actual_count}")
        else:
            print(f"⚠️  Capture count mismatch: expected {expected_count}, got {actual_count}")

        # Test image access
        sample_capture = self.db.query(Capture).filter(Capture.image_stored == True).first()
        if sample_capture:
            try:
                url = self.storage.get_url(sample_capture.s3_image_key)
                print(f"✅ Image access test passed (sample URL generated)")
            except Exception as e:
                print(f"⚠️  Image access test failed: {e}")

    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("   Migration Summary")
        print("=" * 60)

        if not self.dry_run:
            print(f"\nOrganization: {self.org.name} ({self.org.id})")
            print(f"Devices: {self.db.query(Device).count()}")
            print(f"Captures: {self.db.query(Capture).count()}")
            print(f"Storage: {self.storage_backend.upper()}")

        print("\n=== Device API Keys ===")
        print("Update device configuration files with these API keys:\n")
        for device_id, api_key in sorted(self.device_api_keys.items()):
            print(f"  {device_id}: {api_key}")

        if not self.dry_run:
            print("\n=== Next Steps ===")
            print("1. Update device config files with API keys above")
            print("2. Set environment variable: STORAGE_BACKEND=s3")
            print("3. Restart Visant server")
            print("4. Test dashboard login")
            print("5. Keep filesystem backup for 30 days")
            print("\n✅ Migration complete!\n")


def main():
    parser = argparse.ArgumentParser(description="Migrate Visant to multi-tenant architecture")
    parser.add_argument("--dry-run", action="store_true", help="Test migration without writing data")
    parser.add_argument("--storage", choices=["s3", "filesystem"], default="s3", help="Storage backend")
    args = parser.parse_args()

    try:
        migration = MigrationScript(dry_run=args.dry_run, storage_backend=args.storage)
        migration.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

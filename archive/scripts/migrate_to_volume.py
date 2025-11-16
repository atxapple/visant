#!/usr/bin/env python3
"""
Migrate existing images from ephemeral /app/uploads to persistent /mnt/data volume.

Run this ONCE on Railway after mounting the volume at /mnt/data.
"""

import os
import shutil
from pathlib import Path


def migrate_images():
    """Migrate images from old ephemeral location to persistent volume."""

    old_location = Path("/app/uploads")
    new_location = Path("/mnt/data")

    print("=" * 70)
    print("Visant Image Migration to Railway Volume")
    print("=" * 70)

    # Check if we're on Railway
    if not os.getenv("RAILWAY_ENVIRONMENT"):
        print("\n⚠️  WARNING: Not running on Railway!")
        print("This script should only be run on Railway after mounting /mnt/data volume")
        return

    # Check old location
    if not old_location.exists():
        print(f"\n✗ Old location {old_location} does not exist")
        print("  No images to migrate (filesystem may have already been wiped)")
        return

    # Count existing files
    old_files = list(old_location.rglob("*.jpg")) + list(old_location.rglob("*.jpeg")) + list(old_location.rglob("*.png"))
    print(f"\nFound {len(old_files)} images in {old_location}")

    if len(old_files) == 0:
        print("  No images to migrate")
        return

    # Check new location
    new_location.mkdir(parents=True, exist_ok=True)
    print(f"Target location: {new_location}")

    # Migrate files
    migrated = 0
    skipped = 0
    errors = 0

    for old_file in old_files:
        try:
            # Get relative path
            rel_path = old_file.relative_to(old_location)
            new_file = new_location / rel_path

            # Skip if already exists
            if new_file.exists():
                skipped += 1
                continue

            # Create parent directory
            new_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(old_file, new_file)
            migrated += 1

            if migrated % 100 == 0:
                print(f"  Migrated {migrated} files...")

        except Exception as e:
            print(f"  Error migrating {old_file}: {e}")
            errors += 1

    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print(f"  Migrated: {migrated} files")
    print(f"  Skipped:  {skipped} files (already exist)")
    print(f"  Errors:   {errors} files")

    if errors == 0 and migrated > 0:
        print("\n✓ All images successfully migrated to persistent volume!")
        print(f"  Old location: {old_location} (can be deleted after verification)")
        print(f"  New location: {new_location} (persistent across deployments)")


if __name__ == "__main__":
    migrate_images()

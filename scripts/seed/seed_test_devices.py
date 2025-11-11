"""Seed test devices for development and testing.

Usage:
    python -m scripts.seed_test_devices
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloud.api.database.session import get_db
from cloud.api.database.models import Device


TEST_DEVICES = [
    {"device_id": "TEST1", "batch_id": "BATCH_TEST_001"},
    {"device_id": "TEST2", "batch_id": "BATCH_TEST_001"},
    {"device_id": "TEST3", "batch_id": "BATCH_TEST_001"},
    {"device_id": "ABC12", "batch_id": "BATCH_TEST_001"},
    {"device_id": "XYZ99", "batch_id": "BATCH_TEST_001"},
]


def seed_test_devices():
    """Seed test devices into database."""
    db = next(get_db())

    try:
        print("Seeding test devices...")

        for device_data in TEST_DEVICES:
            # Check if device already exists
            existing = db.query(Device).filter(
                Device.device_id == device_data["device_id"]
            ).first()

            if existing:
                print(f"  [SKIP] {device_data['device_id']} (already exists)")
                continue

            # Create manufactured device (not yet activated)
            device = Device(
                device_id=device_data["device_id"],
                manufactured_at=datetime.now(timezone.utc),
                batch_id=device_data["batch_id"],
                status="manufactured",
                created_at=datetime.now(timezone.utc),
                org_id=None,  # Not activated yet
            )

            db.add(device)
            print(f"  [OK] Created {device_data['device_id']}")

        db.commit()
        print("\n[SUCCESS] Test devices seeded successfully!")

        # Show summary
        print("\nSummary of Test Devices:")
        print("-" * 60)
        devices = db.query(Device).filter(Device.batch_id == "BATCH_TEST_001").all()
        for device in devices:
            print(f"Device ID: {device.device_id}")
            print(f"  Status: {device.status}")
            print(f"  Batch: {device.batch_id}")
            print(f"  Activated: {'Yes' if device.org_id else 'No'}")
            print()

    except Exception as e:
        print(f"[ERROR] Error seeding devices: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_devices()

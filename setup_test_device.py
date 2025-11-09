#!/usr/bin/env python3
"""Setup test device for cloud-triggered camera testing."""

from dotenv import load_dotenv
load_dotenv()

from cloud.api.database import SessionLocal, Organization, User, Device
from datetime import datetime
import uuid

def setup_test_device():
    """Create test organization, user, and device for testing."""
    db = SessionLocal()
    try:
        # Check if test org exists
        org = db.query(Organization).filter(Organization.name == "Test Organization").first()
        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Test Organization",
                created_at=datetime.utcnow(),
                subscription_status="active",
                allowed_devices=10
            )
            db.add(org)
            db.commit()
            print(f"[OK] Created test organization: {org.id}")
        else:
            print(f"[OK] Test organization exists: {org.id}")

        # Check if test user exists
        user = db.query(User).filter(User.email == "test@visant.local").first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="test@visant.local",
                org_id=org.id,
                created_at=datetime.utcnow(),
                role="admin"
            )
            db.add(user)
            db.commit()
            print(f"[OK] Created test user: {user.id}")
        else:
            print(f"[OK] Test user exists: {user.id}")

        # Check if test device exists
        device = db.query(Device).filter(Device.device_id == "TEST_CAM_01").first()
        if not device:
            device = Device(
                device_id="TEST_CAM_01",
                org_id=org.id,
                friendly_name="Test Camera 01",
                api_key="test_api_key_12345",
                status="active",
                activated_by_user_id=user.id,
                activated_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                config={
                    "trigger": {
                        "enabled": True,
                        "interval_seconds": 10  # Capture every 10 seconds for testing
                    }
                }
            )
            db.add(device)
            db.commit()
            print(f"[OK] Created test device: {device.device_id}")
        else:
            print(f"[OK] Test device exists: {device.device_id}")
            # Update config to enable triggers
            device.config = {
                "trigger": {
                    "enabled": True,
                    "interval_seconds": 10
                }
            }
            device.status = "active"
            db.commit()
            print(f"  Updated config: trigger enabled, 10s interval")

        print("\n" + "=" * 70)
        print("Test Device Setup Complete!")
        print("=" * 70)
        print(f"\nOrganization ID: {org.id}")
        print(f"User Email:      {user.email}")
        print(f"Device ID:       {device.device_id}")
        print(f"Device Status:   {device.status}")
        print(f"Trigger Config:  {device.config}")
        print("\nYou can now run the device client with:")
        print(f"  python -m device.main_v2 \\")
        print(f"    --api-url http://localhost:8000 \\")
        print(f"    --device-id TEST_CAM_01 \\")
        print(f"    --camera-source 0")
        print("=" * 70)

    finally:
        db.close()

if __name__ == "__main__":
    setup_test_device()

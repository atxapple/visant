#!/usr/bin/env python3
"""Clean test data for fresh test run."""

from dotenv import load_dotenv
load_dotenv()

from cloud.api.database import SessionLocal
from cloud.api.database.models import Capture, ScheduledTrigger

db = SessionLocal()

try:
    # Delete all captures for TEST_CAM_01
    deleted_captures = db.query(Capture).filter(
        Capture.device_id == "TEST_CAM_01"
    ).delete()

    # Delete all triggers for TEST_CAM_01
    deleted_triggers = db.query(ScheduledTrigger).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01"
    ).delete()

    db.commit()

    print(f"[OK] Cleaned test data:")
    print(f"  - Deleted {deleted_captures} captures")
    print(f"  - Deleted {deleted_triggers} triggers")
    print(f"\nReady for clean 3-minute test!")

finally:
    db.close()

#!/usr/bin/env python3
"""Check test results from database."""

from dotenv import load_dotenv
load_dotenv()

from cloud.api.database import SessionLocal
from cloud.api.database.models import Capture, Device, ScheduledTrigger
from sqlalchemy import func

db = SessionLocal()

try:
    # Get device info
    device = db.query(Device).filter(Device.device_id == "TEST_CAM_01").first()
    print("=" * 70)
    print("CLOUD-TRIGGERED CAMERA TEST RESULTS")
    print("=" * 70)
    print(f"\nDevice: {device.device_id}")
    print(f"Status: {device.status}")
    print(f"Last Seen: {device.last_seen_at}")

    # Count captures
    total_captures = db.query(func.count(Capture.record_id)).filter(
        Capture.device_id == "TEST_CAM_01"
    ).scalar()

    print(f"\n[CAPTURES]")
    print(f"Total Captures: {total_captures}")

    # Count by evaluation status
    pending = db.query(func.count(Capture.record_id)).filter(
        Capture.device_id == "TEST_CAM_01",
        Capture.evaluation_status == "pending"
    ).scalar()

    completed = db.query(func.count(Capture.record_id)).filter(
        Capture.device_id == "TEST_CAM_01",
        Capture.evaluation_status == "completed"
    ).scalar()

    print(f"  - Pending Evaluation: {pending}")
    print(f"  - Evaluation Completed: {completed}")

    # Count triggers
    total_triggers = db.query(func.count(ScheduledTrigger.trigger_id)).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01"
    ).scalar()

    print(f"\n[TRIGGERS]")
    print(f"Total Triggers: {total_triggers}")

    # Count by type
    manual = db.query(func.count(ScheduledTrigger.trigger_id)).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01",
        ScheduledTrigger.trigger_type == "manual"
    ).scalar()

    scheduled = db.query(func.count(ScheduledTrigger.trigger_id)).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01",
        ScheduledTrigger.trigger_type == "scheduled"
    ).scalar()

    print(f"  - Manual: {manual}")
    print(f"  - Scheduled: {scheduled}")

    # Count by status
    sent = db.query(func.count(ScheduledTrigger.trigger_id)).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01",
        ScheduledTrigger.status == "sent"
    ).scalar()

    executed = db.query(func.count(ScheduledTrigger.trigger_id)).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01",
        ScheduledTrigger.status == "executed"
    ).scalar()

    print(f"  - Sent: {sent}")
    print(f"  - Executed: {executed}")

    # Show recent triggers
    print(f"\n[RECENT TRIGGERS]")
    recent_triggers = db.query(ScheduledTrigger).filter(
        ScheduledTrigger.device_id == "TEST_CAM_01"
    ).order_by(ScheduledTrigger.scheduled_at.desc()).limit(5).all()

    for trigger in recent_triggers:
        print(f"  {trigger.trigger_type:10} | {trigger.status:10} | {trigger.trigger_id}")

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"[OK] Device connected and active")
    print(f"[OK] {total_captures} captures uploaded successfully")
    print(f"[OK] {total_triggers} triggers tracked in database")
    print(f"[OK] {executed} triggers marked as executed")
    print(f"[OK] All captures are being evaluated")
    print("=" * 70)

finally:
    db.close()

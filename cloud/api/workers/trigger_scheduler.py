"""
TriggerScheduler - Background worker that manages scheduled captures.

This worker runs every second and checks all active devices to see if
they need a scheduled capture based on their trigger configuration.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy.orm import Session

from cloud.api.database.models import Device, Capture, ScheduledTrigger
from cloud.api.database.session import SessionLocal

logger = logging.getLogger(__name__)


class TriggerScheduler:
    """
    Background scheduler that triggers captures based on per-device configuration.

    Runs every 1 second, checks all active devices, and publishes capture
    commands via CommandHub when triggers are due.
    """

    def __init__(self, command_hub):
        """
        Initialize the scheduler.

        Args:
            command_hub: CommandHub instance for publishing commands
        """
        self.command_hub = command_hub
        self.running = False
        self._task = None

    async def start(self):
        """Start the scheduler background task."""
        if self.running:
            logger.warning("[TriggerScheduler] Already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._schedule_loop())
        logger.info("[TriggerScheduler] Started")

    async def stop(self):
        """Stop the scheduler background task."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("[TriggerScheduler] Stopped")

    async def _schedule_loop(self):
        """Main scheduler loop that runs every second."""
        logger.info("[TriggerScheduler] Schedule loop started")

        while self.running:
            try:
                await self._process_devices()
                await asyncio.sleep(1.0)  # Check every second
            except asyncio.CancelledError:
                logger.info("[TriggerScheduler] Schedule loop cancelled")
                break
            except Exception as e:
                logger.error(f"[TriggerScheduler] Error in schedule loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Continue after error

    async def _process_devices(self):
        """Check all active devices and trigger captures if needed."""
        db = SessionLocal()
        try:
            # Get all active devices
            devices = db.query(Device).filter(
                Device.status == "active"
            ).all()

            for device in devices:
                try:
                    if await self._should_trigger(device, db):
                        await self._trigger_capture(device, db)
                except Exception as e:
                    logger.error(f"[TriggerScheduler] Error processing device {device.device_id}: {e}")

        finally:
            db.close()

    async def _should_trigger(self, device: Device, db: Session) -> bool:
        """
        Check if device needs a scheduled capture.

        Args:
            device: Device to check
            db: Database session

        Returns:
            True if capture should be triggered
        """
        # Get trigger config
        config = device.config or {}
        trigger_config = config.get("trigger", {})

        # Check if scheduled triggers enabled
        if not trigger_config.get("enabled", False):
            return False

        interval_seconds = trigger_config.get("interval_seconds")
        if interval_seconds is None or interval_seconds <= 0:
            return False

        # Get last capture time for this device
        last_capture = db.query(Capture).filter(
            Capture.device_id == device.device_id
        ).order_by(Capture.captured_at.desc()).first()

        now = datetime.utcnow()

        if last_capture is None:
            # No captures yet, trigger immediately
            return True

        # Check if enough time has elapsed
        time_since_last = (now - last_capture.captured_at).total_seconds()

        return time_since_last >= interval_seconds

    async def _trigger_capture(self, device: Device, db: Session):
        """
        Trigger a scheduled capture for a device.

        Args:
            device: Device to trigger
            db: Database session
        """
        # Generate trigger ID
        now = datetime.utcnow()
        trigger_id = f"sched_{device.device_id}_{now.strftime('%Y%m%d_%H%M%S_%f')}"

        # Create trigger record
        trigger = ScheduledTrigger(
            trigger_id=trigger_id,
            device_id=device.device_id,
            trigger_type="scheduled",
            scheduled_at=now,
            sent_at=now,
            status="sent"
        )
        db.add(trigger)
        db.commit()

        # Publish capture command via CommandHub
        try:
            await self.command_hub.publish(device.device_id, {
                "cmd": "capture",
                "trigger_id": trigger_id,
                "type": "scheduled"
            })

            logger.info(f"[TriggerScheduler] Triggered scheduled capture {trigger_id} for device {device.device_id}")

        except Exception as e:
            # Mark trigger as failed
            trigger.status = "failed"
            trigger.error_message = str(e)
            db.commit()

            logger.error(f"[TriggerScheduler] Failed to send trigger {trigger_id}: {e}")

    async def trigger_manual_capture(self, device_id: str, db: Session) -> str:
        """
        Trigger a manual capture immediately.

        This is called by the API endpoint when user clicks "Capture Now".

        Args:
            device_id: Device to trigger
            db: Database session

        Returns:
            trigger_id of created trigger
        """
        # Generate trigger ID
        now = datetime.utcnow()
        trigger_id = f"manual_{device_id}_{now.strftime('%Y%m%d_%H%M%S_%f')}"

        # Create trigger record
        trigger = ScheduledTrigger(
            trigger_id=trigger_id,
            device_id=device_id,
            trigger_type="manual",
            scheduled_at=now,
            sent_at=now,
            status="sent"
        )
        db.add(trigger)
        db.commit()

        # Publish capture command
        await self.command_hub.publish(device_id, {
            "cmd": "capture",
            "trigger_id": trigger_id,
            "type": "manual"
        })

        logger.info(f"[TriggerScheduler] Triggered manual capture {trigger_id} for device {device_id}")

        return trigger_id

    def mark_trigger_executed(self, trigger_id: str, capture_id: str, db: Session):
        """
        Mark a trigger as executed when capture is received.

        Called by the capture upload endpoint.

        Args:
            trigger_id: Trigger ID from device
            capture_id: Resulting capture record ID
            db: Database session
        """
        trigger = db.query(ScheduledTrigger).filter(
            ScheduledTrigger.trigger_id == trigger_id
        ).first()

        if trigger:
            trigger.status = "executed"
            trigger.executed_at = datetime.utcnow()
            trigger.capture_id = capture_id
            db.commit()

            logger.info(f"[TriggerScheduler] Marked trigger {trigger_id} as executed (capture: {capture_id})")
        else:
            logger.warning(f"[TriggerScheduler] Trigger {trigger_id} not found for marking executed")

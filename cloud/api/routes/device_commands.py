"""
Device Command Stream - SSE endpoint for pushing commands to devices.

Replaces the old polling-based architecture with event-driven push.
"""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from cloud.api.database.session import get_db
from cloud.api.database.models import Device

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/devices/{device_id}/commands")
async def device_command_stream(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    SSE stream that pushes commands to devices.

    Commands sent via this stream:
    - {"cmd": "capture", "trigger_id": "...", "type": "scheduled"}
    - {"cmd": "capture", "trigger_id": "...", "type": "manual"}
    - {"cmd": "update_config", "config": {...}}

    The device should:
    1. Connect to this endpoint on startup
    2. Listen for commands continuously
    3. Execute commands when received
    4. Reconnect if connection drops
    """
    # Verify device exists and is active
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    if device.status != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Device {device_id} is not active (status: {device.status})"
        )

    # Get command hub from app state
    from cloud.api.server import get_command_hub
    command_hub = get_command_hub()

    # Subscribe to commands for this device
    queue = await command_hub.subscribe(device_id)

    async def event_generator():
        """Generate SSE events from command queue."""
        try:
            # Send initial connected event
            yield 'data: {"event": "connected", "device_id": "' + device_id + '"}\n\n'

            logger.info(f"[device_commands] Device {device_id} connected to command stream")

            # Stream commands
            while True:
                # Wait for command with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=60.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield 'data: {"event": "ping"}\n\n'

        except asyncio.CancelledError:
            logger.info(f"[device_commands] Device {device_id} command stream cancelled")
        except Exception as e:
            logger.error(f"[device_commands] Error streaming to device {device_id}: {e}")
        finally:
            # Unsubscribe when connection closes
            await command_hub.unsubscribe(device_id, queue)
            logger.info(f"[device_commands] Device {device_id} disconnected from command stream")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/v1/devices/{device_id}/trigger")
async def manual_trigger(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Trigger a manual capture immediately.

    This endpoint is called when user clicks "Capture Now" button in UI.
    It pushes a capture command to the device via CommandHub.
    """
    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Get command hub
    from cloud.api.server import get_command_hub
    command_hub = get_command_hub()

    # Generate trigger ID
    from datetime import datetime
    trigger_id = f"manual_{device_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

    # Publish capture command
    await command_hub.publish(device_id, {
        "cmd": "capture",
        "trigger_id": trigger_id,
        "type": "manual"
    })

    logger.info(f"[manual_trigger] Sent manual trigger {trigger_id} to device {device_id}")

    return {
        "trigger_id": trigger_id,
        "device_id": device_id,
        "status": "sent",
        "connected": command_hub.get_subscriber_count(device_id) > 0
    }


@router.get("/v1/devices/connected")
async def list_connected_devices():
    """
    List all devices currently connected to command stream.

    Useful for debugging and monitoring.
    """
    from cloud.api.server import get_command_hub
    command_hub = get_command_hub()

    connected = command_hub.get_connected_devices()

    return {
        "connected_devices": connected,
        "count": len(connected)
    }

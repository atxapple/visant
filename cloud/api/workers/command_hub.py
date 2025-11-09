"""
CommandHub - Pub/Sub system for pushing commands to devices via SSE.

This replaces the old TriggerHub and supports multiple command types:
- capture (scheduled or manual triggers)
- update_config (push config changes)
- ping (health check)
"""

import asyncio
import json
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)


class CommandHub:
    """
    In-memory pub/sub hub for device commands.

    Devices subscribe via SSE streams, cloud publishes commands.
    Each device has its own set of subscriber queues.
    """

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, device_id: str) -> asyncio.Queue:
        """
        Subscribe to commands for a specific device.

        Args:
            device_id: Device identifier

        Returns:
            Queue that will receive command dictionaries
        """
        async with self._lock:
            queue = asyncio.Queue()

            if device_id not in self._subscribers:
                self._subscribers[device_id] = set()

            self._subscribers[device_id].add(queue)

            logger.info(f"[CommandHub] Device {device_id} subscribed (total: {len(self._subscribers[device_id])})")

            return queue

    async def unsubscribe(self, device_id: str, queue: asyncio.Queue):
        """
        Unsubscribe from device commands.

        Args:
            device_id: Device identifier
            queue: Queue to remove
        """
        async with self._lock:
            if device_id in self._subscribers:
                self._subscribers[device_id].discard(queue)

                # Clean up empty device entries
                if not self._subscribers[device_id]:
                    del self._subscribers[device_id]

                logger.info(f"[CommandHub] Device {device_id} unsubscribed")

    async def publish(self, device_id: str, command: dict):
        """
        Publish a command to all subscribers of a device.

        Args:
            device_id: Device identifier
            command: Command dictionary to send

        Example commands:
            {"cmd": "capture", "trigger_id": "abc123", "type": "manual"}
            {"cmd": "update_config", "config": {...}}
        """
        async with self._lock:
            if device_id not in self._subscribers:
                logger.warning(f"[CommandHub] No subscribers for device {device_id}")
                return

            # Serialize once
            message = json.dumps(command)

            # Send to all subscribers
            for queue in self._subscribers[device_id]:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"[CommandHub] Failed to send command to device {device_id}: {e}")

            logger.info(f"[CommandHub] Published {command.get('cmd')} to device {device_id} ({len(self._subscribers[device_id])} subscribers)")

    async def broadcast(self, command: dict):
        """
        Broadcast a command to all connected devices.

        Args:
            command: Command dictionary to broadcast
        """
        async with self._lock:
            device_ids = list(self._subscribers.keys())

        for device_id in device_ids:
            await self.publish(device_id, command)

        logger.info(f"[CommandHub] Broadcasted {command.get('cmd')} to {len(device_ids)} devices")

    def get_subscriber_count(self, device_id: str) -> int:
        """Get number of active subscribers for a device."""
        return len(self._subscribers.get(device_id, set()))

    def get_connected_devices(self) -> list[str]:
        """Get list of device IDs with active subscribers."""
        return list(self._subscribers.keys())

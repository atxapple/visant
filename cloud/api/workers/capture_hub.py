"""
CaptureHub - Pub/Sub system for broadcasting capture events to web clients.

Multi-tenant architecture with org-level isolation:
- Web clients subscribe via SSE or WebSocket
- Cloud publishes events when captures are processed
- Subscription keys: "{org_id}:{device_id}" or "{org_id}:__all__"
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)


class CaptureHub:
    """
    In-memory pub/sub hub for capture events.

    Web clients subscribe to receive real-time capture notifications.
    Events are isolated by organization ID for multi-tenant security.
    """

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, org_id: str, device_id: Optional[str] = None) -> str:
        """
        Create subscription key with multi-tenant isolation.

        Args:
            org_id: Organization UUID
            device_id: Optional device ID (None means all devices in org)

        Returns:
            Subscription key: "{org_id}:{device_id}" or "{org_id}:__all__"
        """
        if device_id:
            return f"{org_id}:{device_id}"
        return f"{org_id}:__all__"

    async def subscribe(self, org_id: str, device_id: Optional[str] = None) -> tuple[str, asyncio.Queue]:
        """
        Subscribe to capture events for an organization/device.

        Args:
            org_id: Organization UUID
            device_id: Optional device ID (None = all devices in org)

        Returns:
            (subscription_key, queue) tuple where queue receives event dictionaries
        """
        key = self._make_key(org_id, device_id)

        async with self._lock:
            queue = asyncio.Queue()

            if key not in self._subscribers:
                self._subscribers[key] = set()

            self._subscribers[key].add(queue)

            logger.info(
                f"[CaptureHub] Subscribed to {key} "
                f"(total subscribers: {len(self._subscribers[key])})"
            )

            return key, queue

    async def unsubscribe(self, key: str, queue: asyncio.Queue):
        """
        Unsubscribe from capture events.

        Args:
            key: Subscription key returned by subscribe()
            queue: Queue to remove
        """
        async with self._lock:
            if key in self._subscribers:
                self._subscribers[key].discard(queue)

                # Clean up empty subscription entries
                if not self._subscribers[key]:
                    del self._subscribers[key]

                logger.info(f"[CaptureHub] Unsubscribed from {key}")

    async def publish(self, org_id: str, device_id: str, event: dict):
        """
        Publish capture event to all relevant subscribers.

        Events are sent to TWO subscriber groups:
        1. Device-specific: "{org_id}:{device_id}"
        2. Org-wide: "{org_id}:__all__"

        Args:
            org_id: Organization UUID
            device_id: Device ID that created the capture
            event: Event dictionary to send

        Example event:
            {
                "event": "new_capture",
                "capture_id": "abc123",
                "device_id": "laptop-01",
                "state": "abnormal",
                "score": 0.85,
                "captured_at": "2025-01-15T10:30:00Z"
            }
        """
        # Prepare subscription keys
        device_key = self._make_key(org_id, device_id)
        all_key = self._make_key(org_id, None)

        # Serialize once
        message = json.dumps(event)

        async with self._lock:
            keys_to_publish = []

            if device_key in self._subscribers:
                keys_to_publish.append((device_key, self._subscribers[device_key]))

            if all_key in self._subscribers:
                keys_to_publish.append((all_key, self._subscribers[all_key]))

            if not keys_to_publish:
                logger.debug(
                    f"[CaptureHub] No subscribers for org={org_id}, device={device_id}"
                )
                return

        # Send to all subscriber queues (outside lock to avoid blocking)
        total_sent = 0
        for key, queues in keys_to_publish:
            for queue in queues:
                try:
                    await queue.put(message)
                    total_sent += 1
                except Exception as e:
                    logger.error(
                        f"[CaptureHub] Failed to send event to {key}: {e}"
                    )

        logger.info(
            f"[CaptureHub] Published {event.get('event')} "
            f"to org={org_id}, device={device_id} "
            f"({total_sent} subscribers)"
        )

    def get_subscriber_count(self, org_id: str, device_id: Optional[str] = None) -> int:
        """Get number of active subscribers for org/device."""
        key = self._make_key(org_id, device_id)
        return len(self._subscribers.get(key, set()))

    def get_active_subscriptions(self) -> list[str]:
        """Get list of all active subscription keys."""
        return list(self._subscribers.keys())

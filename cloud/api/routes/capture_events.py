"""
Capture Event Streaming - Real-time notifications for web clients.

Provides SSE and WebSocket endpoints for broadcasting capture events
to the web dashboard with multi-tenant isolation.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from cloud.api.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/capture-events/stream")
async def capture_event_stream_sse(
    device_id: Optional[str] = Query(None, description="Filter by device ID (optional)"),
    current_user: dict = Depends(get_current_user)
):
    """
    SSE stream that pushes capture events to web clients.

    Events sent via this stream:
    - {"event": "new_capture", "capture_id": "...", "device_id": "...", "state": "..."}
    - {"event": "capture_updated", "capture_id": "...", ...}

    The web client should:
    1. Connect to this endpoint after login
    2. Listen for capture events continuously
    3. Update UI when events received
    4. Reconnect if connection drops
    """
    org_id = current_user["org_id"]

    # Get capture hub from app state
    from cloud.api.server import get_capture_hub
    capture_hub = get_capture_hub()

    # Subscribe to org's capture events (device-specific or all)
    key, queue = await capture_hub.subscribe(org_id, device_id)

    async def event_generator():
        """Generate SSE events from capture queue."""
        try:
            # Send initial connected event
            yield f'data: {json.dumps({"event": "connected", "org_id": org_id, "device_id": device_id})}\n\n'

            logger.info(
                f"[capture_events] User {current_user['email']} connected to SSE stream "
                f"(org={org_id}, device={device_id or 'all'})"
            )

            # Stream capture events
            while True:
                # Wait for event with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=60.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield f'data: {json.dumps({"event": "ping"})}\n\n'

        except asyncio.CancelledError:
            logger.info(
                f"[capture_events] SSE stream cancelled for user {current_user['email']}"
            )
        except Exception as e:
            logger.error(
                f"[capture_events] Error streaming to user {current_user['email']}: {e}"
            )
        finally:
            # Unsubscribe when connection closes
            await capture_hub.unsubscribe(key, queue)
            logger.info(
                f"[capture_events] User {current_user['email']} disconnected from SSE stream"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.websocket("/ws/capture-events")
async def capture_event_stream_ws(
    websocket: WebSocket,
    device_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time capture events.

    Alternative to SSE with bidirectional communication support.

    Messages sent to client:
    - {"event": "new_capture", "capture_id": "...", ...}
    - {"event": "capture_updated", ...}
    - {"event": "ping"}

    Messages from client:
    - {"cmd": "subscribe", "device_id": "laptop-01"}  (switch device filter)
    - {"cmd": "pong"}  (keepalive response)
    """
    await websocket.accept()

    # Extract JWT token from query or headers
    # For now, we'll accept token as query param or in first message
    token = websocket.query_params.get("token")

    if not token:
        # Wait for first message with auth token
        try:
            auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            token = auth_msg.get("token")
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"[ws_capture_events] No auth token received: {e}")
            await websocket.close(code=1008, reason="Authentication required")
            return

    # Validate token and get user info
    try:
        from cloud.api.auth.middleware import verify_jwt_token
        current_user = verify_jwt_token(token)
        org_id = current_user["org_id"]
    except Exception as e:
        logger.warning(f"[ws_capture_events] Invalid token: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Get capture hub
    from cloud.api.server import get_capture_hub
    capture_hub = get_capture_hub()

    # Subscribe to capture events
    key, queue = await capture_hub.subscribe(org_id, device_id)

    logger.info(
        f"[ws_capture_events] User {current_user['email']} connected "
        f"(org={org_id}, device={device_id or 'all'})"
    )

    # Send connected confirmation
    await websocket.send_json({
        "event": "connected",
        "org_id": org_id,
        "device_id": device_id
    })

    async def send_events():
        """Task to send capture events from queue to websocket."""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=60.0)
                    await websocket.send_text(message)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({"event": "ping"})
        except Exception as e:
            logger.error(f"[ws_capture_events] Error sending events: {e}")

    async def receive_commands():
        """Task to receive commands from websocket (e.g., device filter changes)."""
        nonlocal key, queue, device_id
        try:
            while True:
                data = await websocket.receive_json()
                cmd = data.get("cmd")

                if cmd == "pong":
                    # Keepalive response
                    continue
                elif cmd == "subscribe":
                    # Change device filter
                    new_device_id = data.get("device_id")

                    # Unsubscribe from old key
                    await capture_hub.unsubscribe(key, queue)

                    # Subscribe to new key
                    device_id = new_device_id
                    key, queue = await capture_hub.subscribe(org_id, device_id)

                    logger.info(
                        f"[ws_capture_events] User {current_user['email']} "
                        f"switched to device={device_id or 'all'}"
                    )

                    await websocket.send_json({
                        "event": "subscribed",
                        "device_id": device_id
                    })
        except WebSocketDisconnect:
            logger.info(f"[ws_capture_events] Client disconnected")
        except Exception as e:
            logger.error(f"[ws_capture_events] Error receiving commands: {e}")

    # Run both tasks concurrently
    try:
        await asyncio.gather(send_events(), receive_commands())
    finally:
        # Cleanup
        await capture_hub.unsubscribe(key, queue)
        logger.info(f"[ws_capture_events] User {current_user['email']} disconnected")

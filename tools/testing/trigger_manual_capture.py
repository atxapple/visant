"""Manually trigger a capture using webcam to test thumbnails."""
import cv2
import base64
import requests
from datetime import datetime, timezone
import time

def capture_and_upload(device_id="AJ73C", count=5):
    """Capture multiple images and upload them."""

    print(f"Initializing webcam...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Cannot open webcam")
        return

    print(f"Will capture {count} images...\n")

    for i in range(count):
        print(f"[{i+1}/{count}] Capturing frame...")

        # Capture frame
        ret, frame = cap.read()

        if not ret:
            print("  ERROR: Failed to capture frame")
            continue

        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_bytes = buffer.tobytes()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Upload capture
        upload_data = {
            "device_id": device_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "image_base64": image_base64,
            "trigger_label": f"manual_test_{i+1}"
        }

        response = requests.post("http://localhost:8000/v1/captures", json=upload_data, timeout=10)

        if response.status_code == 201:
            data = response.json()
            print(f"  OK Upload successful: {data['record_id']}")
            print(f"     Image: {len(image_bytes)} bytes | Thumbnail: {data['thumbnail_stored']}")
        else:
            print(f"  ERROR Upload failed: {response.status_code} - {response.text[:100]}")

        # Wait between captures
        if i < count - 1:
            time.sleep(2)

    cap.release()
    print(f"\nDone! {count} captures uploaded.")
    print(f"View in browser: http://localhost:8000/ui/camera/{device_id}")

if __name__ == "__main__":
    capture_and_upload(device_id="AJ73C", count=5)

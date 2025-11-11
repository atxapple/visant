"""Test webcam capture upload and thumbnail generation."""
import cv2
import base64
import requests
from datetime import datetime, timezone
import time

print("Initializing webcam...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open webcam")
    exit(1)

# Capture frame
ret, frame = cap.read()
cap.release()

if not ret:
    print("ERROR: Failed to capture frame")
    exit(1)

print(f"Captured frame: {frame.shape}")

# Encode to JPEG
ret, buffer = cv2.imencode('.jpg', frame)
image_bytes = buffer.tobytes()
image_base64 = base64.b64encode(image_bytes).decode('utf-8')

print(f"Image size: {len(image_bytes)} bytes")

# Upload capture
upload_data = {
    "device_id": "AJ73C",
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "image_base64": image_base64,
    "trigger_label": "test_thumbnail_feature"
}

print("\nUploading capture to http://localhost:8000/v1/captures...")
response = requests.post("http://localhost:8000/v1/captures", json=upload_data)

print(f"Upload response: {response.status_code}")

if response.status_code == 201:
    data = response.json()
    record_id = data["record_id"]
    print(f"✓ Upload successful!")
    print(f"  Record ID: {record_id}")
    print(f"  Image stored: {data['image_stored']}")
    print(f"  Thumbnail stored: {data['thumbnail_stored']}")

    # Wait for file write
    time.sleep(1)

    # Test thumbnail endpoint
    print(f"\n Testing thumbnail endpoint...")
    thumb_url = f"http://localhost:8000/ui/captures/{record_id}/thumbnail"
    thumb_response = requests.get(thumb_url)

    print(f"Thumbnail response: {thumb_response.status_code}")

    if thumb_response.status_code == 200:
        print(f"✓ Thumbnail generated successfully!")
        print(f"  Content-Type: {thumb_response.headers.get('Content-Type')}")
        print(f"  Content-Length: {len(thumb_response.content)} bytes")
        print(f"  Cache-Control: {thumb_response.headers.get('Cache-Control')}")
        print(f"  Compression: {100 - (len(thumb_response.content) / len(image_bytes) * 100):.1f}%")
        print(f"\n  Original: {len(image_bytes):,} bytes")
        print(f"  Thumbnail: {len(thumb_response.content):,} bytes")
        print(f"\n✅ THUMBNAIL FEATURE WORKING! Load time improvement: {len(image_bytes) / len(thumb_response.content):.1f}x faster")
        print(f"\nView in browser: http://localhost:8000/ui/camera/AJ73C")
    else:
        print(f"✗ Thumbnail failed: {thumb_response.text}")
else:
    print(f"✗ Upload failed: {response.text}")

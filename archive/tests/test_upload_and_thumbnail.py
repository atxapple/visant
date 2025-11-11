"""Test upload a capture and then retrieve its thumbnail."""
import base64
import requests
from datetime import datetime, timezone
from pathlib import Path
import time

# Read an existing image
image_path = Path("uploads/c472e36a-a36a-4723-a50b-34483e8672c6/devices/TEST3/captures/TEST3_20251109_042031_f7dd9cb9.jpg")
image_bytes = image_path.read_bytes()
image_base64 = base64.b64encode(image_bytes).decode('utf-8')

print(f"Image loaded: {len(image_bytes)} bytes")

# Upload capture
upload_data = {
    "device_id": "TEST3",
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "image_base64": image_base64,
    "trigger_label": "test_thumbnail_endpoint"
}

print("\nUploading capture...")
response = requests.post("http://localhost:8000/v1/captures", json=upload_data)
print(f"Upload status: {response.status_code}")

if response.status_code == 201:
    data = response.json()
    record_id = data["record_id"]
    print(f"Record ID: {record_id}")
    print(f"Evaluation status: {data['evaluation_status']}")
    print(f"Image stored: {data['image_stored']}")
    print(f"Thumbnail stored: {data['thumbnail_stored']}")

    # Wait a moment for file to be written
    time.sleep(1)

    # Test thumbnail endpoint
    print("\nTesting thumbnail endpoint...")
    thumb_url = f"http://localhost:8000/ui/captures/{record_id}/thumbnail"
    thumb_response = requests.get(thumb_url)

    print(f"Thumbnail status: {thumb_response.status_code}")
    if thumb_response.status_code == 200:
        print(f"Content-Type: {thumb_response.headers.get('Content-Type')}")
        print(f"Content-Length: {len(thumb_response.content)} bytes")
        print(f"Cache-Control: {thumb_response.headers.get('Cache-Control')}")
        print(f"\n✓ SUCCESS - Thumbnail generated on-demand!")
        print(f"  Original image: {len(image_bytes)} bytes")
        print(f"  Thumbnail: {len(thumb_response.content)} bytes")
        print(f"  Compression: {100 - (len(thumb_response.content) / len(image_bytes) * 100):.1f}%")

        # Save thumbnail for inspection
        thumb_path = Path("test_generated_thumbnail.jpg")
        thumb_path.write_bytes(thumb_response.content)
        print(f"  Saved to: {thumb_path}")
    else:
        print(f"Error: {thumb_response.text}")
else:
    print(f"Upload failed: {response.text}")

"""Test the UI endpoint performance with local SQLite database."""
import requests
import time

device_id = "TEST3"

print(f"Testing UI performance for device: {device_id}\n")

# Test 1: UI captures endpoint (no auth required)
print("Test 1: UI captures endpoint")
url = f"http://localhost:8000/ui/captures?device_id={device_id}&limit=20"
print(f"  URL: {url}")

start = time.time()
response = requests.get(url)
elapsed = time.time() - start

print(f"  Status: {response.status_code}")
print(f"  Time: {elapsed:.3f}s")
if response.status_code == 200:
    data = response.json()
    print(f"  Captures returned: {len(data)}")
    print()

    # Test 2: Load first thumbnail
    if len(data) > 0:
        print("Test 2: Loading first thumbnail")
        capture = data[0]
        record_id = capture.get('record_id')
        thumb_url = f"http://localhost:8000/ui/captures/{record_id}/thumbnail"
        print(f"  Thumbnail URL: {thumb_url}")

        start = time.time()
        thumb_response = requests.get(thumb_url)
        elapsed = time.time() - start

        print(f"  Status: {thumb_response.status_code}")
        if thumb_response.status_code == 200:
            print(f"  Size: {len(thumb_response.content):,} bytes")
        print(f"  Time: {elapsed:.3f}s")

print("\n" + "="*60)
print("Expected results with local SQLite:")
print("  - Database query: < 0.1s (was 1-2s with Railway)")
print("  - Thumbnail generation + load: < 0.3s (first time)")
print("  - Thumbnail load (cached): < 0.05s (subsequent loads)")
print("="*60)

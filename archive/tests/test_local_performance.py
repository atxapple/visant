"""Test the performance with local SQLite database."""
import requests
import time

device_id = "TEST3"
url = f"http://localhost:8000/v1/devices/{device_id}/captures"

print(f"Testing capture list performance for device: {device_id}")
print(f"URL: {url}\n")

# Test database query speed
print("Test 1: Capture list API (database query)")
start = time.time()
response = requests.get(url, params={"limit": 20})
elapsed = time.time() - start

print(f"  Status: {response.status_code}")
print(f"  Time: {elapsed:.3f}s")
if response.status_code == 200:
    data = response.json()
    print(f"  Captures returned: {len(data)}")
    print()

# Test 2: Load first thumbnail
if response.status_code == 200 and len(data) > 0:
    print("Test 2: Loading first thumbnail")
    capture = data[0]
    if capture.get('thumbnail_url'):
        thumb_url = f"http://localhost:8000{capture['thumbnail_url']}"
        print(f"  Thumbnail URL: {thumb_url}")

        start = time.time()
        thumb_response = requests.get(thumb_url)
        elapsed = time.time() - start

        print(f"  Status: {thumb_response.status_code}")
        print(f"  Size: {len(thumb_response.content)} bytes")
        print(f"  Time: {elapsed:.3f}s")

print("\n" + "="*60)
print("Expected results with local SQLite:")
print("  - Database query: < 0.1s (was 1-2s with Railway)")
print("  - Thumbnail load: < 0.2s (on-demand generation + local file)")
print("="*60)

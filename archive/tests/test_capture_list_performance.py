"""Test the performance of the capture list API endpoint."""
import requests
import time

def test_capture_list_performance():
    """Time the capture list API endpoint."""

    device_id = "AJ73C"
    url = f"http://localhost:8000/v1/devices/{device_id}/captures"

    print(f"Testing capture list performance for device: {device_id}")
    print(f"URL: {url}\n")

    # Test 1: First request (cold)
    print("Test 1: First request (cold cache)")
    start = time.time()
    response = requests.get(url, params={"limit": 20})
    elapsed = time.time() - start

    print(f"  Status: {response.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    if response.status_code == 200:
        data = response.json()
        print(f"  Captures returned: {len(data)}")
        print()

    # Test 2: Second request (should be faster if caching works)
    print("Test 2: Second request")
    start = time.time()
    response = requests.get(url, params={"limit": 20})
    elapsed = time.time() - start

    print(f"  Status: {response.status_code}")
    print(f"  Time: {elapsed:.3f}s")
    if response.status_code == 200:
        data = response.json()
        print(f"  Captures returned: {len(data)}")

    print("\n" + "="*60)

    # Test 3: Time to load first 3 thumbnails
    if response.status_code == 200 and len(data) > 0:
        print("\nTest 3: Loading first 3 thumbnails")
        for i, capture in enumerate(data[:3]):
            if capture.get('thumbnail_url'):
                thumb_url = f"http://localhost:8000{capture['thumbnail_url']}"
                print(f"\n  Thumbnail {i+1}: {capture['record_id']}")

                start = time.time()
                thumb_response = requests.get(thumb_url)
                elapsed = time.time() - start

                print(f"    Status: {thumb_response.status_code}")
                print(f"    Size: {len(thumb_response.content)} bytes")
                print(f"    Time: {elapsed:.3f}s")

if __name__ == "__main__":
    test_capture_list_performance()

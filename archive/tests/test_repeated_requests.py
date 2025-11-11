"""Test repeated requests to check for connection overhead."""
import requests
import time

device_id = "TEST3"
url = f"http://localhost:8000/ui/captures?device_id={device_id}&limit=20"

print("Testing repeated requests to identify connection overhead\n")

for i in range(5):
    start = time.time()
    response = requests.get(url)
    elapsed = time.time() - start

    print(f"Request {i+1}: {response.status_code} - {elapsed:.3f}s")

print("\nIf first request is slow but subsequent requests are fast,")
print("it indicates connection establishment overhead.")

"""
Test script for Cloud AI evaluation flow.

This tests:
1. Upload image with base64
2. Get immediate response with status="pending"
3. Poll status endpoint until evaluation completes
4. Verify state/score/reason are populated by Cloud AI
"""

import requests
import time
import base64
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
DEVICE_API_KEY = "RPNnepNUCCeDP-xl6ltfPO0C9WoNNjoLITvUoe9eoTY"  # Alice's camera-01
DEVICE_ID = "camera-01"

# Headers with device API key authentication
headers = {
    "Authorization": f"Bearer {DEVICE_API_KEY}",
    "Content-Type": "application/json"
}

# Create a simple 1x1 red pixel PNG for testing
# This is a valid PNG image in base64
test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

print("=" * 60)
print("CLOUD AI EVALUATION TEST")
print("=" * 60)

# Step 1: Upload capture with image
print("\n[STEP 1] Uploading capture with image...")
upload_payload = {
    "device_id": DEVICE_ID,
    "captured_at": datetime.now().isoformat() + "Z",
    "image_base64": test_image_base64,
    "trigger_label": "test_cloud_ai",
    "metadata": {
        "test": True,
        "description": "Testing Cloud AI evaluation"
    }
}

response = requests.post(
    f"{API_URL}/v1/captures",
    headers=headers,
    json=upload_payload
)

print(f"Status Code: {response.status_code}")

if response.status_code != 201:
    print(f"ERROR: Upload failed!")
    print(f"Response: {response.text}")
    exit(1)

result = response.json()
record_id = result["record_id"]

print(f"[OK] Upload successful!")
print(f"  Record ID: {record_id}")
print(f"  Evaluation Status: {result['evaluation_status']}")
print(f"  State: {result['state']}")
print(f"  Score: {result['score']}")
print(f"  Reason: {result['reason']}")

if result["evaluation_status"] != "pending":
    print(f"WARNING: Expected status='pending', got '{result['evaluation_status']}'")

# Step 2: Poll status endpoint until evaluation completes
print(f"\n[STEP 2] Polling status endpoint...")
print(f"Waiting for Cloud AI evaluation to complete...")

max_attempts = 30  # 30 seconds max
attempt = 0

while attempt < max_attempts:
    attempt += 1
    time.sleep(1)  # Poll every 1 second

    response = requests.get(
        f"{API_URL}/v1/captures/{record_id}/status",
        headers=headers
    )

    if response.status_code != 200:
        print(f"ERROR: Status check failed!")
        print(f"Response: {response.text}")
        exit(1)

    status = response.json()
    eval_status = status["evaluation_status"]

    print(f"  Attempt {attempt}: status={eval_status}", end="")

    if eval_status == "completed":
        print(" [OK] DONE!")
        print(f"\n[STEP 3] Evaluation Results:")
        print(f"  State: {status['state']}")
        print(f"  Score: {status['score']}")
        print(f"  Reason: {status['reason']}")
        print(f"  Evaluated At: {status['evaluated_at']}")

        # Validate results
        if status['state'] is None:
            print(f"\n[FAIL] State is still null after completion!")
            exit(1)

        if status['score'] is None:
            print(f"\n[FAIL] Score is still null after completion!")
            exit(1)

        print(f"\n{'=' * 60}")
        print(f"[OK] CLOUD AI TEST PASSED!")
        print(f"{'=' * 60}")
        print(f"\nSummary:")
        print(f"  - Image uploaded successfully")
        print(f"  - Background AI evaluation triggered")
        print(f"  - Evaluation completed in {attempt} seconds")
        print(f"  - Result: {status['state']} (score: {status['score']:.2f})")
        break

    elif eval_status == "failed":
        print(" [FAILED]")
        print(f"\n[FAIL] EVALUATION FAILED!")
        print(f"  Reason: {status['reason']}")
        exit(1)

    else:
        print(f" (waiting...)")

else:
    print(f"\n[FAIL] TIMEOUT: Evaluation did not complete within {max_attempts} seconds")
    print(f"  Last status: {eval_status}")
    exit(1)

# Step 4: Verify capture appears in list
print(f"\n[STEP 4] Verifying capture in list...")
response = requests.get(
    f"{API_URL}/v1/captures",
    headers=headers
)

if response.status_code == 200:
    captures = response.json()["captures"]
    found = any(c["record_id"] == record_id for c in captures)

    if found:
        print(f"[OK] Capture found in list")
    else:
        print(f"[FAIL] Capture NOT found in list")
        exit(1)
else:
    print(f"WARNING: Could not verify list (status: {response.status_code})")

print(f"\n{'=' * 60}")
print(f"ALL TESTS PASSED!")
print(f"{'=' * 60}")

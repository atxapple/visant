"""
Laptop Camera Test - Device ID Authentication

Tests the device registration and upload flow using your laptop webcam.

Requirements:
1. Start test server: .venv\Scripts\python test_auth_server.py
2. Login to dashboard: http://localhost:8000
3. Activate a device (e.g., TEST2) with code "DEV2025"
4. Update DEVICE_ID below to match your activated device
5. Run this script: .venv\Scripts\python laptop_camera_test.py

No API key needed - device authentication is by device_id only!
"""

import requests
import base64
import time
from datetime import datetime
import cv2
import sys

# ===== CONFIGURATION =====
API_URL = "http://localhost:8000"
DEVICE_ID = "TEST2"  # Change this to your activated device
# =========================

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def capture_from_webcam():
    """Capture an image from the laptop webcam."""
    print("\n[STEP 1] Capturing image from webcam...")

    cap = cv2.VideoCapture(0)  # 0 = default webcam

    if not cap.isOpened():
        print("[ERROR] Could not open webcam")
        print("  Make sure:")
        print("  - Webcam is connected")
        print("  - No other application is using it")
        print("  - Webcam permissions are granted")
        return None

    # Let camera warm up
    print("[INFO] Warming up camera...")
    for i in range(5):
        ret, frame = cap.read()
        time.sleep(0.1)

    # Capture frame
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[ERROR] Could not capture frame from webcam")
        return None

    print(f"[OK] Captured image: {frame.shape[1]}x{frame.shape[0]} pixels")

    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    image_bytes = buffer.tobytes()

    # Encode to base64
    image_base64 = base64.b64encode(image_bytes).decode('ascii')
    print(f"[OK] Encoded to base64: {len(image_base64)} characters ({len(image_bytes)} bytes)")

    return image_base64

def upload_capture(device_id, image_base64):
    """Upload capture to cloud - NO API KEY REQUIRED."""
    print("\n[STEP 2] Uploading capture to cloud...")
    print(f"[INFO] Device ID: {device_id}")
    print(f"[INFO] Image size: {len(image_base64)} characters")
    print("[INFO] Authentication: Device ID only (no API key)")

    # No Authorization header needed!
    response = requests.post(
        f"{API_URL}/v1/captures",
        json={
            "device_id": device_id,
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "image_base64": image_base64,
            "trigger_label": "laptop_webcam_test",
            "metadata": {
                "test_type": "laptop_camera",
                "source": "opencv_webcam"
            }
        }
    )

    if response.status_code != 201:
        print(f"[ERROR] Upload failed with status {response.status_code}")
        print(f"[ERROR] Response: {response.text}")
        return None

    result = response.json()
    record_id = result["record_id"]

    print(f"[OK] Upload successful!")
    print(f"  Record ID: {record_id}")
    print(f"  Evaluation Status: {result['evaluation_status']}")
    print(f"  Device ID: {result['device_id']}")

    return record_id

def poll_for_evaluation(record_id, device_id, max_attempts=30):
    """Poll for Cloud AI evaluation results - NO API KEY REQUIRED."""
    print("\n[STEP 3] Polling for Cloud AI evaluation...")
    print(f"[INFO] Will poll up to {max_attempts} times (1 second intervals)")

    for attempt in range(1, max_attempts + 1):
        response = requests.get(
            f"{API_URL}/v1/captures/{record_id}",
            params={"device_id": device_id}  # Validate device ownership
        )

        if response.status_code != 200:
            print(f"[ERROR] Poll failed with status {response.status_code}")
            return None

        status = response.json()
        eval_status = status["evaluation_status"]

        if eval_status == "completed":
            print(f"\n[OK] Evaluation completed on attempt {attempt}")
            return status
        elif eval_status == "failed":
            print(f"\n[ERROR] Evaluation failed!")
            print(f"  Reason: {status.get('reason', 'Unknown')}")
            return None

        # Show progress
        print(f"  Attempt {attempt}/{max_attempts}: {eval_status}...", end="\r")
        time.sleep(1)

    print(f"\n[ERROR] Evaluation timed out after {max_attempts} seconds")
    print(f"  Status still: {eval_status}")
    return None

def main():
    print_section("LAPTOP CAMERA TEST - DEVICE ID AUTHENTICATION")

    print(f"\nConfiguration:")
    print(f"  API URL: {API_URL}")
    print(f"  Device ID: {DEVICE_ID}")
    print(f"  Authentication: Device ID only (no API key needed)")

    # Step 1: Capture from webcam
    image_base64 = capture_from_webcam()
    if not image_base64:
        print("\n[FAIL] Could not capture from webcam")
        return False

    # Step 2: Upload to cloud
    record_id = upload_capture(DEVICE_ID, image_base64)
    if not record_id:
        print("\n[FAIL] Could not upload capture")
        return False

    # Step 3: Poll for evaluation
    result = poll_for_evaluation(record_id, DEVICE_ID)
    if not result:
        print("\n[FAIL] Could not get evaluation results")
        return False

    # Step 4: Display results
    print_section("CLOUD AI EVALUATION RESULTS")

    print(f"\nRecord ID: {result['record_id']}")
    print(f"Device ID: {result['device_id']}")
    print(f"Captured At: {result['captured_at']}")
    print(f"Evaluated At: {result['evaluated_at']}")
    print(f"\nEvaluation Results:")
    print(f"  State: {result['state']}")
    print(f"  Score: {result['score']}")
    print(f"  Reason: {result['reason']}")

    print_section("TEST COMPLETE - SUCCESS!")

    print("\nWhat was tested:")
    print("  [OK] Webcam capture using OpenCV")
    print("  [OK] Image encoding to base64")
    print("  [OK] Device authentication (device_id only, no API key)")
    print("  [OK] Capture upload to Cloud API")
    print("  [OK] Cloud AI async evaluation")
    print("  [OK] Result polling")

    print("\nThis demonstrates the complete camera registration and upload flow!")
    print("No API key was required - only the device_id.")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server")
        print("  Make sure test_auth_server.py is running on port 8000")
        print("  Start with: .venv\\Scripts\\python test_auth_server.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

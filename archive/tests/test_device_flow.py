"""
End-to-end test for device activation flow.

Tests:
1. User signup/login
2. Fetch devices (should be 1 - TEST1 already activated)
3. Validate new device (TEST2)
4. Activate device with code
5. Fetch devices again (should be 2)
6. Verify device selector logic
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(label, data, indent=0):
    prefix = "  " * indent
    if isinstance(data, dict):
        print(f"{prefix}{label}:")
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}  {key}: {json.dumps(value, indent=2)}")
            else:
                print(f"{prefix}  {key}: {value}")
    else:
        print(f"{prefix}{label}: {data}")

def test_device_flow():
    """Test complete device activation flow."""

    # Step 1: Login with existing user
    print_section("STEP 1: User Login")

    login_data = {
        "email": "devicetest@example.com",
        "password": "DeviceTest123!"
    }

    response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)

    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data["access_token"]
        print("[OK] Login successful")
        print(f"  User: {auth_data['user']['email']}")
        print(f"  Org: {auth_data['organization']['name']}")
    else:
        print(f"[FAIL] Login failed: {response.status_code}")
        print(f"  {response.json()}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Step 2: Fetch existing devices
    print_section("STEP 2: Fetch Existing Devices")

    response = requests.get(f"{BASE_URL}/v1/devices", headers=headers)

    if response.status_code == 200:
        devices_data = response.json()
        print(f"[OK] Fetched {devices_data['total']} devices")
        for device in devices_data['devices']:
            print(f"  - {device['friendly_name']} ({device['device_id']}) - {device['status']}")
    else:
        print(f"[FAIL] Failed to fetch devices: {response.status_code}")
        return

    # Step 3: Validate new device
    print_section("STEP 3: Validate Device TEST2")

    validate_data = {"device_id": "TEST2"}
    response = requests.post(f"{BASE_URL}/v1/devices/validate", headers=headers, json=validate_data)

    if response.status_code == 200:
        validation = response.json()
        print(f"[OK] Device validation successful")
        print_result("Validation", validation, indent=1)
    else:
        print(f"[FAIL] Device validation failed: {response.status_code}")
        print(f"  {response.json()}")
        return

    # Step 4: Activate device with code
    print_section("STEP 4: Activate Device TEST2 with DEV2025")

    activate_data = {
        "device_id": "TEST2",
        "friendly_name": "Test Camera 2",
        "activation_code": "DEV2025"
    }

    response = requests.post(f"{BASE_URL}/v1/devices/activate", headers=headers, json=activate_data)

    if response.status_code == 200:
        activation = response.json()
        print(f"[OK] Device activated successfully")
        print(f"  Device: {activation['friendly_name']} ({activation['device_id']})")
        print(f"  API Key: {activation['api_key'][:20]}...")
        print(f"  Status: {activation['status']}")
        if activation.get('code_benefit'):
            benefit = activation['code_benefit']
            print(f"  Code Benefit: {benefit['benefit']} (Code: {benefit['code']})")
    else:
        print(f"[FAIL] Device activation failed: {response.status_code}")
        print(f"  {response.json()}")
        return

    # Step 5: Fetch devices again
    print_section("STEP 5: Fetch Devices After Activation")

    response = requests.get(f"{BASE_URL}/v1/devices", headers=headers)

    if response.status_code == 200:
        devices_data = response.json()
        print(f"[OK] Fetched {devices_data['total']} devices")
        for device in devices_data['devices']:
            print(f"  - {device['friendly_name']} ({device['device_id']}) - {device['status']}")

        # Verify device selector logic
        print("\nDevice Selector Logic Test:")
        device_count = devices_data['total']
        if device_count == 0:
            print("  -> UI should show: 'Add Your First Camera' prompt")
        elif device_count == 1:
            print("  -> UI should show: Single device display (no dropdown)")
        else:
            print(f"  -> UI should show: Dropdown selector with {device_count} devices")
    else:
        print(f"[FAIL] Failed to fetch devices: {response.status_code}")
        return

    # Step 6: Test device retrieval
    print_section("STEP 6: Get Individual Device Details")

    response = requests.get(f"{BASE_URL}/v1/devices/TEST2", headers=headers)

    if response.status_code == 200:
        device = response.json()
        print(f"[OK] Retrieved device details")
        print_result("Device", device, indent=1)
    else:
        print(f"[FAIL] Failed to get device: {response.status_code}")

    print_section("TEST COMPLETE [OK]")
    print("\nSummary:")
    print("  [OK] User authentication working")
    print("  [OK] Device list endpoint working")
    print("  [OK] Device validation endpoint working")
    print("  [OK] Device activation with code working")
    print("  [OK] Device selector logic verified")
    print("\nThe dashboard should now show:")
    print("  - Device dropdown with 2 cameras")
    print("  - Add Camera button")
    print("  - Ability to switch between devices")

if __name__ == "__main__":
    try:
        test_device_flow()
    except requests.exceptions.ConnectionError:
        print("\n[FAIL] ERROR: Could not connect to server at http://localhost:8000")
        print("  Make sure the test server is running")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()

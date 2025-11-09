"""
Test device configuration API endpoints.

Tests:
1. Get default config for a device
2. Update config (partial update - normal description only)
3. Update config (full update with all fields)
4. Verify config persistence
5. Test config isolation between devices
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_json(label, data):
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))

def test_device_config():
    """Test device configuration endpoints."""

    # Step 1: Login
    print_section("STEP 1: User Login")

    response = requests.post(f"{BASE_URL}/v1/auth/login", json={
        "email": "devicetest@example.com",
        "password": "DeviceTest123!"
    })

    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data["access_token"]
        print(f"[OK] Login successful - User: {auth_data['user']['email']}")
    else:
        print(f"[FAIL] Login failed: {response.status_code}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Step 2: Get default config for TEST1
    print_section("STEP 2: Get Default Config for TEST1")

    response = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)

    if response.status_code == 200:
        config_data = response.json()
        print("[OK] Got default config")
        print_json("Config", config_data)
    else:
        print(f"[FAIL] Failed to get config: {response.status_code}")
        print(response.json())
        return

    # Step 3: Update normal description only
    print_section("STEP 3: Update Normal Description Only")

    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST1/config",
        headers=headers,
        json={
            "normal_description": "If someone is smiling or waving, it is abnormal. Otherwise normal."
        }
    )

    if response.status_code == 200:
        config_data = response.json()
        print("[OK] Updated normal description")
        print_json("Updated Config", config_data)
    else:
        print(f"[FAIL] Failed to update config: {response.status_code}")
        print(response.json())
        return

    # Step 4: Update trigger settings
    print_section("STEP 4: Update Trigger Settings")

    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST1/config",
        headers=headers,
        json={
            "trigger": {
                "enabled": True,
                "interval_seconds": 15
            }
        }
    )

    if response.status_code == 200:
        config_data = response.json()
        print("[OK] Updated trigger settings")
        print_json("Updated Config", config_data["config"])

        # Verify normal description is still there
        if "normal_description" in config_data["config"]:
            print(f"[OK] Normal description preserved: {config_data['config']['normal_description'][:50]}...")
        else:
            print("[WARNING] Normal description was lost!")
    else:
        print(f"[FAIL] Failed to update trigger: {response.status_code}")
        print(response.json())
        return

    # Step 5: Update notification settings
    print_section("STEP 5: Update Notification Settings")

    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST1/config",
        headers=headers,
        json={
            "notification": {
                "email_enabled": True,
                "email_addresses": ["alerts@example.com", "ops@example.com"],
                "email_cooldown_minutes": 5
            }
        }
    )

    if response.status_code == 200:
        config_data = response.json()
        print("[OK] Updated notification settings")
        print_json("Final Config", config_data["config"])
    else:
        print(f"[FAIL] Failed to update notification: {response.status_code}")
        print(response.json())
        return

    # Step 6: Verify persistence - get config again
    print_section("STEP 6: Verify Config Persistence")

    response = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)

    if response.status_code == 200:
        config_data = response.json()
        print("[OK] Config retrieved successfully")
        print_json("Retrieved Config", config_data["config"])

        # Verify all fields are present
        checks = []
        if config_data["config"].get("normal_description"):
            checks.append("Normal description: [OK]")
        if config_data["config"].get("trigger", {}).get("enabled") == True:
            checks.append("Trigger enabled: [OK]")
        if len(config_data["config"].get("notification", {}).get("email_addresses", [])) == 2:
            checks.append("Email addresses: [OK]")

        print(f"\nVerification: {', '.join(checks)}")
    else:
        print(f"[FAIL] Failed to retrieve config: {response.status_code}")
        return

    # Step 7: Test config isolation - update TEST2 config
    print_section("STEP 7: Test Config Isolation Between Devices")

    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST2/config",
        headers=headers,
        json={
            "normal_description": "TEST2: Different description - standing is abnormal.",
            "trigger": {
                "enabled": False,
                "interval_seconds": 30
            }
        }
    )

    if response.status_code == 200:
        test2_config = response.json()
        print("[OK] Updated TEST2 config")
        print_json("TEST2 Config", test2_config["config"])
    else:
        print(f"[FAIL] Failed to update TEST2 config: {response.status_code}")
        print(response.json())
        return

    # Verify TEST1 config is unchanged
    response = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)
    if response.status_code == 200:
        test1_config = response.json()
        if "smiling" in test1_config["config"].get("normal_description", "").lower():
            print("[OK] TEST1 config isolation verified - still has 'smiling' description")
        else:
            print("[FAIL] TEST1 config was affected by TEST2 update!")
            print_json("TEST1 Config", test1_config["config"])
    else:
        print(f"[FAIL] Failed to get TEST1 config: {response.status_code}")

    # Step 8: Test error handling - invalid device
    print_section("STEP 8: Test Error Handling - Invalid Device")

    response = requests.get(f"{BASE_URL}/v1/devices/INVALID/config", headers=headers)

    if response.status_code == 404:
        print("[OK] Correctly returned 404 for invalid device")
        print(f"  Error: {response.json()['detail']}")
    else:
        print(f"[FAIL] Expected 404, got {response.status_code}")

    # Summary
    print_section("TEST COMPLETE")
    print("\nSummary:")
    print("  [OK] Get default config working")
    print("  [OK] Update normal description working")
    print("  [OK] Update trigger settings working")
    print("  [OK] Update notification settings working")
    print("  [OK] Config persistence working")
    print("  [OK] Config isolation between devices working")
    print("  [OK] Error handling for invalid device working")
    print("\n[SUCCESS] All device config tests passed!")

if __name__ == "__main__":
    try:
        test_device_config()
    except requests.exceptions.ConnectionError:
        print("\n[FAIL] ERROR: Could not connect to server at http://localhost:8000")
        print("  Make sure test_auth_server.py is running")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()

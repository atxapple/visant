"""
Complete Week 3 Testing: Per-Device Configuration

Comprehensive end-to-end tests for all Week 3 deliverables:
- Day 3: Trigger configuration per device
- Day 4: Notification settings per device
- Day 5: Config persistence, device switching, data isolation
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_week3_complete():
    """Complete Week 3 testing suite."""

    # Step 1: Login
    print_section("STEP 1: Authentication")

    response = requests.post(f"{BASE_URL}/v1/auth/login", json={
        "email": "devicetest@example.com",
        "password": "DeviceTest123!"
    })

    if response.status_code == 200:
        token = response.json()["access_token"]
        print("[OK] Login successful")
    else:
        print(f"[FAIL] Login failed: {response.status_code}")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Step 2: Set up TEST1 with specific config
    print_section("DAY 3 TEST: Per-Device Trigger Configuration")

    print("\n[TEST] Set TEST1 trigger: enabled=true, interval=20")
    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST1/config",
        headers=headers,
        json={
            "normal_description": "TEST1: Smiling or waving is abnormal",
            "trigger": {
                "enabled": True,
                "interval_seconds": 20,
                "digital_input_enabled": False
            }
        }
    )

    if response.status_code == 200:
        print("[OK] TEST1 config saved")
    else:
        print(f"[FAIL] Failed to save TEST1 config: {response.status_code}")
        return False

    # Step 3: Set up TEST2 with different trigger config
    print("\n[TEST] Set TEST2 trigger: enabled=false, interval=30")
    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST2/config",
        headers=headers,
        json={
            "normal_description": "TEST2: Standing is abnormal",
            "trigger": {
                "enabled": False,
                "interval_seconds": 30,
                "digital_input_enabled": False
            }
        }
    )

    if response.status_code == 200:
        print("[OK] TEST2 config saved")
    else:
        print(f"[FAIL] Failed to save TEST2 config: {response.status_code}")
        return False

    # Step 4: Verify TEST1 trigger config persists
    print("\n[TEST] Verify TEST1 trigger config persists")
    response = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)

    if response.status_code == 200:
        config = response.json()["config"]
        if config["trigger"]["enabled"] == True and config["trigger"]["interval_seconds"] == 20:
            print("[OK] TEST1 trigger config correct: enabled=True, interval=20")
        else:
            print(f"[FAIL] TEST1 trigger config wrong: {config['trigger']}")
            return False
    else:
        print(f"[FAIL] Failed to get TEST1 config: {response.status_code}")
        return False

    # Step 5: Verify TEST2 trigger config is different
    print("\n[TEST] Verify TEST2 trigger config is different from TEST1")
    response = requests.get(f"{BASE_URL}/v1/devices/TEST2/config", headers=headers)

    if response.status_code == 200:
        config = response.json()["config"]
        if config["trigger"]["enabled"] == False and config["trigger"]["interval_seconds"] == 30:
            print("[OK] TEST2 trigger config correct: enabled=False, interval=30")
            print("[OK] Trigger configs are properly isolated per device")
        else:
            print(f"[FAIL] TEST2 trigger config wrong: {config['trigger']}")
            return False
    else:
        print(f"[FAIL] Failed to get TEST2 config: {response.status_code}")
        return False

    # Step 6: Day 4 - Notification settings per device
    print_section("DAY 4 TEST: Per-Device Notification Settings")

    print("\n[TEST] Set TEST1 notification: emails=['alert1@example.com'], cooldown=5")
    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST1/config",
        headers=headers,
        json={
            "notification": {
                "email_enabled": True,
                "email_addresses": ["alert1@example.com", "ops1@example.com"],
                "email_cooldown_minutes": 5,
                "digital_output_enabled": False
            }
        }
    )

    if response.status_code == 200:
        print("[OK] TEST1 notification config saved")
    else:
        print(f"[FAIL] Failed to save TEST1 notification: {response.status_code}")
        return False

    print("\n[TEST] Set TEST2 notification: emails=['alert2@example.com'], cooldown=15")
    response = requests.put(
        f"{BASE_URL}/v1/devices/TEST2/config",
        headers=headers,
        json={
            "notification": {
                "email_enabled": True,
                "email_addresses": ["alert2@example.com", "ops2@example.com"],
                "email_cooldown_minutes": 15,
                "digital_output_enabled": False
            }
        }
    )

    if response.status_code == 200:
        print("[OK] TEST2 notification config saved")
    else:
        print(f"[FAIL] Failed to save TEST2 notification: {response.status_code}")
        return False

    # Step 7: Verify notification configs are per-device
    print("\n[TEST] Verify notification configs are isolated per device")

    response1 = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)
    response2 = requests.get(f"{BASE_URL}/v1/devices/TEST2/config", headers=headers)

    if response1.status_code == 200 and response2.status_code == 200:
        config1 = response1.json()["config"]["notification"]
        config2 = response2.json()["config"]["notification"]

        if ("alert1@example.com" in config1["email_addresses"] and
            config1["email_cooldown_minutes"] == 5):
            print("[OK] TEST1 notification config correct")
        else:
            print(f"[FAIL] TEST1 notification config wrong: {config1}")
            return False

        if ("alert2@example.com" in config2["email_addresses"] and
            config2["email_cooldown_minutes"] == 15):
            print("[OK] TEST2 notification config correct")
            print("[OK] Notification configs are properly isolated per device")
        else:
            print(f"[FAIL] TEST2 notification config wrong: {config2}")
            return False
    else:
        print("[FAIL] Failed to get configs")
        return False

    # Step 8: Day 5 - Config persistence test
    print_section("DAY 5 TEST: Config Persistence")

    print("\n[TEST] Verify all TEST1 config fields persist together")
    response = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)

    if response.status_code == 200:
        config = response.json()["config"]

        checks = []
        if "TEST1" in config.get("normal_description", ""):
            checks.append("[OK] Normal description persisted")
        else:
            checks.append(f"[FAIL] Normal description wrong: {config.get('normal_description')}")

        if config["trigger"]["enabled"] == True and config["trigger"]["interval_seconds"] == 20:
            checks.append("[OK] Trigger config persisted")
        else:
            checks.append(f"[FAIL] Trigger config wrong: {config['trigger']}")

        if "alert1@example.com" in config["notification"]["email_addresses"]:
            checks.append("[OK] Notification config persisted")
        else:
            checks.append(f"[FAIL] Notification config wrong: {config['notification']}")

        for check in checks:
            print(check)

        if all("[OK]" in check for check in checks):
            print("\n[OK] All config fields persist correctly")
        else:
            return False
    else:
        print(f"[FAIL] Failed to get TEST1 config: {response.status_code}")
        return False

    # Step 9: Device switching test
    print_section("DAY 5 TEST: Device Switching Behavior")

    print("\n[TEST] Simulate device switching: TEST1 -> TEST2 -> TEST1")

    # Get TEST1 config
    response1a = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)
    test1_config_before = response1a.json()["config"]
    print(f"[INFO] Loaded TEST1 config: trigger interval={test1_config_before['trigger']['interval_seconds']}")

    # Switch to TEST2
    response2 = requests.get(f"{BASE_URL}/v1/devices/TEST2/config", headers=headers)
    test2_config = response2.json()["config"]
    print(f"[INFO] Switched to TEST2 config: trigger interval={test2_config['trigger']['interval_seconds']}")

    # Switch back to TEST1
    response1b = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)
    test1_config_after = response1b.json()["config"]
    print(f"[INFO] Switched back to TEST1 config: trigger interval={test1_config_after['trigger']['interval_seconds']}")

    if (test1_config_before == test1_config_after and
        test1_config_before["trigger"]["interval_seconds"] != test2_config["trigger"]["interval_seconds"]):
        print("[OK] Device switching works correctly - each device retains its own config")
    else:
        print("[FAIL] Config changed during device switching")
        return False

    # Step 10: Data leakage test
    print_section("DAY 5 TEST: No Data Leakage Between Devices")

    print("\n[TEST] Verify TEST1 and TEST2 configs don't interfere")

    response1 = requests.get(f"{BASE_URL}/v1/devices/TEST1/config", headers=headers)
    response2 = requests.get(f"{BASE_URL}/v1/devices/TEST2/config", headers=headers)

    config1 = response1.json()["config"]
    config2 = response2.json()["config"]

    differences = []
    if config1["normal_description"] != config2["normal_description"]:
        differences.append("Normal descriptions are different")
    if config1["trigger"]["interval_seconds"] != config2["trigger"]["interval_seconds"]:
        differences.append("Trigger intervals are different")
    if config1["notification"]["email_addresses"] != config2["notification"]["email_addresses"]:
        differences.append("Email addresses are different")
    if config1["notification"]["email_cooldown_minutes"] != config2["notification"]["email_cooldown_minutes"]:
        differences.append("Email cooldowns are different")

    if len(differences) >= 3:  # At least 3 out of 4 fields are different
        print(f"[OK] Configs are properly isolated ({len(differences)}/4 fields different)")
        for diff in differences:
            print(f"  - {diff}")
    else:
        print(f"[FAIL] Configs may be leaking ({len(differences)}/4 fields different)")
        return False

    # Step 11: Cross-organization test
    print_section("DAY 5 TEST: Cross-Organization Isolation")

    print("\n[TEST] Verify cannot access ABC12 (owned by different org)")
    response = requests.get(f"{BASE_URL}/v1/devices/ABC12/config", headers=headers)

    if response.status_code == 404:
        print("[OK] Cannot access config for device in different organization")
        print("[OK] Cross-org data isolation verified")
    else:
        print(f"[FAIL] Should not be able to access ABC12: got {response.status_code}")
        return False

    # Final summary
    print_section("WEEK 3 COMPLETE - TEST SUMMARY")

    print("\nAll Week 3 Deliverables Tested:")
    print("  [OK] Day 3: Per-device trigger configuration")
    print("  [OK] Day 4: Per-device notification settings")
    print("  [OK] Day 5: Config persistence verified")
    print("  [OK] Day 5: Device switching verified")
    print("  [OK] Day 5: No data leakage between devices")
    print("  [OK] Day 5: Cross-organization isolation verified")

    print("\nWeek 3 Deliverables:")
    print("  [OK] Per-device normal descriptions")
    print("  [OK] Per-device trigger configuration")
    print("  [OK] Per-device notification settings")

    print("\n[SUCCESS] All Week 3 tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_week3_complete()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n[FAIL] ERROR: Could not connect to server at http://localhost:8000")
        print("  Make sure test_auth_server.py is running")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

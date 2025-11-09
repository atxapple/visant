"""
Comprehensive test suite for Phase 5 Week 2 implementation.

Tests all aspects of device activation system:
- API endpoints
- Authentication
- Activation codes
- Database integrity
- Error handling
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

class TestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None

    def print_header(self, title):
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def assert_equal(self, actual, expected, test_name):
        if actual == expected:
            print(f"[PASS] {test_name}")
            self.tests_passed += 1
            return True
        else:
            print(f"[FAIL] {test_name}")
            print(f"  Expected: {expected}")
            print(f"  Got: {actual}")
            self.tests_failed += 1
            return False

    def assert_status(self, response, expected_status, test_name):
        return self.assert_equal(response.status_code, expected_status, test_name)

    def assert_in(self, item, container, test_name):
        if item in container:
            print(f"[PASS] {test_name}")
            self.tests_passed += 1
            return True
        else:
            print(f"[FAIL] {test_name}")
            print(f"  '{item}' not found in {container}")
            self.tests_failed += 1
            return False

    def test_authentication(self):
        """Test user authentication."""
        self.print_header("TEST 1: Authentication")

        # Test login
        response = requests.post(f"{BASE_URL}/v1/auth/login", json={
            "email": "devicetest@example.com",
            "password": "DeviceTest123!"
        })

        if self.assert_status(response, 200, "Login successful"):
            data = response.json()
            self.token = data.get("access_token")
            self.assert_in("access_token", data, "Access token present")
            self.assert_in("user", data, "User data present")
            self.assert_in("organization", data, "Organization data present")

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_device_list(self):
        """Test device list endpoint."""
        self.print_header("TEST 2: Device List Endpoint")

        response = requests.get(f"{BASE_URL}/v1/devices", headers=self.get_headers())

        if self.assert_status(response, 200, "Get devices successful"):
            data = response.json()
            self.assert_in("devices", data, "Devices array present")
            self.assert_in("total", data, "Total count present")
            print(f"  Found {data['total']} devices")

    def test_device_validation_valid(self):
        """Test device validation with valid device."""
        self.print_header("TEST 3: Device Validation - Valid Device")

        response = requests.post(
            f"{BASE_URL}/v1/devices/validate",
            headers=self.get_headers(),
            json={"device_id": "TEST3"}
        )

        if self.assert_status(response, 200, "Validate TEST3 successful"):
            data = response.json()
            self.assert_equal(data.get("status"), "available", "Device status is available")
            self.assert_equal(data.get("can_activate"), True, "Can activate is True")

    def test_device_validation_invalid_format(self):
        """Test device validation with invalid format."""
        self.print_header("TEST 4: Device Validation - Invalid Format")

        response = requests.post(
            f"{BASE_URL}/v1/devices/validate",
            headers=self.get_headers(),
            json={"device_id": "abc"}
        )

        self.assert_status(response, 400, "Invalid format rejected")

    def test_device_validation_not_found(self):
        """Test device validation with non-existent device."""
        self.print_header("TEST 5: Device Validation - Not Found")

        response = requests.post(
            f"{BASE_URL}/v1/devices/validate",
            headers=self.get_headers(),
            json={"device_id": "ZZZZZ"}
        )

        self.assert_status(response, 404, "Non-existent device returns 404")

    def test_activation_without_code_or_subscription(self):
        """Test activation without code or subscription."""
        self.print_header("TEST 6: Activation - No Code or Subscription")

        # First create a new user with no subscription
        signup_response = requests.post(f"{BASE_URL}/v1/auth/signup", json={
            "email": "nosubscription@example.com",
            "password": "NoSub123!",
            "org_name": "No Subscription Org"
        })

        if signup_response.status_code == 200:
            new_token = signup_response.json().get("access_token")
            new_headers = {
                "Authorization": f"Bearer {new_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{BASE_URL}/v1/devices/activate",
                headers=new_headers,
                json={"device_id": "XYZ99"}
            )

            self.assert_status(response, 402, "Returns 402 Payment Required")
        else:
            print("[SKIP] Could not create new user for this test")

    def test_activation_with_valid_code(self):
        """Test activation with valid activation code."""
        self.print_header("TEST 7: Activation - Valid Code")

        response = requests.post(
            f"{BASE_URL}/v1/devices/activate",
            headers=self.get_headers(),
            json={
                "device_id": "TEST3",
                "friendly_name": "Test Camera 3",
                "activation_code": "BETA30"
            }
        )

        if self.assert_status(response, 200, "Activation with BETA30 successful"):
            data = response.json()
            self.assert_equal(data.get("device_id"), "TEST3", "Device ID correct")
            self.assert_in("api_key", data, "API key generated")
            self.assert_in("code_benefit", data, "Code benefit applied")

            # Verify API key is not empty
            if data.get("api_key"):
                print(f"[PASS] API key generated: {data['api_key'][:20]}...")
                self.tests_passed += 1
            else:
                print("[FAIL] API key is empty")
                self.tests_failed += 1

    def test_activation_duplicate(self):
        """Test activating already activated device."""
        self.print_header("TEST 8: Activation - Duplicate")

        response = requests.post(
            f"{BASE_URL}/v1/devices/activate",
            headers=self.get_headers(),
            json={
                "device_id": "TEST3",
                "activation_code": "BETA30"
            }
        )

        self.assert_status(response, 409, "Duplicate activation rejected")

    def test_activation_invalid_code(self):
        """Test activation with invalid code."""
        self.print_header("TEST 9: Activation - Invalid Code")

        response = requests.post(
            f"{BASE_URL}/v1/devices/activate",
            headers=self.get_headers(),
            json={
                "device_id": "XYZ99",
                "activation_code": "INVALID123"
            }
        )

        self.assert_status(response, 404, "Invalid code rejected")

    def test_get_individual_device(self):
        """Test getting individual device details."""
        self.print_header("TEST 10: Get Individual Device")

        response = requests.get(
            f"{BASE_URL}/v1/devices/TEST1",
            headers=self.get_headers()
        )

        if self.assert_status(response, 200, "Get device TEST1 successful"):
            data = response.json()
            self.assert_equal(data.get("device_id"), "TEST1", "Device ID correct")
            self.assert_in("friendly_name", data, "Friendly name present")
            self.assert_in("status", data, "Status present")

    def test_get_device_not_owned(self):
        """Test getting device not owned by user."""
        self.print_header("TEST 11: Get Device - Not Owned")

        # Try to get ABC12 which is owned by 'youngmok'
        response = requests.get(
            f"{BASE_URL}/v1/devices/ABC12",
            headers=self.get_headers()
        )

        self.assert_status(response, 404, "Cannot access other user's device")

    def test_static_files(self):
        """Test static file serving."""
        self.print_header("TEST 12: Static Files")

        # Test auth.js
        response = requests.get(f"{BASE_URL}/static/js/auth.js")
        self.assert_status(response, 200, "auth.js served")

        # Test device_wizard.js
        response = requests.get(f"{BASE_URL}/static/js/device_wizard.js")
        self.assert_status(response, 200, "device_wizard.js served")

        # Test device_manager.js
        response = requests.get(f"{BASE_URL}/static/js/device_manager.js")
        self.assert_status(response, 200, "device_manager.js served")

    def test_dashboard_ui(self):
        """Test dashboard UI loads."""
        self.print_header("TEST 13: Dashboard UI")

        response = requests.get(f"{BASE_URL}/ui")

        if self.assert_status(response, 200, "Dashboard loads"):
            html = response.text

            # Check for key UI elements
            self.assert_in("Add Camera", html, "Add Camera button present")
            self.assert_in("device_wizard", html, "Device wizard script included")
            self.assert_in("device_manager", html, "Device manager script included")
            self.assert_in("deviceWizardModal", html, "Device wizard modal present")

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 70)
        print("  COMPREHENSIVE TEST SUITE - Phase 5 Week 2")
        print("=" * 70)

        try:
            self.test_authentication()
            if not self.token:
                print("\n[ERROR] Authentication failed, cannot continue tests")
                return False

            self.test_device_list()
            self.test_device_validation_valid()
            self.test_device_validation_invalid_format()
            self.test_device_validation_not_found()
            self.test_activation_without_code_or_subscription()
            self.test_activation_with_valid_code()
            self.test_activation_duplicate()
            self.test_activation_invalid_code()
            self.test_get_individual_device()
            self.test_get_device_not_owned()
            self.test_static_files()
            self.test_dashboard_ui()

            # Print summary
            self.print_header("TEST SUMMARY")
            total = self.tests_passed + self.tests_failed
            pass_rate = (self.tests_passed / total * 100) if total > 0 else 0

            print(f"\nTotal Tests: {total}")
            print(f"Passed: {self.tests_passed}")
            print(f"Failed: {self.tests_failed}")
            print(f"Pass Rate: {pass_rate:.1f}%")

            if self.tests_failed == 0:
                print("\n[SUCCESS] All tests passed!")
                return True
            else:
                print(f"\n[WARNING] {self.tests_failed} test(s) failed")
                return False

        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Cannot connect to server at http://localhost:8000")
            print("Make sure test_auth_server.py is running")
            return False
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

"""Test API call directly with Python requests."""

import requests
import json

# JWT token from earlier
token = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImRWZkxrck1abXJ5VEN3NmciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL21wYWd1bXdrdXppcHBscXFmaGFyLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3MTM3ZGJiMi1kMTIzLTQzMDYtOWMyYi1mNzcwOWE5ZDcyN2YiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYyNjIzNDgwLCJpYXQiOjE3NjI2MTk4ODAsImVtYWlsIjoiZGV2aWNldGVzdEBleGFtcGxlLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzYyNjE5ODgwfV0sInNlc3Npb25faWQiOiI5YWIxYTRhZC04NTVmLTRhMjktYjJlNi1jMzIwZGZkMmYwNzkiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.yTb1zPiJl1uaHFOxCKHq2ypuLfR72CtWuPujl2JojKE"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# Test 1: Validate device
print("=" * 60)
print("TEST 1: Validate device TEST1")
print("=" * 60)

url = "http://localhost:8000/v1/devices/validate"
data = {"device_id": "TEST1"}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n")

# Test 2: Activate device with code
print("=" * 60)
print("TEST 2: Activate device TEST1 with DEV2025 code")
print("=" * 60)

url = "http://localhost:8000/v1/devices/activate"
data = {
    "device_id": "TEST1",
    "friendly_name": "Test Camera 1",
    "activation_code": "DEV2025"
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

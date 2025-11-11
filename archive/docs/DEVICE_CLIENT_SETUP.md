# Visant Device Client Setup Guide

This guide explains how to set up and test the Visant device client (camera) with the multi-tenant cloud backend.

## Prerequisites

- Server running on `http://localhost:8000` (or your deployed URL)
- Test devices seeded in database with status="manufactured"
- User account (create via signup or use existing account)

## Quick Start

### 1. Start the Server

```bash
.venv/Scripts/python test_auth_server.py
```

Server will start on `http://localhost:8000`

### 2. Seed Test Devices

Run the seeding script to create test devices in the database:

```bash
.venv/Scripts/python -m scripts.seed_test_devices
```

This creates the following devices:
- TEST1, TEST2, TEST3 (for basic testing)
- ABC12, XYZ99 (additional test devices)

All devices are created with:
- Status: `manufactured` (ready for activation)
- Batch: `BATCH_TEST_001`
- org_id: `NULL` (not yet activated)

### 3. Create User Account & Activate Device

#### Option A: Via Web UI

1. Open browser to `http://localhost:8000/ui/signup`
2. Sign up with email/password
3. Navigate to "Add New Camera" from dashboard
4. Enter device ID (e.g., `TEST2`)
5. Enter activation code: `DEV2025`
6. Device is now activated and linked to your workspace

#### Option B: Via End-to-End Test Script

Run the automated test that creates a user, activates a device, and uploads a capture:

```bash
.venv/Scripts/python test_end_to_end_device_flow.py
```

This script:
- Creates a new user account
- Activates device NEW99 (or another available device)
- Uploads a test capture
- Polls for Cloud AI evaluation
- Verifies the complete flow

### 4. Upload Captures from Device Client

#### Using laptop_camera_test.py

1. Update the device ID in the script:
   ```python
   DEVICE_ID = "TEST2"  # Use your activated device ID
   ```

2. Run the script:
   ```bash
   .venv/Scripts/python laptop_camera_test.py
   ```

3. The script will:
   - Capture an image from your webcam
   - Upload it to the cloud
   - Poll for AI evaluation results
   - Display the evaluation (normal/concern/issue)

## Device Flow Architecture

### Device Lifecycle

```
manufactured → activated → active
```

1. **Manufactured**: Device created in database, not yet activated
   - org_id: NULL
   - api_key: NULL
   - status: "manufactured"

2. **Activated**: User links device to their organization
   - org_id: Set to user's organization
   - api_key: Generated (for future use)
   - status: "active"
   - friendly_name: Auto-generated from device_id

3. **Active**: Device can upload captures
   - Uploads authenticated by device_id (no API key required currently)
   - Captures linked to device and organization
   - Data isolation enforced via org_id

### Device ID Format

- Must be exactly **5 uppercase alphanumeric characters**
- Regex: `^[A-Z0-9]{5}$`
- Examples: TEST2, ABC12, XYZ99, NEW99

### Activation Codes

The system supports activation codes for device slot allocation:

- `DEV2025`: Development code (99 additional device slots)
- Codes can have expiration dates
- Codes tracked in `activation_codes` table

## API Endpoints

### Device Validation (requires JWT token)

```bash
POST /v1/devices/validate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "device_id": "TEST2"
}
```

Response:
- 200: Device exists and available for activation
- 404: Device ID not found
- 409: Device already activated by another user

### Device Activation (requires JWT token)

```bash
POST /v1/devices/activate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "device_id": "TEST2",
  "activation_code": "DEV2025"
}
```

Response:
- 200/201: Device activated successfully
- Returns: device_id, friendly_name, api_key, status, organization info

### Capture Upload (device authentication only)

```bash
POST /v1/captures
Content-Type: application/json

{
  "device_id": "TEST2",
  "captured_at": "2025-11-08T22:51:08.564244Z",
  "image_base64": "<base64-encoded-image>",
  "trigger_label": "test_upload",
  "metadata": {
    "source": "laptop_webcam",
    "resolution": "640x480"
  }
}
```

Response:
- 201: Capture uploaded successfully
- Returns: record_id, evaluation_status, device_id, image_stored

### Get Capture Evaluation (device authentication)

```bash
GET /v1/captures/{record_id}?device_id=TEST2
```

Response:
- 200: Evaluation results
- Returns: state (normal/concern/issue), score, reason, timestamps

## Multi-Tenant Features

The device client works with the multi-tenant architecture:

1. **Organization Isolation**: Each user has their own workspace
   - Auto-created as "{username}'s Workspace" during signup
   - Devices belong to specific organizations
   - Captures linked to both device and organization

2. **Data Isolation**: All queries filtered by org_id
   - Users can only see their own devices
   - Users can only see captures from their devices
   - Row-level security enforced at database level

3. **Device Ownership**: One device = one organization
   - Once activated, device cannot be transferred
   - Attempting to activate already-activated device returns 409

## Troubleshooting

### "Device ID not found" Error

- Device must exist in database with status="manufactured"
- Run `scripts/seed_test_devices.py` to create test devices
- Or manually create device in database

### "Device already activated by another user"

- Device is already linked to another organization
- Use a different device ID
- Or deactivate the device in database (for testing only)

### "Invalid device ID format"

- Device ID must be exactly 5 uppercase alphanumeric characters
- Examples: TEST2 ✓, test2 ✗, TEST ✗, TEST123 ✗

### Capture Upload Fails

- Verify device is activated (`status = 'active'`)
- Check device_id matches exactly (case-sensitive)
- Ensure image is base64 encoded
- Check server logs for detailed error

## Database Queries (for debugging)

### Check device status
```sql
SELECT device_id, status, org_id, friendly_name
FROM devices
WHERE device_id = 'TEST2';
```

### View all captures for a device
```sql
SELECT record_id, state, score, captured_at, evaluated_at
FROM captures
WHERE device_id = 'TEST2'
ORDER BY captured_at DESC;
```

### List unactivated devices
```sql
SELECT device_id, manufactured_at, batch_id
FROM devices
WHERE org_id IS NULL AND status = 'manufactured';
```

## Next Steps

After testing locally:

1. Test with real webcam using `laptop_camera_test.py`
2. Deploy to Railway (Phase 6)
3. Update device clients to use production URL
4. Set up proper SSL certificates
5. Implement device API key authentication (currently optional)

## Files Reference

- `test_end_to_end_device_flow.py` - Automated E2E test
- `laptop_camera_test.py` - Webcam capture test client
- `scripts/seed_test_devices.py` - Device seeding script
- `cloud/api/routes/devices.py` - Device endpoints
- `cloud/api/routes/captures.py` - Capture upload endpoints

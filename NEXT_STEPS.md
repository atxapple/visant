# Next Steps: Phase 5 Week 2 Continuation

**Current Status**: Day 1-2 Complete (Backend Foundation)
**Date**: 2025-11-08
**Remaining Work**: ~12-18 hours (2-3 days)

---

## ✅ What's Been Completed

### 1. Database Schema (100% Done)
- Created `activation_codes` table for promotional codes
- Created `code_redemptions` table for tracking usage
- Updated `organizations` with subscription fields
- Updated `devices` with activation workflow fields
- All changes migrated successfully via Alembic

### 2. Development Tools (100% Done)
- Seeded 3 activation codes:
  - **DEV2025**: 99 device slots, unlimited uses (for development)
  - **QA100**: 12 months free, 10 uses (for QA team)
  - **BETA30**: 30 day trial extension, 100 uses (for beta testers)
- Seed script: `scripts/seed_activation_codes.py`

### 3. Documentation (100% Done)
- `PHASE5_WEEK2_PROGRESS.md` - Detailed progress report
- `PROJECT_PLAN.md` - Updated with Week 2 status
- `NEXT_STEPS.md` - This file

---

## 🎯 Next: API Endpoints Implementation

### Priority 1: Device Validation Endpoint (1-2 hours)

**File**: `cloud/api/routes/devices.py`

**Add this endpoint**:
```python
@router.post("/validate", status_code=status.HTTP_200_OK)
def validate_device(
    request: DeviceValidationRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Validate device ID before activation.

    Checks:
    - Device ID exists in database
    - Device not already activated
    - Device ID format correct (5 chars, alphanumeric)

    Does NOT check subscription status.
    """
    pass
```

**Request/Response Models to Add**:
```python
class DeviceValidationRequest(BaseModel):
    device_id: str

class DeviceValidationResponse(BaseModel):
    device_id: str
    status: str  # "available", "already_activated_by_you", etc.
    can_activate: bool
    message: str
```

---

### Priority 2: Device Activation with Code Support (2-3 hours)

**Update existing endpoint**:
```python
@router.post("/activate", response_model=DeviceActivationResponse)
def activate_device(
    request: DeviceActivationRequest,
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate device with optional activation code.

    Authorization options:
    1. Valid activation code (no payment required)
    2. Active subscription (payment in Phase 7)

    If neither, returns 402 Payment Required.
    """
    pass
```

**Request/Response Models to Add**:
```python
class DeviceActivationRequest(BaseModel):
    device_id: str
    friendly_name: Optional[str] = None
    activation_code: Optional[str] = None  # NEW!

class CodeBenefitResponse(BaseModel):
    code: str
    benefit: str
    expires_at: Optional[datetime]

class DeviceActivationResponse(BaseModel):
    device_id: str
    friendly_name: str
    api_key: str  # ONE TIME ONLY
    status: str
    activated_at: datetime
    code_benefit: Optional[CodeBenefitResponse]  # If code used
    organization: dict
```

**Helper function to create**:
```python
def validate_and_apply_activation_code(
    code: str,
    org: Organization,
    user: User,
    device_id: str,
    db: Session
) -> Dict:
    """
    Validate activation code and apply benefits.

    Returns:
        Dict with code, benefit description, and expiration

    Raises:
        HTTPException if code invalid/expired/used
    """
    pass
```

---

### Priority 3: Update Existing Device Registration (30 min)

**Current `/v1/devices` POST endpoint needs updates**:
- Change to work with pre-manufactured devices
- This is for admin/manufacturing to create device records
- Regular users should use `/v1/devices/activate` instead

---

## 🎨 Next: Frontend Device Wizard (3-4 hours)

### File Structure:
```
cloud/web/
  templates/
    index.html (modify - add modal trigger)
  static/
    js/
      device_activation.js (create new)
    css/
      device_wizard.css (optional - inline in index.html is fine)
```

### Implementation Steps:

1. **Add "Add Device" Button to Dashboard** (15 min)
```html
<!-- In index.html header -->
<button onclick="openDeviceWizard()" class="btn-primary">
  + Add Device
</button>

<div id="deviceWizardModal" class="modal" style="display:none">
  <!-- Wizard content here -->
</div>
```

2. **Create Device Wizard Modal** (1-2 hours)
```html
<!-- Screen 1: Enter Device ID -->
<div id="wizardStep1" class="wizard-screen">
  <h2>Add New Camera</h2>
  <p>Enter the Device ID from your camera sticker</p>
  <input type="text" id="deviceIdInput" placeholder="ABC12" maxlength="5">
  <button onclick="validateDeviceId()">Next →</button>
</div>

<!-- Screen 2: Validation Success + Options -->
<div id="wizardStep2" class="wizard-screen" style="display:none">
  <!-- Shows different content based on subscription status -->
</div>

<!-- Screen 3: Activation Success -->
<div id="wizardStep3" class="wizard-screen" style="display:none">
  <h2>Device Activated!</h2>
  <!-- Show success message + benefits -->
</div>
```

3. **Implement Wizard Logic** (1-2 hours)
```javascript
// device_activation.js

async function validateDeviceId() {
    const deviceId = document.getElementById('deviceIdInput').value.toUpperCase();

    const response = await fetch('/v1/devices/validate', {
        method: 'POST',
        headers: auth.getAuthHeaders(),
        body: JSON.stringify({ device_id: deviceId })
    });

    if (response.ok) {
        const data = await response.json();
        showActivationOptions(deviceId);
    } else {
        showError(await response.json());
    }
}

async function activateWithCode() {
    const deviceId = currentDeviceId;
    const code = document.getElementById('activationCodeInput').value;
    const name = document.getElementById('friendlyNameInput').value;

    const response = await fetch('/v1/devices/activate', {
        method: 'POST',
        headers: auth.getAuthHeaders(),
        body: JSON.stringify({
            device_id: deviceId,
            friendly_name: name,
            activation_code: code
        })
    });

    if (response.ok) {
        const data = await response.json();
        showActivationSuccess(data);
    } else {
        showError(await response.json());
    }
}
```

---

## 🧪 Testing Plan

### API Testing (with curl/Postman):

1. **Test Device Validation**:
```bash
# Should succeed (device exists)
curl -X POST http://localhost:8000/v1/devices/validate \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "TEST1"}'

# Should fail (device not found)
curl -X POST http://localhost:8000/v1/devices/validate \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{"device_id": "XXXXX"}'
```

2. **Test Activation with Code**:
```bash
# Should succeed with DEV2025 code
curl -X POST http://localhost:8000/v1/devices/activate \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST1",
    "friendly_name": "Test Camera",
    "activation_code": "DEV2025"
  }'
```

3. **Test Activation without Code/Subscription**:
```bash
# Should fail with 402 Payment Required
curl -X POST http://localhost:8000/v1/devices/activate \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "device_id": "TEST1",
    "friendly_name": "Test Camera"
  }'
```

### Frontend Testing:

1. **Device Wizard Flow**:
   - [ ] Open wizard
   - [ ] Enter valid device ID → shows activation options
   - [ ] Enter invalid device ID → shows error
   - [ ] Activate with valid code → shows success
   - [ ] Activate with invalid code → shows error

2. **User Experience**:
   - [ ] Free user sees activation code + payment options
   - [ ] Paid user sees simple activation form
   - [ ] Success screen shows code benefits (if applicable)
   - [ ] Device appears in dashboard after activation

---

## 📝 Pre-Manufacturing Test Devices

**Need to create test devices in database first**:

```bash
# Run this SQL or create a script
INSERT INTO devices (device_id, manufactured_at, batch_id, status, created_at)
VALUES
  ('TEST1', datetime('now'), 'BATCH_TEST_001', 'manufactured', datetime('now')),
  ('TEST2', datetime('now'), 'BATCH_TEST_001', 'manufactured', datetime('now')),
  ('TEST3', datetime('now'), 'BATCH_TEST_001', 'manufactured', datetime('now')),
  ('ABC12', datetime('now'), 'BATCH_TEST_001', 'manufactured', datetime('now')),
  ('XYZ99', datetime('now'), 'BATCH_TEST_001', 'manufactured', datetime('now'));
```

**Or create a seed script**:
```python
# scripts/seed_test_devices.py
from cloud.api.database import get_db, Device
from datetime import datetime

def seed_test_devices():
    db = next(get_db())
    test_devices = ['TEST1', 'TEST2', 'TEST3', 'ABC12', 'XYZ99']

    for device_id in test_devices:
        if not db.query(Device).filter(Device.device_id == device_id).first():
            device = Device(
                device_id=device_id,
                manufactured_at=datetime.utcnow(),
                batch_id='BATCH_TEST_001',
                status='manufactured',
                created_at=datetime.utcnow()
            )
            db.add(device)

    db.commit()
    print(f"Seeded {len(test_devices)} test devices")

if __name__ == "__main__":
    seed_test_devices()
```

---

## 🔧 Development Workflow

### Starting Your Next Session:

1. **Read This Document**: `NEXT_STEPS.md`
2. **Check Progress**: `PHASE5_WEEK2_PROGRESS.md`
3. **Verify Database**: Run `python -m scripts.seed_activation_codes` (should show existing codes)
4. **Start Coding**: Begin with API endpoints (Priority 1)

### Recommended Order:

1. Create test devices seed script (15 min)
2. Implement device validation endpoint (1 hour)
3. Test validation endpoint (30 min)
4. Implement activation endpoint with code support (2 hours)
5. Test activation with DEV2025 code (30 min)
6. Create frontend device wizard (3 hours)
7. End-to-end testing (1 hour)

**Total**: ~8-9 hours to complete backend + frontend wizard

---

## 📚 Reference Documents

- `PHASE5_WEEK2_PROGRESS.md` - Detailed implementation guide
- `PROJECT_PLAN.md` - Overall project status
- `cloud/api/database/models.py` - Database schema
- `cloud/api/routes/devices.py` - Existing device endpoints
- `cloud/web/templates/login.html` - Example of auth UI
- `cloud/web/static/js/auth.js` - Auth helper functions

---

## 💡 Quick Commands

```bash
# Activate virtual environment
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run migrations
.venv/Scripts/alembic upgrade head

# Seed activation codes
.venv/Scripts/python -m scripts.seed_activation_codes

# Run test server
.venv/Scripts/python test_auth_server.py

# Test API endpoint
curl -X POST http://localhost:8000/v1/devices/validate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "TEST1"}'
```

---

## ❓ Questions to Resolve

- [ ] Should we add device auto-provisioning endpoint now or later?
  - `GET /v1/devices/{device_id}/config` (returns api_key if activated)

- [ ] Should test devices have realistic-looking IDs or simple ones?
  - Current: TEST1, TEST2, ABC12 (mix of both)

- [ ] Should activation code be case-sensitive?
  - Recommendation: No, convert to uppercase

---

**Ready to Continue?**

Start with:
1. Create `scripts/seed_test_devices.py`
2. Run seed script
3. Implement `POST /v1/devices/validate` in `cloud/api/routes/devices.py`
4. Test with curl

Good luck! 🚀

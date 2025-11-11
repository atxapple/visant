# Phase 5 Week 3: Per-Device Configuration

**Start Date**: 2025-11-08
**Status**: 🔄 In Progress
**Goal**: Migrate global configuration to per-device configuration
**Duration**: 5 days

---

## 📋 Overview

### Current State
The dashboard has three configuration sections that are currently **global** (not device-specific):
1. **Abnormal Condition** - Normal description for AI classification
2. **Trigger Sources** - Recurring trigger settings and interval
3. **Notification & Actions** - Email notification settings and cooldown

### Target State
All three configuration sections should be **per-device**:
- Each device has its own normal description
- Each device has its own trigger configuration
- Each device has its own notification settings
- Switching devices loads that device's configuration
- Changes to config only affect the current device

---

## 🎯 Goals

1. **Backend**: Create device config API endpoints
2. **Storage**: Use `device.config` JSON column (already exists)
3. **Frontend**: Update forms to load/save per-device config
4. **UX**: Seamless config switching when changing devices
5. **Testing**: Verify no config leakage between devices

---

## 📦 Implementation Plan

### Day 1: Device Config API (3-4 hours)

#### Task 1.1: Create Pydantic Models
**File**: `cloud/api/database/schemas.py` (or in routes file)

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class TriggerConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = 10
    digital_input_enabled: bool = False

class NotificationConfig(BaseModel):
    email_enabled: bool = True
    email_addresses: List[EmailStr] = []
    email_cooldown_minutes: int = 10
    digital_output_enabled: bool = False

class DeviceConfig(BaseModel):
    """Complete device configuration."""
    normal_description: Optional[str] = None
    trigger: TriggerConfig = TriggerConfig()
    notification: NotificationConfig = NotificationConfig()

class DeviceConfigResponse(BaseModel):
    device_id: str
    config: DeviceConfig
    last_updated: Optional[str] = None
```

#### Task 1.2: Create Config Endpoints
**File**: `cloud/api/routes/devices.py`

```python
@router.get("/{device_id}/config", response_model=DeviceConfigResponse)
def get_device_config(
    device_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Get device configuration.

    Returns the device's complete config including:
    - normal_description
    - trigger settings
    - notification settings
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id,
        Device.status == "active"
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Return config (defaults to empty dict if not set)
    config = device.config or {}

    return {
        "device_id": device.device_id,
        "config": config,
        "last_updated": device.updated_at.isoformat() if device.updated_at else None
    }


@router.put("/{device_id}/config", response_model=DeviceConfigResponse)
def update_device_config(
    device_id: str,
    config: DeviceConfig,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db)
):
    """
    Update device configuration.

    Accepts partial updates - only provided fields will be updated.
    """
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.org_id == org.id,
        Device.status == "active"
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Update config (merge with existing)
    current_config = device.config or {}
    current_config.update(config.dict(exclude_unset=True))
    device.config = current_config
    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return {
        "device_id": device.device_id,
        "config": device.config,
        "last_updated": device.updated_at.isoformat()
    }
```

#### Testing Day 1
```bash
# Test GET config (should return default config)
curl http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>"

# Test PUT config
curl -X PUT http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "normal_description": "If someone is smiling, it is abnormal.",
    "trigger": {"enabled": true, "interval_seconds": 15},
    "notification": {"email_enabled": true, "email_cooldown_minutes": 5}
  }'

# Verify config was saved
curl http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>"
```

---

### Day 2: Frontend Config Management (3-4 hours)

#### Task 2.1: Create Config Manager
**File**: `cloud/web/static/js/device_config.js`

```javascript
/**
 * Device Configuration Manager
 *
 * Manages loading and saving device-specific configuration.
 */
class DeviceConfigManager {
    constructor(authManager) {
        this.auth = authManager;
        this.API_URL = window.location.origin;
        this.currentDeviceId = null;
        this.currentConfig = null;
    }

    /**
     * Load config for a specific device
     */
    async loadConfig(deviceId) {
        if (!deviceId) {
            console.error('No device ID provided');
            return null;
        }

        try {
            const response = await fetch(
                `${this.API_URL}/v1/devices/${deviceId}/config`,
                {
                    method: 'GET',
                    headers: this.auth.getAuthHeaders()
                }
            );

            if (!response.ok) {
                throw new Error('Failed to load device config');
            }

            const data = await response.json();
            this.currentDeviceId = deviceId;
            this.currentConfig = data.config;

            return this.currentConfig;
        } catch (error) {
            console.error('Error loading device config:', error);
            return null;
        }
    }

    /**
     * Save config for current device
     */
    async saveConfig(configUpdate) {
        if (!this.currentDeviceId) {
            console.error('No device selected');
            return false;
        }

        try {
            const response = await fetch(
                `${this.API_URL}/v1/devices/${this.currentDeviceId}/config`,
                {
                    method: 'PUT',
                    headers: this.auth.getAuthHeaders(),
                    body: JSON.stringify(configUpdate)
                }
            );

            if (!response.ok) {
                throw new Error('Failed to save device config');
            }

            const data = await response.json();
            this.currentConfig = data.config;

            return true;
        } catch (error) {
            console.error('Error saving device config:', error);
            return false;
        }
    }

    /**
     * Populate form fields with config
     */
    populateForms(config) {
        if (!config) return;

        // Normal description
        const normalText = document.getElementById('normal-text');
        if (normalText && config.normal_description) {
            normalText.value = config.normal_description;
        }

        // Trigger settings
        if (config.trigger) {
            const triggerEnabled = document.getElementById('trigger-enabled');
            const intervalInput = document.getElementById('interval-input');

            if (triggerEnabled) triggerEnabled.checked = config.trigger.enabled || false;
            if (intervalInput) intervalInput.value = config.trigger.interval_seconds || 10;
        }

        // Notification settings
        if (config.notification) {
            const emailEnabled = document.getElementById('email-enabled');
            const emailAddresses = document.getElementById('email-addresses');
            const emailCooldown = document.getElementById('email-cooldown');

            if (emailEnabled) emailEnabled.checked = config.notification.email_enabled !== false;
            if (emailAddresses && config.notification.email_addresses) {
                emailAddresses.value = config.notification.email_addresses.join(', ');
            }
            if (emailCooldown) emailCooldown.value = config.notification.email_cooldown_minutes || 10;
        }
    }
}
```

#### Task 2.2: Update Form Handlers
**File**: `cloud/web/templates/index.html` (in existing `<script>` section)

Update the form submit handlers to use device config manager:

```javascript
// Initialize config manager
let deviceConfigManager;
document.addEventListener('DOMContentLoaded', () => {
    deviceConfigManager = new DeviceConfigManager(auth);
});

// Update normal description form
document.getElementById('normal-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const normalText = document.getElementById('normal-text').value;

    const success = await deviceConfigManager.saveConfig({
        normal_description: normalText
    });

    const status = document.getElementById('normal-status');
    if (success) {
        status.textContent = 'Description saved';
        status.className = 'status success';
    } else {
        status.textContent = 'Failed to save description';
        status.className = 'status error';
    }
});

// Update trigger form
document.getElementById('trigger-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const enabled = document.getElementById('trigger-enabled').checked;
    const interval = parseInt(document.getElementById('interval-input').value);

    const success = await deviceConfigManager.saveConfig({
        trigger: {
            enabled: enabled,
            interval_seconds: interval
        }
    });

    const status = document.getElementById('trigger-status');
    if (success) {
        status.textContent = 'Trigger settings saved';
        status.className = 'status success';
    } else {
        status.textContent = 'Failed to save trigger settings';
        status.className = 'status error';
    }
});

// Update notification form
document.getElementById('notify-submit').addEventListener('click', async () => {
    const emailEnabled = document.getElementById('email-enabled').checked;
    const emailAddresses = document.getElementById('email-addresses').value
        .split(',')
        .map(e => e.trim())
        .filter(e => e);
    const cooldown = parseInt(document.getElementById('email-cooldown').value);

    const success = await deviceConfigManager.saveConfig({
        notification: {
            email_enabled: emailEnabled,
            email_addresses: emailAddresses,
            email_cooldown_minutes: cooldown
        }
    });

    const status = document.getElementById('notify-status');
    if (success) {
        status.textContent = 'Notification settings saved';
        status.className = 'status success';
    } else {
        status.textContent = 'Failed to save notification settings';
        status.className = 'status error';
    }
});
```

---

### Day 3: Device Switching Integration (2-3 hours)

#### Task 3.1: Update Device Manager
**File**: `cloud/web/static/js/device_manager.js`

Add config loading to device switching:

```javascript
// In DeviceManager class, update switchToDevice method
async switchToDevice(deviceId) {
    this.currentDeviceId = deviceId;
    sessionStorage.setItem('selected_device_id', deviceId);

    // Update UI
    this.updateDeviceDisplay();

    // Load device config
    if (typeof deviceConfigManager !== 'undefined') {
        const config = await deviceConfigManager.loadConfig(deviceId);
        if (config) {
            deviceConfigManager.populateForms(config);
        }
    }

    // Refresh captures for this device
    await this.refreshCaptures();

    // Update WebSocket subscription if needed
    this.updateWebSocketSubscription();
}
```

#### Task 3.2: Initial Config Load
**File**: `cloud/web/templates/index.html`

Add initial config load after device selection:

```javascript
// After devices are loaded and device is selected
document.addEventListener('DOMContentLoaded', async () => {
    // ... existing device loading code ...

    // Load config for selected device
    if (deviceManager.currentDeviceId && deviceConfigManager) {
        const config = await deviceConfigManager.loadConfig(deviceManager.currentDeviceId);
        if (config) {
            deviceConfigManager.populateForms(config);
        }
    }
});
```

---

### Day 4: Testing & Polish (2-3 hours)

#### Test Scenarios

1. **Single Device Config**:
   - [ ] Set normal description for TEST1
   - [ ] Save and verify it persists
   - [ ] Refresh page and verify config loads

2. **Multi-Device Config**:
   - [ ] Set normal description for TEST1: "Smiling is abnormal"
   - [ ] Switch to TEST2
   - [ ] Set normal description for TEST2: "Standing is abnormal"
   - [ ] Switch back to TEST1
   - [ ] Verify TEST1 config is restored (shows "Smiling is abnormal")

3. **Config Isolation**:
   - [ ] Set different trigger intervals for each device
   - [ ] Set different email cooldowns for each device
   - [ ] Switch between devices and verify each shows correct settings

4. **Form Validation**:
   - [ ] Test with invalid email addresses
   - [ ] Test with negative intervals
   - [ ] Verify error handling

---

### Day 5: Documentation & Migration (1-2 hours)

#### Task 5.1: Update Documentation
- Update NEXT_STEPS.md
- Document config API in API_REFERENCE.md (if exists)
- Add config management to user guide

#### Task 5.2: Migration Script (Optional)
If there's existing global config data that needs to be migrated:

```python
# scripts/migrate_global_config.py
"""
Migrate global config to per-device config.
Run this once if you have existing configuration.
"""
from cloud.api.database import get_db, Device

def migrate_config():
    # If you had a global config, copy it to all devices
    global_config = {
        "normal_description": "Your global description",
        "trigger": {"enabled": False, "interval_seconds": 10},
        "notification": {
            "email_enabled": True,
            "email_addresses": ["ops@example.com"],
            "email_cooldown_minutes": 10
        }
    }

    db = next(get_db())
    devices = db.query(Device).filter(Device.status == "active").all()

    for device in devices:
        if not device.config:
            device.config = global_config

    db.commit()
    print(f"Migrated config to {len(devices)} devices")
```

---

## 📝 Files to Create

- [ ] `cloud/web/static/js/device_config.js` - Config manager
- [ ] `PHASE5_WEEK3_PROGRESS.md` - Progress tracking

## 📄 Files to Modify

- [ ] `cloud/api/routes/devices.py` - Add GET/PUT config endpoints
- [ ] `cloud/web/static/js/device_manager.js` - Add config loading on device switch
- [ ] `cloud/web/templates/index.html` - Update form handlers, add config.js script

## 🧪 Testing Checklist

- [ ] GET /v1/devices/{id}/config returns default config
- [ ] PUT /v1/devices/{id}/config saves config
- [ ] Normal description form saves per device
- [ ] Trigger form saves per device
- [ ] Notification form saves per device
- [ ] Switching devices loads correct config
- [ ] No config leakage between devices
- [ ] Config persists after page refresh
- [ ] Error handling for invalid inputs
- [ ] Cross-organization config isolation

---

## 🎯 Success Criteria

- ✅ Each device has independent configuration
- ✅ Config saved to `device.config` JSON column
- ✅ Switching devices loads correct config
- ✅ Forms populate with device-specific settings
- ✅ No config leakage between devices or orgs
- ✅ All tests passing

---

## 📚 Reference

- Database: `device.config` column already exists (models.py:130)
- Existing forms: index.html lines 690-743
- Device switching: device_manager.js
- Auth headers: auth.js (getAuthHeaders method)

---

**Estimated Time**: 12-16 hours (2-3 days of focused work)
**Complexity**: Medium
**Dependencies**: Week 2 multi-device support must be complete

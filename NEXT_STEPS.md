# Next Steps: Phase 5 Week 3 - Per-Device Configuration

**Current Status**: Week 2 Complete ✅ | Week 3 Starting
**Date**: 2025-11-08
**Estimated Time**: 12-16 hours (2-3 days)

---

## ✅ What's Been Completed (Week 2)

- ✅ Multi-device dashboard with smart UI (0/1/2+ devices)
- ✅ Device activation wizard (3-step flow)
- ✅ Activation code system with benefits
- ✅ Device validation and activation APIs
- ✅ Device selector dropdown
- ✅ Comprehensive test suite (23/26 tests passed)

---

## 🎯 Week 3 Goal

**Migrate global configuration to per-device configuration**

Currently, the dashboard has three configuration sections that are global:
1. **Abnormal Condition** - Normal description for AI classification
2. **Trigger Sources** - Recurring trigger settings and interval
3. **Notification & Actions** - Email notification settings and cooldown

All three should become **per-device** so each camera can have its own settings.

---

## 📋 Implementation Order

### Priority 1: Backend API (Day 1) - 3-4 hours

**Create Device Config Endpoints**

File: `cloud/api/routes/devices.py`

1. Add Pydantic models for config structure:
   - `TriggerConfig` (enabled, interval_seconds, digital_input_enabled)
   - `NotificationConfig` (email_enabled, email_addresses, email_cooldown_minutes)
   - `DeviceConfig` (normal_description, trigger, notification)

2. Add endpoints:
   - `GET /v1/devices/{device_id}/config` - Get device configuration
   - `PUT /v1/devices/{device_id}/config` - Update device configuration

3. Use existing `device.config` JSON column (already in database)

**Testing**:
```bash
# Get config (should return defaults)
curl http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>"

# Update config
curl -X PUT http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "normal_description": "If someone is smiling, it is abnormal.",
    "trigger": {"enabled": true, "interval_seconds": 15},
    "notification": {"email_enabled": true, "email_cooldown_minutes": 5}
  }'
```

---

### Priority 2: Frontend Config Manager (Day 2) - 3-4 hours

**Create Config Management JavaScript**

File: `cloud/web/static/js/device_config.js` (new file)

1. Create `DeviceConfigManager` class:
   - `loadConfig(deviceId)` - Fetch config from API
   - `saveConfig(configUpdate)` - Save config to API
   - `populateForms(config)` - Fill form fields with config

2. Update form handlers in `index.html`:
   - Normal description form (`#normal-form`)
   - Trigger form (`#trigger-form`)
   - Notification form (`#notify-form`)

3. Add `<script src="/static/js/device_config.js"></script>` to index.html

---

### Priority 3: Device Switching Integration (Day 3) - 2-3 hours

**Update Device Manager**

File: `cloud/web/static/js/device_manager.js`

1. Add config loading to `switchToDevice()` method
2. Load config when device is initially selected
3. Populate forms with device-specific config

**User Flow**:
1. User selects Device A → loads Device A's config
2. User changes normal description → saves to Device A
3. User switches to Device B → loads Device B's config
4. User switches back to Device A → Device A's config restored

---

### Priority 4: Testing (Day 4) - 2-3 hours

**Test Scenarios**:

1. **Single Device Config**:
   - Set normal description for TEST1
   - Save and refresh page
   - Verify config persists

2. **Multi-Device Config**:
   - Set different configs for TEST1 and TEST2
   - Switch between devices
   - Verify each device shows its own config

3. **Config Isolation**:
   - Login as different user/org
   - Verify cannot access other org's device config
   - Verify config stays isolated

4. **Error Handling**:
   - Test with invalid inputs
   - Test with missing device
   - Verify error messages

---

### Priority 5: Documentation & Cleanup (Day 5) - 1-2 hours

1. Create `PHASE5_WEEK3_PROGRESS.md` with completion status
2. Update `PROJECT_PLAN.md` Week 3 checkboxes
3. Document config API in comments
4. Test end-to-end user flow

---

## 🚀 Quick Start

**Step 1**: Read the detailed plan
```bash
cat PHASE5_WEEK3_PLAN.md
```

**Step 2**: Start the test server
```bash
.venv/Scripts/python test_auth_server.py
```

**Step 3**: Begin with backend API
- Open `cloud/api/routes/devices.py`
- Add config endpoints (see PHASE5_WEEK3_PLAN.md for code)

**Step 4**: Test with curl
```bash
# Login to get token
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "devicetest@example.com", "password": "DeviceTest123!"}'

# Test config endpoints (use token from above)
curl http://localhost:8000/v1/devices/TEST1/config \
  -H "Authorization: Bearer <token>"
```

---

## 📚 Reference Documents

- **PHASE5_WEEK3_PLAN.md** - Detailed implementation guide with code examples
- **PROJECT_PLAN.md** - Overall project status
- **PHASE5_WEEK2_PROGRESS.md** - Previous week's implementation notes

---

## 💡 Key Files

**Backend**:
- `cloud/api/routes/devices.py` - Add GET/PUT /v1/devices/{id}/config
- `cloud/api/database/models.py` - Device.config column (already exists!)

**Frontend**:
- `cloud/web/static/js/device_config.js` - NEW: Config manager
- `cloud/web/static/js/device_manager.js` - MODIFY: Add config loading
- `cloud/web/templates/index.html` - MODIFY: Update form handlers

---

## ✅ Success Criteria

- [ ] GET /v1/devices/{id}/config returns device config
- [ ] PUT /v1/devices/{id}/config saves device config
- [ ] Normal description is per-device
- [ ] Trigger settings are per-device
- [ ] Notification settings are per-device
- [ ] Switching devices loads correct config
- [ ] Config persists after page refresh
- [ ] No config leakage between devices

---

**Ready to start? Begin with Priority 1 (Backend API)!** 🚀

See `PHASE5_WEEK3_PLAN.md` for detailed implementation guide with complete code examples.

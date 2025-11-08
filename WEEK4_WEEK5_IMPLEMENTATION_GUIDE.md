# Week 4 & Week 5 Implementation Guide

**Status**: ShareManager created (Week 4 Day 1-2 complete)
**Remaining**: Week 4 Day 3-5, Week 5 Day 1-5

This document provides detailed implementation instructions for completing Phase 5 Weeks 4-5.

---

## ✅ Completed: Week 4 Day 1-2 (ShareManager)

### What Was Done:
- ✅ Created `cloud/web/static/js/share_manager.js` - Full ShareManager class
- ✅ Added script include to `index.html`
- ✅ Implemented share modal creation and display
- ✅ QR code display and download
- ✅ Copy to clipboard functionality
- ✅ List and revoke share links methods

### Features Implemented:
- Create device/capture/date_range shares
- Configurable expiration (1-365 days)
- Optional view limits
- QR code generation
- Share URL copy
- Modal UI (created dynamically in JavaScript)

---

## 📋 Remaining Tasks

### Week 4 Day 3: Share Links Management Page

**Goal**: Create dedicated page to view and manage all share links

**Files to Create:**
1. `cloud/web/templates/shares.html`
2. `cloud/web/static/js/shares_page.js` (optional, can be inline)

**Files to Modify:**
1. `cloud/web/routes.py` - Add `/ui/shares` route
2. `cloud/web/templates/index.html` - Add navigation link

**Implementation Steps:**

#### 1. Add Route to `cloud/web/routes.py`

```python
@router.get("/shares")
async def shares_page(request: Request):
    """Share links management page"""
    return templates.TemplateResponse("shares.html", {"request": request})
```

#### 2. Create `cloud/web/templates/shares.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Share Links - Visant</title>
    <link rel="icon" type="image/png" href="/ui/static/favicon.png" />
    <!-- Copy styles from index.html or create shared CSS -->
    <style>
        /* Same base styles as index.html */
        /* Add table styles for share links list */
        .share-table {
            width: 100%;
            border-collapse: collapse;
        }
        .share-table th,
        .share-table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        .share-table th {
            background: #f9fafb;
            font-weight: 600;
        }
        .share-actions {
            display: flex;
            gap: 0.5rem;
        }
        .btn-sm {
            padding: 0.4rem 0.8rem;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <header>
        <h1>Share Links</h1>
        <div>
            <button onclick="window.location.href='/ui/'">Back to Dashboard</button>
        </div>
    </header>

    <main>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h2>Active Share Links</h2>
                <select id="deviceFilter" onchange="loadShareLinks()">
                    <option value="">All Devices</option>
                    <!-- Populated dynamically -->
                </select>
            </div>

            <table class="share-table">
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Type</th>
                        <th>Created</th>
                        <th>Expires</th>
                        <th>Views</th>
                        <th>Share URL</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="shareLinksBody">
                    <!-- Populated dynamically -->
                </tbody>
            </table>

            <div id="emptyState" style="display: none; text-align: center; padding: 3rem; color: #6b7280;">
                <p>No share links found. Create one from the dashboard!</p>
            </div>
        </div>
    </main>

    <script src="/static/js/auth.js"></script>
    <script src="/static/js/share_manager.js"></script>
    <script>
        let devices = [];

        async function loadDevices() {
            try {
                const response = await fetch('/v1/devices', {
                    headers: {
                        'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    devices = data.devices;

                    // Populate filter
                    const filter = document.getElementById('deviceFilter');
                    devices.forEach(device => {
                        const option = document.createElement('option');
                        option.value = device.device_id;
                        option.textContent = device.friendly_name || device.device_id;
                        filter.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        }

        async function loadShareLinks() {
            const deviceId = document.getElementById('deviceFilter').value;
            const shareLinks = await shareManager.listShareLinks(deviceId || null);

            const tbody = document.getElementById('shareLinksBody');
            const emptyState = document.getElementById('emptyState');

            if (shareLinks.length === 0) {
                tbody.innerHTML = '';
                emptyState.style.display = 'block';
                return;
            }

            emptyState.style.display = 'none';

            tbody.innerHTML = shareLinks.map(link => {
                const device = devices.find(d => d.device_id === link.device_id);
                const deviceName = device ? (device.friendly_name || device.device_id) : link.device_id;
                const created = new Date(link.created_at).toLocaleDateString();
                const expires = new Date(link.expires_at).toLocaleDateString();
                const views = link.max_views ? `${link.view_count}/${link.max_views}` : link.view_count;

                return `
                    <tr>
                        <td>${deviceName}</td>
                        <td><span class="badge">${link.share_type}</span></td>
                        <td>${created}</td>
                        <td>${expires}</td>
                        <td>${views}</td>
                        <td>
                            <input type="text" value="${link.share_url}" readonly style="width: 300px;" />
                            <button class="btn-sm" onclick="copyUrl('${link.share_url}')">Copy</button>
                        </td>
                        <td class="share-actions">
                            <button class="btn-sm" onclick="shareManager.showQRCode('${link.token}')">QR</button>
                            <button class="btn-sm" onclick="window.open('${link.share_url}', '_blank')">Open</button>
                            <button class="btn-sm btn-danger" onclick="revokeLink('${link.token}')">Revoke</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        async function revokeLink(token) {
            if (await shareManager.revokeShareLink(token)) {
                await loadShareLinks();
            }
        }

        function copyUrl(url) {
            navigator.clipboard.writeText(url);
            alert('Share URL copied!');
        }

        (async () => {
            await loadDevices();
            await loadShareLinks();
        })();
    </script>
</body>
</html>
```

#### 3. Add Navigation Link to `index.html`

Find the header section and add a link:
```html
<header>
    <h1>OK Monitor Dashboard</h1>
    <div>
        <a href="/ui/shares" style="margin-right: 1rem;">Share Links</a>
        <!-- Other header buttons -->
    </div>
</header>
```

---

### Week 4 Day 4-5: Device Management Page & Enhanced Wizard

**Goal**: Create device management page and enhance device wizard with API key display

**Files to Create:**
1. `cloud/web/templates/devices.html`

**Files to Modify:**
1. `cloud/web/routes.py` - Add `/ui/devices` route
2. `cloud/web/static/js/device_wizard.js` - Enhance success screen
3. `cloud/web/templates/index.html` - Add navigation link

**Implementation Steps:**

#### 1. Add Route to `cloud/web/routes.py`

```python
@router.get("/devices")
async def devices_page(request: Request):
    """Device management page"""
    return templates.TemplateResponse("devices.html", {"request": request})
```

#### 2. Create `cloud/web/templates/devices.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>My Cameras - Visant</title>
    <link rel="icon" type="image/png" href="/ui/static/favicon.png" />
    <!-- Styles -->
</head>
<body>
    <header>
        <h1>My Cameras</h1>
        <div>
            <button onclick="window.location.href='/ui/'">Dashboard</button>
            <button onclick="openAddDeviceWizard()">Add Camera</button>
        </div>
    </header>

    <main>
        <div class="panels" id="devicesGrid">
            <!-- Populated dynamically -->
        </div>
    </main>

    <script src="/static/js/auth.js"></script>
    <script src="/static/js/device_manager.js"></script>
    <script src="/static/js/device_wizard.js"></script>
    <script>
        async function loadDevices() {
            try {
                const response = await fetch('/v1/devices', {
                    headers: {
                        'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                    }
                });

                if (!response.ok) throw new Error('Failed to load devices');

                const data = await response.json();
                displayDevices(data.devices);
            } catch (error) {
                console.error('Error:', error);
            }
        }

        function displayDevices(devices) {
            const grid = document.getElementById('devicesGrid');

            if (devices.length === 0) {
                grid.innerHTML = '<p>No devices found. Click "Add Camera" to get started!</p>';
                return;
            }

            grid.innerHTML = devices.map(device => `
                <div class="card">
                    <h3>${device.friendly_name || device.device_id}</h3>
                    <p><strong>Device ID:</strong> ${device.device_id}</p>
                    <p><strong>Status:</strong> <span class="badge">${device.status}</span></p>
                    <p><strong>Activated:</strong> ${new Date(device.activated_at).toLocaleDateString()}</p>
                    <p><strong>Last Seen:</strong> ${device.last_seen_at ? new Date(device.last_seen_at).toLocaleDateString() : 'Never'}</p>
                    <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                        <button onclick="editDevice('${device.device_id}')">Edit Name</button>
                        <button onclick="viewConfig('${device.device_id}')">View Config</button>
                        <button onclick="deleteDevice('${device.device_id}')">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        function openAddDeviceWizard() {
            window.location.href = '/ui/';
            // TODO: Open wizard modal automatically
        }

        async function editDevice(deviceId) {
            const newName = prompt('Enter new friendly name:');
            if (!newName) return;

            try {
                const response = await fetch(`/v1/devices/${deviceId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                    },
                    body: JSON.stringify({ friendly_name: newName })
                });

                if (response.ok) {
                    await loadDevices();
                }
            } catch (error) {
                alert('Error updating device: ' + error.message);
            }
        }

        async function deleteDevice(deviceId) {
            if (!confirm('Are you sure? This cannot be undone.')) return;

            try {
                const response = await fetch(`/v1/devices/${deviceId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                    }
                });

                if (response.ok) {
                    await loadDevices();
                }
            } catch (error) {
                alert('Error deleting device: ' + error.message);
            }
        }

        function viewConfig(deviceId) {
            window.location.href = `/ui/?device=${deviceId}`;
        }

        loadDevices();
    </script>
</body>
</html>
```

#### 3. Enhance Device Wizard Success Screen

Modify `cloud/web/static/js/device_wizard.js` to show API key on success:

Find the `showSuccess()` method and update it to display the API key prominently with a warning that it will only be shown once.

---

### Week 5 Day 1: User Menu Component

**Goal**: Add user profile menu to all pages

**Files to Create:**
1. `cloud/web/static/js/user_menu.js`

**Files to Modify:**
1. All template HTML files - Add user menu to header

**Implementation Steps:**

#### 1. Create `cloud/web/static/js/user_menu.js`

```javascript
class UserMenu {
    constructor() {
        this.menuVisible = false;
    }

    init() {
        this.createUserMenu();
        this.loadUserInfo();
    }

    createUserMenu() {
        const menuHTML = `
            <div id="userMenuContainer" style="position: relative;">
                <button id="userMenuButton" class="user-menu-btn" onclick="userMenu.toggleMenu()">
                    <span id="userInitial">?</span>
                </button>
                <div id="userMenuDropdown" class="user-menu-dropdown" style="display: none;">
                    <div class="user-menu-header">
                        <div id="userEmail">Loading...</div>
                        <div id="orgName" style="font-size: 0.875rem; color: #6b7280;">Loading...</div>
                    </div>
                    <div class="user-menu-divider"></div>
                    <a href="/ui/" class="user-menu-item">Dashboard</a>
                    <a href="/ui/devices" class="user-menu-item">My Cameras</a>
                    <a href="/ui/shares" class="user-menu-item">Share Links</a>
                    <a href="/ui/settings" class="user-menu-item">Settings</a>
                    <div class="user-menu-divider"></div>
                    <button class="user-menu-item" onclick="userMenu.logout()">Logout</button>
                    <div class="user-menu-footer">Powered by Visant</div>
                </div>
            </div>
        `;

        // Inject into header (adjust selector based on your header structure)
        const header = document.querySelector('header');
        if (header) {
            const container = document.createElement('div');
            container.innerHTML = menuHTML.trim();
            header.appendChild(container.firstChild);
        }
    }

    async loadUserInfo() {
        try {
            const response = await fetch('/v1/auth/me', {
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                document.getElementById('userEmail').textContent = user.email;
                document.getElementById('orgName').textContent = user.org_name || 'Organization';
                document.getElementById('userInitial').textContent = user.email[0].toUpperCase();
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
    }

    toggleMenu() {
        const dropdown = document.getElementById('userMenuDropdown');
        this.menuVisible = !this.menuVisible;
        dropdown.style.display = this.menuVisible ? 'block' : 'none';
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            sessionStorage.clear();
            window.location.href = '/ui/login';
        }
    }
}

const userMenu = new UserMenu();
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => userMenu.init());
} else {
    userMenu.init();
}
```

#### 2. Add Styles for User Menu

Add to `<style>` section of each page:

```css
.user-menu-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #3b82f6;
    color: white;
    border: none;
    cursor: pointer;
    font-weight: 600;
}

.user-menu-dropdown {
    position: absolute;
    right: 0;
    top: 50px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    min-width: 220px;
    z-index: 1000;
}

.user-menu-header {
    padding: 1rem;
    border-bottom: 1px solid #e5e7eb;
}

.user-menu-item {
    display: block;
    width: 100%;
    padding: 0.75rem 1rem;
    text-align: left;
    border: none;
    background: none;
    cursor: pointer;
    text-decoration: none;
    color: #374151;
}

.user-menu-item:hover {
    background: #f9fafb;
}

.user-menu-footer {
    padding: 0.75rem 1rem;
    font-size: 0.75rem;
    color: #9ca3af;
    text-align: center;
    border-top: 1px solid #e5e7eb;
}

.user-menu-divider {
    height: 1px;
    background: #e5e7eb;
}
```

---

### Week 5 Day 2: Settings Page

**Goal**: Create settings page to display user and organization information

**Files to Create:**
1. `cloud/web/templates/settings.html`

**Files to Modify:**
1. `cloud/web/routes.py` - Add `/ui/settings` route

**Implementation Steps:**

#### 1. Add Route

```python
@router.get("/settings")
async def settings_page(request: Request):
    """User settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})
```

#### 2. Create `settings.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Settings - Visant</title>
    <link rel="icon" type="image/png" href="/ui/static/favicon.png" />
    <!-- Styles -->
</head>
<body>
    <header>
        <h1>Settings</h1>
        <button onclick="window.location.href='/ui/'">Back to Dashboard</button>
    </header>

    <main>
        <div class="card">
            <h2>Organization Settings</h2>
            <div class="settings-row">
                <label>Organization Name:</label>
                <span id="orgName">Loading...</span>
            </div>
            <div class="settings-row">
                <label>Created:</label>
                <span id="orgCreated">Loading...</span>
            </div>
            <div class="settings-row">
                <label>Active Devices:</label>
                <span id="deviceCount">Loading...</span>
            </div>
        </div>

        <div class="card">
            <h2>User Profile</h2>
            <div class="settings-row">
                <label>Email:</label>
                <span id="userEmail">Loading...</span>
            </div>
            <div class="settings-row">
                <label>Member Since:</label>
                <span id="memberSince">Loading...</span>
            </div>
        </div>
    </main>

    <script src="/static/js/auth.js"></script>
    <script src="/static/js/user_menu.js"></script>
    <script>
        async function loadSettings() {
            try {
                const [userResponse, devicesResponse] = await Promise.all([
                    fetch('/v1/auth/me', {
                        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}` }
                    }),
                    fetch('/v1/devices', {
                        headers: { 'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}` }
                    })
                ]);

                if (userResponse.ok) {
                    const user = await userResponse.json();
                    document.getElementById('orgName').textContent = user.org_name || 'N/A';
                    document.getElementById('userEmail').textContent = user.email;
                    document.getElementById('memberSince').textContent = new Date(user.created_at).toLocaleDateString();
                }

                if (devicesResponse.ok) {
                    const devices = await devicesResponse.json();
                    document.getElementById('deviceCount').textContent = devices.devices.length;
                }
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }

        loadSettings();
    </script>
</body>
</html>
```

---

### Week 5 Day 3-4: Bug Fixes & Polish

**Areas to Address:**

1. **Error Handling**
   - Add try/catch to all async functions
   - Display user-friendly error messages
   - Handle network errors gracefully

2. **Loading States**
   - Add loading spinners to buttons during API calls
   - Show skeleton loaders for data loading
   - Disable buttons during operations

3. **Mobile Responsive**
   - Test on mobile devices
   - Fix modal layouts for small screens
   - Adjust table layouts to be scrollable

4. **Cross-Browser Testing**
   - Test on Chrome, Firefox, Safari, Edge
   - Fix any browser-specific issues

5. **UX Polish**
   - Add toast notifications for success/error
   - Confirm dialogs for destructive actions
   - Keyboard shortcuts (ESC to close modals)
   - Focus management in modals
   - ARIA labels for accessibility

---

### Week 5 Day 5: End-to-End Testing

**Test Scenarios:**

1. **New User Flow**
   - Sign up
   - Activate first device
   - View dashboard
   - Create share link
   - Test public share page

2. **Multi-Device User**
   - Switch between devices
   - Verify config loads correctly
   - Test device-specific share links

3. **Share Link Management**
   - Create various share types
   - Revoke share links
   - Test QR codes
   - Verify view counts

4. **Settings & Profile**
   - View user info
   - Check device counts
   - Test logout

**Performance Testing:**
- Load dashboard with 100+ captures
- Create 20 share links
- Switch devices rapidly
- Monitor response times (<2s target)

**Security Audit:**
- Verify JWT tokens in sessionStorage
- Test org isolation (no cross-org data)
- Verify share link token randomness
- Test expired share links

---

## Summary

### Completed:
- ✅ Week 4 Day 1-2: ShareManager

### Remaining:
- ⏳ Week 4 Day 3: Shares page
- ⏳ Week 4 Day 4-5: Devices page
- ⏳ Week 5 Day 1: User menu
- ⏳ Week 5 Day 2: Settings page
- ⏳ Week 5 Day 3-4: Polish
- ⏳ Week 5 Day 5: Testing

### Files Created So Far:
1. `cloud/web/static/js/share_manager.js` ✅

### Files Still Needed:
1. `cloud/web/templates/shares.html`
2. `cloud/web/templates/devices.html`
3. `cloud/web/templates/settings.html`
4. `cloud/web/static/js/user_menu.js`

### Estimated Effort:
- Week 4 remaining: 6-8 hours
- Week 5: 10-12 hours
- Total: 16-20 hours

This guide provides all the code and instructions needed to complete Phase 5 Weeks 4-5.

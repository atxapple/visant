/**
 * Device Manager
 *
 * Handles device list fetching and selection UI with smart logic:
 * - 0 devices: Show "Add Camera" prompt
 * - 1 device: Show device name only (no dropdown)
 * - 2+ devices: Show dropdown selector
 */

class DeviceManager {
    constructor(authManager) {
        this.auth = authManager;
        this.API_URL = window.location.origin;
        this.devices = [];
        this.selectedDeviceId = null;
        this.onDeviceChange = null; // Callback when device selection changes
    }

    /**
     * Fetch devices from API
     */
    async fetchDevices() {
        try {
            const response = await fetch(`${this.API_URL}/v1/devices`, {
                method: 'GET',
                headers: this.auth.getAuthHeaders()
            });

            if (!response.ok) {
                console.error('Failed to fetch devices:', response.status);
                return [];
            }

            const data = await response.json();
            this.devices = data.devices || [];

            // Auto-select first device if none selected
            if (this.devices.length > 0 && !this.selectedDeviceId) {
                this.selectedDeviceId = this.devices[0].device_id;
            }

            return this.devices;
        } catch (error) {
            console.error('Error fetching devices:', error);
            return [];
        }
    }

    /**
     * Get currently selected device
     */
    getSelectedDevice() {
        if (!this.selectedDeviceId) return null;
        return this.devices.find(d => d.device_id === this.selectedDeviceId);
    }

    /**
     * Set selected device
     */
    async selectDevice(deviceId) {
        this.selectedDeviceId = deviceId;

        // Load config for this device
        if (typeof deviceConfigManager !== 'undefined') {
            const config = await deviceConfigManager.loadConfig(deviceId);
            if (config) {
                deviceConfigManager.populateForms(config);
            }
        }

        if (this.onDeviceChange) {
            this.onDeviceChange(deviceId);
        }
        this.renderDeviceSelector();
    }

    /**
     * Render device selector UI with smart logic
     */
    renderDeviceSelector() {
        const container = document.getElementById('device-selector-container');
        if (!container) return;

        const deviceCount = this.devices.length;

        if (deviceCount === 0) {
            // No devices - show prompt to add camera
            container.innerHTML = `
                <div class="no-devices-prompt">
                    <p class="muted" style="margin: 0;">No cameras connected</p>
                    <button class="btn-add-device btn-small" onclick="deviceWizard.openModal()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                        Add Your First Camera
                    </button>
                </div>
            `;
        } else if (deviceCount === 1) {
            // Single device - just show name
            const device = this.devices[0];
            container.innerHTML = `
                <div class="single-device-display">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                        <circle cx="12" cy="13" r="4"/>
                    </svg>
                    <div>
                        <div class="device-name">${this.escapeHtml(device.friendly_name)}</div>
                        <div class="device-id-small">${device.device_id}</div>
                    </div>
                    <span class="status-badge status-${device.status}">${device.status}</span>
                </div>
            `;
        } else {
            // Multiple devices - show dropdown
            const selectedDevice = this.getSelectedDevice();
            const options = this.devices.map(d =>
                `<option value="${d.device_id}" ${d.device_id === this.selectedDeviceId ? 'selected' : ''}>
                    ${this.escapeHtml(d.friendly_name)} (${d.device_id})
                </option>`
            ).join('');

            container.innerHTML = `
                <div class="device-selector">
                    <label for="device-select">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                            <circle cx="12" cy="13" r="4"/>
                        </svg>
                        Camera:
                    </label>
                    <select id="device-select" onchange="deviceManager.selectDevice(this.value)">
                        ${options}
                    </select>
                    ${selectedDevice ? `<span class="status-badge status-${selectedDevice.status}">${selectedDevice.status}</span>` : ''}
                </div>
            `;
        }
    }

    /**
     * Initialize device selector
     */
    async initialize(containerId = 'device-selector-container') {
        // Create container if it doesn't exist
        let container = document.getElementById(containerId);
        if (!container) {
            // Insert container in header
            const header = document.querySelector('header');
            if (header) {
                const deviceContainer = document.createElement('div');
                deviceContainer.id = containerId;
                deviceContainer.style.cssText = 'flex: 1; display: flex; justify-content: center; align-items: center;';

                // Insert between title and buttons
                const headerChildren = Array.from(header.children);
                if (headerChildren.length >= 2) {
                    header.insertBefore(deviceContainer, headerChildren[1]);
                } else {
                    header.appendChild(deviceContainer);
                }
            }
        }

        // Fetch and render
        await this.fetchDevices();
        this.renderDeviceSelector();

        // Return selected device for initial setup
        return this.getSelectedDevice();
    }

    /**
     * Refresh device list
     */
    async refresh() {
        await this.fetchDevices();
        this.renderDeviceSelector();
        return this.getSelectedDevice();
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-initialize when DOM loads
let deviceManager;
document.addEventListener('DOMContentLoaded', () => {
    if (typeof auth !== 'undefined') {
        deviceManager = new DeviceManager(auth);
        // Initialize after a short delay to ensure DOM is ready
        setTimeout(async () => {
            await deviceManager.initialize();
        }, 100);
    }
});

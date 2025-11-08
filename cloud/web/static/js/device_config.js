/**
 * Device Configuration Manager
 *
 * Manages loading and saving device-specific configuration.
 * Each device has its own:
 * - Normal description (for AI classification)
 * - Trigger settings (recurring trigger, interval)
 * - Notification settings (email addresses, cooldown)
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
                console.error('Failed to load device config:', response.status);
                return null;
            }

            const data = await response.json();
            this.currentDeviceId = deviceId;
            this.currentConfig = data.config;

            console.log(`[DeviceConfig] Loaded config for ${deviceId}`, this.currentConfig);
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
                console.error('Failed to save device config:', response.status);
                return false;
            }

            const data = await response.json();
            this.currentConfig = data.config;

            console.log(`[DeviceConfig] Saved config for ${this.currentDeviceId}`, this.currentConfig);
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
        if (!config) {
            console.warn('[DeviceConfig] No config to populate');
            return;
        }

        console.log('[DeviceConfig] Populating forms with config', config);

        // Normal description
        const normalText = document.getElementById('normal-text');
        if (normalText) {
            normalText.value = config.normal_description || '';
        }

        // Trigger settings
        if (config.trigger) {
            const triggerEnabled = document.getElementById('trigger-enabled');
            const intervalInput = document.getElementById('interval-input');

            if (triggerEnabled) {
                triggerEnabled.checked = config.trigger.enabled || false;
            }
            if (intervalInput) {
                intervalInput.value = config.trigger.interval_seconds || 10;
            }
        }

        // Notification settings
        if (config.notification) {
            const emailEnabled = document.getElementById('email-enabled');
            const emailAddresses = document.getElementById('email-addresses');
            const emailCooldown = document.getElementById('email-cooldown');

            if (emailEnabled) {
                emailEnabled.checked = config.notification.email_enabled !== false;
            }
            if (emailAddresses && config.notification.email_addresses) {
                emailAddresses.value = config.notification.email_addresses.join(', ');
            }
            if (emailCooldown) {
                emailCooldown.value = config.notification.email_cooldown_minutes || 10;
            }
        }
    }

    /**
     * Clear all form fields
     */
    clearForms() {
        const normalText = document.getElementById('normal-text');
        if (normalText) normalText.value = '';

        const triggerEnabled = document.getElementById('trigger-enabled');
        if (triggerEnabled) triggerEnabled.checked = false;

        const intervalInput = document.getElementById('interval-input');
        if (intervalInput) intervalInput.value = 10;

        const emailEnabled = document.getElementById('email-enabled');
        if (emailEnabled) emailEnabled.checked = true;

        const emailAddresses = document.getElementById('email-addresses');
        if (emailAddresses) emailAddresses.value = '';

        const emailCooldown = document.getElementById('email-cooldown');
        if (emailCooldown) emailCooldown.value = 10;
    }

    /**
     * Show status message
     */
    showStatus(elementId, message, isSuccess = true) {
        const statusEl = document.getElementById(elementId);
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = isSuccess ? 'status success' : 'status error';
            statusEl.style.display = 'block';

            // Auto-hide after 3 seconds
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * Setup form handlers
     */
    setupFormHandlers() {
        // Normal description form
        const normalForm = document.getElementById('normal-form');
        if (normalForm) {
            normalForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const normalText = document.getElementById('normal-text').value.trim();

                const success = await this.saveConfig({
                    normal_description: normalText
                });

                this.showStatus(
                    'normal-status',
                    success ? 'Description saved' : 'Failed to save description',
                    success
                );
            });
        }

        // Trigger form
        const triggerForm = document.getElementById('trigger-form');
        if (triggerForm) {
            triggerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const enabled = document.getElementById('trigger-enabled').checked;
                const interval = parseInt(document.getElementById('interval-input').value);

                const success = await this.saveConfig({
                    trigger: {
                        enabled: enabled,
                        interval_seconds: interval,
                        digital_input_enabled: false
                    }
                });

                this.showStatus(
                    'trigger-status',
                    success ? 'Trigger settings saved' : 'Failed to save trigger settings',
                    success
                );
            });
        }

        // Notification settings
        const notifySubmit = document.getElementById('notify-submit');
        if (notifySubmit) {
            // Enable the button
            notifySubmit.disabled = false;

            notifySubmit.addEventListener('click', async () => {
                const emailEnabled = document.getElementById('email-enabled').checked;
                const emailAddresses = document.getElementById('email-addresses').value
                    .split(',')
                    .map(e => e.trim())
                    .filter(e => e);
                const cooldown = parseInt(document.getElementById('email-cooldown').value);

                const success = await this.saveConfig({
                    notification: {
                        email_enabled: emailEnabled,
                        email_addresses: emailAddresses,
                        email_cooldown_minutes: cooldown,
                        digital_output_enabled: false
                    }
                });

                this.showStatus(
                    'notify-status',
                    success ? 'Notification settings saved' : 'Failed to save notification settings',
                    success
                );
            });
        }

        console.log('[DeviceConfig] Form handlers setup complete');
    }
}

// Initialize when DOM is loaded
let deviceConfigManager;
document.addEventListener('DOMContentLoaded', () => {
    // Wait for auth manager to be available
    if (typeof auth !== 'undefined') {
        deviceConfigManager = new DeviceConfigManager(auth);
        deviceConfigManager.setupFormHandlers();
        console.log('[DeviceConfig] Device config manager initialized');
    } else {
        console.error('[DeviceConfig] Auth manager not available');
    }
});

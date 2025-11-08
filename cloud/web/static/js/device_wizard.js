/**
 * Device Activation Wizard
 *
 * Handles the multi-step device activation flow:
 * 1. Enter Device ID
 * 2. Validate device (check availability)
 * 3. Enter activation code or proceed with subscription
 * 4. Activate device and show success
 */

class DeviceWizard {
    constructor(authManager) {
        this.auth = authManager;
        this.API_URL = window.location.origin;
        this.currentDeviceId = null;
        this.currentStep = 1;

        this.initializeModal();
        this.attachEventListeners();
    }

    /**
     * Initialize modal HTML
     */
    initializeModal() {
        const modalHTML = `
            <div id="deviceWizardModal" class="modal" style="display: none;">
                <div class="modal-overlay" onclick="deviceWizard.closeModal()"></div>
                <div class="modal-content">
                    <!-- Step 1: Enter Device ID -->
                    <div id="wizardStep1" class="wizard-step">
                        <div class="modal-header">
                            <h2>Add New Camera</h2>
                            <button class="modal-close" onclick="deviceWizard.closeModal()">&times;</button>
                        </div>
                        <div class="modal-body">
                            <p class="modal-description">Enter the 5-character Device ID found on your camera sticker</p>
                            <div class="form-group">
                                <label for="deviceIdInput">Device ID</label>
                                <input
                                    type="text"
                                    id="deviceIdInput"
                                    placeholder="ABC12"
                                    maxlength="5"
                                    style="text-transform: uppercase;"
                                    autocomplete="off"
                                />
                                <div id="deviceIdError" class="error-message" style="display: none;"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn-secondary" onclick="deviceWizard.closeModal()">Cancel</button>
                            <button class="btn-primary" onclick="deviceWizard.validateDevice()">Next →</button>
                        </div>
                    </div>

                    <!-- Step 2: Activation Options -->
                    <div id="wizardStep2" class="wizard-step" style="display: none;">
                        <div class="modal-header">
                            <h2>Activate Camera</h2>
                            <button class="modal-close" onclick="deviceWizard.closeModal()">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="device-info">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                                    <circle cx="12" cy="13" r="4"/>
                                </svg>
                                <div>
                                    <div class="device-id-display" id="deviceIdDisplay"></div>
                                    <div class="status-badge status-available">Available</div>
                                </div>
                            </div>

                            <div class="form-group">
                                <label for="friendlyNameInput">Camera Name (optional)</label>
                                <input
                                    type="text"
                                    id="friendlyNameInput"
                                    placeholder="e.g., Front Door Camera"
                                    autocomplete="off"
                                />
                            </div>

                            <div class="form-group">
                                <label for="activationCodeInput">Activation Code (optional)</label>
                                <input
                                    type="text"
                                    id="activationCodeInput"
                                    placeholder="Enter promotional code"
                                    style="text-transform: uppercase;"
                                    autocomplete="off"
                                />
                                <div class="help-text">If you have a promotional code, enter it here. Otherwise, your subscription will be used.</div>
                                <div id="activationCodeError" class="error-message" style="display: none;"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn-secondary" onclick="deviceWizard.goToStep(1)">← Back</button>
                            <button class="btn-primary" onclick="deviceWizard.activateDevice()">Activate Camera</button>
                        </div>
                    </div>

                    <!-- Step 3: Success -->
                    <div id="wizardStep3" class="wizard-step" style="display: none;">
                        <div class="modal-header">
                            <h2>Camera Activated!</h2>
                            <button class="modal-close" onclick="deviceWizard.closeModal()">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="success-icon">
                                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
                                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                    <polyline points="22 4 12 14.01 9 11.01"/>
                                </svg>
                            </div>

                            <div id="successMessage" class="success-message"></div>

                            <div class="api-key-section" id="apiKeySection" style="display: none;">
                                <div class="warning-box">
                                    <strong>⚠️ Important: Save your API key!</strong>
                                    <p>This API key will only be shown once. Copy it now and configure your camera device.</p>
                                </div>
                                <div class="api-key-display">
                                    <code id="apiKeyDisplay"></code>
                                    <button class="btn-copy" onclick="deviceWizard.copyApiKey()">Copy</button>
                                </div>
                            </div>

                            <div id="codeBenefitSection" style="display: none;">
                                <div class="benefit-box">
                                    <h3>Code Benefits Applied</h3>
                                    <div id="benefitDetails"></div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn-primary" onclick="deviceWizard.closeAndRefresh()">Done</button>
                        </div>
                    </div>

                    <!-- Loading indicator -->
                    <div id="wizardLoading" class="wizard-loading" style="display: none;">
                        <div class="spinner"></div>
                        <p>Processing...</p>
                    </div>
                </div>
            </div>
        `;

        // Inject modal into DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Enter key on device ID input
        const deviceIdInput = document.getElementById('deviceIdInput');
        if (deviceIdInput) {
            deviceIdInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.validateDevice();
                }
            });

            // Auto-uppercase input
            deviceIdInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        }

        // Enter key on activation code input
        const codeInput = document.getElementById('activationCodeInput');
        if (codeInput) {
            codeInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.activateDevice();
                }
            });

            // Auto-uppercase input
            codeInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        }
    }

    /**
     * Open the wizard modal
     */
    openModal() {
        document.getElementById('deviceWizardModal').style.display = 'flex';
        this.goToStep(1);
        // Focus on device ID input
        setTimeout(() => {
            document.getElementById('deviceIdInput').focus();
        }, 100);
    }

    /**
     * Close the wizard modal
     */
    closeModal() {
        document.getElementById('deviceWizardModal').style.display = 'none';
        this.resetWizard();
    }

    /**
     * Close modal and refresh device list
     */
    closeAndRefresh() {
        this.closeModal();
        // Refresh device manager if available
        if (typeof deviceManager !== 'undefined') {
            deviceManager.refresh();
        } else {
            // Fallback to full page reload
            window.location.reload();
        }
    }

    /**
     * Reset wizard to initial state
     */
    resetWizard() {
        this.currentDeviceId = null;
        this.currentStep = 1;
        document.getElementById('deviceIdInput').value = '';
        document.getElementById('friendlyNameInput').value = '';
        document.getElementById('activationCodeInput').value = '';
        this.hideError('deviceIdError');
        this.hideError('activationCodeError');
    }

    /**
     * Navigate to specific step
     */
    goToStep(stepNumber) {
        // Hide all steps
        for (let i = 1; i <= 3; i++) {
            document.getElementById(`wizardStep${i}`).style.display = 'none';
        }

        // Show target step
        document.getElementById(`wizardStep${stepNumber}`).style.display = 'block';
        this.currentStep = stepNumber;
    }

    /**
     * Show loading indicator
     */
    showLoading() {
        document.getElementById('wizardLoading').style.display = 'flex';
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        document.getElementById('wizardLoading').style.display = 'none';
    }

    /**
     * Show error message
     */
    showError(elementId, message) {
        const errorEl = document.getElementById(elementId);
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }

    /**
     * Hide error message
     */
    hideError(elementId) {
        const errorEl = document.getElementById(elementId);
        errorEl.style.display = 'none';
    }

    /**
     * Step 1: Validate device ID
     */
    async validateDevice() {
        const deviceId = document.getElementById('deviceIdInput').value.trim().toUpperCase();

        // Validation
        if (!deviceId) {
            this.showError('deviceIdError', 'Please enter a device ID');
            return;
        }

        if (!/^[A-Z0-9]{5}$/.test(deviceId)) {
            this.showError('deviceIdError', 'Device ID must be 5 uppercase alphanumeric characters');
            return;
        }

        this.hideError('deviceIdError');
        this.showLoading();

        try {
            const response = await fetch(`${this.API_URL}/v1/devices/validate`, {
                method: 'POST',
                headers: this.auth.getAuthHeaders(),
                body: JSON.stringify({ device_id: deviceId })
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('deviceIdError', 'Device ID not found. Please check the ID on your camera sticker.');
                } else if (response.status === 409) {
                    this.showError('deviceIdError', 'This device is already activated by another user.');
                } else {
                    this.showError('deviceIdError', data.detail || 'Validation failed');
                }
                return;
            }

            // Check validation result
            if (data.status === 'already_activated_by_you') {
                this.showError('deviceIdError', data.message);
                return;
            }

            if (data.can_activate) {
                // Success! Move to step 2
                this.currentDeviceId = deviceId;
                document.getElementById('deviceIdDisplay').textContent = deviceId;
                this.goToStep(2);

                // Set default friendly name
                const defaultName = deviceId.replace(/(.{3})(.{2})/, '$1-$2');
                document.getElementById('friendlyNameInput').placeholder = `Camera ${defaultName}`;
            } else {
                this.showError('deviceIdError', data.message || 'Device cannot be activated');
            }

        } catch (error) {
            console.error('Validation error:', error);
            this.showError('deviceIdError', 'Failed to validate device. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Step 2: Activate device
     */
    async activateDevice() {
        if (!this.currentDeviceId) {
            return;
        }

        const friendlyName = document.getElementById('friendlyNameInput').value.trim();
        const activationCode = document.getElementById('activationCodeInput').value.trim().toUpperCase();

        this.hideError('activationCodeError');
        this.showLoading();

        try {
            const requestBody = {
                device_id: this.currentDeviceId,
                friendly_name: friendlyName || null,
                activation_code: activationCode || null
            };

            const response = await fetch(`${this.API_URL}/v1/devices/activate`, {
                method: 'POST',
                headers: this.auth.getAuthHeaders(),
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 402) {
                    this.showError('activationCodeError', 'Please enter an activation code or subscribe to continue.');
                } else if (response.status === 404) {
                    this.showError('activationCodeError', 'Invalid activation code.');
                } else if (response.status === 410) {
                    this.showError('activationCodeError', 'Activation code has expired.');
                } else if (response.status === 429) {
                    this.showError('activationCodeError', 'Activation code usage limit reached.');
                } else if (response.status === 409) {
                    this.showError('activationCodeError', 'You already used this activation code.');
                } else {
                    this.showError('activationCodeError', data.detail || 'Activation failed');
                }
                return;
            }

            // Success! Show step 3
            this.showSuccessScreen(data);

        } catch (error) {
            console.error('Activation error:', error);
            this.showError('activationCodeError', 'Failed to activate device. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Show success screen with activation details
     */
    showSuccessScreen(data) {
        // Build success message
        let message = `<h3>${data.friendly_name}</h3>`;
        message += `<p class="muted">Device ID: ${data.device_id}</p>`;
        message += `<p>Your camera has been successfully activated and is ready to use!</p>`;

        document.getElementById('successMessage').innerHTML = message;

        // Show API key
        if (data.api_key) {
            document.getElementById('apiKeyDisplay').textContent = data.api_key;
            document.getElementById('apiKeySection').style.display = 'block';
        }

        // Show code benefits if applied
        if (data.code_benefit) {
            const benefit = data.code_benefit;
            let benefitHTML = `
                <p><strong>Code:</strong> ${benefit.code}</p>
                <p><strong>Benefit:</strong> ${benefit.benefit}</p>
            `;
            if (benefit.expires_at) {
                const expiryDate = new Date(benefit.expires_at).toLocaleDateString();
                benefitHTML += `<p><strong>Expires:</strong> ${expiryDate}</p>`;
            }
            document.getElementById('benefitDetails').innerHTML = benefitHTML;
            document.getElementById('codeBenefitSection').style.display = 'block';
        }

        this.goToStep(3);
    }

    /**
     * Copy API key to clipboard
     */
    async copyApiKey() {
        const apiKey = document.getElementById('apiKeyDisplay').textContent;

        try {
            await navigator.clipboard.writeText(apiKey);

            // Show feedback
            const copyBtn = document.querySelector('.btn-copy');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            copyBtn.style.background = '#10b981';

            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '';
            }, 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
            alert('Failed to copy API key. Please copy it manually.');
        }
    }
}

// Initialize wizard when DOM is loaded
let deviceWizard;
document.addEventListener('DOMContentLoaded', () => {
    // Assuming AuthManager is already initialized as 'auth'
    if (typeof auth !== 'undefined') {
        deviceWizard = new DeviceWizard(auth);
    }
});

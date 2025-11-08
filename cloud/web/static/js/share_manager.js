/**
 * ShareManager - Handles share link creation and management
 *
 * Features:
 * - Create share links (device/capture/date_range)
 * - List existing share links
 * - Revoke share links
 * - Generate and display QR codes
 * - Copy share URLs to clipboard
 */

class ShareManager {
    constructor() {
        this.modal = null;
        this.qrModal = null;
        this.currentDeviceId = null;
        this.currentCaptureId = null;
    }

    /**
     * Initialize the share manager and create modal HTML
     */
    init() {
        this.createShareModal();
        this.createQRModal();
    }

    /**
     * Create the share link modal HTML
     */
    createShareModal() {
        const modalHTML = `
            <div id="shareModal" class="modal" style="display: none;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h2>Create Share Link</h2>
                        <button class="modal-close" onclick="shareManager.closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="shareForm">
                            <div class="form-group">
                                <label>Share Type</label>
                                <select id="shareType" class="form-control" onchange="shareManager.onShareTypeChange()">
                                    <option value="device">Entire Device (all captures)</option>
                                    <option value="capture">Single Capture</option>
                                    <option value="date_range">Date Range</option>
                                </select>
                            </div>

                            <div id="captureIdGroup" class="form-group" style="display: none;">
                                <label>Capture ID</label>
                                <input type="text" id="captureId" class="form-control" readonly />
                            </div>

                            <div id="dateRangeGroup" class="form-group" style="display: none;">
                                <label>Start Date</label>
                                <input type="datetime-local" id="startDate" class="form-control" />
                                <label style="margin-top: 0.5rem;">End Date</label>
                                <input type="datetime-local" id="endDate" class="form-control" />
                            </div>

                            <div class="form-group">
                                <label>Expires In (days)</label>
                                <input type="number" id="expiresInDays" class="form-control" value="7" min="1" max="365" />
                                <small>Link will expire after this many days</small>
                            </div>

                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="enableMaxViews" onchange="shareManager.toggleMaxViews()" />
                                    Limit number of views
                                </label>
                                <input type="number" id="maxViews" class="form-control" value="100" min="1" disabled style="margin-top: 0.5rem;" />
                            </div>

                            <div class="form-actions">
                                <button type="button" class="btn btn-secondary" onclick="shareManager.closeModal()">Cancel</button>
                                <button type="button" class="btn btn-primary" onclick="shareManager.createShareLink()" id="createShareBtn">
                                    Create Share Link
                                </button>
                            </div>
                        </form>

                        <div id="shareResult" style="display: none; margin-top: 1.5rem;">
                            <div style="padding: 1rem; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #0ea5e9;">
                                <h3 style="margin: 0 0 1rem 0; font-size: 1rem;">Share Link Created!</h3>

                                <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                                    <input type="text" id="shareUrl" class="form-control" readonly style="flex: 1;" />
                                    <button class="btn btn-primary" onclick="shareManager.copyToClipboard()">Copy</button>
                                </div>

                                <div style="text-align: center; margin-bottom: 1rem;">
                                    <img id="shareQRCode" src="" alt="QR Code" style="max-width: 200px; border: 1px solid #ddd; border-radius: 8px;" />
                                </div>

                                <div style="display: flex; gap: 0.5rem;">
                                    <button class="btn btn-secondary" onclick="shareManager.openShareLink()">Open Public Page</button>
                                    <button class="btn btn-secondary" onclick="shareManager.downloadQRCode()">Download QR</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert modal into body
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = modalHTML.trim();
        document.body.appendChild(tempDiv.firstChild);
        this.modal = document.getElementById('shareModal');
    }

    /**
     * Create QR code preview modal
     */
    createQRModal() {
        const modalHTML = `
            <div id="qrModal" class="modal" style="display: none;">
                <div class="modal-content" style="max-width: 400px;">
                    <div class="modal-header">
                        <h2>QR Code</h2>
                        <button class="modal-close" onclick="shareManager.closeQRModal()">&times;</button>
                    </div>
                    <div class="modal-body" style="text-align: center;">
                        <img id="qrModalImage" src="" alt="QR Code" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;" />
                        <div style="margin-top: 1rem;">
                            <button class="btn btn-primary" onclick="shareManager.downloadQRFromModal()">Download</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = modalHTML.trim();
        document.body.appendChild(tempDiv.firstChild);
        this.qrModal = document.getElementById('qrModal');
    }

    /**
     * Open share modal for device
     */
    openShareModal(deviceId, captureId = null) {
        this.currentDeviceId = deviceId;
        this.currentCaptureId = captureId;

        // Reset form
        document.getElementById('shareForm').reset();
        document.getElementById('shareResult').style.display = 'none';
        document.getElementById('expiresInDays').value = 7;

        // Set capture ID if provided
        if (captureId) {
            document.getElementById('shareType').value = 'capture';
            document.getElementById('captureId').value = captureId;
            this.onShareTypeChange();
        }

        this.modal.style.display = 'flex';
    }

    /**
     * Close share modal
     */
    closeModal() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    /**
     * Close QR modal
     */
    closeQRModal() {
        if (this.qrModal) {
            this.qrModal.style.display = 'none';
        }
    }

    /**
     * Handle share type change
     */
    onShareTypeChange() {
        const shareType = document.getElementById('shareType').value;
        const captureIdGroup = document.getElementById('captureIdGroup');
        const dateRangeGroup = document.getElementById('dateRangeGroup');

        captureIdGroup.style.display = shareType === 'capture' ? 'block' : 'none';
        dateRangeGroup.style.display = shareType === 'date_range' ? 'block' : 'none';
    }

    /**
     * Toggle max views input
     */
    toggleMaxViews() {
        const enabled = document.getElementById('enableMaxViews').checked;
        document.getElementById('maxViews').disabled = !enabled;
    }

    /**
     * Create share link via API
     */
    async createShareLink() {
        const btn = document.getElementById('createShareBtn');
        btn.disabled = true;
        btn.textContent = 'Creating...';

        try {
            const shareType = document.getElementById('shareType').value;
            const expiresInDays = parseInt(document.getElementById('expiresInDays').value);
            const enableMaxViews = document.getElementById('enableMaxViews').checked;
            const maxViews = enableMaxViews ? parseInt(document.getElementById('maxViews').value) : null;

            const payload = {
                device_id: this.currentDeviceId,
                share_type: shareType,
                expires_in_days: expiresInDays,
                max_views: maxViews
            };

            // Add type-specific fields
            if (shareType === 'capture') {
                payload.capture_id = this.currentCaptureId || document.getElementById('captureId').value;
            } else if (shareType === 'date_range') {
                payload.start_date = document.getElementById('startDate').value;
                payload.end_date = document.getElementById('endDate').value;
            }

            const response = await fetch(`/v1/devices/${this.currentDeviceId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create share link');
            }

            const result = await response.json();
            this.showShareResult(result);

        } catch (error) {
            alert('Error creating share link: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Create Share Link';
        }
    }

    /**
     * Display share link result with QR code
     */
    async showShareResult(result) {
        document.getElementById('shareUrl').value = result.share_url;

        // Load QR code
        try {
            const qrResponse = await fetch(`/v1/share-links/${result.token}/qrcode`, {
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (qrResponse.ok) {
                const blob = await qrResponse.blob();
                const qrUrl = URL.createObjectURL(blob);
                document.getElementById('shareQRCode').src = qrUrl;
            }
        } catch (error) {
            console.error('Error loading QR code:', error);
        }

        document.getElementById('shareResult').style.display = 'block';
    }

    /**
     * Copy share URL to clipboard
     */
    async copyToClipboard() {
        const url = document.getElementById('shareUrl').value;

        try {
            await navigator.clipboard.writeText(url);
            alert('Share link copied to clipboard!');
        } catch (error) {
            // Fallback for older browsers
            const input = document.getElementById('shareUrl');
            input.select();
            document.execCommand('copy');
            alert('Share link copied to clipboard!');
        }
    }

    /**
     * Open share link in new tab
     */
    openShareLink() {
        const url = document.getElementById('shareUrl').value;
        window.open(url, '_blank');
    }

    /**
     * Download QR code image
     */
    downloadQRCode() {
        const img = document.getElementById('shareQRCode');
        const link = document.createElement('a');
        link.href = img.src;
        link.download = 'share-qr-code.png';
        link.click();
    }

    /**
     * Download QR code from modal
     */
    downloadQRFromModal() {
        const img = document.getElementById('qrModalImage');
        const link = document.createElement('a');
        link.href = img.src;
        link.download = 'share-qr-code.png';
        link.click();
    }

    /**
     * List all share links for current organization
     */
    async listShareLinks(deviceId = null) {
        try {
            let url = '/v1/share-links';
            if (deviceId) {
                url += `?device_id=${deviceId}`;
            }

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch share links');
            }

            const data = await response.json();
            return data.share_links;

        } catch (error) {
            console.error('Error listing share links:', error);
            return [];
        }
    }

    /**
     * Revoke a share link
     */
    async revokeShareLink(token) {
        if (!confirm('Are you sure you want to revoke this share link? It will no longer be accessible.')) {
            return false;
        }

        try {
            const response = await fetch(`/v1/share-links/${token}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to revoke share link');
            }

            return true;

        } catch (error) {
            alert('Error revoking share link: ' + error.message);
            return false;
        }
    }

    /**
     * Show QR code in modal
     */
    async showQRCode(token) {
        try {
            const response = await fetch(`/v1/share-links/${token}/qrcode`, {
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load QR code');
            }

            const blob = await response.blob();
            const qrUrl = URL.createObjectURL(blob);
            document.getElementById('qrModalImage').src = qrUrl;
            this.qrModal.style.display = 'flex';

        } catch (error) {
            alert('Error loading QR code: ' + error.message);
        }
    }
}

// Global instance
const shareManager = new ShareManager();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => shareManager.init());
} else {
    shareManager.init();
}

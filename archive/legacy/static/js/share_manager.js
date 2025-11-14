/**
 * ShareManager - Simple public link sharing
 *
 * Features:
 * - One permanent public link per device
 * - Copy link to clipboard
 * - Open link in new tab
 * - Revoke/remove link
 *
 * Advanced features (QR codes, expiration, analytics) available in backend
 * but hidden in UI for simplicity. See documentation to re-enable.
 */

class ShareManager {
    constructor() {
        this.modal = null;
        this.currentDeviceId = null;
        this.currentShareLink = null;
    }

    /**
     * Initialize the share manager and create modal HTML
     */
    init() {
        this.createShareModal();
    }

    /**
     * Create the simplified share link modal HTML
     */
    createShareModal() {
        const modalHTML = `
            <div id="shareModal" class="modal" style="display: none;">
                <div class="modal-content" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2 id="shareModalTitle">Share Camera</h2>
                        <button class="modal-close" onclick="shareManager.closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div id="shareLoading" style="text-align: center; padding: 2rem;">
                            <p>Loading share link...</p>
                        </div>

                        <div id="shareContent" style="display: none;">
                            <div style="margin-bottom: 1rem;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Public Link:</label>
                                <input type="text" id="shareUrl" class="form-control" readonly
                                       style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; font-family: monospace; font-size: 0.875rem;" />
                            </div>

                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                <button class="btn btn-primary" onclick="shareManager.copyToClipboard()" style="flex: 1;">
                                    Copy Link
                                </button>
                                <button class="btn btn-secondary" onclick="shareManager.openShareLink()" style="flex: 1;">
                                    Open Link
                                </button>
                                <button class="btn btn-danger" onclick="shareManager.removeLink()" style="flex: 1;">
                                    Remove Link
                                </button>
                            </div>

                            <div style="margin-top: 1rem; padding: 0.75rem; background: #f3f4f6; border-radius: 6px; font-size: 0.875rem; color: #6b7280;">
                                <p style="margin: 0;"><strong>Note:</strong> This link is permanent and allows anyone to view all captures from this camera. Click "Remove Link" to revoke access.</p>
                            </div>
                        </div>

                        <div id="shareError" style="display: none; padding: 1rem; background: #fee2e2; border-radius: 6px; color: #991b1b;">
                            <p id="shareErrorMessage" style="margin: 0;"></p>
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
     * Open share modal for device
     */
    async openShareModal(deviceId, deviceName = null) {
        this.currentDeviceId = deviceId;

        // Update modal title
        const title = deviceName ? `Share ${deviceName}` : 'Share Camera';
        document.getElementById('shareModalTitle').textContent = title;

        // Show modal with loading state
        document.getElementById('shareLoading').style.display = 'block';
        document.getElementById('shareContent').style.display = 'none';
        document.getElementById('shareError').style.display = 'none';
        this.modal.style.display = 'flex';

        // Check if share link already exists
        await this.loadOrCreateShareLink();
    }

    /**
     * Load existing share link or create new one
     */
    async loadOrCreateShareLink() {
        try {
            // First, try to get existing share links for this device
            const existingLinks = await this.listShareLinks(this.currentDeviceId);

            if (existingLinks.length > 0) {
                // Use the first existing link
                this.currentShareLink = existingLinks[0];
                this.displayShareLink(this.currentShareLink);
            } else {
                // Create a new share link
                await this.createShareLink();
            }
        } catch (error) {
            this.showError('Failed to load share link: ' + error.message);
        }
    }

    /**
     * Create a new share link (simplified - always device type, permanent)
     */
    async createShareLink() {
        try {
            const payload = {
                device_id: this.currentDeviceId,
                share_type: 'device',  // Always share entire device
                expires_in_days: 365,  // Permanent (1 year, can be longer)
                max_views: null        // No view limit
            };

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
            this.currentShareLink = result;
            this.displayShareLink(result);

        } catch (error) {
            this.showError('Failed to create share link: ' + error.message);
        }
    }

    /**
     * Display the share link in the modal
     */
    displayShareLink(shareLink) {
        document.getElementById('shareUrl').value = shareLink.share_url;
        document.getElementById('shareLoading').style.display = 'none';
        document.getElementById('shareContent').style.display = 'block';
    }

    /**
     * Show error message
     */
    showError(message) {
        document.getElementById('shareErrorMessage').textContent = message;
        document.getElementById('shareLoading').style.display = 'none';
        document.getElementById('shareError').style.display = 'block';
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
     * Remove/revoke the share link
     */
    async removeLink() {
        if (!confirm('Are you sure you want to remove this share link? The link will no longer work and you will need to create a new one to share again.')) {
            return;
        }

        if (!this.currentShareLink) {
            alert('No share link to remove');
            return;
        }

        try {
            const response = await fetch(`/v1/share-links/${this.currentShareLink.token}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${sessionStorage.getItem('auth_token')}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to remove share link');
            }

            alert('Share link has been removed successfully!');
            this.closeModal();

        } catch (error) {
            alert('Error removing share link: ' + error.message);
        }
    }

    /**
     * List all share links for a device (used internally)
     */
    async listShareLinks(deviceId) {
        try {
            const url = `/v1/share-links?device_id=${deviceId}`;

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
}

// Global instance
const shareManager = new ShareManager();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => shareManager.init());
} else {
    shareManager.init();
}

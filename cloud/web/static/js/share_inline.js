/**
 * Inline Share Management for Camera Cards
 * Simple click-to-share with clipboard copy and inline display
 */

const ShareInline = {
    /**
     * Create or get existing share link for a device
     * @param {string} deviceId - The device ID to share
     * @returns {Promise<object>} Share link data
     */
    async createOrGetShareLink(deviceId) {
        try {
            // Check if share link already exists
            const existing = await this.getExistingShareLink(deviceId);
            if (existing) {
                return existing;
            }

            // Create new share link
            const response = await fetch(`/v1/devices/${deviceId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${auth.getAccessToken()}`
                },
                body: JSON.stringify({
                    share_type: 'device',
                    expires_in_days: 7  // Default 7-day expiration
                })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Failed to create share link');
            }

            const data = await response.json();
            return data;

        } catch (error) {
            console.error('Error creating share link:', error);
            throw error;
        }
    },

    /**
     * Get existing share link for a device
     * @param {string} deviceId - The device ID
     * @returns {Promise<object|null>} Share link data or null if none exists
     */
    async getExistingShareLink(deviceId) {
        try {
            const response = await fetch(`/v1/share-links?device_id=${deviceId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${auth.getAccessToken()}`
                }
            });

            if (!response.ok) {
                return null;
            }

            const links = await response.json();
            // Return first active link for this device
            return links && links.length > 0 ? links[0] : null;

        } catch (error) {
            console.error('Error fetching share links:', error);
            return null;
        }
    },

    /**
     * Revoke (delete) a share link
     * @param {string} token - The share link token
     * @returns {Promise<boolean>} Success status
     */
    async revokeShareLink(token) {
        try {
            const response = await fetch(`/v1/share-links/${token}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${auth.getAccessToken()}`
                }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Failed to revoke share link');
            }

            return true;

        } catch (error) {
            console.error('Error revoking share link:', error);
            throw error;
        }
    },

    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} Success status
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return true;
            } catch (fallbackError) {
                document.body.removeChild(textArea);
                throw fallbackError;
            }
        }
    },

    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type of toast (success, error, info)
     */
    showToast(message, type = 'success') {
        // Remove any existing toasts
        const existingToast = document.querySelector('.share-toast');
        if (existingToast) {
            existingToast.remove();
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `share-toast share-toast-${type}`;
        toast.textContent = message;

        // Add to document
        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = date - now;
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays < 0) {
            return 'Expired';
        } else if (diffDays === 0) {
            return 'Expires today';
        } else if (diffDays === 1) {
            return 'Expires tomorrow';
        } else if (diffDays <= 7) {
            return `Expires in ${diffDays} days`;
        } else {
            return date.toLocaleDateString();
        }
    },

    /**
     * Format relative time (e.g., "2 days ago")
     * @param {string} dateString - ISO date string
     * @returns {string} Relative time string
     */
    formatRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSeconds < 60) {
            return 'just now';
        } else if (diffMinutes < 60) {
            return `${diffMinutes}m ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ago`;
        } else if (diffDays === 1) {
            return 'yesterday';
        } else if (diffDays < 7) {
            return `${diffDays}d ago`;
        } else {
            return date.toLocaleDateString();
        }
    },

    /**
     * Handle share button click
     * @param {string} deviceId - Device ID
     * @param {HTMLElement} shareContainer - Share container element
     */
    async handleShareClick(deviceId, shareContainer) {
        try {
            // Show loading state
            const shareBtn = shareContainer.querySelector('.share-btn');
            const originalText = shareBtn.innerHTML;
            shareBtn.innerHTML = '<span class="spinner"></span>';
            shareBtn.disabled = true;

            // Create or get share link
            const shareData = await this.createOrGetShareLink(deviceId);

            // Copy to clipboard
            await this.copyToClipboard(shareData.share_url);

            // Update UI to show the link
            this.displayShareLink(shareContainer, shareData);

            // Show success toast
            this.showToast('Link copied to clipboard!', 'success');

        } catch (error) {
            console.error('Share error:', error);
            this.showToast(error.message || 'Failed to create share link', 'error');

            // Reset button
            const shareBtn = shareContainer.querySelector('.share-btn');
            shareBtn.innerHTML = '🔗 Share';
            shareBtn.disabled = false;
        }
    },

    /**
     * Display share link in UI
     * @param {HTMLElement} shareContainer - Share container element
     * @param {object} shareData - Share link data
     */
    displayShareLink(shareContainer, shareData) {
        const shareBtn = shareContainer.querySelector('.share-btn');
        const linkDisplay = shareContainer.querySelector('.share-link-display');
        const shareUrl = shareContainer.querySelector('.share-url');
        const shareMetadata = shareContainer.querySelector('.share-metadata');
        const removeBtn = shareContainer.querySelector('.share-remove-btn');

        // Update button
        shareBtn.innerHTML = '🔗 Shared';
        shareBtn.disabled = false;
        shareBtn.onclick = async () => {
            // Copy again when clicked
            await this.copyToClipboard(shareData.share_url);
            this.showToast('Link copied!', 'success');
        };

        // Show link
        shareUrl.textContent = shareData.share_url;
        shareUrl.href = shareData.share_url;

        // Show metadata
        const createdText = `Created ${this.formatRelativeTime(shareData.created_at)}`;
        const expiresText = this.formatDate(shareData.expires_at);
        const viewsText = `${shareData.view_count || 0} views`;
        shareMetadata.textContent = `${createdText} • ${expiresText} • ${viewsText}`;

        // Show display and remove button
        linkDisplay.style.display = 'block';
        removeBtn.style.display = 'inline-block';
        removeBtn.onclick = () => this.handleRemoveClick(shareData.token, shareContainer);
    },

    /**
     * Handle remove button click
     * @param {string} token - Share link token
     * @param {HTMLElement} shareContainer - Share container element
     */
    async handleRemoveClick(token, shareContainer) {
        if (!confirm('Remove this share link? The link will stop working.')) {
            return;
        }

        try {
            await this.revokeShareLink(token);

            // Reset UI
            this.hideShareLink(shareContainer);

            // Show success toast
            this.showToast('Share link removed', 'success');

        } catch (error) {
            console.error('Remove error:', error);
            this.showToast(error.message || 'Failed to remove share link', 'error');
        }
    },

    /**
     * Hide share link display
     * @param {HTMLElement} shareContainer - Share container element
     */
    hideShareLink(shareContainer) {
        const shareBtn = shareContainer.querySelector('.share-btn');
        const linkDisplay = shareContainer.querySelector('.share-link-display');
        const removeBtn = shareContainer.querySelector('.share-remove-btn');

        // Reset button
        shareBtn.innerHTML = '🔗 Share';
        shareBtn.disabled = false;

        // Hide display and remove button
        linkDisplay.style.display = 'none';
        removeBtn.style.display = 'none';
    },

    /**
     * Load share status for a camera card
     * @param {string} deviceId - Device ID
     * @param {HTMLElement} shareContainer - Share container element
     */
    async loadShareStatus(deviceId, shareContainer) {
        try {
            const shareData = await this.getExistingShareLink(deviceId);

            if (shareData) {
                // Display existing share link
                this.displayShareLink(shareContainer, shareData);
            }

        } catch (error) {
            console.error('Error loading share status:', error);
        }
    }
};

// Make available globally
window.ShareInline = ShareInline;

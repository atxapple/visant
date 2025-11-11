#!/bin/bash
# Visant Scheduled Update Script
#
# Runs at 2 AM daily to update long-running devices.
# Updates code, then restarts the service to run the latest version.
#
# Note: The service restart will also trigger pre-start-update.sh,
# but this script does the update first for better logging and error handling.

set -e

INSTALL_DIR="/opt/visant"
LOG_FILE="/var/log/visant-update.log"

# Detect which service is active (v1 or v2)
if systemctl is-enabled --quiet visant-device-v2.service 2>/dev/null; then
    SERVICE_NAME="visant-device-v2.service"
elif systemctl is-enabled --quiet visant-device.service 2>/dev/null; then
    SERVICE_NAME="visant-device.service"
else
    # Fallback: check which is active
    if systemctl is-active --quiet visant-device-v2.service 2>/dev/null; then
        SERVICE_NAME="visant-device-v2.service"
    else
        SERVICE_NAME="visant-device.service"
    fi
fi

# Configure git safe.directory to avoid ownership issues when running as root
git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "===== Starting Visant device update (service: $SERVICE_NAME) ====="

# Change to install directory
cd "$INSTALL_DIR" || {
    log "ERROR: Failed to change to $INSTALL_DIR"
    exit 1
}

# Check if git repository
if [ ! -d ".git" ]; then
    log "ERROR: Not a git repository. Skipping update."
    exit 1
fi

# Detect current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log "Current branch: $CURRENT_BRANCH"

# Fetch latest changes
log "Fetching latest changes from remote..."
git fetch origin "$CURRENT_BRANCH" || {
    log "ERROR: Failed to fetch from remote"
    exit 1
}

# Get current and remote commit hashes
CURRENT_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse "origin/$CURRENT_BRANCH")

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    log "Already up to date (${CURRENT_COMMIT:0:7}). No restart needed."
    exit 0
fi

log "Update available: ${CURRENT_COMMIT:0:7} -> ${REMOTE_COMMIT:0:7}"

# Reset to latest code (hard reset ensures clean state)
log "Updating to latest code..."
git reset --hard "origin/$CURRENT_BRANCH" || {
    log "ERROR: Failed to reset to origin/$CURRENT_BRANCH"
    exit 1
}

# Ensure all deployment scripts are executable (defensive fix for git permission issues)
chmod +x "$INSTALL_DIR"/deployment/*.sh 2>/dev/null || true

# Update Python dependencies (always run to ensure consistency)
log "Updating Python dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r requirements.txt || {
    log "ERROR: Failed to install dependencies"
    exit 1
}

# Restart the service (this will also trigger pre-start-update.sh via ExecStartPre)
log "Restarting $SERVICE_NAME service..."
systemctl restart "$SERVICE_NAME"

# Wait a moment and check status
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Service restarted successfully"
    NEW_COMMIT=$(git rev-parse HEAD)
    log "Now running commit: ${NEW_COMMIT:0:7}"
else
    log "WARNING: Service failed to start after update"
    systemctl status "$SERVICE_NAME" --no-pager | tee -a "$LOG_FILE"
    exit 1
fi

log "===== Scheduled update completed successfully ====="
exit 0

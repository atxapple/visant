#!/bin/bash
#
# OK Monitor Pre-Start Update Script
#
# This script runs BEFORE the device service starts to ensure
# the application is always running the latest code.
#
# Failure behavior: If this script fails, the service will NOT start.
# This ensures we never run outdated code.
#
# Called by: okmonitor-device.service (ExecStartPre)
#

set -e  # Exit immediately if any command fails

INSTALL_DIR="/opt/okmonitor"
LOG_PREFIX="[PRE-START-UPDATE]"

echo "$LOG_PREFIX Starting pre-start update check..."

# Change to installation directory
cd "$INSTALL_DIR" || {
    echo "$LOG_PREFIX ERROR: Cannot access $INSTALL_DIR"
    exit 1
}

# Fetch latest code from remote
echo "$LOG_PREFIX Fetching latest code from origin/main..."
git fetch origin main || {
    echo "$LOG_PREFIX ERROR: Failed to fetch from remote"
    exit 1
}

# Check if we're behind
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    echo "$LOG_PREFIX Already up to date (${LOCAL_HASH:0:7})"
else
    echo "$LOG_PREFIX Update available: ${LOCAL_HASH:0:7} -> ${REMOTE_HASH:0:7}"

    # Reset to latest code (hard reset to ensure clean state)
    echo "$LOG_PREFIX Updating to latest code..."
    git reset --hard origin/main || {
        echo "$LOG_PREFIX ERROR: Failed to reset to origin/main"
        exit 1
    }

    # Update Python dependencies
    echo "$LOG_PREFIX Updating Python dependencies..."
    venv/bin/pip install --quiet --upgrade pip
    venv/bin/pip install --quiet -r requirements.txt || {
        echo "$LOG_PREFIX ERROR: Failed to install dependencies"
        exit 1
    }

    echo "$LOG_PREFIX Update completed successfully (${REMOTE_HASH:0:7})"
fi

echo "$LOG_PREFIX Pre-start update check complete - service will now start"
exit 0

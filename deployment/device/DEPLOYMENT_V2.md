# Visant v2.0 Cloud-Triggered Deployment Guide

This guide covers deploying Visant v2.0 (Cloud-Triggered Architecture) on Raspberry Pi 5.

## What is v2.0?

Visant v2.0 uses **cloud-triggered architecture** where the cloud pushes commands to devices in real-time using Server-Sent Events (SSE), rather than devices polling for schedules.

**Key Differences from v1.0:**

| Feature | v1.0 (Polling) | v2.0 (Cloud-Triggered) |
|---------|----------------|------------------------|
| Communication | Device polls cloud | Cloud pushes to device via SSE |
| Latency | 5-10 seconds | <100ms |
| Device Complexity | Complex (scheduling logic) | Simple (just executes commands) |
| Cloud Requirements | Basic REST API | REST API + SSE endpoint |
| Scaling | Good (1-100 devices) | Excellent (1000+ devices) |
| Trigger Scheduling | Device-side | Cloud-side (TriggerScheduler) |

**When to use v2.0:**
- Multi-tenant deployments
- Real-time capture requirements
- Large-scale deployments (10+ devices)
- When cloud server runs v2.0 infrastructure (CommandHub + TriggerScheduler)

**When to use v1.0:**
- Simple single-tenant deployments
- Existing v1.0 cloud infrastructure
- Minimal cloud server requirements
- Smaller deployments (1-10 devices)

---

## Prerequisites

### Hardware
- Raspberry Pi 5 (4GB+ RAM recommended)
- 32GB+ microSD card (Class 10 or better)
- **USB webcam** (V4L2 compatible)
- 27W USB-C power supply
- Ethernet cable or WiFi credentials

### Cloud Server
- Railway, AWS, or other cloud hosting
- v2.0 cloud server running with:
  - CommandHub (SSE command streaming)
  - TriggerScheduler (automated capture scheduling)
  - PostgreSQL database
- Cloud server must expose:
  - `POST /v1/captures` - Capture upload endpoint
  - `GET /v1/devices/{device_id}/commands` - SSE command stream
  - `POST /v1/devices/{device_id}/trigger` - Manual trigger endpoint

### Network
- Internet connectivity
- Outbound HTTPS (port 443) access
- No inbound ports required

---

## Installation

### Step 1: Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash **Raspberry Pi OS Bookworm 64-bit** to microSD card
3. Enable SSH in Raspberry Pi Imager settings
4. Boot Raspberry Pi and connect via SSH

### Step 2: Clone Repository

```bash
git clone https://github.com/atxapple/visant.git
cd visant
```

### Step 3: Configure Environment

Create the configuration file:

```bash
sudo mkdir -p /opt/visant
sudo nano /opt/visant/.env.device
```

Add the following configuration (**v2.0 specific settings in bold**):

```bash
# Device identification
DEVICE_ID=your-unique-device-id

# Cloud API configuration
API_URL=https://your-cloud-server.railway.app

# Camera configuration
CAMERA_SOURCE=0
CAMERA_WARMUP=2

# v2.0 SPECIFIC: SSE connection settings
UPLOAD_TIMEOUT=30
STREAM_TIMEOUT=70
RECONNECT_DELAY=5

# Debug settings
SAVE_FRAMES_DIR=/opt/visant/debug_captures
```

**Configuration Notes:**
- `DEVICE_ID`: Unique identifier for this device (e.g., `FLOOR1`, `LOBBY_CAM_01`)
- `API_URL`: Your v2.0 cloud server URL
- `STREAM_TIMEOUT`: SSE read timeout (70s allows for 60s keepalive + margin)
- `RECONNECT_DELAY`: Seconds to wait before reconnecting after disconnect

### Step 4: Run Installer

Install with v2.0 architecture:

```bash
sudo deployment/install_device.sh --v2
```

**Installation Options:**

```bash
# Basic v2.0 install
sudo deployment/install_device.sh --v2

# v2.0 with Tailscale remote access
sudo deployment/install_device.sh --v2 --tailscale-key tskey-auth-xxxxx

# v2.0 from dev branch
sudo deployment/install_device.sh --v2 --branch dev

# Reinstall v2.0, keep Tailscale
sudo deployment/install_device.sh --v2 --skip-tailscale
```

The installer will:
1. Install system dependencies (Python, OpenCV, ffmpeg, etc.)
2. Clone repository to `/opt/visant`
3. Create Python virtual environment
4. Install `visant-device-v2.service` systemd service
5. Install auto-update system
6. Install Comitup (WiFi hotspot)
7. Install Tailscale (optional remote access)

### Step 5: Configure WiFi

Choose one method:

**Method 1: Comitup (Recommended - No SSH needed)**

1. Reboot device: `sudo reboot`
2. Device creates WiFi hotspot: `visant-XXXX`
3. Connect phone/laptop to hotspot (no password)
4. Open browser: http://10.41.0.1
5. Select customer WiFi and configure

**Method 2: addwifi.sh (SSH required)**

```bash
~/addwifi.sh "WiFi-Network-Name" "password"
~/addwifi.sh --list    # Show configured networks
```

### Step 6: Verify Deployment

```bash
sudo deployment/verify_deployment.sh
```

This checks:
- Configuration file validity
- Python environment setup
- Systemd service status
- Camera access
- **SSE connection to cloud** (v2.0 specific)
- Network connectivity

### Step 7: Start Service

```bash
sudo systemctl start visant-device-v2.service
sudo journalctl -u visant-device-v2.service -f
```

You should see:
```
[INFO] Visant Device Client v2.0 - Cloud-Triggered Architecture
[INFO] Device ID: YOUR_DEVICE_ID
[INFO] API URL: https://your-cloud.railway.app
[INFO] Connecting to command stream...
[INFO] ✓ Connected to command stream
[INFO] ✓ Connection confirmed by server
```

### Step 8: Test Capture

From the cloud server or UI, trigger a manual capture:

```bash
curl -X POST https://your-cloud.railway.app/v1/devices/YOUR_DEVICE_ID/trigger
```

Device should execute capture immediately and upload to cloud.

---

## Service Management

### Start/Stop Service

```bash
# Start device client
sudo systemctl start visant-device-v2.service

# Stop device client
sudo systemctl stop visant-device-v2.service

# Restart device client
sudo systemctl restart visant-device-v2.service

# Check status
sudo systemctl status visant-device-v2.service
```

### View Logs

```bash
# Follow live logs
sudo journalctl -u visant-device-v2.service -f

# View recent logs
sudo journalctl -u visant-device-v2.service --since "1 hour ago"

# View errors only
sudo journalctl -u visant-device-v2.service --since "1 hour ago" | grep -i error
```

### Auto-Start on Boot

The service is automatically enabled to start on boot. To disable:

```bash
sudo systemctl disable visant-device-v2.service
```

---

## Automatic Updates

Visant v2.0 uses a hybrid update system:

### Pre-Start Updates (Every Boot/Restart)

Runs before service starts via `ExecStartPre` in systemd service:
```bash
/opt/visant/deployment/pre-start-update.sh
```

- Fetches latest code from git
- Updates Python dependencies
- Ensures latest version on every start
- **Fail-safe:** Service won't start if update fails

### Scheduled Updates (Long-Running Devices)

Runs daily at 2:00 AM via systemd timer:
```bash
/opt/visant/deployment/update_device.sh
```

- Updates code and restarts service
- Logs to `/var/log/visant-update.log`
- Ensures devices stay updated without manual intervention

**Check update status:**

```bash
# View update timer status
sudo systemctl list-timers visant-update

# View update logs
sudo cat /var/log/visant-update.log

# Force update now
sudo systemctl start visant-update.service
```

---

## Troubleshooting

### Device Not Connecting to Cloud

**Check 1: Verify Configuration**
```bash
cat /opt/visant/.env.device
```
Ensure `API_URL` and `DEVICE_ID` are correct.

**Check 2: Test Network Connectivity**
```bash
ping -c 3 google.com
curl -I https://your-cloud.railway.app
```

**Check 3: Verify SSE Endpoint**
```bash
curl -N https://your-cloud.railway.app/v1/devices/YOUR_DEVICE_ID/commands
```
Should keep connection open and send keepalive pings.

**Check 4: View Service Logs**
```bash
sudo journalctl -u visant-device-v2.service --since "10 minutes ago"
```

### SSE Connection Timeouts

**Symptom:** Device keeps reconnecting every 60-70 seconds

**Cause:** Normal behavior - SSE has `STREAM_TIMEOUT` of 70 seconds

**Fix:** Increase timeout if needed in `.env.device`:
```bash
STREAM_TIMEOUT=120
```

Then restart service:
```bash
sudo systemctl restart visant-device-v2.service
```

### Captures Not Uploading

**Check 1: Camera Access**
```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

**Check 2: Test Camera Manually**
```bash
/opt/visant/venv/bin/python -m device.main_v2 \
    --api-url http://your-cloud.railway.app \
    --device-id YOUR_DEVICE_ID \
    --camera-source 0 \
    --verbose
```

**Check 3: Verify Upload Endpoint**
```bash
curl -X POST https://your-cloud.railway.app/v1/captures \
    -H "Content-Type: application/json" \
    -d '{"device_id":"test","trigger_id":"test","image_base64":"","captured_at":"2025-01-01T00:00:00Z"}'
```

### Service Fails to Start

**Check 1: View Full Error**
```bash
sudo systemctl status visant-device-v2.service
sudo journalctl -u visant-device-v2.service -n 50
```

**Check 2: Verify Pre-Start Update Script**
```bash
sudo /opt/visant/deployment/pre-start-update.sh
```

**Check 3: Test Device Client Directly**
```bash
cd /opt/visant
source venv/bin/activate
python -m device.main_v2 --api-url $API_URL --device-id $DEVICE_ID --camera-source 0 --verbose
```

### Permission Issues

**Fix Camera Permissions:**
```bash
sudo usermod -a -G video pi
# Then logout and login or reboot
```

**Fix Directory Permissions:**
```bash
sudo chown -R pi:pi /opt/visant
sudo chmod -R 755 /opt/visant
```

---

## Monitoring

### Health Checks

```bash
# Service status
sudo systemctl is-active visant-device-v2.service

# Last capture time (check debug_captures directory)
ls -lt /opt/visant/debug_captures | head -5

# Network connectivity
ping -c 1 your-cloud.railway.app

# Disk space
df -h /opt/visant
```

### Remote Access via Tailscale

If installed with `--tailscale-key`:

```bash
# Check Tailscale status
sudo tailscale status

# Get Tailscale IP
sudo tailscale ip -4

# SSH from anywhere
ssh pi@visant-YOUR_DEVICE_ID
```

### Cloud Dashboard

Check cloud server dashboard for:
- Device connection status (connected/disconnected)
- Last seen timestamp
- Capture count and success rate
- Trigger execution history

---

## Advanced Configuration

### Custom Camera Settings

Edit `/opt/visant/.env.device`:

```bash
# USB Camera with specific resolution
CAMERA_SOURCE=0
CAMERA_WARMUP=2
# Note: Resolution set in systemd service file

# RTSP camera stream
CAMERA_SOURCE=rtsp://192.168.1.100:554/stream
```

### Debug Frame Saving

Debug frames are saved by default to `/opt/visant/debug_captures/`.

**Disable debug saving:**

Edit `/etc/systemd/system/visant-device-v2.service`:

Remove the `--save-frames` flag from ExecStart.

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart visant-device-v2.service
```

### Change Update Schedule

Edit `/etc/systemd/system/visant-update.timer`:

```bash
# Change from 2:00 AM to 3:00 AM
OnCalendar=*-*-* 03:00:00
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart visant-update.timer
```

---

## Migration from v1.0 to v2.0

If you have existing v1.0 deployment:

1. **Stop v1.0 service:**
```bash
sudo systemctl stop visant-device.service
sudo systemctl disable visant-device.service
```

2. **Update configuration:**
```bash
sudo nano /opt/visant/.env.device
```

Add v2.0 settings:
```bash
UPLOAD_TIMEOUT=30
STREAM_TIMEOUT=70
RECONNECT_DELAY=5
```

3. **Install v2.0 service:**
```bash
sudo deployment/install_device.sh --v2 --skip-tailscale
```

4. **Verify new service:**
```bash
sudo systemctl status visant-device-v2.service
sudo journalctl -u visant-device-v2.service -f
```

---

## Uninstallation

To completely remove Visant (preserves Tailscale):

```bash
sudo deployment/uninstall.sh
```

This will:
- Stop and disable all services
- Remove systemd service files
- Remove `/opt/visant` directory
- Keep Tailscale installation (for remote access)

---

## Support

For issues and questions:
- Documentation: `deployment/` directory
- Cloud API docs: https://your-cloud.railway.app/docs
- Architecture details: `CLOUD_TRIGGERED_V2.md`

## Reference

- Main deployment guide: `deployment/DEPLOYMENT.md` (v1.0)
- WiFi setup: `deployment/WIFI.md`
- Comitup guide: `deployment/COMITUP.md`
- Tailscale setup: `deployment/TAILSCALE.md`
- Cloning guide: `deployment/CLONING.md` (fleet deployment)

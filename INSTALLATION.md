# Drone Ground Station Installation Guide

This guide provides step-by-step instructions for setting up the complete drone ground station system with Raspberry Pi 3, camera, Crossflight flight controller, and Windows ground station.

## System Overview

- **Drone**: Raspberry Pi 3 + Camera + Crossflight FC (UART connection)
- **Ground Station**: Windows PC with ROS2
- **Communication**: WiFi (192.168.4.x network)
- **Video**: H.264 streaming via GStreamer
- **Telemetry**: MSP protocol via UDP/TCP

## Prerequisites

### Hardware Requirements

#### Drone Side:
- Raspberry Pi 3 Model B/B+
- Raspberry Pi Camera Module or USB Camera
- Crossflight-compatible flight controller
- UART cable for FC connection
- MicroSD card (32GB+ recommended)
- WiFi capability (built-in on Pi 3)

#### Ground Station Side:
- Windows 10/11 PC
- WiFi adapter
- Minimum 8GB RAM
- Python 3.8+

### Software Requirements

#### Ground Station (Windows):
- ROS2 Humble
- Python 3.8+
- GStreamer 1.0+
- Git

#### Raspberry Pi:
- Raspberry Pi OS (Bullseye or newer)
- Python 3.8+
- GStreamer 1.0+
- Camera drivers

## Part 1: Ground Station Setup (Windows)

### Step 1: Install ROS2 Humble

1. Download ROS2 Humble for Windows from [official website](https://docs.ros.org/en/humble/Installation/Windows-Install-Binary.html)

2. Follow the installation instructions:
```powershell
# Extract ROS2 to C:\dev\ros2_humble
# Add to PATH in environment variables
```

3. Install Visual Studio 2019 Build Tools

4. Install Python dependencies:
```powershell
pip install -U colcon-common-extensions vcstool
```

### Step 2: Install GStreamer

1. Download GStreamer 1.20+ from [gstreamer.freedesktop.org](https://gstreamer.freedesktop.org/download/)

2. Install both runtime and development packages

3. Add GStreamer to PATH:
```
C:\gstreamer\1.0\msvc_x86_64\bin
```

### Step 3: Setup Ground Station Project

1. Clone or extract the project:
```powershell
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR"
```

2. Install Python dependencies:
```powershell
pip install -r requirements.txt
```

3. Install additional Windows-specific packages:
```powershell
pip install pywin32 windows-curses
```

4. Setup ROS2 environment:
```powershell
# Add to your PowerShell profile or run each time
C:\dev\ros2_humble\local_setup.ps1
```

### Step 4: Build the ROS2 Package

1. Build the workspace:
```powershell
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR"
colcon build --packages-select drone_ground_station
```

2. Source the workspace:
```powershell
.\install\setup.ps1
```

### Step 5: Configure Network

1. Connect to drone WiFi network:
   - SSID: `DroneNetwork`
   - Password: `drone123`
   - Drone IP: `192.168.4.1`
   - Your IP should be: `192.168.4.19`

## Part 2: Raspberry Pi Setup

### Step 1: Prepare Raspberry Pi OS

1. Flash Raspberry Pi OS to SD card using Raspberry Pi Imager

2. Enable SSH and configure WiFi in boot partition:
```
# Create empty file named 'ssh' in boot partition
# Create wpa_supplicant.conf with WiFi credentials
```

3. Boot Raspberry Pi and connect via SSH:
```bash
ssh pi@192.168.4.1
```

### Step 2: Install Dependencies

1. Update system:
```bash
sudo apt update && sudo apt upgrade -y
```

2. Install required packages:
```bash
sudo apt install -y python3-pip python3-dev python3-setuptools
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base
sudo apt install -y gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
sudo apt install -y gstreamer1.0-plugins-ugly gstreamer1.0-libav
sudo apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
sudo apt install -y hostapd dnsmasq
```

3. Install Python packages:
```bash
pip3 install pymavlink pyserial opencv-python numpy
```

### Step 3: Configure Camera

#### For Raspberry Pi Camera:
```bash
# Enable camera interface
sudo raspi-config
# Navigate to Interface Options > Camera > Enable

# Test camera
libcamera-hello --timeout 5000
```

#### For USB Camera:
```bash
# Check camera device
ls /dev/video*

# Test camera
v4l2-ctl --list-devices
```

### Step 4: Configure UART for Crossflight

1. Enable UART:
```bash
sudo raspi-config
# Interface Options > Serial Port
# Login shell over serial: No
# Serial port hardware: Yes
```

2. Edit boot config:
```bash
sudo nano /boot/config.txt
# Add these lines:
enable_uart=1
dtoverlay=disable-bt
```

3. Disable serial console:
```bash
sudo systemctl disable hciuart
```

4. Reboot:
```bash
sudo reboot
```

### Step 5: Setup WiFi Hotspot

1. Configure hostapd:
```bash
sudo nano /etc/hostapd/hostapd.conf
```

Add:
```
interface=wlan0
driver=nl80211
ssid=DroneNetwork
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=drone123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

2. Configure dnsmasq:
```bash
sudo nano /etc/dnsmasq.conf
```

Add:
```
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
```

3. Configure static IP:
```bash
sudo nano /etc/dhcpcd.conf
```

Add:
```
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
```

### Step 6: Install Drone Scripts

1. Copy scripts to Raspberry Pi:
```bash
# Create directory
mkdir -p /home/pi/drone_scripts

# Copy files (use scp from Windows or create manually)
scp raspberry_pi_scripts/* pi@192.168.4.1:/home/pi/drone_scripts/
```

2. Make scripts executable:
```bash
chmod +x /home/pi/drone_scripts/*.py
```

3. Test scripts:
```bash
cd /home/pi/drone_scripts
python3 video_streamer.py
```

### Step 7: Setup Auto-start Service

1. Create systemd service:
```bash
sudo nano /etc/systemd/system/drone.service
```

Add:
```ini
[Unit]
Description=Drone Services
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/drone_scripts
ExecStart=/usr/bin/python3 drone_startup.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable service:
```bash
sudo systemctl enable drone.service
sudo systemctl start drone.service
```

## Part 3: Crossflight Configuration

### Step 1: Connect Flight Controller

1. Connect FC to Raspberry Pi via UART:
   - FC TX → Pi RX (GPIO 15)
   - FC RX → Pi TX (GPIO 14)
   - FC GND → Pi GND

2. Configure Crossflight:
   - Enable MSP on UART
   - Set baud rate to 115200
   - Configure telemetry output

### Step 2: Test Connection

1. Test serial communication:
```bash
# On Raspberry Pi
python3 -c "import serial; s=serial.Serial('/dev/ttyAMA0', 115200); print('Serial OK')"
```

## Part 4: Testing and Verification

### Step 1: Test Ground Station

1. Launch ground station:
```powershell
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR"
ros2 launch drone_ground_station ground_station.launch.py
```

2. Verify components:
   - Video feed display
   - Telemetry data reception
   - Command interface

### Step 2: Test Drone Services

1. Check service status:
```bash
sudo systemctl status drone.service
```

2. Monitor logs:
```bash
journalctl -u drone.service -f
```

3. Test video stream:
```bash
# On Windows, test GStreamer reception
gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### Step 3: End-to-End Testing

1. Power on drone
2. Connect ground station to drone WiFi
3. Launch ground station software
4. Verify:
   - Video streaming
   - Telemetry reception
   - Command transmission
   - Flight control response

## Troubleshooting

### Common Issues

#### No Video Stream:
- Check GStreamer installation
- Verify camera functionality
- Check network connectivity
- Verify firewall settings

#### No Telemetry:
- Check UART connection
- Verify Crossflight MSP configuration
- Check serial port permissions
- Verify network ports

#### WiFi Connection Issues:
- Check hostapd configuration
- Verify dnsmasq setup
- Check IP address configuration
- Restart networking services

#### ROS2 Issues:
- Source ROS2 environment
- Check package build
- Verify Python dependencies
- Check topic communication

### Log Files

- Ground Station: Check ROS2 logs
- Raspberry Pi: `/var/log/drone/`
- System logs: `journalctl -u drone.service`

### Performance Optimization

1. **Video Quality**:
   - Adjust bitrate in config
   - Change resolution/framerate
   - Optimize GStreamer pipeline

2. **Network Performance**:
   - Use 5GHz WiFi if available
   - Optimize buffer sizes
   - Reduce telemetry rate if needed

3. **System Performance**:
   - Increase GPU memory split
   - Optimize CPU governor
   - Use faster SD card

## Support

For issues and questions:
1. Check log files for error messages
2. Verify all connections and configurations
3. Test components individually
4. Consult ROS2 and GStreamer documentation

## Safety Notes

⚠️ **Important Safety Reminders**:
- Always test in a safe environment
- Keep manual control available
- Monitor battery levels
- Respect local regulations
- Have emergency stop procedures ready
# Current Setup Steps - Remote Pi Configuration

You have successfully connected to your Raspberry Pi via SSH but encountered network connectivity issues. This guide provides step-by-step instructions to resolve the issues and set up your drone ground station remotely.

## Current Status

✅ **Completed:**
- SSH connection to Pi established (`pi@192.168.4.1`)
- Pi is running Debian GNU/Linux with kernel 6.1.21-v8+
- Basic Python packages are installed (numpy, picamera2, RPi.GPIO, etc.)

❌ **Issues:**
- DNS resolution failures preventing package updates
- Cannot reach Debian and Raspberry Pi repositories
- Need to set up drone ground station software

## Immediate Next Steps

### Step 1: Fix Network Issues on Pi

**On your Windows laptop, run the network fix script:**

```bash
# Navigate to your project directory
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR\scripts"

# Run the remote setup script
python remote_pi_setup.py
```

This script will:
- Transfer the network diagnostics script to your Pi
- Run comprehensive network tests
- Fix DNS configuration
- Set up alternative package sources if needed
- Create basic project structure

**Alternative manual approach (if script fails):**

1. **Transfer the network fix script manually:**
   ```bash
   scp pi_network_fix.sh pi@192.168.4.1:~/
   ```

2. **SSH to Pi and run the fix:**
   ```bash
   ssh pi@192.168.4.1
   chmod +x ~/pi_network_fix.sh
   ./pi_network_fix.sh
   ```

### Step 2: Manual DNS Fix (if automated fix doesn't work)

**On the Pi (via SSH):**

```bash
# Backup current DNS configuration
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# Set reliable DNS servers
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf

# Test connectivity
ping -c 3 google.com

# Try package update
sudo apt update
```

### Step 3: Install Essential Packages

**Once network is working on Pi:**

```bash
# Update package lists
sudo apt update

# Install essential packages
sudo apt install -y python3-pip git hostapd dnsmasq

# Install Python packages
pip3 install pyserial opencv-python-headless
```

### Step 4: Set Up Project Structure

**On the Pi:**

```bash
# Create project directory
mkdir -p ~/drone_ground_station/{scripts,config,logs}

# Create basic configuration
cat > ~/drone_ground_station/config/drone_config.json << 'EOF'
{
    "video": {
        "port": 5000,
        "width": 640,
        "height": 480,
        "framerate": 30
    },
    "telemetry": {
        "serial_port": "/dev/serial0",
        "baud_rate": 57600,
        "udp_port": 14550
    },
    "network": {
        "ground_station_ip": "192.168.4.2",
        "pi_ip": "192.168.4.1"
    }
}
EOF
```

### Step 5: Test Hardware Components

**Test camera:**
```bash
# Test camera with libcamera
libcamera-hello --timeout 5000

# If successful, test video recording
libcamera-vid -t 10000 -o test_video.h264
```

**Test UART/Serial:**
```bash
# Check available serial ports
ls -la /dev/serial* /dev/ttyS* /dev/ttyAMA*

# Test serial port (if flight controller connected)
python3 -c "import serial; s=serial.Serial('/dev/serial0', 57600, timeout=1); print('Serial OK' if s.is_open else 'Serial FAIL'); s.close()"
```

### Step 6: Set Up Ground Station on Laptop

**On your Windows laptop:**

1. **Test network connection to Pi:**
   ```bash
   ping 192.168.4.1
   ```

2. **Run the receiver test:**
   ```bash
   cd "C:\Users\hussa\OneDrive\Desktop\drone with GR\scripts"
   python laptop_receiver_test.py
   ```

3. **Install GStreamer (if not already installed):**
   - Download from: https://gstreamer.freedesktop.org/download/
   - Install the complete package
   - Add to PATH: `C:\gstreamer\1.0\msvc_x86_64\bin`

### Step 7: Test End-to-End Communication

**On Pi (in separate SSH sessions):**

```bash
# Terminal 1: Start video streaming
python3 ~/drone_ground_station/scripts/video_streamer.py

# Terminal 2: Start telemetry bridge (if flight controller connected)
python3 ~/drone_ground_station/scripts/telemetry_bridge.py
```

**On laptop:**
```bash
# Run receiver test
python laptop_receiver_test.py
```

You should see:
- Video packets being received
- Telemetry data (if flight controller connected)
- Video display window (if GStreamer working)

## Hardware Connections (Next Phase)

Once software is working, connect hardware:

### Camera Module
- Connect to CSI port on Pi
- Ensure ribbon cable is properly seated
- Camera should face away from Pi board

### Flight Controller (UART)
- **Pi GPIO 14 (TXD)** → **Flight Controller RX**
- **Pi GPIO 15 (RXD)** → **Flight Controller TX**
- **Pi GND** → **Flight Controller GND**
- **Do NOT connect 5V/3.3V** (use separate power)

### Power Supply
- Use quality 5V 3A power supply for Pi
- Ensure stable power during operation
- Consider UPS/battery backup for field use

## Troubleshooting

### Network Issues
- **No internet on Pi:** Check DNS settings, try ethernet connection
- **Cannot connect to Pi:** Check WiFi hotspot, verify IP address
- **Slow connection:** Check signal strength, reduce distance

### Camera Issues
- **Camera not detected:** Check CSI connection, enable camera in raspi-config
- **Poor video quality:** Adjust resolution/framerate in config
- **No video stream:** Check GStreamer installation on laptop

### Serial/Telemetry Issues
- **No serial data:** Check UART enable, verify connections
- **Wrong baud rate:** Match flight controller settings
- **Permission denied:** Add pi user to dialout group

## Success Criteria

✅ **Network connectivity working on Pi**
✅ **Package installation successful**
✅ **Camera streaming video to laptop**
✅ **Telemetry data flowing (when FC connected)**
✅ **Ground station receiving data**

## Next Steps After Basic Setup

1. **Hardware Integration:**
   - Connect and test camera module
   - Connect and test flight controller UART
   - Set up proper power management

2. **Software Enhancement:**
   - Implement MAVLink parsing
   - Add flight control commands
   - Create web-based ground station interface

3. **System Integration:**
   - Auto-start services on boot
   - Add system monitoring
   - Implement error handling and recovery

4. **Flight Testing:**
   - Ground tests with tethered drone
   - Range testing
   - Full flight test with safety pilot

## Emergency Procedures

- **Lost connection:** Check power, restart Pi, verify network
- **System freeze:** Power cycle Pi, check logs
- **Flight emergency:** Always have manual override ready

---

**Current Priority:** Run `python remote_pi_setup.py` to fix network issues and establish basic communication.
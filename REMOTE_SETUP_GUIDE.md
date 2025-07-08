# Remote Drone Ground Station Setup Guide
# Working with Raspberry Pi via SSH Connection

🔗 **You're now connected to your Raspberry Pi! Let's set up the drone ground station system remotely.**

## Current Status Analysis

✅ **Successfully Connected**: SSH to Pi at 192.168.4.1  
✅ **System Info**: Debian GNU/Linux, Kernel 6.1.21-v8+ (64-bit ARM)  
✅ **Basic Packages**: Python environment with essential libraries installed  
❌ **Network Issue**: Cannot resolve external DNS (deb.debian.org, security.debian.org)

## Immediate Network Troubleshooting

### Step 1: Check Network Configuration
```bash
# On Pi - Check current network status
ip addr show
ip route show
cat /etc/resolv.conf

# Test basic connectivity
ping 8.8.8.8          # Test internet connectivity
ping google.com       # Test DNS resolution
```

### Step 2: Fix DNS Resolution
```bash
# Temporarily fix DNS
sudo nano /etc/resolv.conf
# Add these lines:
# nameserver 8.8.8.8
# nameserver 8.8.4.4

# Or use systemd-resolved
sudo systemctl restart systemd-resolved
```

### Step 3: Alternative Package Sources
```bash
# If DNS issues persist, try different mirrors
sudo nano /etc/apt/sources.list
# Replace with:
# deb http://mirror.ox.ac.uk/sites/archive.ubuntu.com/ubuntu/ bullseye main
# deb http://mirror.ox.ac.uk/sites/archive.ubuntu.com/ubuntu/ bullseye-updates main
```

## Remote Setup Process

### Phase 1: Prepare Pi Environment (10 minutes)

1. **Create project directory**
   ```bash
   # On Pi
   mkdir -p ~/drone_ground_station
   cd ~/drone_ground_station
   ```

2. **Check Python environment**
   ```bash
   python3 --version
   pip3 --version
   
   # Install essential packages (if network works)
   pip3 install --user pyserial opencv-python numpy
   ```

3. **Enable required interfaces**
   ```bash
   sudo raspi-config
   # Navigate to Interface Options
   # Enable: Camera, SSH, UART
   # Disable: Serial Console (keep hardware enabled)
   ```

### Phase 2: Transfer Files from Laptop

#### Method 1: SCP Transfer (Recommended)
```bash
# On your Windows laptop (Command Prompt)
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR"

# Transfer setup script
scp raspberry_pi_setup.sh pi@192.168.4.1:~/

# Transfer Python requirements
scp raspberry_pi_requirements.txt pi@192.168.4.1:~/

# Transfer Pi scripts
scp -r raspberry_pi_scripts pi@192.168.4.1:~/drone_ground_station/

# Transfer configuration
scp -r config pi@192.168.4.1:~/drone_ground_station/
```

#### Method 2: Manual File Creation
If SCP fails, create files manually on Pi:

```bash
# On Pi - Create essential configuration
cat > ~/drone_ground_station/config.json << 'EOF'
{
  "network": {
    "video_port": 5600,
    "telemetry_port": 14550,
    "command_port": 14551,
    "ground_station_ip": "192.168.4.2"
  },
  "camera": {
    "resolution": [1280, 720],
    "framerate": 30,
    "bitrate": 2000000
  },
  "uart": {
    "port": "/dev/serial0",
    "baudrate": 115200
  }
}
EOF
```

### Phase 3: Install Dependencies

#### Option A: With Internet (after fixing DNS)
```bash
# On Pi
sudo apt update
sudo apt install -y python3-pip python3-venv git
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-*
sudo apt install -y python3-opencv python3-serial python3-numpy
```

#### Option B: Offline Installation
```bash
# Use pre-installed packages
python3 -c "import cv2, serial, numpy; print('Core packages available')"

# Install from local wheels (if available)
pip3 install --user --no-index --find-links ~/wheels/ pyserial
```

### Phase 4: Hardware Setup Verification

1. **Test Camera**
   ```bash
   # On Pi
   libcamera-hello --timeout 5000
   # Or for older systems:
   raspistill -o test.jpg -t 5000
   ```

2. **Test UART**
   ```bash
   # Check UART availability
   ls -la /dev/serial*
   ls -la /dev/ttyAMA*
   
   # Test UART communication
   sudo minicom -D /dev/serial0 -b 115200
   # Press Ctrl+A then X to exit
   ```

3. **Test GPIO**
   ```bash
   # Quick GPIO test
   python3 -c "import RPi.GPIO as GPIO; print('GPIO available')"
   ```

### Phase 5: Create Core Scripts

#### Video Streamer Script
```bash
# On Pi - Create video streaming script
cat > ~/drone_ground_station/video_streamer.py << 'EOF'
#!/usr/bin/env python3
import subprocess
import time
import json

def start_video_stream():
    """Start GStreamer video pipeline"""
    try:
        # Load configuration
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        video_port = config['network']['video_port']
        gs_ip = config['network']['ground_station_ip']
        
        # GStreamer pipeline for H.264 streaming
        pipeline = [
            'gst-launch-1.0',
            'libcamerasrc', '!',
            'video/x-raw,width=1280,height=720,framerate=30/1', '!',
            'videoconvert', '!',
            'x264enc', 'tune=zerolatency', 'bitrate=2000', '!',
            'rtph264pay', '!',
            'udpsink', f'host={gs_ip}', f'port={video_port}'
        ]
        
        print(f"Starting video stream to {gs_ip}:{video_port}")
        subprocess.run(pipeline)
        
    except Exception as e:
        print(f"Video stream error: {e}")
        
if __name__ == "__main__":
    start_video_stream()
EOF

chmod +x ~/drone_ground_station/video_streamer.py
```

#### Telemetry Bridge Script
```bash
# On Pi - Create telemetry forwarding script
cat > ~/drone_ground_station/telemetry_bridge.py << 'EOF'
#!/usr/bin/env python3
import serial
import socket
import json
import time
import threading

class TelemetryBridge:
    def __init__(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            
        self.uart_port = self.config['uart']['port']
        self.baudrate = self.config['uart']['baudrate']
        self.telemetry_port = self.config['network']['telemetry_port']
        self.gs_ip = self.config['network']['ground_station_ip']
        
        self.running = False
        
    def start(self):
        """Start telemetry bridge"""
        try:
            # Open UART
            self.serial_conn = serial.Serial(self.uart_port, self.baudrate, timeout=1)
            
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.running = True
            print(f"Telemetry bridge started: {self.uart_port} -> {self.gs_ip}:{self.telemetry_port}")
            
            # Start forwarding
            while self.running:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    self.udp_socket.sendto(data, (self.gs_ip, self.telemetry_port))
                    
                time.sleep(0.01)  # 100Hz loop
                
        except Exception as e:
            print(f"Telemetry bridge error: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Stop telemetry bridge"""
        self.running = False
        if hasattr(self, 'serial_conn'):
            self.serial_conn.close()
        if hasattr(self, 'udp_socket'):
            self.udp_socket.close()
            
if __name__ == "__main__":
    bridge = TelemetryBridge()
    try:
        bridge.start()
    except KeyboardInterrupt:
        bridge.stop()
EOF

chmod +x ~/drone_ground_station/telemetry_bridge.py
```

#### System Startup Script
```bash
# On Pi - Create main startup script
cat > ~/drone_ground_station/drone_startup.py << 'EOF'
#!/usr/bin/env python3
import subprocess
import time
import signal
import sys
import os

class DroneGroundStation:
    def __init__(self):
        self.processes = []
        
    def start_services(self):
        """Start all ground station services"""
        print("Starting Drone Ground Station...")
        
        # Start video streaming
        video_proc = subprocess.Popen(['python3', 'video_streamer.py'])
        self.processes.append(video_proc)
        print("Video streaming started")
        
        time.sleep(2)
        
        # Start telemetry bridge
        telemetry_proc = subprocess.Popen(['python3', 'telemetry_bridge.py'])
        self.processes.append(telemetry_proc)
        print("Telemetry bridge started")
        
        print("All services running. Press Ctrl+C to stop.")
        
    def stop_services(self):
        """Stop all services"""
        print("Stopping services...")
        for proc in self.processes:
            proc.terminate()
            proc.wait()
        print("All services stopped")
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stop_services()
        sys.exit(0)
        
if __name__ == "__main__":
    os.chdir('/home/pi/drone_ground_station')
    
    station = DroneGroundStation()
    signal.signal(signal.SIGINT, station.signal_handler)
    signal.signal(signal.SIGTERM, station.signal_handler)
    
    station.start_services()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        station.stop_services()
EOF

chmod +x ~/drone_ground_station/drone_startup.py
```

### Phase 6: Test the System

1. **Test Video Stream**
   ```bash
   # On Pi
   cd ~/drone_ground_station
   python3 video_streamer.py
   ```

2. **Test on Laptop** (separate terminal)
   ```bash
   # On Windows laptop
   gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
   ```

3. **Test Telemetry**
   ```bash
   # On Pi
   python3 telemetry_bridge.py
   ```

### Phase 7: Create Systemd Service (Auto-start)

```bash
# On Pi - Create systemd service
sudo tee /etc/systemd/system/drone-ground-station.service << 'EOF'
[Unit]
Description=Drone Ground Station
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/drone_ground_station
ExecStart=/usr/bin/python3 drone_startup.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable drone-ground-station.service
sudo systemctl start drone-ground-station.service

# Check status
sudo systemctl status drone-ground-station.service
```

## Laptop Ground Station Setup

### Test Video Reception
```bash
# On Windows laptop - test GStreamer
gst-launch-1.0 --version

# Receive video stream
gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### Test Telemetry Reception
```python
# On laptop - create telemetry_test.py
import socket
import time

def test_telemetry():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 14550))
    sock.settimeout(5)
    
    print("Listening for telemetry on port 14550...")
    
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            print(f"Received {len(data)} bytes from {addr}")
            print(f"Data: {data[:50]}...")  # First 50 bytes
    except socket.timeout:
        print("No telemetry data received")
    except KeyboardInterrupt:
        print("Test stopped")
    finally:
        sock.close()

if __name__ == "__main__":
    test_telemetry()
```

## Troubleshooting Common Issues

### Network Connectivity
```bash
# On Pi - Check WiFi status
iwconfig
sudo iwlist scan | grep ESSID

# Restart networking
sudo systemctl restart networking
sudo systemctl restart dhcpcd
```

### Camera Issues
```bash
# Check camera detection
lsusb  # For USB cameras
vcgencmd get_camera  # For CSI camera

# Test camera
libcamera-hello --list-cameras
libcamera-vid -t 5000 --inline
```

### UART Issues
```bash
# Check UART configuration
sudo raspi-config  # Interface Options -> Serial Port

# Check boot configuration
grep -E "enable_uart|console" /boot/config.txt
grep -E "console" /boot/cmdline.txt
```

### Service Management
```bash
# Check service logs
sudo journalctl -u drone-ground-station.service -f

# Restart service
sudo systemctl restart drone-ground-station.service

# Stop service
sudo systemctl stop drone-ground-station.service
```

## Next Steps

1. **Complete hardware connections** (camera, UART to flight controller)
2. **Test video streaming** between Pi and laptop
3. **Verify telemetry data flow** from flight controller
4. **Run integration tests** using the provided scripts
5. **Configure flight controller** for MSP telemetry output

## Quick Commands Reference

```bash
# On Pi - Essential commands
cd ~/drone_ground_station
python3 drone_startup.py                    # Start all services
sudo systemctl status drone-ground-station  # Check service status
sudo journalctl -f                          # View live logs
vcgencmd measure_temp                       # Check Pi temperature
htop                                        # Monitor system resources

# On Laptop - Test commands
ping 192.168.4.1                           # Test Pi connectivity
python telemetry_test.py                   # Test telemetry reception
gst-launch-1.0 udpsrc port=5600 ...        # Test video reception
```

---

**🎯 Current Status**: You're successfully connected to the Pi and ready to deploy the drone ground station system remotely!

**⚠️ Priority**: Fix the DNS resolution issue first, then proceed with the setup steps above.

**📋 Next Action**: Run the network troubleshooting commands and start transferring/creating the necessary files on the Pi.
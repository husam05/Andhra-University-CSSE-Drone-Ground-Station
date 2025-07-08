# Practical Implementation Guide
# Raspberry Pi 3 + Laptop Drone Ground Station Setup

This guide provides step-by-step instructions for setting up the complete drone ground station system with a Raspberry Pi 3 and your laptop.

## Hardware Requirements

### Raspberry Pi 3 Setup
- Raspberry Pi 3 Model B/B+
- MicroSD card (32GB+ recommended)
- Raspberry Pi Camera Module v2 or USB camera
- MicroUSB power supply (5V 2.5A)
- UART-to-USB converter (for Crossflight connection)
- Jumper wires
- WiFi dongle (if using Pi 3 as hotspot)

### Laptop Setup
- Windows 10/11 laptop
- WiFi capability
- USB ports for development
- Minimum 8GB RAM, 4GB free disk space

### Drone Hardware
- Flight controller running Crossflight firmware
- UART pins accessible for telemetry
- Power distribution for Pi 3

## Phase 1: Raspberry Pi 3 Setup

### Step 1: Prepare Raspberry Pi OS

1. **Download Raspberry Pi OS Lite**
   ```bash
   # Download from: https://www.raspberrypi.org/software/operating-systems/
   # Use Raspberry Pi Imager to flash to SD card
   ```

2. **Enable SSH and WiFi (Headless Setup)**
   ```bash
   # Create empty 'ssh' file in boot partition
   touch /boot/ssh
   
   # Create wpa_supplicant.conf in boot partition
   cat > /boot/wpa_supplicant.conf << EOF
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   
   network={
       ssid="YourWiFiName"
       psk="YourWiFiPassword"
   }
   EOF
   ```

3. **First Boot and SSH Connection**
   ```bash
   # Insert SD card and boot Pi
   # Find Pi IP address from router or use:
   nmap -sn 192.168.1.0/24
   
   # SSH into Pi (default: pi/raspberry)
   ssh pi@192.168.1.XXX
   ```

### Step 2: System Configuration

1. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo raspi-config
   # Enable Camera, SPI, I2C, Serial (disable console)
   ```

2. **Install Required Packages**
   ```bash
   # Python and development tools
   sudo apt install -y python3-pip python3-venv git
   
   # Video streaming dependencies
   sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base \
                       gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
                       gstreamer1.0-plugins-ugly gstreamer1.0-libav
   
   # Camera support
   sudo apt install -y python3-picamera
   
   # Serial communication
   sudo apt install -y python3-serial
   
   # Network tools
   sudo apt install -y hostapd dnsmasq iptables-persistent
   ```

### Step 3: Hardware Connections

1. **Camera Connection**
   ```
   Raspberry Pi Camera Module v2:
   - Connect ribbon cable to camera port
   - Ensure contacts face away from ethernet port
   
   USB Camera (alternative):
   - Connect to any USB port
   - Verify with: lsusb
   ```

2. **UART Connection to Flight Controller**
   ```
   Raspberry Pi 3 GPIO:     Flight Controller:
   GPIO 14 (TXD) ---------> RX pin
   GPIO 15 (RXD) ---------> TX pin
   GND -----------------> GND
   
   Note: Use 3.3V logic level. Add level shifter if FC uses 5V.
   ```

3. **Power Connection**
   ```
   Option 1: Separate 5V BEC from drone battery
   Option 2: USB power bank mounted on drone
   Option 3: Direct battery connection with voltage regulator
   ```

### Step 4: Software Installation on Pi

1. **Clone Project**
   ```bash
   cd /home/pi
   git clone <your-repo-url> drone_station
   cd drone_station
   ```

2. **Install Python Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r raspberry_pi_requirements.txt
   ```

3. **Configure System**
   ```bash
   # Copy configuration files
   cp raspberry_pi_scripts/config.json /home/pi/
   
   # Edit configuration
   nano /home/pi/config.json
   # Update ground_station_ip to your laptop's IP
   ```

### Step 5: WiFi Hotspot Setup

1. **Configure hostapd**
   ```bash
   sudo nano /etc/hostapd/hostapd.conf
   ```
   ```
   interface=wlan0
   driver=nl80211
   ssid=DroneStation
   hw_mode=g
   channel=7
   wmm_enabled=0
   macaddr_acl=0
   auth_algs=1
   ignore_broadcast_ssid=0
   wpa=2
   wpa_passphrase=DronePass123
   wpa_key_mgmt=WPA-PSK
   wpa_pairwise=TKIP
   rsn_pairwise=CCMP
   ```

2. **Configure dnsmasq**
   ```bash
   sudo nano /etc/dnsmasq.conf
   ```
   ```
   interface=wlan0
   dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
   ```

3. **Configure Network Interface**
   ```bash
   sudo nano /etc/dhcpcd.conf
   ```
   ```
   interface wlan0
   static ip_address=192.168.4.1/24
   nohook wpa_supplicant
   ```

4. **Enable Services**
   ```bash
   sudo systemctl enable hostapd
   sudo systemctl enable dnsmasq
   ```

### Step 6: Auto-Start Service

1. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/drone-station.service
   ```
   ```ini
   [Unit]
   Description=Drone Ground Station
   After=network.target
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/drone_station
   ExecStart=/home/pi/drone_station/venv/bin/python raspberry_pi_scripts/drone_startup.py
   Restart=always
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable Service**
   ```bash
   sudo systemctl enable drone-station.service
   sudo systemctl start drone-station.service
   ```

## Phase 2: Laptop Setup

### Step 1: Install ROS2 Humble

1. **Download and Install**
   ```powershell
   # Download ROS2 Humble from:
   # https://github.com/ros2/ros2/releases
   
   # Extract to C:\dev\ros2_humble
   # Add to PATH in environment variables
   ```

2. **Install Visual Studio Build Tools**
   ```powershell
   # Download from Microsoft
   # Install C++ build tools and Windows SDK
   ```

### Step 2: Install GStreamer

1. **Download GStreamer**
   ```powershell
   # Download from: https://gstreamer.freedesktop.org/download/
   # Install both runtime and development packages
   # Add to PATH: C:\gstreamer\1.0\msvc_x86_64\bin
   ```

2. **Verify Installation**
   ```powershell
   gst-launch-1.0 --version
   ```

### Step 3: Setup Project

1. **Clone Repository**
   ```powershell
   cd C:\dev
   git clone <your-repo-url> drone_ground_station
   cd drone_ground_station
   ```

2. **Install Python Dependencies**
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Build ROS2 Package**
   ```powershell
   # Setup ROS2 environment
   C:\dev\ros2_humble\local_setup.bat
   
   # Build package
   colcon build --packages-select drone_ground_station
   
   # Source workspace
   install\setup.bat
   ```

## Phase 3: Network Configuration

### Step 1: Connect Laptop to Pi Hotspot

1. **WiFi Connection**
   - SSID: `DroneStation`
   - Password: `DronePass123`
   - Pi IP: `192.168.4.1`
   - Laptop will get IP: `192.168.4.x`

2. **Verify Connection**
   ```powershell
   ping 192.168.4.1
   ```

### Step 2: Configure Firewall

1. **Windows Firewall**
   ```powershell
   # Allow ROS2 and GStreamer ports
   netsh advfirewall firewall add rule name="ROS2 DDS" dir=in action=allow protocol=UDP localport=7400-7500
   netsh advfirewall firewall add rule name="Video Stream" dir=in action=allow protocol=UDP localport=5600
   netsh advfirewall firewall add rule name="Telemetry" dir=in action=allow protocol=UDP localport=5000
   ```

## Phase 4: Testing and Validation

### Step 1: Basic Connectivity Test

1. **Run System Test**
   ```powershell
   cd C:\dev\drone_ground_station
   python test_system.py --drone_ip 192.168.4.1 --verbose
   ```

2. **Manual Tests**
   ```powershell
   # Test video stream
   gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,encoding-name=H264,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
   
   # Test telemetry
   python examples/telemetry_monitor.py --drone_ip 192.168.4.1
   ```

### Step 2: Integration Test

1. **Run Full Integration Test**
   ```powershell
   python examples/integration_test.py --drone_ip 192.168.4.1 --full_test
   ```

2. **Launch Ground Station**
   ```powershell
   ros2 launch drone_ground_station ground_station.launch.py drone_ip:=192.168.4.1
   ```

## Phase 5: Flight Testing

### Step 1: Pre-Flight Checks

1. **System Status**
   ```bash
   # On Raspberry Pi
   sudo systemctl status drone-station.service
   
   # Check logs
   journalctl -u drone-station.service -f
   ```

2. **Ground Station Status**
   ```powershell
   # On laptop
   ros2 topic list
   ros2 topic echo /drone/telemetry
   ```

### Step 2: Basic Flight Test

1. **Run Flight Demo**
   ```powershell
   python examples/basic_flight_demo.py --drone_ip 192.168.4.1
   ```

2. **Monitor Systems**
   ```powershell
   # Terminal 1: Telemetry
   python examples/telemetry_monitor.py --drone_ip 192.168.4.1 --log_file flight_data.csv
   
   # Terminal 2: Video
   python examples/video_analyzer.py --drone_ip 192.168.4.1 --save_frames
   
   # Terminal 3: Ground Station GUI
   ros2 run drone_ground_station ground_station_gui
   ```

## Troubleshooting

### Common Issues

1. **No Video Stream**
   ```bash
   # Check camera on Pi
   raspistill -o test.jpg
   
   # Check GStreamer pipeline
   gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480 ! videoconvert ! x264enc ! rtph264pay ! udpsink host=192.168.4.2 port=5600
   ```

2. **No Telemetry Data**
   ```bash
   # Check serial connection
   sudo dmesg | grep tty
   
   # Test serial port
   sudo minicom -D /dev/serial0 -b 115200
   ```

3. **Network Issues**
   ```bash
   # Check WiFi status
   iwconfig
   
   # Restart networking
   sudo systemctl restart dhcpcd
   sudo systemctl restart hostapd
   ```

4. **ROS2 Issues**
   ```powershell
   # Check ROS2 environment
   echo %ROS_DOMAIN_ID%
   
   # Reset ROS2
   ros2 daemon stop
   ros2 daemon start
   ```

### Performance Optimization

1. **Video Quality**
   ```json
   // In config.json
   {
     "video": {
       "resolution": [1280, 720],
       "framerate": 30,
       "bitrate": 2000000
     }
   }
   ```

2. **Network Optimization**
   ```bash
   # Increase network buffers
   echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
   echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
   ```

## Safety Considerations

1. **Emergency Procedures**
   - Always have manual override capability
   - Test emergency landing function
   - Monitor battery levels continuously
   - Maintain visual line of sight

2. **System Monitoring**
   - Set up low battery alerts
   - Monitor communication link quality
   - Check system temperatures
   - Log all flight data

## Next Steps

1. **Advanced Features**
   - Implement autonomous waypoint navigation
   - Add computer vision capabilities
   - Integrate additional sensors
   - Develop mission planning interface

2. **System Improvements**
   - Implement redundant communication links
   - Add real-time video recording
   - Develop mobile app interface
   - Create cloud data logging

## Support and Resources

- **Documentation**: See INSTALLATION.md and QUICK_START.md
- **Testing**: Use test_system.py for diagnostics
- **Examples**: Check examples/ directory for sample code
- **Troubleshooting**: See logs in /var/log/ on Pi and Windows Event Viewer

---

**Remember**: Always follow local regulations for drone operations and ensure proper safety measures are in place before flight testing.
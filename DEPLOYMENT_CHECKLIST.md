# Drone Ground Station Deployment Checklist
# Complete Setup and Testing Guide

This checklist ensures proper deployment and testing of the drone ground station system with Raspberry Pi 3 and laptop.

## Pre-Deployment Preparation

### Hardware Requirements Verification

#### Raspberry Pi 3 Setup
- [ ] Raspberry Pi 3 Model B/B+ with heat sinks installed
- [ ] MicroSD card (32GB+ Class 10) with Raspberry Pi OS Lite
- [ ] Raspberry Pi Camera Module v2 or USB camera
- [ ] 5V 3A power supply or USB power bank (10,000mAh+)
- [ ] Jumper wires for UART connection (3 wires minimum)
- [ ] Case or mounting solution for drone integration
- [ ] WiFi antenna (built-in should be sufficient)

#### Flight Controller
- [ ] Crossflight-compatible flight controller
- [ ] UART pins identified and accessible
- [ ] 3.3V logic level confirmed (or level converter available)
- [ ] MSP protocol enabled in flight controller firmware
- [ ] Telemetry output configured

#### Laptop/Ground Station
- [ ] Laptop with Windows/Linux/macOS
- [ ] Python 3.8+ installed
- [ ] Git installed
- [ ] Administrative privileges for software installation
- [ ] WiFi capability
- [ ] Minimum 8GB RAM, 20GB free disk space

#### Network Equipment
- [ ] WiFi router/hotspot capability on Raspberry Pi
- [ ] Network cables (if needed for testing)
- [ ] USB WiFi adapter (backup, if needed)

### Software Preparation

#### Download Required Files
- [ ] Clone or download the drone ground station project
- [ ] Raspberry Pi OS image downloaded
- [ ] SD card flashing tool (Raspberry Pi Imager)
- [ ] SSH client (PuTTY for Windows, or built-in terminal)

#### Verify Dependencies
- [ ] Python 3.8+ available on laptop
- [ ] pip package manager working
- [ ] Git command line tools functional
- [ ] Internet connection for package downloads

## Phase 1: Raspberry Pi Setup

### Step 1: SD Card Preparation
- [ ] Flash Raspberry Pi OS Lite to SD card
- [ ] Enable SSH before first boot
  ```bash
  # Create empty 'ssh' file in boot partition
  touch /boot/ssh
  ```
- [ ] Configure WiFi for initial setup (optional)
  ```bash
  # Create wpa_supplicant.conf in boot partition
  country=US
  ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
  update_config=1
  
  network={
      ssid="YourWiFiNetwork"
      psk="YourPassword"
  }
  ```
- [ ] Insert SD card into Raspberry Pi

### Step 2: Initial Boot and Access
- [ ] Power on Raspberry Pi
- [ ] Wait for boot completion (green LED stops flashing)
- [ ] Find Pi IP address on network
  ```bash
  # Scan network for Pi
  nmap -sn 192.168.1.0/24
  # Or check router admin panel
  ```
- [ ] SSH into Raspberry Pi
  ```bash
  ssh pi@<PI_IP_ADDRESS>
  # Default password: raspberry
  ```
- [ ] Change default password
  ```bash
  passwd
  ```

### Step 3: Basic Configuration
- [ ] Update system packages
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- [ ] Configure timezone
  ```bash
  sudo raspi-config
  # Navigate to Localisation Options > Timezone
  ```
- [ ] Enable camera interface
  ```bash
  sudo raspi-config
  # Navigate to Interface Options > Camera > Enable
  ```
- [ ] Enable UART
  ```bash
  sudo raspi-config
  # Navigate to Interface Options > Serial Port
  # Enable serial port hardware: Yes
  # Enable login shell over serial: No
  ```
- [ ] Reboot to apply changes
  ```bash
  sudo reboot
  ```

### Step 4: Automated Setup
- [ ] Copy setup script to Raspberry Pi
  ```bash
  # On laptop, copy the setup script
  scp scripts/raspberry_pi_setup.sh pi@<PI_IP>:~/
  ```
- [ ] Make script executable and run
  ```bash
  # On Raspberry Pi
  chmod +x raspberry_pi_setup.sh
  ./raspberry_pi_setup.sh
  ```
- [ ] Monitor installation progress (may take 30-60 minutes)
- [ ] Reboot after installation completes
  ```bash
  sudo reboot
  ```

### Step 5: Hardware Connections
- [ ] Power off Raspberry Pi
  ```bash
  sudo shutdown -h now
  ```
- [ ] Connect camera module
  - [ ] Lift CSI port connector
  - [ ] Insert ribbon cable (contacts away from Ethernet port)
  - [ ] Press connector down to secure
- [ ] Connect flight controller UART
  - [ ] FC TX → Pi GPIO 15 (Pin 10, RXD)
  - [ ] FC RX → Pi GPIO 14 (Pin 8, TXD)
  - [ ] FC GND → Pi GND (Pin 6)
  - [ ] **DO NOT connect 5V** (Pi uses 3.3V logic)
- [ ] Secure all connections with tape or heat shrink
- [ ] Power on Raspberry Pi

### Step 6: Hardware Testing
- [ ] Test camera functionality
  ```bash
  # SSH into Pi and test camera
  ~/drone_ground_station/scripts/test_camera.sh
  ```
- [ ] Test UART connection
  ```bash
  ~/drone_ground_station/scripts/test_uart.sh
  ```
- [ ] Verify WiFi hotspot
  ```bash
  ~/drone_ground_station/scripts/test_network.sh
  ```
- [ ] Check system status
  ```bash
  ~/drone_ground_station/scripts/system_status.sh
  ```

## Phase 2: Laptop Ground Station Setup

### Step 1: Environment Preparation
- [ ] Open terminal/command prompt with admin privileges
- [ ] Navigate to project directory
  ```bash
  cd /path/to/drone-ground-station
  ```
- [ ] Verify Python installation
  ```bash
  python --version  # Should be 3.8+
  ```

### Step 2: Automated Setup
- [ ] Run laptop setup script
  ```bash
  # Windows
  python scripts/laptop_setup.py
  
  # Linux/macOS
  python3 scripts/laptop_setup.py
  ```
- [ ] Follow installation prompts
- [ ] Install any additional system dependencies as prompted
- [ ] Verify virtual environment creation

### Step 3: Manual Dependency Installation (if needed)
- [ ] Install GStreamer (if not automated)
  
  **Windows:**
  - [ ] Download from https://gstreamer.freedesktop.org/download/
  - [ ] Install both runtime and development packages
  - [ ] Add to system PATH
  
  **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-*
  ```
  
  **macOS:**
  ```bash
  brew install gstreamer gst-plugins-base gst-plugins-good
  ```

- [ ] Install ROS2 (Linux only, optional)
  ```bash
  # Ubuntu 22.04
  sudo apt install ros-humble-desktop
  ```

### Step 4: Configuration
- [ ] Edit configuration file
  ```bash
  # Edit config/ground_station_config.json
  {
    "network": {
      "drone_ip": "192.168.4.1",
      "ground_station_ip": "192.168.4.2"
    }
  }
  ```
- [ ] Configure firewall rules (if needed)
  
  **Windows:**
  ```cmd
  # Allow video port
  netsh advfirewall firewall add rule name="Drone Video" dir=in action=allow protocol=UDP localport=5600
  ```
  
  **Linux:**
  ```bash
  sudo ufw allow 5600/udp
  sudo ufw allow 14550/udp
  ```

### Step 5: Testing Ground Station
- [ ] Test GStreamer installation
  ```bash
  python scripts/test_gstreamer.py
  ```
- [ ] Test Python dependencies
  ```bash
  # Activate virtual environment
  source venv/bin/activate  # Linux/macOS
  venv\Scripts\activate     # Windows
  
  # Test imports
  python -c "import cv2, numpy, PyQt5; print('All imports successful')"
  ```

## Phase 3: System Integration

### Step 1: Network Connection
- [ ] Connect laptop to Raspberry Pi WiFi hotspot
  - [ ] SSID: `DroneGroundStation`
  - [ ] Password: `DroneControl123`
- [ ] Verify IP assignment
  ```bash
  # Check laptop IP (should be 192.168.4.x)
  ipconfig        # Windows
  ip addr show    # Linux
  ifconfig        # macOS
  ```
- [ ] Test basic connectivity
  ```bash
  ping 192.168.4.1
  ```

### Step 2: Communication Testing
- [ ] Run comprehensive integration test
  ```bash
  python scripts/system_integration_test.py
  ```
- [ ] Verify all test results
  - [ ] Network connectivity: PASS
  - [ ] Port accessibility: PASS
  - [ ] Video stream reception: PASS
  - [ ] Telemetry reception: PASS
  - [ ] Command interface: PASS

### Step 3: Individual Component Testing
- [ ] Test video streaming
  ```bash
  # On laptop, test video reception
  gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
  ```
- [ ] Test telemetry data
  ```bash
  python examples/telemetry_monitor.py --drone-ip 192.168.4.1
  ```
- [ ] Test basic flight commands
  ```bash
  python examples/basic_flight_demo.py --drone-ip 192.168.4.1 --test-mode
  ```

## Phase 4: Flight Testing

### Pre-Flight Safety Checks
- [ ] **SAFETY FIRST**: Ensure safe testing environment
- [ ] Remove propellers for initial testing
- [ ] Have manual override ready (RC transmitter)
- [ ] Check battery levels (drone and ground station)
- [ ] Verify emergency stop procedures
- [ ] Ensure clear area for testing

### Step 1: Ground Testing
- [ ] Power on flight controller
- [ ] Start Raspberry Pi ground station
  ```bash
  # SSH to Pi
  ~/drone_ground_station/scripts/start_drone_system.sh
  ```
- [ ] Launch laptop ground station
  ```bash
  # On laptop
  scripts/launch_ground_station.sh  # Linux/macOS
  scripts/launch_ground_station.bat # Windows
  ```
- [ ] Verify all systems operational
  - [ ] Video feed visible
  - [ ] Telemetry data updating
  - [ ] Command interface responsive

### Step 2: Communication Range Testing
- [ ] Test at 1 meter distance
- [ ] Test at 5 meter distance
- [ ] Test at 10 meter distance
- [ ] Test at maximum intended range
- [ ] Monitor signal quality and latency
- [ ] Document any connection issues

### Step 3: Basic Flight Test (with propellers)
- [ ] **SAFETY**: Ensure safe flight area
- [ ] Install propellers
- [ ] Arm flight controller via ground station
- [ ] Test basic movements:
  - [ ] Throttle up/down
  - [ ] Roll left/right
  - [ ] Pitch forward/back
  - [ ] Yaw left/right
- [ ] Test emergency stop
- [ ] Land safely

## Phase 5: Performance Optimization

### Step 1: Video Quality Optimization
- [ ] Adjust video resolution for optimal performance
- [ ] Test different bitrate settings
- [ ] Optimize GStreamer pipeline
- [ ] Monitor CPU usage during streaming

### Step 2: Network Optimization
- [ ] Test different WiFi channels
- [ ] Optimize antenna positioning
- [ ] Monitor packet loss
- [ ] Test interference resistance

### Step 3: System Performance
- [ ] Monitor Raspberry Pi temperature
- [ ] Check CPU and memory usage
- [ ] Optimize startup time
- [ ] Test battery life

## Troubleshooting Common Issues

### Network Issues
- [ ] **No WiFi hotspot visible**
  - Check hostapd service: `sudo systemctl status hostapd`
  - Restart networking: `sudo systemctl restart hostapd dnsmasq`
  - Check configuration files

- [ ] **Cannot connect to hotspot**
  - Verify password: `DroneControl123`
  - Check DHCP service: `sudo systemctl status dnsmasq`
  - Try manual IP configuration

- [ ] **High latency/packet loss**
  - Change WiFi channel in hostapd.conf
  - Check for interference
  - Reduce video bitrate
  - Optimize antenna positioning

### Video Issues
- [ ] **No video stream**
  - Test camera: `raspistill -o test.jpg`
  - Check GStreamer pipeline
  - Verify network connectivity
  - Check firewall settings

- [ ] **Poor video quality**
  - Adjust camera settings
  - Increase bitrate
  - Check lighting conditions
  - Verify lens cleanliness

- [ ] **Video lag**
  - Reduce resolution
  - Lower bitrate
  - Optimize network
  - Check CPU usage

### Telemetry Issues
- [ ] **No telemetry data**
  - Check UART connections
  - Verify baud rate (115200)
  - Test with multimeter
  - Check flight controller MSP settings

- [ ] **Corrupted telemetry**
  - Check ground connections
  - Verify voltage levels (3.3V)
  - Test with logic analyzer
  - Check for electromagnetic interference

### System Issues
- [ ] **Raspberry Pi overheating**
  - Install heat sinks
  - Improve ventilation
  - Reduce CPU load
  - Monitor temperature: `vcgencmd measure_temp`

- [ ] **Power issues**
  - Check power supply capacity (3A minimum)
  - Monitor voltage: `vcgencmd measure_volts`
  - Check for under-voltage warnings
  - Use quality power cables

- [ ] **SD card corruption**
  - Use high-quality SD card (Class 10+)
  - Enable read-only filesystem for critical partitions
  - Regular backups
  - Monitor disk usage

## Maintenance and Updates

### Regular Maintenance
- [ ] **Weekly**
  - Check system logs for errors
  - Verify all connections secure
  - Test emergency procedures
  - Update flight logs

- [ ] **Monthly**
  - Update system packages
  - Check SD card health
  - Calibrate sensors
  - Review performance metrics

- [ ] **Before each flight**
  - Run system integration test
  - Check battery levels
  - Verify communication range
  - Test emergency stop

### Software Updates
- [ ] Keep Raspberry Pi OS updated
  ```bash
  sudo apt update && sudo apt upgrade
  ```
- [ ] Update Python packages
  ```bash
  pip install --upgrade -r requirements.txt
  ```
- [ ] Update flight controller firmware as needed
- [ ] Backup configurations before updates

### Documentation
- [ ] Maintain flight logs
- [ ] Document any modifications
- [ ] Record performance metrics
- [ ] Update troubleshooting procedures

## Emergency Procedures

### Communication Loss
1. [ ] Attempt manual RC control
2. [ ] Check ground station status
3. [ ] Restart communication systems
4. [ ] Execute return-to-home if available
5. [ ] Manual landing if necessary

### System Failure
1. [ ] Immediate manual override
2. [ ] Emergency landing
3. [ ] Power down systems safely
4. [ ] Investigate failure cause
5. [ ] Document incident

### Power Loss
1. [ ] Monitor battery levels continuously
2. [ ] Low battery warning at 20%
3. [ ] Automatic landing at 10%
4. [ ] Emergency power-off procedures

## Success Criteria

### System Ready for Operation
- [ ] All integration tests pass
- [ ] Video latency < 200ms
- [ ] Telemetry update rate > 5Hz
- [ ] Communication range > 100m
- [ ] Battery life > 30 minutes
- [ ] Emergency procedures tested
- [ ] Documentation complete

### Performance Benchmarks
- [ ] Video: 720p @ 30fps, < 2Mbps
- [ ] Latency: < 100ms end-to-end
- [ ] Packet loss: < 1%
- [ ] CPU usage: < 70% average
- [ ] Temperature: < 70°C
- [ ] Range: 200m+ line of sight

---

**⚠️ SAFETY REMINDER**: Always follow local drone regulations and safety guidelines. Never fly beyond visual line of sight without proper authorization. Always have manual override capability available.

**📋 COMPLETION**: Check off each item as completed. Keep this checklist for reference during deployment and troubleshooting.
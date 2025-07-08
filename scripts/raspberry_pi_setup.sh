#!/bin/bash
# Raspberry Pi 3 Drone Ground Station Setup Script
# This script automates the installation and configuration of the drone ground station system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as pi user."
        exit 1
    fi
}

# Check Raspberry Pi model
check_pi_model() {
    log "Checking Raspberry Pi model..."
    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
    info "Detected: $PI_MODEL"
    
    if [[ ! "$PI_MODEL" =~ "Raspberry Pi 3" ]]; then
        warn "This script is optimized for Raspberry Pi 3. Continuing anyway..."
    fi
}

# Update system
update_system() {
    log "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
    
    log "Installing essential packages..."
    sudo apt install -y \
        git \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        cmake \
        pkg-config \
        libjpeg-dev \
        libtiff5-dev \
        libjasper-dev \
        libpng-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libfontconfig1-dev \
        libcairo2-dev \
        libgdk-pixbuf2.0-dev \
        libpango1.0-dev \
        libgtk2.0-dev \
        libgtk-3-dev \
        libatlas-base-dev \
        gfortran \
        libhdf5-dev \
        libhdf5-serial-dev \
        libhdf5-103 \
        python3-pyqt5 \
        python3-h5py \
        libblas-dev \
        liblapack-dev \
        libatlas-base-dev \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        libgstreamer1.0-dev \
        libgstreamer-plugins-base1.0-dev \
        hostapd \
        dnsmasq \
        iptables-persistent \
        supervisor \
        screen \
        htop \
        nano \
        curl \
        wget
}

# Configure GPU memory split
configure_gpu_memory() {
    log "Configuring GPU memory split..."
    
    # Set GPU memory to 128MB for better camera/video performance
    if ! grep -q "gpu_mem=128" /boot/config.txt; then
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
        info "GPU memory set to 128MB"
    else
        info "GPU memory already configured"
    fi
}

# Enable camera
enable_camera() {
    log "Enabling camera interface..."
    
    # Enable camera in config.txt
    sudo raspi-config nonint do_camera 0
    
    # Add camera settings to config.txt if not present
    if ! grep -q "start_x=1" /boot/config.txt; then
        echo "start_x=1" | sudo tee -a /boot/config.txt
    fi
    
    if ! grep -q "disable_camera_led=1" /boot/config.txt; then
        echo "disable_camera_led=1" | sudo tee -a /boot/config.txt
        info "Camera LED disabled to save power"
    fi
    
    info "Camera interface enabled"
}

# Configure UART
configure_uart() {
    log "Configuring UART for flight controller communication..."
    
    # Enable UART
    if ! grep -q "enable_uart=1" /boot/config.txt; then
        echo "enable_uart=1" | sudo tee -a /boot/config.txt
        info "UART enabled in config.txt"
    fi
    
    # Disable Bluetooth to free up UART
    if ! grep -q "dtoverlay=disable-bt" /boot/config.txt; then
        echo "dtoverlay=disable-bt" | sudo tee -a /boot/config.txt
        info "Bluetooth disabled to free UART"
    fi
    
    # Remove console from UART
    sudo sed -i 's/console=serial0,115200 //g' /boot/cmdline.txt
    
    # Stop and disable Bluetooth services
    sudo systemctl disable hciuart
    sudo systemctl disable bluetooth
    
    info "UART configured for flight controller"
}

# Setup WiFi hotspot
setup_wifi_hotspot() {
    log "Setting up WiFi hotspot..."
    
    # Configure hostapd
    sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=wlan0
driver=nl80211
ssid=DroneGroundStation
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=DroneControl123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF
    
    # Configure dnsmasq
    sudo tee /etc/dnsmasq.conf > /dev/null <<EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF
    
    # Configure static IP for wlan0
    sudo tee -a /etc/dhcpcd.conf > /dev/null <<EOF

# Static IP for hotspot
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF
    
    # Enable IP forwarding
    echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
    
    # Configure iptables for NAT (if internet sharing needed)
    sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
    sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
    
    # Save iptables rules
    sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
    
    # Enable services
    sudo systemctl enable hostapd
    sudo systemctl enable dnsmasq
    
    info "WiFi hotspot configured"
    info "SSID: DroneGroundStation"
    info "Password: DroneControl123"
    info "IP: 192.168.4.1"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv ~/drone_env
    source ~/drone_env/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install packages from requirements file
    if [ -f "raspberry_pi_requirements.txt" ]; then
        pip install -r raspberry_pi_requirements.txt
    else
        # Install essential packages manually
        pip install \
            pyserial \
            asyncio \
            websockets \
            flask \
            numpy \
            opencv-python \
            Pillow \
            psutil \
            schedule \
            supervisor
    fi
    
    info "Python dependencies installed in virtual environment"
}

# Setup project structure
setup_project() {
    log "Setting up project structure..."
    
    # Create project directory
    mkdir -p ~/drone_ground_station
    cd ~/drone_ground_station
    
    # Create directory structure
    mkdir -p {
        src/{camera,telemetry,communication,utils},
        config,
        logs,
        scripts,
        data/{video,telemetry,logs}
    }
    
    # Copy project files if they exist
    if [ -d "/home/pi/drone_project" ]; then
        cp -r /home/pi/drone_project/* ~/drone_ground_station/
    fi
    
    info "Project structure created at ~/drone_ground_station"
}

# Create system services
create_services() {
    log "Creating system services..."
    
    # Create drone ground station service
    sudo tee /etc/systemd/system/drone-ground-station.service > /dev/null <<EOF
[Unit]
Description=Drone Ground Station Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/drone_ground_station
Environment=PATH=/home/pi/drone_env/bin
ExecStart=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Create video streaming service
    sudo tee /etc/systemd/system/drone-video-stream.service > /dev/null <<EOF
[Unit]
Description=Drone Video Streaming Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/drone_ground_station
Environment=PATH=/home/pi/drone_env/bin
ExecStart=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/camera/video_streamer.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Create telemetry service
    sudo tee /etc/systemd/system/drone-telemetry.service > /dev/null <<EOF
[Unit]
Description=Drone Telemetry Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/drone_ground_station
Environment=PATH=/home/pi/drone_env/bin
ExecStart=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/telemetry/telemetry_bridge.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    info "System services created"
}

# Configure supervisor for process management
setup_supervisor() {
    log "Setting up Supervisor for process management..."
    
    sudo tee /etc/supervisor/conf.d/drone-ground-station.conf > /dev/null <<EOF
[group:drone-ground-station]
programs=video-stream,telemetry-bridge,main-controller

[program:video-stream]
command=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/camera/video_streamer.py
directory=/home/pi/drone_ground_station
user=pi
autostart=true
autorestart=true
stderr_logfile=/home/pi/drone_ground_station/logs/video_stream_error.log
stdout_logfile=/home/pi/drone_ground_station/logs/video_stream.log

[program:telemetry-bridge]
command=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/telemetry/telemetry_bridge.py
directory=/home/pi/drone_ground_station
user=pi
autostart=true
autorestart=true
stderr_logfile=/home/pi/drone_ground_station/logs/telemetry_error.log
stdout_logfile=/home/pi/drone_ground_station/logs/telemetry.log

[program:main-controller]
command=/home/pi/drone_env/bin/python /home/pi/drone_ground_station/src/main.py
directory=/home/pi/drone_ground_station
user=pi
autostart=true
autorestart=true
stderr_logfile=/home/pi/drone_ground_station/logs/main_error.log
stdout_logfile=/home/pi/drone_ground_station/logs/main.log
EOF
    
    # Enable supervisor
    sudo systemctl enable supervisor
    
    info "Supervisor configured"
}

# Create startup script
create_startup_script() {
    log "Creating startup script..."
    
    tee ~/drone_ground_station/scripts/start_drone_system.sh > /dev/null <<EOF
#!/bin/bash
# Drone Ground Station Startup Script

echo "Starting Drone Ground Station System..."

# Activate virtual environment
source ~/drone_env/bin/activate

# Start services using supervisor
sudo supervisorctl start drone-ground-station:*

# Check status
sudo supervisorctl status

echo "Drone Ground Station System started!"
echo "WiFi Hotspot: DroneGroundStation (Password: DroneControl123)"
echo "Ground Station IP: 192.168.4.1"
echo "Video Stream: rtsp://192.168.4.1:8554/stream"
echo "Telemetry Port: 14550"
echo "Web Interface: http://192.168.4.1:5000"
EOF
    
    chmod +x ~/drone_ground_station/scripts/start_drone_system.sh
    
    info "Startup script created at ~/drone_ground_station/scripts/start_drone_system.sh"
}

# Create stop script
create_stop_script() {
    log "Creating stop script..."
    
    tee ~/drone_ground_station/scripts/stop_drone_system.sh > /dev/null <<EOF
#!/bin/bash
# Drone Ground Station Stop Script

echo "Stopping Drone Ground Station System..."

# Stop services
sudo supervisorctl stop drone-ground-station:*

# Check status
sudo supervisorctl status

echo "Drone Ground Station System stopped!"
EOF
    
    chmod +x ~/drone_ground_station/scripts/stop_drone_system.sh
    
    info "Stop script created at ~/drone_ground_station/scripts/stop_drone_system.sh"
}

# Create system status script
create_status_script() {
    log "Creating system status script..."
    
    tee ~/drone_ground_station/scripts/system_status.sh > /dev/null <<EOF
#!/bin/bash
# Drone Ground Station System Status

echo "=== Drone Ground Station System Status ==="
echo

# System info
echo "System Information:"
echo "  Hostname: $(hostname)"
echo "  Uptime: $(uptime -p)"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "  Memory: $(free -h | awk 'NR==2{printf "%.1f/%.1f GB (%.2f%%)\n", $3/1024/1024, $2/1024/1024, $3*100/$2}')"
echo "  Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s)\n", $3, $2, $5}')"
echo "  Temperature: $(vcgencmd measure_temp | cut -d'=' -f2)"
echo

# Network status
echo "Network Status:"
echo "  WiFi Interface: $(ip addr show wlan0 | grep 'inet ' | awk '{print $2}' || echo 'Not configured')"
echo "  Ethernet: $(ip addr show eth0 | grep 'inet ' | awk '{print $2}' || echo 'Not connected')"
echo "  Hotspot Status: $(sudo systemctl is-active hostapd)"
echo "  Connected Clients: $(cat /var/lib/dhcp/dhcpd.leases 2>/dev/null | grep -c 'binding state active' || echo '0')"
echo

# Service status
echo "Service Status:"
echo "  Supervisor: $(sudo systemctl is-active supervisor)"
echo "  Hostapd: $(sudo systemctl is-active hostapd)"
echo "  Dnsmasq: $(sudo systemctl is-active dnsmasq)"
echo

# Process status
echo "Drone Processes:"
sudo supervisorctl status 2>/dev/null || echo "Supervisor not running"
echo

# Hardware status
echo "Hardware Status:"
echo "  Camera: $(vcgencmd get_camera | cut -d'=' -f2)"
echo "  UART: $(ls /dev/serial* 2>/dev/null || echo 'Not available')"
echo "  GPIO: $(gpio readall 2>/dev/null | head -5 | tail -1 || echo 'GPIO tools not installed')"
echo

# Log files
echo "Recent Log Entries:"
echo "  System: $(sudo journalctl --since '5 minutes ago' --no-pager -q | wc -l) entries"
echo "  Drone Logs: $(find ~/drone_ground_station/logs -name '*.log' -mmin -5 2>/dev/null | wc -l) files updated"
EOF
    
    chmod +x ~/drone_ground_station/scripts/system_status.sh
    
    info "Status script created at ~/drone_ground_station/scripts/system_status.sh"
}

# Configure auto-start on boot
configure_autostart() {
    log "Configuring auto-start on boot..."
    
    # Add to rc.local for auto-start
    if ! grep -q "drone_ground_station" /etc/rc.local; then
        sudo sed -i '/^exit 0/i\# Start Drone Ground Station\nsudo -u pi /home/pi/drone_ground_station/scripts/start_drone_system.sh &' /etc/rc.local
        info "Auto-start configured in rc.local"
    fi
    
    # Alternative: Create systemd service for auto-start
    sudo tee /etc/systemd/system/drone-autostart.service > /dev/null <<EOF
[Unit]
Description=Drone Ground Station Auto-start
After=network.target
Wants=network.target

[Service]
Type=oneshot
User=pi
ExecStart=/home/pi/drone_ground_station/scripts/start_drone_system.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl enable drone-autostart.service
    
    info "Auto-start service enabled"
}

# Create configuration file
create_config() {
    log "Creating configuration file..."
    
    tee ~/drone_ground_station/config/drone_config.json > /dev/null <<EOF
{
    "system": {
        "name": "Drone Ground Station",
        "version": "1.0.0",
        "debug": false
    },
    "network": {
        "hotspot_ssid": "DroneGroundStation",
        "hotspot_password": "DroneControl123",
        "ground_station_ip": "192.168.4.1",
        "client_ip_range": "192.168.4.2-192.168.4.20"
    },
    "video": {
        "resolution": "1280x720",
        "framerate": 30,
        "bitrate": 2000000,
        "format": "h264",
        "port": 5600,
        "rtsp_port": 8554
    },
    "telemetry": {
        "protocol": "MSP",
        "uart_device": "/dev/serial0",
        "baud_rate": 115200,
        "update_rate": 10,
        "port": 14550
    },
    "camera": {
        "type": "picamera",
        "device": 0,
        "auto_exposure": true,
        "iso": 400,
        "shutter_speed": 0
    },
    "logging": {
        "level": "INFO",
        "file_rotation": true,
        "max_file_size": "10MB",
        "backup_count": 5
    },
    "safety": {
        "max_altitude": 120,
        "max_distance": 500,
        "low_battery_threshold": 20,
        "emergency_land_enabled": true
    }
}
EOF
    
    info "Configuration file created at ~/drone_ground_station/config/drone_config.json"
}

# Performance optimization
optimize_performance() {
    log "Applying performance optimizations..."
    
    # Increase swap file size
    sudo dphys-swapfile swapoff
    sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon
    
    # Optimize GPU memory split
    if ! grep -q "gpu_mem=128" /boot/config.txt; then
        echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    fi
    
    # Disable unnecessary services
    sudo systemctl disable bluetooth
    sudo systemctl disable hciuart
    sudo systemctl disable triggerhappy
    
    # Set CPU governor to performance
    echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
    
    info "Performance optimizations applied"
}

# Create test scripts
create_test_scripts() {
    log "Creating test scripts..."
    
    # Camera test
    tee ~/drone_ground_station/scripts/test_camera.sh > /dev/null <<EOF
#!/bin/bash
echo "Testing camera..."
raspistill -o ~/test_image.jpg -t 1000
if [ -f ~/test_image.jpg ]; then
    echo "Camera test PASSED - Image saved as ~/test_image.jpg"
    ls -lh ~/test_image.jpg
else
    echo "Camera test FAILED"
fi
EOF
    
    # UART test
    tee ~/drone_ground_station/scripts/test_uart.sh > /dev/null <<EOF
#!/bin/bash
echo "Testing UART..."
if [ -e /dev/serial0 ]; then
    echo "UART device found: /dev/serial0"
    sudo chmod 666 /dev/serial0
    echo "UART test PASSED"
else
    echo "UART test FAILED - /dev/serial0 not found"
fi
EOF
    
    # Network test
    tee ~/drone_ground_station/scripts/test_network.sh > /dev/null <<EOF
#!/bin/bash
echo "Testing network configuration..."
echo "WiFi interface:"
ip addr show wlan0
echo "Hotspot status:"
sudo systemctl status hostapd --no-pager -l
echo "DHCP status:"
sudo systemctl status dnsmasq --no-pager -l
EOF
    
    chmod +x ~/drone_ground_station/scripts/test_*.sh
    
    info "Test scripts created"
}

# Main installation function
main() {
    echo -e "${BLUE}"
    echo "================================================"
    echo "  Raspberry Pi 3 Drone Ground Station Setup"
    echo "================================================"
    echo -e "${NC}"
    
    check_root
    check_pi_model
    
    log "Starting installation process..."
    
    update_system
    configure_gpu_memory
    enable_camera
    configure_uart
    setup_wifi_hotspot
    install_python_deps
    setup_project
    create_services
    setup_supervisor
    create_startup_script
    create_stop_script
    create_status_script
    configure_autostart
    create_config
    optimize_performance
    create_test_scripts
    
    echo -e "${GREEN}"
    echo "================================================"
    echo "  Installation Complete!"
    echo "================================================"
    echo -e "${NC}"
    
    info "Next steps:"
    echo "1. Reboot the Raspberry Pi: sudo reboot"
    echo "2. Connect flight controller to UART pins"
    echo "3. Test camera: ~/drone_ground_station/scripts/test_camera.sh"
    echo "4. Test UART: ~/drone_ground_station/scripts/test_uart.sh"
    echo "5. Test network: ~/drone_ground_station/scripts/test_network.sh"
    echo "6. Check system status: ~/drone_ground_station/scripts/system_status.sh"
    echo "7. Start system: ~/drone_ground_station/scripts/start_drone_system.sh"
    echo ""
    echo "WiFi Hotspot Details:"
    echo "  SSID: DroneGroundStation"
    echo "  Password: DroneControl123"
    echo "  IP Address: 192.168.4.1"
    echo ""
    warn "A reboot is required to apply all changes!"
}

# Run main function
main "$@"
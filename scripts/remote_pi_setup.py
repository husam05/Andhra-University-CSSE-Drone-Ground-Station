#!/usr/bin/env python3
"""
Remote Raspberry Pi Setup Script
This script helps transfer files to the Pi and run setup commands remotely via SSH.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_status(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def print_warning(message):
    print(f"[WARNING] {message}")

def run_command(command, capture_output=True, timeout=30):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=capture_output, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_ssh_connection(pi_ip="192.168.4.1", username="pi"):
    """Test SSH connection to the Pi"""
    print_status(f"Testing SSH connection to {username}@{pi_ip}...")
    
    # Simple SSH test command
    cmd = f'ssh -o ConnectTimeout=10 -o BatchMode=yes {username}@{pi_ip} "echo SSH_OK"'
    success, stdout, stderr = run_command(cmd, timeout=15)
    
    if success and "SSH_OK" in stdout:
        print_success("SSH connection successful")
        return True
    else:
        print_error(f"SSH connection failed: {stderr}")
        print_warning("Make sure you can manually SSH to the Pi first")
        return False

def transfer_file_to_pi(local_file, remote_path, pi_ip="192.168.4.1", username="pi"):
    """Transfer a file to the Pi using SCP"""
    print_status(f"Transferring {local_file} to Pi...")
    
    cmd = f'scp "{local_file}" {username}@{pi_ip}:{remote_path}'
    success, stdout, stderr = run_command(cmd, timeout=60)
    
    if success:
        print_success(f"File transferred successfully to {remote_path}")
        return True
    else:
        print_error(f"File transfer failed: {stderr}")
        return False

def run_ssh_command(command, pi_ip="192.168.4.1", username="pi", timeout=60):
    """Run a command on the Pi via SSH"""
    print_status(f"Running command on Pi: {command[:50]}...")
    
    # Escape quotes in the command
    escaped_command = command.replace('"', '\\"')
    cmd = f'ssh {username}@{pi_ip} "{escaped_command}"'
    
    success, stdout, stderr = run_command(cmd, capture_output=False, timeout=timeout)
    
    if success:
        print_success("Command completed successfully")
    else:
        print_error(f"Command failed: {stderr}")
    
    return success

def create_basic_scripts_on_pi(pi_ip="192.168.4.1", username="pi"):
    """Create basic scripts directly on the Pi"""
    print_status("Creating basic scripts on Pi...")
    
    # Create project directory
    run_ssh_command("mkdir -p ~/drone_ground_station/scripts", pi_ip, username)
    
    # Create a simple video streamer script
    video_script = '''
cat > ~/drone_ground_station/scripts/video_streamer.py << 'EOF'
#!/usr/bin/env python3
import subprocess
import time
import sys

def start_video_stream(port=5000):
    """Start video streaming using libcamera and GStreamer"""
    print(f"Starting video stream on port {port}...")
    
    # Check if camera is available
    try:
        result = subprocess.run(["libcamera-hello", "--timeout", "1000"], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            print("ERROR: Camera not detected or libcamera not working")
            return False
    except Exception as e:
        print(f"ERROR: Camera test failed: {e}")
        return False
    
    # Start streaming
    cmd = [
        "libcamera-vid",
        "-t", "0",  # Run indefinitely
        "--width", "640",
        "--height", "480",
        "--framerate", "30",
        "--inline",
        "-o", "-"
    ]
    
    gst_cmd = [
        "gst-launch-1.0",
        "fdsrc", "fd=0",
        "!", "h264parse",
        "!", "rtph264pay", "config-interval=1", "pt=96",
        "!", "udpsink", "host=192.168.4.2", f"port={port}"
    ]
    
    try:
        # Start libcamera process
        camera_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        
        # Start GStreamer process
        gst_proc = subprocess.Popen(gst_cmd, stdin=camera_proc.stdout)
        
        camera_proc.stdout.close()
        
        print(f"Video streaming started on UDP port {port}")
        print("Press Ctrl+C to stop")
        
        # Wait for processes
        try:
            gst_proc.wait()
        except KeyboardInterrupt:
            print("\nStopping video stream...")
            gst_proc.terminate()
            camera_proc.terminate()
            
    except Exception as e:
        print(f"ERROR: Failed to start video stream: {e}")
        return False
    
    return True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    start_video_stream(port)
EOF
'''
    
    run_ssh_command(video_script, pi_ip, username, timeout=30)
    run_ssh_command("chmod +x ~/drone_ground_station/scripts/video_streamer.py", pi_ip, username)
    
    # Create a simple telemetry bridge script
    telemetry_script = '''
cat > ~/drone_ground_station/scripts/telemetry_bridge.py << 'EOF'
#!/usr/bin/env python3
import serial
import socket
import json
import time
import threading
from datetime import datetime

class TelemetryBridge:
    def __init__(self, serial_port="/dev/serial0", baud_rate=57600, 
                 udp_host="192.168.4.2", udp_port=14550):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.running = False
        
    def start(self):
        """Start the telemetry bridge"""
        print(f"Starting telemetry bridge...")
        print(f"Serial: {self.serial_port} @ {self.baud_rate}")
        print(f"UDP: {self.udp_host}:{self.udp_port}")
        
        try:
            # Open serial connection
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            print(f"Serial port opened: {self.serial_port}")
            
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"UDP socket created")
            
            self.running = True
            
            # Start threads
            serial_thread = threading.Thread(target=self._serial_to_udp)
            serial_thread.daemon = True
            serial_thread.start()
            
            print("Telemetry bridge started. Press Ctrl+C to stop.")
            
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping telemetry bridge...")
                self.stop()
                
        except Exception as e:
            print(f"ERROR: Failed to start telemetry bridge: {e}")
            
    def _serial_to_udp(self):
        """Read from serial and forward to UDP"""
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    if data:
                        # Forward raw data to ground station
                        self.sock.sendto(data, (self.udp_host, self.udp_port))
                        
                        # Also send a status message
                        status = {
                            "timestamp": datetime.now().isoformat(),
                            "bytes_received": len(data),
                            "source": "flight_controller"
                        }
                        status_msg = json.dumps(status).encode()
                        self.sock.sendto(status_msg, (self.udp_host, self.udp_port + 1))
                        
                time.sleep(0.01)  # Small delay to prevent CPU overload
                
            except Exception as e:
                print(f"Serial read error: {e}")
                time.sleep(1)
                
    def stop(self):
        """Stop the telemetry bridge"""
        self.running = False
        if hasattr(self, 'ser'):
            self.ser.close()
        if hasattr(self, 'sock'):
            self.sock.close()
        print("Telemetry bridge stopped")

if __name__ == "__main__":
    bridge = TelemetryBridge()
    bridge.start()
EOF
'''
    
    run_ssh_command(telemetry_script, pi_ip, username, timeout=30)
    run_ssh_command("chmod +x ~/drone_ground_station/scripts/telemetry_bridge.py", pi_ip, username)
    
    print_success("Basic scripts created on Pi")

def main():
    print("=== Remote Raspberry Pi Setup ===")
    print("This script will help you set up the drone ground station on your Pi remotely.")
    print()
    
    # Configuration
    pi_ip = "192.168.4.1"
    username = "pi"
    
    print(f"Target Pi: {username}@{pi_ip}")
    print()
    
    # Step 1: Test SSH connection
    print("Step 1: Testing SSH connection...")
    if not test_ssh_connection(pi_ip, username):
        print_error("Cannot connect to Pi via SSH")
        print("Please ensure:")
        print("1. Pi is powered on and connected to network")
        print("2. SSH is enabled on the Pi")
        print("3. You can manually SSH to the Pi")
        print("4. SSH keys are set up or you can enter password")
        return False
    
    print()
    
    # Step 2: Transfer network fix script
    print("Step 2: Transferring network diagnostics script...")
    script_dir = Path(__file__).parent
    network_fix_script = script_dir / "pi_network_fix.sh"
    
    if network_fix_script.exists():
        if transfer_file_to_pi(str(network_fix_script), "~/pi_network_fix.sh", pi_ip, username):
            # Make it executable and run it
            run_ssh_command("chmod +x ~/pi_network_fix.sh", pi_ip, username)
            print_status("Running network diagnostics and fixes...")
            run_ssh_command("~/pi_network_fix.sh", pi_ip, username, timeout=120)
        else:
            print_warning("Could not transfer network fix script")
    else:
        print_warning(f"Network fix script not found at {network_fix_script}")
    
    print()
    
    # Step 3: Create basic project structure
    print("Step 3: Creating project structure...")
    create_basic_scripts_on_pi(pi_ip, username)
    
    print()
    
    # Step 4: Test basic functionality
    print("Step 4: Testing basic functionality...")
    
    # Test camera
    print_status("Testing camera...")
    run_ssh_command("libcamera-hello --timeout 2000", pi_ip, username, timeout=10)
    
    # Test UART
    print_status("Testing UART...")
    run_ssh_command("ls -la /dev/serial* /dev/ttyS* /dev/ttyAMA*", pi_ip, username)
    
    # Check system status
    print_status("Checking system status...")
    run_ssh_command("df -h && free -h && vcgencmd measure_temp", pi_ip, username)
    
    print()
    
    # Step 5: Instructions for next steps
    print("=== Next Steps ===")
    print("1. Hardware Connections:")
    print("   - Connect camera module to CSI port")
    print("   - Connect flight controller UART to GPIO pins 14/15")
    print("   - Ensure proper power supply")
    print()
    print("2. Test Video Streaming:")
    print(f"   SSH to Pi: ssh {username}@{pi_ip}")
    print("   Run: python3 ~/drone_ground_station/scripts/video_streamer.py")
    print()
    print("3. Test Telemetry:")
    print("   Run: python3 ~/drone_ground_station/scripts/telemetry_bridge.py")
    print()
    print("4. On your laptop, run the ground station software to receive:")
    print("   - Video stream on UDP port 5000")
    print("   - Telemetry on UDP port 14550")
    print()
    print("5. For detailed instructions, see REMOTE_SETUP_GUIDE.md")
    
    print_success("Remote setup completed!")
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)
#!/usr/bin/env python3
"""
Drone Ground Station Deployment Script

This script automates the deployment of the drone ground station system,
including ground station setup and Raspberry Pi configuration.

Usage:
    python deploy.py [--target ground_station|raspberry_pi|both] [--drone-ip 192.168.4.1]
"""

import os
import sys
import time
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from typing import List, Dict, Optional

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class DeploymentManager:
    """Main deployment management class"""
    
    def __init__(self, drone_ip: str = "192.168.4.1", verbose: bool = False):
        self.drone_ip = drone_ip
        self.verbose = verbose
        self.project_root = Path(__file__).parent
        self.is_windows = sys.platform == 'win32'
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Log message with color"""
        print(f"{color}{message}{Colors.END}")
        
    def log_verbose(self, message: str):
        """Log verbose message"""
        if self.verbose:
            self.log(f"  → {message}", Colors.CYAN)
            
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, shell: bool = None) -> bool:
        """Run system command"""
        if shell is None:
            shell = self.is_windows
            
        try:
            self.log_verbose(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                shell=shell,
                check=True,
                capture_output=not self.verbose
            )
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", Colors.RED)
            return False
        except Exception as e:
            self.log(f"Error running command: {e}", Colors.RED)
            return False
            
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        self.log(f"\n{Colors.BOLD}Checking Prerequisites{Colors.END}")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.log("Python 3.8+ required", Colors.RED)
            return False
        self.log(f"✓ Python {sys.version.split()[0]}", Colors.GREEN)
        
        # Check Git
        if not shutil.which('git'):
            self.log("Git not found in PATH", Colors.RED)
            return False
        self.log("✓ Git available", Colors.GREEN)
        
        # Check pip
        if not shutil.which('pip') and not shutil.which('pip3'):
            self.log("pip not found in PATH", Colors.RED)
            return False
        self.log("✓ pip available", Colors.GREEN)
        
        return True
        
    def setup_ground_station(self) -> bool:
        """Setup ground station environment"""
        self.log(f"\n{Colors.BOLD}Setting up Ground Station{Colors.END}")
        
        # Check ROS2 installation
        if not self.check_ros2():
            self.log("Please install ROS2 Humble first", Colors.RED)
            return False
            
        # Install Python dependencies
        if not self.install_python_dependencies():
            return False
            
        # Build ROS2 package
        if not self.build_ros2_package():
            return False
            
        # Setup configuration
        if not self.setup_configuration():
            return False
            
        self.log("✓ Ground station setup complete", Colors.GREEN)
        return True
        
    def check_ros2(self) -> bool:
        """Check ROS2 installation"""
        if self.is_windows:
            # Check for ROS2 installation on Windows
            ros2_paths = [
                Path("C:/dev/ros2_humble"),
                Path("C:/opt/ros/humble"),
                Path("C:/ros2_humble")
            ]
            
            for path in ros2_paths:
                if path.exists():
                    self.log(f"✓ Found ROS2 at {path}", Colors.GREEN)
                    return True
                    
            self.log("ROS2 Humble not found", Colors.RED)
            return False
        else:
            # Check for ROS2 on Linux
            return shutil.which('ros2') is not None
            
    def install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.log("Installing Python dependencies...")
        
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            self.log("requirements.txt not found", Colors.RED)
            return False
            
        pip_cmd = "pip" if shutil.which("pip") else "pip3"
        return self.run_command([pip_cmd, "install", "-r", str(requirements_file)])
        
    def build_ros2_package(self) -> bool:
        """Build ROS2 package"""
        self.log("Building ROS2 package...")
        
        # Source ROS2 environment first
        if self.is_windows:
            # On Windows, we need to source ROS2 in the same shell
            cmd = [
                "powershell", "-Command",
                "C:/dev/ros2_humble/local_setup.ps1; colcon build --packages-select drone_ground_station"
            ]
        else:
            cmd = ["bash", "-c", "source /opt/ros/humble/setup.bash && colcon build --packages-select drone_ground_station"]
            
        return self.run_command(cmd)
        
    def setup_configuration(self) -> bool:
        """Setup configuration files"""
        self.log("Setting up configuration...")
        
        config_dir = self.project_root / "config"
        if not config_dir.exists():
            config_dir.mkdir()
            
        # Update drone IP in configuration
        params_file = config_dir / "ground_station_params.yaml"
        if params_file.exists():
            content = params_file.read_text()
            content = content.replace("192.168.4.1", self.drone_ip)
            params_file.write_text(content)
            self.log(f"✓ Updated configuration for drone IP: {self.drone_ip}", Colors.GREEN)
            
        return True
        
    def deploy_to_raspberry_pi(self) -> bool:
        """Deploy scripts to Raspberry Pi"""
        self.log(f"\n{Colors.BOLD}Deploying to Raspberry Pi{Colors.END}")
        
        # Check SSH connectivity
        if not self.test_ssh_connection():
            return False
            
        # Copy scripts
        if not self.copy_scripts_to_pi():
            return False
            
        # Install dependencies on Pi
        if not self.install_pi_dependencies():
            return False
            
        # Configure Pi services
        if not self.configure_pi_services():
            return False
            
        self.log("✓ Raspberry Pi deployment complete", Colors.GREEN)
        return True
        
    def test_ssh_connection(self) -> bool:
        """Test SSH connection to Raspberry Pi"""
        self.log(f"Testing SSH connection to {self.drone_ip}...")
        
        cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", 
               f"pi@{self.drone_ip}", "echo 'SSH OK'"]
        
        if self.run_command(cmd):
            self.log("✓ SSH connection successful", Colors.GREEN)
            return True
        else:
            self.log("SSH connection failed. Please ensure:", Colors.RED)
            self.log("  1. Raspberry Pi is powered on", Colors.YELLOW)
            self.log("  2. SSH is enabled on the Pi", Colors.YELLOW)
            self.log("  3. You can connect manually: ssh pi@" + self.drone_ip, Colors.YELLOW)
            return False
            
    def copy_scripts_to_pi(self) -> bool:
        """Copy scripts to Raspberry Pi"""
        self.log("Copying scripts to Raspberry Pi...")
        
        scripts_dir = self.project_root / "raspberry_pi_scripts"
        if not scripts_dir.exists():
            self.log("raspberry_pi_scripts directory not found", Colors.RED)
            return False
            
        # Create remote directory
        cmd = ["ssh", f"pi@{self.drone_ip}", "mkdir -p /home/pi/drone_scripts"]
        if not self.run_command(cmd):
            return False
            
        # Copy all scripts
        for script_file in scripts_dir.glob("*.py"):
            cmd = ["scp", str(script_file), f"pi@{self.drone_ip}:/home/pi/drone_scripts/"]
            if not self.run_command(cmd):
                return False
                
        # Copy config file
        config_file = scripts_dir / "config.json"
        if config_file.exists():
            cmd = ["scp", str(config_file), f"pi@{self.drone_ip}:/home/pi/drone_scripts/"]
            if not self.run_command(cmd):
                return False
                
        # Make scripts executable
        cmd = ["ssh", f"pi@{self.drone_ip}", "chmod +x /home/pi/drone_scripts/*.py"]
        return self.run_command(cmd)
        
    def install_pi_dependencies(self) -> bool:
        """Install dependencies on Raspberry Pi"""
        self.log("Installing dependencies on Raspberry Pi...")
        
        commands = [
            "sudo apt update",
            "sudo apt install -y python3-pip python3-dev python3-setuptools",
            "sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav",
            "sudo apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev",
            "sudo apt install -y hostapd dnsmasq",
            "pip3 install pymavlink pyserial opencv-python numpy"
        ]
        
        for cmd_str in commands:
            cmd = ["ssh", f"pi@{self.drone_ip}", cmd_str]
            if not self.run_command(cmd):
                self.log(f"Failed to run: {cmd_str}", Colors.RED)
                return False
                
        return True
        
    def configure_pi_services(self) -> bool:
        """Configure Raspberry Pi services"""
        self.log("Configuring Raspberry Pi services...")
        
        # Create systemd service file
        service_content = '''[Unit]
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
'''
        
        # Write service file
        cmd = ["ssh", f"pi@{self.drone_ip}", 
               f"echo '{service_content}' | sudo tee /etc/systemd/system/drone.service"]
        if not self.run_command(cmd):
            return False
            
        # Enable and start service
        commands = [
            "sudo systemctl daemon-reload",
            "sudo systemctl enable drone.service",
            "sudo systemctl start drone.service"
        ]
        
        for cmd_str in commands:
            cmd = ["ssh", f"pi@{self.drone_ip}", cmd_str]
            if not self.run_command(cmd):
                return False
                
        return True
        
    def create_desktop_shortcuts(self):
        """Create desktop shortcuts for easy access"""
        self.log(f"\n{Colors.BOLD}Creating Desktop Shortcuts{Colors.END}")
        
        if self.is_windows:
            desktop = Path.home() / "Desktop"
            
            # Create launch script
            launch_script = self.project_root / "launch_ground_station.bat"
            launch_content = f'''@echo off
cd /d "{self.project_root}"
call C:\\dev\\ros2_humble\\local_setup.bat
call install\\setup.bat
ros2 launch drone_ground_station ground_station.launch.py
pause
'''
            launch_script.write_text(launch_content)
            
            # Create test script
            test_script = self.project_root / "test_system.bat"
            test_content = f'''@echo off
cd /d "{self.project_root}"
python test_system.py --drone-ip {self.drone_ip} --verbose
pause
'''
            test_script.write_text(test_content)
            
            self.log("✓ Created launch scripts", Colors.GREEN)
            self.log(f"  - {launch_script}", Colors.CYAN)
            self.log(f"  - {test_script}", Colors.CYAN)
            
    def run_system_test(self) -> bool:
        """Run system test after deployment"""
        self.log(f"\n{Colors.BOLD}Running System Test{Colors.END}")
        
        test_script = self.project_root / "test_system.py"
        if not test_script.exists():
            self.log("Test script not found", Colors.RED)
            return False
            
        cmd = ["python", str(test_script), "--drone-ip", self.drone_ip]
        return self.run_command(cmd)
        
    def deploy_all(self) -> bool:
        """Deploy complete system"""
        self.log(f"{Colors.BOLD}Drone Ground Station Deployment{Colors.END}")
        self.log(f"Target drone IP: {self.drone_ip}")
        self.log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
            
        # Setup ground station
        if not self.setup_ground_station():
            return False
            
        # Create shortcuts
        self.create_desktop_shortcuts()
        
        # Ask about Raspberry Pi deployment
        if self.ask_user_confirmation("Deploy to Raspberry Pi?"):
            if not self.deploy_to_raspberry_pi():
                self.log("Raspberry Pi deployment failed, but ground station is ready", Colors.YELLOW)
                
        # Run system test
        if self.ask_user_confirmation("Run system test?"):
            self.run_system_test()
            
        self.log(f"\n{Colors.GREEN}Deployment completed successfully!{Colors.END}")
        self.log("\nNext steps:")
        self.log("1. Connect to drone WiFi network (DroneNetwork)")
        self.log("2. Run: python test_system.py")
        self.log("3. Launch ground station: ros2 launch drone_ground_station ground_station.launch.py")
        
        return True
        
    def ask_user_confirmation(self, question: str) -> bool:
        """Ask user for confirmation"""
        try:
            response = input(f"{question} (y/N): ").strip().lower()
            return response in ['y', 'yes']
        except KeyboardInterrupt:
            return False

def main():
    parser = argparse.ArgumentParser(description='Deploy drone ground station system')
    parser.add_argument('--target', choices=['ground_station', 'raspberry_pi', 'both'], 
                       default='both', help='Deployment target')
    parser.add_argument('--drone-ip', default='192.168.4.1', help='Drone IP address')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--auto', '-a', action='store_true', help='Automatic mode (no prompts)')
    
    args = parser.parse_args()
    
    deployer = DeploymentManager(args.drone_ip, args.verbose)
    
    # Override user confirmation for auto mode
    if args.auto:
        deployer.ask_user_confirmation = lambda x: True
    
    try:
        if args.target == 'ground_station':
            success = deployer.setup_ground_station()
        elif args.target == 'raspberry_pi':
            success = deployer.deploy_to_raspberry_pi()
        else:  # both
            success = deployer.deploy_all()
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Deployment interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Deployment failed with error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
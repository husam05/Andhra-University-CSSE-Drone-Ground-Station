#!/usr/bin/env python3
"""
Laptop Ground Station Setup Script
Automated installation and configuration for the drone ground station on laptop
"""

import os
import sys
import subprocess
import platform
import json
import urllib.request
import shutil
from pathlib import Path
import argparse

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class LaptopSetup:
    def __init__(self):
        self.system = platform.system().lower()
        self.project_dir = Path.cwd()
        self.venv_dir = self.project_dir / "venv"
        
    def log(self, message):
        print(f"{Colors.GREEN}[{self._get_timestamp()}] {message}{Colors.NC}")
        
    def warn(self, message):
        print(f"{Colors.YELLOW}[WARNING] {message}{Colors.NC}")
        
    def error(self, message):
        print(f"{Colors.RED}[ERROR] {message}{Colors.NC}")
        
    def info(self, message):
        print(f"{Colors.BLUE}[INFO] {message}{Colors.NC}")
        
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    def run_command(self, command, shell=True, check=True):
        """Run a system command"""
        try:
            if isinstance(command, str):
                self.info(f"Running: {command}")
            else:
                self.info(f"Running: {' '.join(command)}")
                
            result = subprocess.run(command, shell=shell, check=check, 
                                  capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            self.error(f"Command failed: {e}")
            self.error(f"Output: {e.stdout}")
            self.error(f"Error: {e.stderr}")
            raise
            
    def check_python_version(self):
        """Check if Python version is compatible"""
        self.log("Checking Python version...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.error(f"Python 3.8+ required, found {version.major}.{version.minor}")
            sys.exit(1)
            
        self.info(f"Python {version.major}.{version.minor}.{version.micro} - OK")
        
    def install_system_dependencies(self):
        """Install system-level dependencies"""
        self.log("Installing system dependencies...")
        
        if self.system == "windows":
            self._install_windows_deps()
        elif self.system == "linux":
            self._install_linux_deps()
        elif self.system == "darwin":
            self._install_macos_deps()
        else:
            self.warn(f"Unsupported system: {self.system}")
            
    def _install_windows_deps(self):
        """Install Windows dependencies"""
        self.info("Installing Windows dependencies...")
        
        # Check if chocolatey is installed
        try:
            self.run_command("choco --version")
            choco_available = True
        except:
            choco_available = False
            
        if choco_available:
            # Install GStreamer via chocolatey
            try:
                self.run_command("choco install gstreamer")
            except:
                self.warn("Failed to install GStreamer via chocolatey")
                
        # Download and install GStreamer manually if needed
        self._install_gstreamer_windows()
        
        # Install Git if not available
        try:
            self.run_command("git --version")
        except:
            self.warn("Git not found. Please install Git for Windows")
            
    def _install_linux_deps(self):
        """Install Linux dependencies"""
        self.info("Installing Linux dependencies...")
        
        # Detect package manager
        if shutil.which("apt"):
            self.run_command([
                "sudo", "apt", "update"
            ])
            self.run_command([
                "sudo", "apt", "install", "-y",
                "python3-pip", "python3-venv", "python3-dev",
                "libgstreamer1.0-dev", "libgstreamer-plugins-base1.0-dev",
                "gstreamer1.0-plugins-base", "gstreamer1.0-plugins-good",
                "gstreamer1.0-plugins-bad", "gstreamer1.0-plugins-ugly",
                "gstreamer1.0-libav", "gstreamer1.0-tools",
                "libgtk-3-dev", "libcairo2-dev", "libgirepository1.0-dev",
                "pkg-config", "git"
            ])
        elif shutil.which("yum"):
            self.run_command([
                "sudo", "yum", "install", "-y",
                "python3-pip", "python3-devel",
                "gstreamer1-devel", "gstreamer1-plugins-base-devel",
                "gstreamer1-plugins-good", "gstreamer1-plugins-bad-free",
                "gstreamer1-plugins-ugly-free", "gstreamer1-libav",
                "gtk3-devel", "cairo-devel", "gobject-introspection-devel",
                "pkgconfig", "git"
            ])
        else:
            self.warn("Unknown package manager. Please install dependencies manually.")
            
    def _install_macos_deps(self):
        """Install macOS dependencies"""
        self.info("Installing macOS dependencies...")
        
        # Check if Homebrew is installed
        try:
            self.run_command("brew --version")
            self.run_command([
                "brew", "install",
                "gstreamer", "gst-plugins-base", "gst-plugins-good",
                "gst-plugins-bad", "gst-plugins-ugly", "gst-libav",
                "gtk+3", "cairo", "gobject-introspection",
                "pkg-config", "git"
            ])
        except:
            self.warn("Homebrew not found. Please install Homebrew first.")
            
    def _install_gstreamer_windows(self):
        """Install GStreamer on Windows manually"""
        self.info("Installing GStreamer for Windows...")
        
        gstreamer_url = "https://gstreamer.freedesktop.org/data/pkg/windows/1.20.3/msvc/gstreamer-1.0-msvc-x86_64-1.20.3.msi"
        gstreamer_dev_url = "https://gstreamer.freedesktop.org/data/pkg/windows/1.20.3/msvc/gstreamer-1.0-devel-msvc-x86_64-1.20.3.msi"
        
        downloads_dir = Path.home() / "Downloads"
        gstreamer_file = downloads_dir / "gstreamer-runtime.msi"
        gstreamer_dev_file = downloads_dir / "gstreamer-devel.msi"
        
        try:
            # Download runtime
            self.info("Downloading GStreamer runtime...")
            urllib.request.urlretrieve(gstreamer_url, gstreamer_file)
            
            # Download development files
            self.info("Downloading GStreamer development files...")
            urllib.request.urlretrieve(gstreamer_dev_url, gstreamer_dev_file)
            
            self.info("Please install the downloaded GStreamer MSI files manually:")
            self.info(f"1. {gstreamer_file}")
            self.info(f"2. {gstreamer_dev_file}")
            
        except Exception as e:
            self.warn(f"Failed to download GStreamer: {e}")
            self.info("Please download and install GStreamer manually from:")
            self.info("https://gstreamer.freedesktop.org/download/")
            
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        self.log("Creating virtual environment...")
        
        if self.venv_dir.exists():
            self.warn("Virtual environment already exists. Removing...")
            shutil.rmtree(self.venv_dir)
            
        self.run_command([sys.executable, "-m", "venv", str(self.venv_dir)])
        self.info(f"Virtual environment created at {self.venv_dir}")
        
    def get_venv_python(self):
        """Get path to virtual environment Python"""
        if self.system == "windows":
            return self.venv_dir / "Scripts" / "python.exe"
        else:
            return self.venv_dir / "bin" / "python"
            
    def get_venv_pip(self):
        """Get path to virtual environment pip"""
        if self.system == "windows":
            return self.venv_dir / "Scripts" / "pip.exe"
        else:
            return self.venv_dir / "bin" / "pip"
            
    def install_python_dependencies(self):
        """Install Python dependencies"""
        self.log("Installing Python dependencies...")
        
        pip_path = self.get_venv_pip()
        
        # Upgrade pip
        self.run_command([str(pip_path), "install", "--upgrade", "pip"])
        
        # Install requirements
        requirements_file = self.project_dir / "requirements.txt"
        if requirements_file.exists():
            self.run_command([str(pip_path), "install", "-r", str(requirements_file)])
        else:
            # Install essential packages
            packages = [
                "PyQt5",
                "opencv-python",
                "numpy",
                "Pillow",
                "pyserial",
                "websockets",
                "asyncio",
                "matplotlib",
                "scipy",
                "pandas",
                "requests",
                "psutil",
                "schedule",
                "flask",
                "flask-socketio",
                "eventlet"
            ]
            
            for package in packages:
                try:
                    self.run_command([str(pip_path), "install", package])
                except:
                    self.warn(f"Failed to install {package}")
                    
        # Install ROS2 dependencies if on Linux
        if self.system == "linux":
            self._install_ros2_dependencies()
            
    def _install_ros2_dependencies(self):
        """Install ROS2 dependencies on Linux"""
        self.log("Installing ROS2 dependencies...")
        
        try:
            # Add ROS2 repository
            self.run_command([
                "sudo", "apt", "update", "&&",
                "sudo", "apt", "install", "-y", "curl", "gnupg2", "lsb-release"
            ])
            
            self.run_command([
                "curl", "-sSL", "https://raw.githubusercontent.com/ros/rosdistro/master/ros.key",
                "-o", "/usr/share/keyrings/ros-archive-keyring.gpg"
            ])
            
            # Install ROS2 Humble
            self.run_command(["sudo", "apt", "update"])
            self.run_command(["sudo", "apt", "install", "-y", "ros-humble-desktop"])
            
            self.info("ROS2 Humble installed successfully")
            
        except Exception as e:
            self.warn(f"Failed to install ROS2: {e}")
            self.info("You may need to install ROS2 manually")
            
    def setup_project_structure(self):
        """Setup project directory structure"""
        self.log("Setting up project structure...")
        
        directories = [
            "src/ground_station",
            "src/gui",
            "src/communication",
            "src/video",
            "src/telemetry",
            "src/utils",
            "config",
            "logs",
            "data/video",
            "data/telemetry",
            "data/logs",
            "scripts",
            "tests",
            "docs",
            "examples"
        ]
        
        for directory in directories:
            dir_path = self.project_dir / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
        self.info("Project structure created")
        
    def create_configuration_files(self):
        """Create configuration files"""
        self.log("Creating configuration files...")
        
        # Main configuration
        config = {
            "system": {
                "name": "Drone Ground Station",
                "version": "1.0.0",
                "debug": True
            },
            "network": {
                "drone_ip": "192.168.4.1",
                "ground_station_ip": "192.168.4.2",
                "video_port": 5600,
                "telemetry_port": 14550,
                "command_port": 14551,
                "web_port": 5000
            },
            "video": {
                "resolution": "1280x720",
                "framerate": 30,
                "bitrate": 2000000,
                "format": "h264",
                "recording_enabled": True,
                "recording_path": "data/video"
            },
            "telemetry": {
                "protocol": "MSP",
                "update_rate": 10,
                "logging_enabled": True,
                "logging_path": "data/telemetry"
            },
            "gui": {
                "theme": "dark",
                "window_size": [1200, 800],
                "fullscreen": False,
                "show_debug_info": True
            },
            "safety": {
                "max_altitude": 120,
                "max_distance": 500,
                "low_battery_threshold": 20,
                "emergency_procedures": {
                    "auto_land": True,
                    "return_to_home": True
                }
            }
        }
        
        config_file = self.project_dir / "config" / "ground_station_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
            
        self.info(f"Configuration file created: {config_file}")
        
    def create_launch_scripts(self):
        """Create launch scripts"""
        self.log("Creating launch scripts...")
        
        # Windows batch script
        if self.system == "windows":
            batch_script = self.project_dir / "scripts" / "launch_ground_station.bat"
            with open(batch_script, 'w') as f:
                f.write(f"""@echo off
echo Starting Drone Ground Station...
cd /d "{self.project_dir}"
call venv\\Scripts\\activate.bat
python src\\ground_station\\main.py
pause
""")
                
        # Unix shell script
        shell_script = self.project_dir / "scripts" / "launch_ground_station.sh"
        with open(shell_script, 'w') as f:
            f.write(f"""#!/bin/bash
echo "Starting Drone Ground Station..."
cd "{self.project_dir}"
source venv/bin/activate
python src/ground_station/main.py
""")
            
        # Make shell script executable
        if self.system != "windows":
            os.chmod(shell_script, 0o755)
            
        self.info("Launch scripts created")
        
    def create_test_scripts(self):
        """Create test scripts"""
        self.log("Creating test scripts...")
        
        # Network connectivity test
        test_network = self.project_dir / "scripts" / "test_network.py"
        with open(test_network, 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"Test network connectivity to drone\"\"\"\n
import socket
import subprocess
import sys

def test_ping(host="192.168.4.1"):
    \"\"\"Test ping connectivity\"\"\"
    try:
        result = subprocess.run(["ping", "-c", "4", host], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def test_port(host="192.168.4.1", port=5600, timeout=5):
    \"\"\"Test port connectivity\"\"\"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

if __name__ == "__main__":
    print("Testing network connectivity...")
    
    # Test ping
    if test_ping():
        print("✓ Ping test passed")
    else:
        print("✗ Ping test failed")
        
    # Test video port
    if test_port(port=5600):
        print("✓ Video port (5600) accessible")
    else:
        print("✗ Video port (5600) not accessible")
        
    # Test telemetry port
    if test_port(port=14550):
        print("✓ Telemetry port (14550) accessible")
    else:
        print("✗ Telemetry port (14550) not accessible")
""")
            
        # GStreamer test
        test_gstreamer = self.project_dir / "scripts" / "test_gstreamer.py"
        with open(test_gstreamer, 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"Test GStreamer installation\"\"\"\n
import subprocess
import sys

def test_gstreamer():
    \"\"\"Test if GStreamer is properly installed\"\"\"
    try:
        result = subprocess.run(["gst-launch-1.0", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ GStreamer is installed")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print("✗ GStreamer not found")
            return False
    except FileNotFoundError:
        print("✗ GStreamer not found in PATH")
        return False

def test_gstreamer_plugins():
    \"\"\"Test GStreamer plugins\"\"\"
    plugins = ["videotestsrc", "autovideosink", "udpsrc", "rtph264depay", "h264parse", "avdec_h264"]
    
    for plugin in plugins:
        try:
            result = subprocess.run(["gst-inspect-1.0", plugin], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Plugin {plugin} available")
            else:
                print(f"✗ Plugin {plugin} not available")
        except:
            print(f"✗ Failed to check plugin {plugin}")

if __name__ == "__main__":
    print("Testing GStreamer installation...")
    test_gstreamer()
    print("\nTesting GStreamer plugins...")
    test_gstreamer_plugins()
""")
            
        # Make test scripts executable
        if self.system != "windows":
            os.chmod(test_network, 0o755)
            os.chmod(test_gstreamer, 0o755)
            
        self.info("Test scripts created")
        
    def create_requirements_file(self):
        """Create requirements.txt file"""
        self.log("Creating requirements.txt...")
        
        requirements = [
            "PyQt5>=5.15.0",
            "opencv-python>=4.5.0",
            "numpy>=1.21.0",
            "Pillow>=8.0.0",
            "pyserial>=3.5",
            "websockets>=10.0",
            "matplotlib>=3.5.0",
            "scipy>=1.7.0",
            "pandas>=1.3.0",
            "requests>=2.25.0",
            "psutil>=5.8.0",
            "schedule>=1.1.0",
            "flask>=2.0.0",
            "flask-socketio>=5.0.0",
            "eventlet>=0.31.0",
            "asyncio-mqtt>=0.11.0",
            "pynput>=1.7.0",
            "keyboard>=1.13.0",
            "configparser>=5.0.0",
            "logging>=0.4.9.6",
            "threading>=1.0.0"
        ]
        
        requirements_file = self.project_dir / "requirements.txt"
        with open(requirements_file, 'w') as f:
            for req in requirements:
                f.write(f"{req}\n")
                
        self.info(f"Requirements file created: {requirements_file}")
        
    def setup_firewall_rules(self):
        """Setup firewall rules for communication"""
        self.log("Setting up firewall rules...")
        
        if self.system == "windows":
            self._setup_windows_firewall()
        elif self.system == "linux":
            self._setup_linux_firewall()
        else:
            self.warn("Firewall setup not implemented for this system")
            
    def _setup_windows_firewall(self):
        """Setup Windows firewall rules"""
        try:
            # Allow video port
            self.run_command([
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=Drone Video Stream", "dir=in", "action=allow",
                "protocol=UDP", "localport=5600"
            ])
            
            # Allow telemetry port
            self.run_command([
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=Drone Telemetry", "dir=in", "action=allow",
                "protocol=UDP", "localport=14550"
            ])
            
            # Allow command port
            self.run_command([
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=Drone Commands", "dir=in", "action=allow",
                "protocol=TCP", "localport=14551"
            ])
            
            self.info("Windows firewall rules added")
            
        except Exception as e:
            self.warn(f"Failed to setup Windows firewall: {e}")
            
    def _setup_linux_firewall(self):
        """Setup Linux firewall rules"""
        try:
            # Check if ufw is available
            if shutil.which("ufw"):
                self.run_command(["sudo", "ufw", "allow", "5600/udp"])
                self.run_command(["sudo", "ufw", "allow", "14550/udp"])
                self.run_command(["sudo", "ufw", "allow", "14551/tcp"])
                self.info("UFW firewall rules added")
            else:
                self.warn("UFW not found. Please configure firewall manually.")
                
        except Exception as e:
            self.warn(f"Failed to setup Linux firewall: {e}")
            
    def create_desktop_shortcut(self):
        """Create desktop shortcut"""
        self.log("Creating desktop shortcut...")
        
        if self.system == "windows":
            self._create_windows_shortcut()
        elif self.system == "linux":
            self._create_linux_shortcut()
        else:
            self.warn("Desktop shortcut not implemented for this system")
            
    def _create_windows_shortcut(self):
        """Create Windows desktop shortcut"""
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "Drone Ground Station.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = str(self.project_dir / "scripts" / "launch_ground_station.bat")
            shortcut.WorkingDirectory = str(self.project_dir)
            shortcut.IconLocation = str(self.project_dir / "assets" / "icon.ico")
            shortcut.save()
            
            self.info("Windows desktop shortcut created")
            
        except ImportError:
            self.warn("winshell not available. Install with: pip install winshell pywin32")
        except Exception as e:
            self.warn(f"Failed to create Windows shortcut: {e}")
            
    def _create_linux_shortcut(self):
        """Create Linux desktop shortcut"""
        try:
            desktop_dir = Path.home() / "Desktop"
            if not desktop_dir.exists():
                desktop_dir = Path.home() / ".local" / "share" / "applications"
                
            shortcut_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Drone Ground Station
Comment=Drone Ground Station Control Interface
Exec={self.project_dir}/scripts/launch_ground_station.sh
Icon={self.project_dir}/assets/icon.png
Path={self.project_dir}
Terminal=false
StartupNotify=false
"""
            
            shortcut_path = desktop_dir / "drone-ground-station.desktop"
            with open(shortcut_path, 'w') as f:
                f.write(shortcut_content)
                
            os.chmod(shortcut_path, 0o755)
            
            self.info("Linux desktop shortcut created")
            
        except Exception as e:
            self.warn(f"Failed to create Linux shortcut: {e}")
            
    def run_tests(self):
        """Run basic tests"""
        self.log("Running basic tests...")
        
        python_path = self.get_venv_python()
        
        # Test Python environment
        try:
            result = self.run_command([str(python_path), "--version"])
            self.info(f"Python test passed: {result.stdout.strip()}")
        except:
            self.error("Python test failed")
            
        # Test package imports
        test_imports = [
            "import PyQt5",
            "import cv2",
            "import numpy",
            "import serial",
            "import websockets",
            "import flask"
        ]
        
        for test_import in test_imports:
            try:
                self.run_command([str(python_path), "-c", test_import])
                package_name = test_import.split()[1]
                self.info(f"✓ {package_name} import successful")
            except:
                package_name = test_import.split()[1]
                self.warn(f"✗ {package_name} import failed")
                
    def print_summary(self):
        """Print installation summary"""
        print(f"\n{Colors.GREEN}" + "="*60)
        print("  Laptop Ground Station Setup Complete!")
        print("="*60 + f"{Colors.NC}")
        
        print(f"\n{Colors.BLUE}Project Information:{Colors.NC}")
        print(f"  Project Directory: {self.project_dir}")
        print(f"  Virtual Environment: {self.venv_dir}")
        print(f"  Configuration: {self.project_dir}/config/ground_station_config.json")
        
        print(f"\n{Colors.BLUE}Network Configuration:{Colors.NC}")
        print(f"  Drone IP: 192.168.4.1")
        print(f"  Ground Station IP: 192.168.4.2")
        print(f"  Video Port: 5600 (UDP)")
        print(f"  Telemetry Port: 14550 (UDP)")
        print(f"  Command Port: 14551 (TCP)")
        
        print(f"\n{Colors.BLUE}Next Steps:{Colors.NC}")
        print(f"  1. Connect to drone WiFi hotspot: 'DroneGroundStation'")
        print(f"  2. Test network connectivity: python scripts/test_network.py")
        print(f"  3. Test GStreamer: python scripts/test_gstreamer.py")
        print(f"  4. Launch ground station: scripts/launch_ground_station.{('bat' if self.system == 'windows' else 'sh')}")
        
        print(f"\n{Colors.YELLOW}Important Notes:{Colors.NC}")
        print(f"  - Ensure drone is powered on and WiFi hotspot is active")
        print(f"  - Check firewall settings if connection fails")
        print(f"  - Use virtual environment: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)")
        
def main():
    parser = argparse.ArgumentParser(description="Laptop Ground Station Setup")
    parser.add_argument("--skip-deps", action="store_true", 
                       help="Skip system dependency installation")
    parser.add_argument("--skip-tests", action="store_true", 
                       help="Skip running tests")
    parser.add_argument("--no-firewall", action="store_true", 
                       help="Skip firewall configuration")
    
    args = parser.parse_args()
    
    setup = LaptopSetup()
    
    try:
        print(f"{Colors.CYAN}" + "="*60)
        print("  Drone Ground Station - Laptop Setup")
        print("="*60 + f"{Colors.NC}")
        
        setup.check_python_version()
        
        if not args.skip_deps:
            setup.install_system_dependencies()
            
        setup.create_virtual_environment()
        setup.install_python_dependencies()
        setup.setup_project_structure()
        setup.create_configuration_files()
        setup.create_requirements_file()
        setup.create_launch_scripts()
        setup.create_test_scripts()
        
        if not args.no_firewall:
            setup.setup_firewall_rules()
            
        setup.create_desktop_shortcut()
        
        if not args.skip_tests:
            setup.run_tests()
            
        setup.print_summary()
        
    except KeyboardInterrupt:
        setup.error("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        setup.error(f"Setup failed: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()
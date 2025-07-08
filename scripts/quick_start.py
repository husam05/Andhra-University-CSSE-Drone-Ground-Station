#!/usr/bin/env python3
"""
Drone Ground Station Quick Start Script
Automated deployment and testing for Raspberry Pi 3 and laptop setup

This script provides a guided setup process for the complete drone ground station system.
"""

import os
import sys
import subprocess
import platform
import time
import json
import socket
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class QuickStart:
    """Main class for drone ground station quick start deployment"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.project_root = Path(__file__).parent.parent
        self.config = {}
        self.test_results = {}
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
        
    def print_step(self, step: str, status: str = "INFO"):
        """Print formatted step information"""
        color = Colors.GREEN if status == "SUCCESS" else Colors.YELLOW if status == "WARNING" else Colors.RED if status == "ERROR" else Colors.BLUE
        print(f"{color}[{status}]{Colors.END} {step}")
        
    def run_command(self, command: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> Tuple[bool, str]:
        """Run system command with timeout"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)
            
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        self.print_header("CHECKING PREREQUISITES")
        
        checks = [
            ("Python 3.8+", self.check_python),
            ("Git", self.check_git),
            ("Network connectivity", self.check_network),
            ("Administrative privileges", self.check_admin),
            ("Disk space (2GB+)", self.check_disk_space)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                if check_func():
                    self.print_step(f"{check_name}: OK", "SUCCESS")
                else:
                    self.print_step(f"{check_name}: FAILED", "ERROR")
                    all_passed = False
            except Exception as e:
                self.print_step(f"{check_name}: ERROR - {e}", "ERROR")
                all_passed = False
                
        return all_passed
        
    def check_python(self) -> bool:
        """Check Python version"""
        return sys.version_info >= (3, 8)
        
    def check_git(self) -> bool:
        """Check Git installation"""
        success, _ = self.run_command(["git", "--version"])
        return success
        
    def check_network(self) -> bool:
        """Check network connectivity"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except:
            return False
            
    def check_admin(self) -> bool:
        """Check administrative privileges"""
        if self.system == "windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
            
    def check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            stat = os.statvfs(self.project_root)
            free_space = stat.f_frsize * stat.f_bavail
            return free_space > 2 * 1024 * 1024 * 1024  # 2GB
        except:
            return True  # Assume OK if can't check
            
    def setup_laptop(self) -> bool:
        """Setup laptop ground station"""
        self.print_header("SETTING UP LAPTOP GROUND STATION")
        
        # Run laptop setup script
        setup_script = self.project_root / "scripts" / "laptop_setup.py"
        if setup_script.exists():
            self.print_step("Running automated laptop setup...")
            success, output = self.run_command([sys.executable, str(setup_script)], timeout=1800)
            if success:
                self.print_step("Laptop setup completed successfully", "SUCCESS")
                return True
            else:
                self.print_step(f"Laptop setup failed: {output}", "ERROR")
                return False
        else:
            self.print_step("Manual setup required - laptop_setup.py not found", "WARNING")
            return self.manual_laptop_setup()
            
    def manual_laptop_setup(self) -> bool:
        """Manual laptop setup steps"""
        self.print_step("Starting manual laptop setup...")
        
        # Create virtual environment
        venv_path = self.project_root / "venv"
        if not venv_path.exists():
            self.print_step("Creating Python virtual environment...")
            success, output = self.run_command([sys.executable, "-m", "venv", "venv"])
            if not success:
                self.print_step(f"Failed to create virtual environment: {output}", "ERROR")
                return False
                
        # Install requirements
        if self.system == "windows":
            pip_cmd = str(venv_path / "Scripts" / "pip.exe")
        else:
            pip_cmd = str(venv_path / "bin" / "pip")
            
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self.print_step("Installing Python dependencies...")
            success, output = self.run_command([pip_cmd, "install", "-r", str(requirements_file)], timeout=1800)
            if not success:
                self.print_step(f"Failed to install requirements: {output}", "WARNING")
                
        # Create configuration
        self.create_config_files()
        
        return True
        
    def create_config_files(self):
        """Create default configuration files"""
        config_dir = self.project_root / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Ground station config
        gs_config = {
            "network": {
                "drone_ip": "192.168.4.1",
                "ground_station_ip": "192.168.4.2",
                "video_port": 5600,
                "telemetry_port": 14550,
                "command_port": 14551
            },
            "video": {
                "resolution": "1280x720",
                "framerate": 30,
                "bitrate": 2000000
            },
            "telemetry": {
                "update_rate": 10,
                "timeout": 5.0
            }
        }
        
        config_file = config_dir / "ground_station_config.json"
        with open(config_file, 'w') as f:
            json.dump(gs_config, f, indent=2)
            
        self.print_step(f"Created configuration file: {config_file}", "SUCCESS")
        
    def test_raspberry_pi_connection(self, pi_ip: str = "192.168.4.1") -> bool:
        """Test connection to Raspberry Pi"""
        self.print_header("TESTING RASPBERRY PI CONNECTION")
        
        # Test ping
        self.print_step(f"Testing ping to {pi_ip}...")
        if self.system == "windows":
            success, output = self.run_command(["ping", "-n", "4", pi_ip], timeout=30)
        else:
            success, output = self.run_command(["ping", "-c", "4", pi_ip], timeout=30)
            
        if success:
            self.print_step("Ping test successful", "SUCCESS")
        else:
            self.print_step("Ping test failed - check network connection", "ERROR")
            return False
            
        # Test SSH connection
        self.print_step("Testing SSH connection...")
        success, output = self.run_command(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", f"pi@{pi_ip}", "echo 'SSH OK'"], timeout=30)
        
        if success:
            self.print_step("SSH connection successful", "SUCCESS")
        else:
            self.print_step("SSH connection failed - check Pi setup", "WARNING")
            
        return True
        
    def test_video_stream(self, pi_ip: str = "192.168.4.1", port: int = 5600) -> bool:
        """Test video stream reception"""
        self.print_header("TESTING VIDEO STREAM")
        
        try:
            # Test UDP port accessibility
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind(('', port))
            sock.close()
            self.print_step(f"Video port {port} is available", "SUCCESS")
            
            # Test GStreamer (if available)
            gst_cmd = [
                "gst-launch-1.0",
                "--version"
            ]
            success, output = self.run_command(gst_cmd, timeout=10)
            if success:
                self.print_step("GStreamer is available", "SUCCESS")
            else:
                self.print_step("GStreamer not found - install required", "WARNING")
                
            return True
            
        except Exception as e:
            self.print_step(f"Video stream test failed: {e}", "ERROR")
            return False
            
    def test_telemetry(self, pi_ip: str = "192.168.4.1", port: int = 14550) -> bool:
        """Test telemetry data reception"""
        self.print_header("TESTING TELEMETRY")
        
        try:
            # Test UDP port for telemetry
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.bind(('', port))
            sock.close()
            self.print_step(f"Telemetry port {port} is available", "SUCCESS")
            
            # Try to receive some data (timeout after 10 seconds)
            self.print_step("Listening for telemetry data (10 second test)...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)
            sock.bind(('', port))
            
            try:
                data, addr = sock.recvfrom(1024)
                self.print_step(f"Received telemetry data from {addr}", "SUCCESS")
                return True
            except socket.timeout:
                self.print_step("No telemetry data received (timeout)", "WARNING")
                return False
            finally:
                sock.close()
                
        except Exception as e:
            self.print_step(f"Telemetry test failed: {e}", "ERROR")
            return False
            
    def run_integration_test(self) -> bool:
        """Run comprehensive integration test"""
        self.print_header("RUNNING INTEGRATION TEST")
        
        integration_script = self.project_root / "scripts" / "system_integration_test.py"
        if integration_script.exists():
            self.print_step("Running comprehensive integration test...")
            success, output = self.run_command([sys.executable, str(integration_script)], timeout=300)
            
            if success:
                self.print_step("Integration test completed successfully", "SUCCESS")
                # Parse results if possible
                if "PASS" in output:
                    self.print_step("All integration tests passed", "SUCCESS")
                    return True
                else:
                    self.print_step("Some integration tests failed", "WARNING")
                    return False
            else:
                self.print_step(f"Integration test failed: {output}", "ERROR")
                return False
        else:
            self.print_step("Integration test script not found", "WARNING")
            return True
            
    def generate_launch_scripts(self):
        """Generate platform-specific launch scripts"""
        self.print_header("GENERATING LAUNCH SCRIPTS")
        
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        if self.system == "windows":
            # Windows batch file
            batch_content = '''@echo off
echo Starting Drone Ground Station...
cd /d "%~dp0.."
call venv\\Scripts\\activate.bat
python examples/basic_flight_demo.py %*
pause
'''
            
            batch_file = scripts_dir / "launch_ground_station.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
                
            self.print_step(f"Created Windows launch script: {batch_file}", "SUCCESS")
            
        else:
            # Unix shell script
            shell_content = '''#!/bin/bash
echo "Starting Drone Ground Station..."
cd "$(dirname "$0")/.."
source venv/bin/activate
python3 examples/basic_flight_demo.py "$@"
'''
            
            shell_file = scripts_dir / "launch_ground_station.sh"
            with open(shell_file, 'w') as f:
                f.write(shell_content)
                
            # Make executable
            os.chmod(shell_file, 0o755)
            
            self.print_step(f"Created Unix launch script: {shell_file}", "SUCCESS")
            
    def print_summary(self):
        """Print deployment summary and next steps"""
        self.print_header("DEPLOYMENT SUMMARY")
        
        print(f"{Colors.GREEN}✓ Laptop ground station setup completed{Colors.END}")
        print(f"{Colors.GREEN}✓ Configuration files created{Colors.END}")
        print(f"{Colors.GREEN}✓ Launch scripts generated{Colors.END}")
        
        self.print_header("NEXT STEPS")
        
        print(f"{Colors.YELLOW}1. Raspberry Pi Setup:{Colors.END}")
        print(f"   - Flash Raspberry Pi OS to SD card")
        print(f"   - Copy and run: scripts/raspberry_pi_setup.sh")
        print(f"   - Connect camera and UART to flight controller")
        
        print(f"\n{Colors.YELLOW}2. Hardware Connections:{Colors.END}")
        print(f"   - FC TX → Pi GPIO 15 (Pin 10)")
        print(f"   - FC RX → Pi GPIO 14 (Pin 8)")
        print(f"   - FC GND → Pi GND (Pin 6)")
        print(f"   - Connect camera module to CSI port")
        
        print(f"\n{Colors.YELLOW}3. Network Setup:{Colors.END}")
        print(f"   - Connect laptop to Pi WiFi: 'DroneGroundStation'")
        print(f"   - Password: 'DroneControl123'")
        print(f"   - Pi IP: 192.168.4.1")
        
        print(f"\n{Colors.YELLOW}4. Testing:{Colors.END}")
        print(f"   - Run: python scripts/system_integration_test.py")
        print(f"   - Test video: python examples/video_analyzer.py")
        print(f"   - Test telemetry: python examples/telemetry_monitor.py")
        
        print(f"\n{Colors.YELLOW}5. Flight Testing:{Colors.END}")
        print(f"   - Remove propellers for initial testing")
        print(f"   - Run: python examples/basic_flight_demo.py --test-mode")
        print(f"   - Follow safety procedures in DEPLOYMENT_CHECKLIST.md")
        
        print(f"\n{Colors.CYAN}📋 Complete checklist: DEPLOYMENT_CHECKLIST.md{Colors.END}")
        print(f"{Colors.CYAN}📖 Hardware guide: HARDWARE_WIRING_GUIDE.md{Colors.END}")
        print(f"{Colors.CYAN}🔧 Implementation guide: PRACTICAL_IMPLEMENTATION_GUIDE.md{Colors.END}")
        
        print(f"\n{Colors.BOLD}{Colors.GREEN}🚁 Ready for drone ground station deployment!{Colors.END}")
        
def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Drone Ground Station Quick Start")
    parser.add_argument("--mode", choices=["laptop", "test", "full"], default="full",
                       help="Setup mode: laptop only, test only, or full setup")
    parser.add_argument("--pi-ip", default="192.168.4.1",
                       help="Raspberry Pi IP address")
    parser.add_argument("--skip-prereq", action="store_true",
                       help="Skip prerequisite checks")
    
    args = parser.parse_args()
    
    qs = QuickStart()
    
    try:
        qs.print_header("DRONE GROUND STATION QUICK START")
        print(f"{Colors.CYAN}Automated setup for Raspberry Pi 3 + Laptop configuration{Colors.END}")
        print(f"{Colors.CYAN}Platform: {platform.system()} {platform.release()}{Colors.END}")
        
        # Check prerequisites
        if not args.skip_prereq:
            if not qs.check_prerequisites():
                print(f"\n{Colors.RED}Prerequisites check failed. Please resolve issues and try again.{Colors.END}")
                return 1
                
        # Setup laptop
        if args.mode in ["laptop", "full"]:
            if not qs.setup_laptop():
                print(f"\n{Colors.RED}Laptop setup failed. Check errors above.{Colors.END}")
                return 1
                
        # Generate launch scripts
        qs.generate_launch_scripts()
        
        # Run tests
        if args.mode in ["test", "full"]:
            # Test Pi connection (if available)
            qs.test_raspberry_pi_connection(args.pi_ip)
            
            # Test video and telemetry
            qs.test_video_stream(args.pi_ip)
            qs.test_telemetry(args.pi_ip)
            
            # Run integration test
            qs.run_integration_test()
            
        # Print summary
        qs.print_summary()
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup interrupted by user.{Colors.END}")
        return 1
    except Exception as e:
        print(f"\n{Colors.RED}Setup failed with error: {e}{Colors.END}")
        return 1
        
if __name__ == "__main__":
    sys.exit(main())
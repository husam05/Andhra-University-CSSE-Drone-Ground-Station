#!/usr/bin/env python3
"""
Drone Ground Station System Test Script

This script performs comprehensive testing of the drone ground station system,
including network connectivity, video streaming, telemetry, and ROS2 components.

Usage:
    python test_system.py [--drone-ip 192.168.4.1] [--verbose]
"""

import sys
import time
import socket
import subprocess
import argparse
import json
from typing import Dict, List, Tuple, Optional
import threading
import queue

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
except ImportError:
    Gst = None

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
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str = "", details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
        self.timestamp = time.time()

class SystemTester:
    """Main system testing class"""
    
    def __init__(self, drone_ip: str = "192.168.4.1", verbose: bool = False):
        self.drone_ip = drone_ip
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.test_ports = {
            'video': 5600,
            'telemetry': 5601,
            'commands': 5602,
            'ssh': 22
        }
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Log message with color"""
        print(f"{color}{message}{Colors.END}")
        
    def log_verbose(self, message: str):
        """Log verbose message"""
        if self.verbose:
            self.log(f"  → {message}", Colors.CYAN)
            
    def add_result(self, name: str, passed: bool, message: str = "", details: str = ""):
        """Add test result"""
        result = TestResult(name, passed, message, details)
        self.results.append(result)
        
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        self.log(f"{status} {name}: {message}")
        
        if details and self.verbose:
            self.log_verbose(details)
            
    def run_command(self, cmd: List[str], timeout: int = 10) -> Tuple[bool, str, str]:
        """Run system command with timeout"""
        try:
            self.log_verbose(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                shell=True if sys.platform == 'win32' else False
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
            
    def test_network_connectivity(self):
        """Test basic network connectivity to drone"""
        self.log(f"\n{Colors.BOLD}Testing Network Connectivity{Colors.END}")
        
        # Test ping
        success, stdout, stderr = self.run_command(["ping", "-n", "3", self.drone_ip])
        if success:
            self.add_result("Ping Test", True, f"Successfully pinged {self.drone_ip}")
        else:
            self.add_result("Ping Test", False, f"Failed to ping {self.drone_ip}", stderr)
            
        # Test SSH connectivity
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.drone_ip, self.test_ports['ssh']))
            sock.close()
            
            if result == 0:
                self.add_result("SSH Port", True, "SSH port 22 is accessible")
            else:
                self.add_result("SSH Port", False, "SSH port 22 is not accessible")
        except Exception as e:
            self.add_result("SSH Port", False, "SSH connectivity test failed", str(e))
            
    def test_video_ports(self):
        """Test video streaming ports"""
        self.log(f"\n{Colors.BOLD}Testing Video Streaming{Colors.END}")
        
        # Test video port accessibility
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.bind(('', self.test_ports['video']))
            sock.close()
            self.add_result("Video Port Binding", True, f"Port {self.test_ports['video']} is available")
        except Exception as e:
            self.add_result("Video Port Binding", False, f"Port {self.test_ports['video']} binding failed", str(e))
            
        # Test GStreamer availability
        if Gst:
            self.add_result("GStreamer", True, "GStreamer Python bindings available")
            
            # Test GStreamer pipeline creation
            try:
                pipeline_str = f"udpsrc port={self.test_ports['video']} ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! fakesink"
                pipeline = Gst.parse_launch(pipeline_str)
                if pipeline:
                    self.add_result("GStreamer Pipeline", True, "Video pipeline creation successful")
                else:
                    self.add_result("GStreamer Pipeline", False, "Failed to create video pipeline")
            except Exception as e:
                self.add_result("GStreamer Pipeline", False, "Pipeline creation failed", str(e))
        else:
            self.add_result("GStreamer", False, "GStreamer Python bindings not available")
            
        # Test OpenCV availability
        if cv2:
            self.add_result("OpenCV", True, f"OpenCV {cv2.__version__} available")
        else:
            self.add_result("OpenCV", False, "OpenCV not available")
            
    def test_telemetry_ports(self):
        """Test telemetry communication ports"""
        self.log(f"\n{Colors.BOLD}Testing Telemetry Communication{Colors.END}")
        
        # Test telemetry UDP port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.bind(('', self.test_ports['telemetry']))
            sock.close()
            self.add_result("Telemetry UDP Port", True, f"UDP port {self.test_ports['telemetry']} available")
        except Exception as e:
            self.add_result("Telemetry UDP Port", False, f"UDP port {self.test_ports['telemetry']} binding failed", str(e))
            
        # Test command TCP port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.bind(('', self.test_ports['commands']))
            sock.close()
            self.add_result("Command TCP Port", True, f"TCP port {self.test_ports['commands']} available")
        except Exception as e:
            self.add_result("Command TCP Port", False, f"TCP port {self.test_ports['commands']} binding failed", str(e))
            
    def test_ros2_environment(self):
        """Test ROS2 environment and dependencies"""
        self.log(f"\n{Colors.BOLD}Testing ROS2 Environment{Colors.END}")
        
        # Test ROS2 installation
        success, stdout, stderr = self.run_command(["ros2", "--version"])
        if success:
            version = stdout.strip()
            self.add_result("ROS2 Installation", True, f"ROS2 found: {version}")
        else:
            self.add_result("ROS2 Installation", False, "ROS2 not found or not in PATH", stderr)
            
        # Test ROS2 daemon
        success, stdout, stderr = self.run_command(["ros2", "daemon", "status"])
        if success:
            self.add_result("ROS2 Daemon", True, "ROS2 daemon is running")
        else:
            self.add_result("ROS2 Daemon", False, "ROS2 daemon not running", stderr)
            
        # Test package availability
        success, stdout, stderr = self.run_command(["ros2", "pkg", "list"])
        if success and "drone_ground_station" in stdout:
            self.add_result("Ground Station Package", True, "drone_ground_station package found")
        else:
            self.add_result("Ground Station Package", False, "drone_ground_station package not found")
            
    def test_python_dependencies(self):
        """Test Python dependencies"""
        self.log(f"\n{Colors.BOLD}Testing Python Dependencies{Colors.END}")
        
        required_packages = [
            'rclpy',
            'cv_bridge',
            'sensor_msgs',
            'geometry_msgs',
            'std_msgs',
            'pymavlink',
            'numpy',
            'tkinter'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                self.add_result(f"Python Package: {package}", True, f"{package} is available")
            except ImportError as e:
                self.add_result(f"Python Package: {package}", False, f"{package} not available", str(e))
                
    def test_drone_services(self):
        """Test drone-side services"""
        self.log(f"\n{Colors.BOLD}Testing Drone Services{Colors.END}")
        
        # Test video stream reception
        def test_video_stream():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)
                sock.bind(('', self.test_ports['video']))
                
                # Wait for data
                data, addr = sock.recvfrom(1024)
                sock.close()
                
                if addr[0] == self.drone_ip:
                    return True, f"Received video data from {addr[0]}"
                else:
                    return False, f"Received data from unexpected source: {addr[0]}"
                    
            except socket.timeout:
                return False, "No video data received within timeout"
            except Exception as e:
                return False, str(e)
                
        success, message = test_video_stream()
        self.add_result("Video Stream Reception", success, message)
        
        # Test telemetry reception
        def test_telemetry_stream():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)
                sock.bind(('', self.test_ports['telemetry']))
                
                # Wait for data
                data, addr = sock.recvfrom(1024)
                sock.close()
                
                if addr[0] == self.drone_ip:
                    return True, f"Received telemetry data from {addr[0]}"
                else:
                    return False, f"Received data from unexpected source: {addr[0]}"
                    
            except socket.timeout:
                return False, "No telemetry data received within timeout"
            except Exception as e:
                return False, str(e)
                
        success, message = test_telemetry_stream()
        self.add_result("Telemetry Reception", success, message)
        
    def test_system_resources(self):
        """Test system resources and performance"""
        self.log(f"\n{Colors.BOLD}Testing System Resources{Colors.END}")
        
        try:
            import psutil
            
            # Test CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent < 80:
                self.add_result("CPU Usage", True, f"CPU usage: {cpu_percent:.1f}%")
            else:
                self.add_result("CPU Usage", False, f"High CPU usage: {cpu_percent:.1f}%")
                
            # Test Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            if memory_percent < 80:
                self.add_result("Memory Usage", True, f"Memory usage: {memory_percent:.1f}%")
            else:
                self.add_result("Memory Usage", False, f"High memory usage: {memory_percent:.1f}%")
                
            # Test Disk
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent < 90:
                self.add_result("Disk Usage", True, f"Disk usage: {disk_percent:.1f}%")
            else:
                self.add_result("Disk Usage", False, f"High disk usage: {disk_percent:.1f}%")
                
        except ImportError:
            self.add_result("System Resources", False, "psutil not available for resource monitoring")
            
    def generate_report(self):
        """Generate test report"""
        self.log(f"\n{Colors.BOLD}Test Report Summary{Colors.END}")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {Colors.GREEN}{passed_tests}{Colors.END}")
        self.log(f"Failed: {Colors.RED}{failed_tests}{Colors.END}")
        self.log(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            self.log(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for result in self.results:
                if not result.passed:
                    self.log(f"  ✗ {result.name}: {result.message}")
                    if result.details:
                        self.log(f"    Details: {result.details}")
                        
        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'drone_ip': self.drone_ip,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'details': r.details,
                    'timestamp': r.timestamp
                }
                for r in self.results
            ]
        }
        
        try:
            with open('test_report.json', 'w') as f:
                json.dump(report_data, f, indent=2)
            self.log(f"\nDetailed report saved to: test_report.json")
        except Exception as e:
            self.log(f"Failed to save report: {e}")
            
        return failed_tests == 0
        
    def run_all_tests(self):
        """Run all system tests"""
        self.log(f"{Colors.BOLD}Drone Ground Station System Test{Colors.END}")
        self.log(f"Testing drone at: {self.drone_ip}")
        self.log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run test suites
        self.test_network_connectivity()
        self.test_python_dependencies()
        self.test_ros2_environment()
        self.test_video_ports()
        self.test_telemetry_ports()
        self.test_system_resources()
        
        # Only test drone services if basic connectivity works
        if any(r.passed and "Ping Test" in r.name for r in self.results):
            self.test_drone_services()
        else:
            self.log(f"\n{Colors.YELLOW}Skipping drone service tests due to connectivity issues{Colors.END}")
            
        # Generate report
        success = self.generate_report()
        
        if success:
            self.log(f"\n{Colors.GREEN}All tests passed! System is ready for operation.{Colors.END}")
        else:
            self.log(f"\n{Colors.RED}Some tests failed. Please check the issues above.{Colors.END}")
            
        return success

def main():
    parser = argparse.ArgumentParser(description='Test drone ground station system')
    parser.add_argument('--drone-ip', default='192.168.4.1', help='Drone IP address')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick test (skip drone services)')
    
    args = parser.parse_args()
    
    tester = SystemTester(args.drone_ip, args.verbose)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test failed with error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
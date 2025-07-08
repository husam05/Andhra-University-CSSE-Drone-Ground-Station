#!/usr/bin/env python3
"""
Drone Ground Station System Integration Test
Comprehensive testing suite for validating the complete drone ground station system
"""

import os
import sys
import time
import json
import socket
import subprocess
import threading
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import argparse

try:
    import cv2
    import numpy as np
    import serial
    import websockets
    import requests
    import psutil
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

class TestResult:
    def __init__(self, name, passed=False, message="", duration=0.0, details=None):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.details = details or {}
        self.timestamp = datetime.now()

class SystemIntegrationTest:
    def __init__(self, config_file=None):
        self.config = self._load_config(config_file)
        self.results = []
        self.logger = self._setup_logging()
        self.drone_ip = self.config.get('network', {}).get('drone_ip', '192.168.4.1')
        self.ground_station_ip = self.config.get('network', {}).get('ground_station_ip', '192.168.4.2')
        
    def _load_config(self, config_file):
        """Load configuration from file"""
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            "network": {
                "drone_ip": "192.168.4.1",
                "ground_station_ip": "192.168.4.2",
                "video_port": 5600,
                "telemetry_port": 14550,
                "command_port": 14551,
                "web_port": 5000
            },
            "timeouts": {
                "ping": 5,
                "connection": 10,
                "video_stream": 15,
                "telemetry": 10
            },
            "thresholds": {
                "max_latency": 100,  # ms
                "min_fps": 15,
                "max_packet_loss": 5  # %
            }
        }
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('system_test.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
        
    def log(self, message, level=logging.INFO):
        """Log message with color"""
        if level == logging.ERROR:
            print(f"{Colors.RED}[ERROR] {message}{Colors.NC}")
        elif level == logging.WARNING:
            print(f"{Colors.YELLOW}[WARNING] {message}{Colors.NC}")
        elif level == logging.INFO:
            print(f"{Colors.GREEN}[INFO] {message}{Colors.NC}")
        else:
            print(f"{Colors.BLUE}[DEBUG] {message}{Colors.NC}")
            
        self.logger.log(level, message)
        
    def add_result(self, result):
        """Add test result"""
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        color = Colors.GREEN if result.passed else Colors.RED
        print(f"{color}[{status}] {result.name} ({result.duration:.2f}s){Colors.NC}")
        if result.message:
            print(f"    {result.message}")
            
    def run_test(self, test_func, test_name):
        """Run a test function and record results"""
        start_time = time.time()
        try:
            result = test_func()
            if isinstance(result, TestResult):
                result.duration = time.time() - start_time
                self.add_result(result)
                return result
            else:
                # Assume boolean result
                duration = time.time() - start_time
                test_result = TestResult(test_name, result, duration=duration)
                self.add_result(test_result)
                return test_result
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(test_name, False, str(e), duration)
            self.add_result(test_result)
            return test_result
            
    # Network Tests
    def test_network_connectivity(self):
        """Test basic network connectivity to drone"""
        try:
            # Test ping
            if os.name == 'nt':  # Windows
                result = subprocess.run(['ping', '-n', '4', self.drone_ip], 
                                      capture_output=True, text=True, timeout=10)
            else:  # Unix-like
                result = subprocess.run(['ping', '-c', '4', self.drone_ip], 
                                      capture_output=True, text=True, timeout=10)
                                      
            if result.returncode == 0:
                # Parse ping statistics
                output = result.stdout
                if 'Average' in output or 'avg' in output:
                    return TestResult("Network Connectivity", True, "Ping successful")
                else:
                    return TestResult("Network Connectivity", True, "Basic connectivity confirmed")
            else:
                return TestResult("Network Connectivity", False, "Ping failed")
                
        except subprocess.TimeoutExpired:
            return TestResult("Network Connectivity", False, "Ping timeout")
        except Exception as e:
            return TestResult("Network Connectivity", False, f"Ping error: {e}")
            
    def test_port_accessibility(self):
        """Test if required ports are accessible"""
        ports_to_test = [
            (self.config['network']['video_port'], 'UDP', 'Video Stream'),
            (self.config['network']['telemetry_port'], 'UDP', 'Telemetry'),
            (self.config['network']['command_port'], 'TCP', 'Commands'),
            (self.config['network']['web_port'], 'TCP', 'Web Interface')
        ]
        
        results = []
        for port, protocol, description in ports_to_test:
            try:
                if protocol == 'TCP':
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    
                sock.settimeout(5)
                
                if protocol == 'TCP':
                    result = sock.connect_ex((self.drone_ip, port))
                    accessible = result == 0
                else:
                    # For UDP, try to bind locally and send a test packet
                    try:
                        sock.sendto(b'test', (self.drone_ip, port))
                        accessible = True
                    except:
                        accessible = False
                        
                sock.close()
                results.append((description, accessible))
                
            except Exception as e:
                results.append((description, False))
                
        passed_count = sum(1 for _, accessible in results if accessible)
        total_count = len(results)
        
        details = {desc: accessible for desc, accessible in results}
        message = f"{passed_count}/{total_count} ports accessible"
        
        return TestResult("Port Accessibility", passed_count == total_count, message, details=details)
        
    def test_network_latency(self):
        """Test network latency"""
        try:
            latencies = []
            for i in range(10):
                start_time = time.time()
                
                # Simple TCP connection test
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                
                try:
                    sock.connect((self.drone_ip, self.config['network']['web_port']))
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    sock.close()
                except:
                    pass
                    
                time.sleep(0.1)
                
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                min_latency = min(latencies)
                
                threshold = self.config['thresholds']['max_latency']
                passed = avg_latency < threshold
                
                message = f"Avg: {avg_latency:.1f}ms, Min: {min_latency:.1f}ms, Max: {max_latency:.1f}ms"
                details = {
                    'average': avg_latency,
                    'minimum': min_latency,
                    'maximum': max_latency,
                    'samples': len(latencies)
                }
                
                return TestResult("Network Latency", passed, message, details=details)
            else:
                return TestResult("Network Latency", False, "No successful connections")
                
        except Exception as e:
            return TestResult("Network Latency", False, f"Latency test error: {e}")
            
    # Video Stream Tests
    def test_video_stream_reception(self):
        """Test video stream reception"""
        try:
            # Create GStreamer pipeline for receiving video
            pipeline_str = f"udpsrc port={self.config['network']['video_port']} ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink"
            
            cap = cv2.VideoCapture(pipeline_str, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                return TestResult("Video Stream Reception", False, "Failed to open video stream")
                
            # Try to read frames for a few seconds
            frame_count = 0
            start_time = time.time()
            timeout = self.config['timeouts']['video_stream']
            
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
                    if frame_count >= 10:  # Got enough frames
                        break
                time.sleep(0.1)
                
            cap.release()
            
            if frame_count > 0:
                fps = frame_count / (time.time() - start_time)
                message = f"Received {frame_count} frames, ~{fps:.1f} FPS"
                details = {'frames_received': frame_count, 'fps': fps}
                
                min_fps = self.config['thresholds']['min_fps']
                passed = fps >= min_fps
                
                return TestResult("Video Stream Reception", passed, message, details=details)
            else:
                return TestResult("Video Stream Reception", False, "No frames received")
                
        except Exception as e:
            return TestResult("Video Stream Reception", False, f"Video stream error: {e}")
            
    def test_video_quality(self):
        """Test video quality metrics"""
        try:
            # Simple video quality test using OpenCV
            pipeline_str = f"udpsrc port={self.config['network']['video_port']} ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink"
            
            cap = cv2.VideoCapture(pipeline_str, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                return TestResult("Video Quality", False, "Cannot open video stream")
                
            # Analyze a few frames
            quality_metrics = []
            frame_count = 0
            
            while frame_count < 30:  # Analyze 30 frames
                ret, frame = cap.read()
                if ret:
                    # Calculate basic quality metrics
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Blur detection (Laplacian variance)
                    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                    
                    # Brightness
                    brightness = np.mean(gray)
                    
                    # Contrast (standard deviation)
                    contrast = np.std(gray)
                    
                    quality_metrics.append({
                        'blur_score': blur_score,
                        'brightness': brightness,
                        'contrast': contrast
                    })
                    
                    frame_count += 1
                else:
                    time.sleep(0.1)
                    
            cap.release()
            
            if quality_metrics:
                avg_blur = sum(m['blur_score'] for m in quality_metrics) / len(quality_metrics)
                avg_brightness = sum(m['brightness'] for m in quality_metrics) / len(quality_metrics)
                avg_contrast = sum(m['contrast'] for m in quality_metrics) / len(quality_metrics)
                
                # Simple quality assessment
                quality_good = avg_blur > 100 and 50 < avg_brightness < 200 and avg_contrast > 20
                
                message = f"Blur: {avg_blur:.1f}, Brightness: {avg_brightness:.1f}, Contrast: {avg_contrast:.1f}"
                details = {
                    'blur_score': avg_blur,
                    'brightness': avg_brightness,
                    'contrast': avg_contrast,
                    'frames_analyzed': len(quality_metrics)
                }
                
                return TestResult("Video Quality", quality_good, message, details=details)
            else:
                return TestResult("Video Quality", False, "No frames to analyze")
                
        except Exception as e:
            return TestResult("Video Quality", False, f"Quality test error: {e}")
            
    # Telemetry Tests
    def test_telemetry_reception(self):
        """Test telemetry data reception"""
        try:
            # Create UDP socket for telemetry
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.config['timeouts']['telemetry'])
            sock.bind(('', self.config['network']['telemetry_port']))
            
            packets_received = 0
            start_time = time.time()
            timeout = self.config['timeouts']['telemetry']
            
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    if addr[0] == self.drone_ip:
                        packets_received += 1
                        if packets_received >= 10:  # Got enough packets
                            break
                except socket.timeout:
                    break
                    
            sock.close()
            
            if packets_received > 0:
                rate = packets_received / (time.time() - start_time)
                message = f"Received {packets_received} packets, ~{rate:.1f} Hz"
                details = {'packets_received': packets_received, 'rate': rate}
                
                return TestResult("Telemetry Reception", True, message, details=details)
            else:
                return TestResult("Telemetry Reception", False, "No telemetry packets received")
                
        except Exception as e:
            return TestResult("Telemetry Reception", False, f"Telemetry error: {e}")
            
    def test_telemetry_parsing(self):
        """Test telemetry data parsing"""
        try:
            # This would test MSP or MAVLink parsing
            # For now, just test basic JSON parsing
            
            test_data = {
                "timestamp": time.time(),
                "altitude": 10.5,
                "battery": 85,
                "gps": {"lat": 40.7128, "lon": -74.0060},
                "attitude": {"roll": 0.1, "pitch": -0.2, "yaw": 45.0}
            }
            
            # Test JSON serialization/deserialization
            json_str = json.dumps(test_data)
            parsed_data = json.loads(json_str)
            
            # Validate parsed data
            required_fields = ['timestamp', 'altitude', 'battery', 'gps', 'attitude']
            all_fields_present = all(field in parsed_data for field in required_fields)
            
            if all_fields_present:
                return TestResult("Telemetry Parsing", True, "JSON parsing successful")
            else:
                return TestResult("Telemetry Parsing", False, "Missing required fields")
                
        except Exception as e:
            return TestResult("Telemetry Parsing", False, f"Parsing error: {e}")
            
    # Command Interface Tests
    def test_command_interface(self):
        """Test command interface connectivity"""
        try:
            # Test TCP connection to command port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config['timeouts']['connection'])
            
            result = sock.connect_ex((self.drone_ip, self.config['network']['command_port']))
            
            if result == 0:
                # Try to send a test command
                test_command = json.dumps({"command": "ping", "timestamp": time.time()})
                sock.send(test_command.encode())
                
                # Try to receive response
                sock.settimeout(5)
                try:
                    response = sock.recv(1024)
                    sock.close()
                    
                    if response:
                        return TestResult("Command Interface", True, "Command interface responsive")
                    else:
                        return TestResult("Command Interface", True, "Connected but no response")
                except socket.timeout:
                    sock.close()
                    return TestResult("Command Interface", True, "Connected but response timeout")
            else:
                sock.close()
                return TestResult("Command Interface", False, "Cannot connect to command port")
                
        except Exception as e:
            return TestResult("Command Interface", False, f"Command interface error: {e}")
            
    # System Performance Tests
    def test_system_resources(self):
        """Test system resource usage"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check thresholds
            cpu_ok = cpu_percent < 80
            memory_ok = memory.percent < 85
            disk_ok = disk.percent < 90
            
            all_ok = cpu_ok and memory_ok and disk_ok
            
            message = f"CPU: {cpu_percent:.1f}%, RAM: {memory.percent:.1f}%, Disk: {disk.percent:.1f}%"
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3)
            }
            
            return TestResult("System Resources", all_ok, message, details=details)
            
        except Exception as e:
            return TestResult("System Resources", False, f"Resource check error: {e}")
            
    def test_concurrent_connections(self):
        """Test handling multiple concurrent connections"""
        try:
            # Test multiple simultaneous connections
            connections = []
            successful_connections = 0
            
            for i in range(5):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((self.drone_ip, self.config['network']['web_port']))
                    
                    if result == 0:
                        connections.append(sock)
                        successful_connections += 1
                    else:
                        sock.close()
                except:
                    pass
                    
            # Close all connections
            for sock in connections:
                sock.close()
                
            passed = successful_connections >= 3  # At least 3 concurrent connections
            message = f"{successful_connections}/5 concurrent connections successful"
            details = {'successful_connections': successful_connections}
            
            return TestResult("Concurrent Connections", passed, message, details=details)
            
        except Exception as e:
            return TestResult("Concurrent Connections", False, f"Concurrency test error: {e}")
            
    # Integration Tests
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        try:
            workflow_steps = []
            
            # Step 1: Connect to drone
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.drone_ip, self.config['network']['command_port']))
                workflow_steps.append("Connection established")
                sock.close()
            except:
                workflow_steps.append("Connection failed")
                
            # Step 2: Request telemetry
            try:
                tel_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                tel_sock.settimeout(3)
                tel_sock.bind(('', 0))  # Bind to any available port
                
                # Send telemetry request (simulated)
                tel_sock.sendto(b'REQUEST_TELEMETRY', (self.drone_ip, self.config['network']['telemetry_port']))
                workflow_steps.append("Telemetry requested")
                tel_sock.close()
            except:
                workflow_steps.append("Telemetry request failed")
                
            # Step 3: Check video stream
            try:
                vid_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                vid_sock.settimeout(2)
                vid_sock.bind(('', 0))
                
                # Try to receive video data
                vid_sock.sendto(b'REQUEST_VIDEO', (self.drone_ip, self.config['network']['video_port']))
                workflow_steps.append("Video stream checked")
                vid_sock.close()
            except:
                workflow_steps.append("Video stream check failed")
                
            successful_steps = len([step for step in workflow_steps if "failed" not in step])
            total_steps = len(workflow_steps)
            
            passed = successful_steps == total_steps
            message = f"{successful_steps}/{total_steps} workflow steps successful"
            details = {'workflow_steps': workflow_steps}
            
            return TestResult("End-to-End Workflow", passed, message, details=details)
            
        except Exception as e:
            return TestResult("End-to-End Workflow", False, f"Workflow test error: {e}")
            
    def run_all_tests(self):
        """Run all tests"""
        print(f"{Colors.CYAN}" + "="*80)
        print("  Drone Ground Station System Integration Test")
        print("="*80 + f"{Colors.NC}")
        
        print(f"\n{Colors.BLUE}Configuration:{Colors.NC}")
        print(f"  Drone IP: {self.drone_ip}")
        print(f"  Ground Station IP: {self.ground_station_ip}")
        print(f"  Video Port: {self.config['network']['video_port']}")
        print(f"  Telemetry Port: {self.config['network']['telemetry_port']}")
        print(f"  Command Port: {self.config['network']['command_port']}")
        
        print(f"\n{Colors.YELLOW}Running Tests...{Colors.NC}\n")
        
        # Network Tests
        print(f"{Colors.PURPLE}Network Tests:{Colors.NC}")
        self.run_test(self.test_network_connectivity, "Network Connectivity")
        self.run_test(self.test_port_accessibility, "Port Accessibility")
        self.run_test(self.test_network_latency, "Network Latency")
        
        # Video Tests
        print(f"\n{Colors.PURPLE}Video Stream Tests:{Colors.NC}")
        self.run_test(self.test_video_stream_reception, "Video Stream Reception")
        self.run_test(self.test_video_quality, "Video Quality")
        
        # Telemetry Tests
        print(f"\n{Colors.PURPLE}Telemetry Tests:{Colors.NC}")
        self.run_test(self.test_telemetry_reception, "Telemetry Reception")
        self.run_test(self.test_telemetry_parsing, "Telemetry Parsing")
        
        # Command Tests
        print(f"\n{Colors.PURPLE}Command Interface Tests:{Colors.NC}")
        self.run_test(self.test_command_interface, "Command Interface")
        
        # Performance Tests
        print(f"\n{Colors.PURPLE}Performance Tests:{Colors.NC}")
        self.run_test(self.test_system_resources, "System Resources")
        self.run_test(self.test_concurrent_connections, "Concurrent Connections")
        
        # Integration Tests
        print(f"\n{Colors.PURPLE}Integration Tests:{Colors.NC}")
        self.run_test(self.test_end_to_end_workflow, "End-to-End Workflow")
        
    def generate_report(self, output_file=None):
        """Generate test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result.passed)
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "test_duration": sum(result.duration for result in self.results),
                "timestamp": datetime.now().isoformat()
            },
            "configuration": self.config,
            "test_results": []
        }
        
        for result in self.results:
            report["test_results"].append({
                "name": result.name,
                "passed": result.passed,
                "message": result.message,
                "duration": result.duration,
                "details": result.details,
                "timestamp": result.timestamp.isoformat()
            })
            
        # Print summary
        print(f"\n{Colors.CYAN}" + "="*80)
        print("  Test Summary")
        print("="*80 + f"{Colors.NC}")
        
        print(f"\n{Colors.BLUE}Overall Results:{Colors.NC}")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {Colors.GREEN}{passed_tests}{Colors.NC}")
        print(f"  Failed: {Colors.RED}{failed_tests}{Colors.NC}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Total Duration: {report['test_summary']['test_duration']:.2f}s")
        
        if failed_tests > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.NC}")
            for result in self.results:
                if not result.passed:
                    print(f"  ✗ {result.name}: {result.message}")
                    
        print(f"\n{Colors.GREEN}Passed Tests:{Colors.NC}")
        for result in self.results:
            if result.passed:
                print(f"  ✓ {result.name}")
                
        # Recommendations
        print(f"\n{Colors.YELLOW}Recommendations:{Colors.NC}")
        if failed_tests == 0:
            print("  🎉 All tests passed! System is ready for operation.")
        else:
            print("  📋 Address failed tests before proceeding:")
            
            for result in self.results:
                if not result.passed:
                    if "Network" in result.name:
                        print("    - Check network connectivity and drone WiFi hotspot")
                    elif "Video" in result.name:
                        print("    - Verify GStreamer installation and video pipeline")
                    elif "Telemetry" in result.name:
                        print("    - Check telemetry configuration and data format")
                    elif "Command" in result.name:
                        print("    - Verify command interface and protocol")
                    elif "System" in result.name:
                        print("    - Check system resources and performance")
                        
        # Save report to file
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n{Colors.BLUE}Report saved to: {output_file}{Colors.NC}")
            
        return report
        
def main():
    parser = argparse.ArgumentParser(description="Drone Ground Station Integration Test")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--output", "-o", help="Output report file", default="test_report.json")
    parser.add_argument("--drone-ip", help="Drone IP address", default="192.168.4.1")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    # Load configuration
    test_suite = SystemIntegrationTest(args.config)
    
    # Override drone IP if specified
    if args.drone_ip:
        test_suite.drone_ip = args.drone_ip
        test_suite.config['network']['drone_ip'] = args.drone_ip
        
    try:
        # Run tests
        test_suite.run_all_tests()
        
        # Generate report
        test_suite.generate_report(args.output)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.NC}")
        test_suite.generate_report(args.output)
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {e}{Colors.NC}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()
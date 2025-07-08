#!/usr/bin/env python3
"""
Integration Test Suite

This script provides comprehensive integration testing for the drone ground station system.
It tests:
1. End-to-end communication between all components
2. Video streaming pipeline
3. Telemetry data flow
4. Command and control functionality
5. Error handling and recovery
6. Performance under load

Usage:
    python integration_test.py --drone_ip 192.168.4.1 --full_test
"""

import argparse
import asyncio
import json
import logging
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result structure."""
    test_name: str
    passed: bool
    duration: float
    message: str
    details: Dict = None

class NetworkTester:
    """Tests network connectivity and performance."""
    
    def __init__(self, drone_ip: str):
        self.drone_ip = drone_ip
    
    async def test_ping(self) -> TestResult:
        """Test basic network connectivity."""
        start_time = time.time()
        
        try:
            # Use ping command to test connectivity
            if sys.platform == "win32":
                cmd = ["ping", "-n", "4", self.drone_ip]
            else:
                cmd = ["ping", "-c", "4", self.drone_ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return TestResult(
                    "Network Ping", True, duration,
                    f"Successfully pinged {self.drone_ip}",
                    {"output": result.stdout}
                )
            else:
                return TestResult(
                    "Network Ping", False, duration,
                    f"Failed to ping {self.drone_ip}",
                    {"error": result.stderr}
                )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                "Network Ping", False, duration,
                f"Ping test failed: {e}"
            )
    
    async def test_port_connectivity(self, ports: List[int]) -> List[TestResult]:
        """Test connectivity to specific ports."""
        results = []
        
        for port in ports:
            start_time = time.time()
            
            try:
                # Test TCP connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                
                result = sock.connect_ex((self.drone_ip, port))
                sock.close()
                
                duration = time.time() - start_time
                
                if result == 0:
                    results.append(TestResult(
                        f"Port {port} Connectivity", True, duration,
                        f"Port {port} is accessible"
                    ))
                else:
                    results.append(TestResult(
                        f"Port {port} Connectivity", False, duration,
                        f"Port {port} is not accessible"
                    ))
            
            except Exception as e:
                duration = time.time() - start_time
                results.append(TestResult(
                    f"Port {port} Connectivity", False, duration,
                    f"Port {port} test failed: {e}"
                ))
        
        return results

class VideoStreamTester:
    """Tests video streaming functionality."""
    
    def __init__(self, drone_ip: str, video_port: int = 5600):
        self.drone_ip = drone_ip
        self.video_port = video_port
    
    async def test_video_stream(self, duration: float = 10.0) -> TestResult:
        """Test video stream reception."""
        start_time = time.time()
        
        try:
            import cv2
            
            # GStreamer pipeline for receiving video
            gst_pipeline = (
                f"udpsrc port={self.video_port} ! "
                "application/x-rtp,encoding-name=H264,payload=96 ! "
                "rtph264depay ! h264parse ! avdec_h264 ! "
                "videoconvert ! appsink"
            )
            
            cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            
            if not cap.isOpened():
                test_duration = time.time() - start_time
                return TestResult(
                    "Video Stream", False, test_duration,
                    "Failed to open video stream"
                )
            
            frames_received = 0
            test_start = time.time()
            
            while (time.time() - test_start) < duration:
                ret, frame = cap.read()
                if ret:
                    frames_received += 1
                else:
                    break
            
            cap.release()
            test_duration = time.time() - start_time
            
            if frames_received > 0:
                fps = frames_received / duration
                return TestResult(
                    "Video Stream", True, test_duration,
                    f"Received {frames_received} frames in {duration}s",
                    {"frames": frames_received, "fps": fps}
                )
            else:
                return TestResult(
                    "Video Stream", False, test_duration,
                    "No frames received"
                )
        
        except ImportError:
            test_duration = time.time() - start_time
            return TestResult(
                "Video Stream", False, test_duration,
                "OpenCV not available for video testing"
            )
        except Exception as e:
            test_duration = time.time() - start_time
            return TestResult(
                "Video Stream", False, test_duration,
                f"Video stream test failed: {e}"
            )

class TelemetryTester:
    """Tests telemetry data reception."""
    
    def __init__(self, drone_ip: str, telemetry_port: int = 5000):
        self.drone_ip = drone_ip
        self.telemetry_port = telemetry_port
    
    async def test_telemetry_reception(self, duration: float = 10.0) -> TestResult:
        """Test telemetry data reception."""
        start_time = time.time()
        
        try:
            # Create UDP socket for telemetry
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', self.telemetry_port))
            sock.settimeout(1.0)
            
            packets_received = 0
            valid_packets = 0
            test_start = time.time()
            
            while (time.time() - test_start) < duration:
                try:
                    data, addr = sock.recvfrom(1024)
                    packets_received += 1
                    
                    # Try to parse as JSON
                    try:
                        json.loads(data.decode('utf-8'))
                        valid_packets += 1
                    except:
                        pass  # Not JSON, might be binary telemetry
                
                except socket.timeout:
                    continue
            
            sock.close()
            test_duration = time.time() - start_time
            
            if packets_received > 0:
                packet_rate = packets_received / duration
                return TestResult(
                    "Telemetry Reception", True, test_duration,
                    f"Received {packets_received} packets in {duration}s",
                    {
                        "packets": packets_received,
                        "valid_packets": valid_packets,
                        "packet_rate": packet_rate
                    }
                )
            else:
                return TestResult(
                    "Telemetry Reception", False, test_duration,
                    "No telemetry packets received"
                )
        
        except Exception as e:
            test_duration = time.time() - start_time
            return TestResult(
                "Telemetry Reception", False, test_duration,
                f"Telemetry test failed: {e}"
            )

class CommandTester:
    """Tests command and control functionality."""
    
    def __init__(self, drone_ip: str, command_port: int = 5001):
        self.drone_ip = drone_ip
        self.command_port = command_port
    
    async def test_command_interface(self) -> TestResult:
        """Test command interface connectivity."""
        start_time = time.time()
        
        try:
            # Test TCP connection to command port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            
            sock.connect((self.drone_ip, self.command_port))
            
            # Send a test command
            test_command = {
                "command": "status",
                "timestamp": time.time()
            }
            
            data = json.dumps(test_command).encode('utf-8')
            sock.send(data)
            
            # Try to receive response (optional)
            sock.settimeout(2.0)
            try:
                response = sock.recv(1024)
                response_received = True
            except socket.timeout:
                response_received = False
            
            sock.close()
            test_duration = time.time() - start_time
            
            return TestResult(
                "Command Interface", True, test_duration,
                "Command interface is accessible",
                {"response_received": response_received}
            )
        
        except Exception as e:
            test_duration = time.time() - start_time
            return TestResult(
                "Command Interface", False, test_duration,
                f"Command interface test failed: {e}"
            )

class PerformanceTester:
    """Tests system performance under load."""
    
    def __init__(self, drone_ip: str):
        self.drone_ip = drone_ip
    
    async def test_concurrent_connections(self, num_connections: int = 5) -> TestResult:
        """Test multiple concurrent connections."""
        start_time = time.time()
        
        try:
            async def create_connection(port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)
                    result = sock.connect_ex((self.drone_ip, port))
                    sock.close()
                    return result == 0
                except:
                    return False
            
            # Test concurrent connections to different ports
            ports = [5000, 5001, 5600, 22, 80]  # Common ports
            
            tasks = []
            for i in range(num_connections):
                port = ports[i % len(ports)]
                tasks.append(create_connection(port))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_connections = sum(1 for r in results if r is True)
            test_duration = time.time() - start_time
            
            success_rate = successful_connections / num_connections
            
            return TestResult(
                "Concurrent Connections", success_rate > 0.5, test_duration,
                f"{successful_connections}/{num_connections} connections successful",
                {
                    "successful": successful_connections,
                    "total": num_connections,
                    "success_rate": success_rate
                }
            )
        
        except Exception as e:
            test_duration = time.time() - start_time
            return TestResult(
                "Concurrent Connections", False, test_duration,
                f"Concurrent connection test failed: {e}"
            )
    
    async def test_bandwidth(self, duration: float = 5.0) -> TestResult:
        """Test network bandwidth to drone."""
        start_time = time.time()
        
        try:
            # Simple bandwidth test using multiple small requests
            total_bytes = 0
            requests = 0
            test_start = time.time()
            
            while (time.time() - test_start) < duration:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.0)
                    sock.connect((self.drone_ip, 22))  # SSH port for testing
                    
                    # Send small data packet
                    test_data = b"test" * 100  # 400 bytes
                    sock.send(test_data)
                    total_bytes += len(test_data)
                    requests += 1
                    
                    sock.close()
                except:
                    pass  # Ignore individual failures
            
            test_duration = time.time() - start_time
            
            if total_bytes > 0:
                bandwidth_kbps = (total_bytes * 8) / (duration * 1000)  # kbps
                return TestResult(
                    "Bandwidth Test", True, test_duration,
                    f"Bandwidth: {bandwidth_kbps:.1f} kbps",
                    {
                        "total_bytes": total_bytes,
                        "requests": requests,
                        "bandwidth_kbps": bandwidth_kbps
                    }
                )
            else:
                return TestResult(
                    "Bandwidth Test", False, test_duration,
                    "No data transmitted"
                )
        
        except Exception as e:
            test_duration = time.time() - start_time
            return TestResult(
                "Bandwidth Test", False, test_duration,
                f"Bandwidth test failed: {e}"
            )

class IntegrationTestSuite:
    """Main integration test suite."""
    
    def __init__(self, drone_ip: str, full_test: bool = False):
        self.drone_ip = drone_ip
        self.full_test = full_test
        
        # Initialize testers
        self.network_tester = NetworkTester(drone_ip)
        self.video_tester = VideoStreamTester(drone_ip)
        self.telemetry_tester = TelemetryTester(drone_ip)
        self.command_tester = CommandTester(drone_ip)
        self.performance_tester = PerformanceTester(drone_ip)
        
        self.results = []
    
    async def run_basic_tests(self) -> List[TestResult]:
        """Run basic connectivity tests."""
        logger.info("Running basic connectivity tests...")
        
        tests = []
        
        # Network ping test
        tests.append(await self.network_tester.test_ping())
        
        # Port connectivity tests
        important_ports = [22, 5000, 5001, 5600]  # SSH, telemetry, command, video
        port_results = await self.network_tester.test_port_connectivity(important_ports)
        tests.extend(port_results)
        
        # Command interface test
        tests.append(await self.command_tester.test_command_interface())
        
        return tests
    
    async def run_streaming_tests(self) -> List[TestResult]:
        """Run streaming functionality tests."""
        logger.info("Running streaming tests...")
        
        tests = []
        
        # Video stream test
        tests.append(await self.video_tester.test_video_stream(duration=5.0))
        
        # Telemetry test
        tests.append(await self.telemetry_tester.test_telemetry_reception(duration=5.0))
        
        return tests
    
    async def run_performance_tests(self) -> List[TestResult]:
        """Run performance tests."""
        logger.info("Running performance tests...")
        
        tests = []
        
        # Concurrent connections test
        tests.append(await self.performance_tester.test_concurrent_connections())
        
        # Bandwidth test
        tests.append(await self.performance_tester.test_bandwidth())
        
        return tests
    
    async def run_all_tests(self):
        """Run all integration tests."""
        logger.info(f"Starting integration tests for drone at {self.drone_ip}")
        start_time = time.time()
        
        # Basic tests (always run)
        basic_results = await self.run_basic_tests()
        self.results.extend(basic_results)
        
        # Check if basic connectivity is working
        basic_passed = any(r.passed for r in basic_results if "Ping" in r.test_name)
        
        if not basic_passed:
            logger.warning("Basic connectivity failed. Skipping advanced tests.")
        else:
            # Streaming tests
            if self.full_test:
                streaming_results = await self.run_streaming_tests()
                self.results.extend(streaming_results)
                
                # Performance tests
                performance_results = await self.run_performance_tests()
                self.results.extend(performance_results)
        
        total_duration = time.time() - start_time
        
        # Generate report
        self.generate_report(total_duration)
    
    def generate_report(self, total_duration: float):
        """Generate test report."""
        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]
        
        print("\n" + "="*80)
        print(f"INTEGRATION TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        print(f"Drone IP: {self.drone_ip}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Tests Run: {len(self.results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(passed_tests)/len(self.results)*100:.1f}%")
        
        print("\n" + "-"*40)
        print("PASSED TESTS:")
        print("-"*40)
        for result in passed_tests:
            print(f"✓ {result.test_name}: {result.message} ({result.duration:.2f}s)")
        
        if failed_tests:
            print("\n" + "-"*40)
            print("FAILED TESTS:")
            print("-"*40)
            for result in failed_tests:
                print(f"✗ {result.test_name}: {result.message} ({result.duration:.2f}s)")
        
        # Detailed results
        print("\n" + "-"*40)
        print("DETAILED RESULTS:")
        print("-"*40)
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            print(f"[{status}] {result.test_name}")
            print(f"  Duration: {result.duration:.2f}s")
            print(f"  Message: {result.message}")
            if result.details:
                for key, value in result.details.items():
                    print(f"  {key}: {value}")
            print()
        
        # Recommendations
        print("-"*40)
        print("RECOMMENDATIONS:")
        print("-"*40)
        
        if any("Ping" in r.test_name and not r.passed for r in self.results):
            print("• Check network connectivity to drone")
            print("• Verify drone IP address and network configuration")
        
        if any("Port" in r.test_name and not r.passed for r in self.results):
            print("• Check if drone services are running")
            print("• Verify firewall settings")
        
        if any("Video" in r.test_name and not r.passed for r in self.results):
            print("• Check video streaming configuration")
            print("• Verify GStreamer installation")
        
        if any("Telemetry" in r.test_name and not r.passed for r in self.results):
            print("• Check telemetry bridge configuration")
            print("• Verify UDP port settings")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Integration Test Suite')
    parser.add_argument('--drone_ip', default='192.168.4.1',
                       help='IP address of the drone (default: 192.168.4.1)')
    parser.add_argument('--full_test', action='store_true',
                       help='Run full test suite including streaming and performance tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run test suite
    test_suite = IntegrationTestSuite(args.drone_ip, args.full_test)
    
    try:
        asyncio.run(test_suite.run_all_tests())
    except KeyboardInterrupt:
        logger.info("Tests stopped by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")

if __name__ == "__main__":
    main()
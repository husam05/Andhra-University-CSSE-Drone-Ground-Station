#!/usr/bin/env python3
"""
Laptop Ground Station Receiver Test
This script tests receiving video and telemetry from the Raspberry Pi.
"""

import socket
import threading
import time
import json
import subprocess
import sys
from datetime import datetime
import os

def print_status(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [INFO] {message}")

def print_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [SUCCESS] {message}")

def print_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [ERROR] {message}")

def print_warning(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [WARNING] {message}")

class VideoReceiver:
    def __init__(self, port=5000):
        self.port = port
        self.running = False
        self.bytes_received = 0
        self.packets_received = 0
        
    def start(self):
        """Start receiving video stream"""
        print_status(f"Starting video receiver on port {self.port}...")
        
        try:
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('', self.port))
            self.sock.settimeout(1.0)  # 1 second timeout
            
            print_success(f"Video receiver listening on port {self.port}")
            self.running = True
            
            # Start GStreamer pipeline to display video
            self._start_gstreamer_display()
            
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(65536)
                    self.bytes_received += len(data)
                    self.packets_received += 1
                    
                    if self.packets_received % 100 == 0:
                        print_status(f"Video: {self.packets_received} packets, {self.bytes_received} bytes from {addr}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print_error(f"Video receive error: {e}")
                    
        except Exception as e:
            print_error(f"Failed to start video receiver: {e}")
        finally:
            if hasattr(self, 'sock'):
                self.sock.close()
                
    def _start_gstreamer_display(self):
        """Start GStreamer pipeline to display received video"""
        try:
            # GStreamer pipeline for receiving and displaying H.264 video
            gst_cmd = [
                "gst-launch-1.0",
                "udpsrc", f"port={self.port}",
                "!", "application/x-rtp,encoding-name=H264,payload=96",
                "!", "rtph264depay",
                "!", "h264parse",
                "!", "avdec_h264",
                "!", "videoconvert",
                "!", "autovideosink"
            ]
            
            print_status("Starting GStreamer video display...")
            self.gst_process = subprocess.Popen(gst_cmd, 
                                              stdout=subprocess.DEVNULL, 
                                              stderr=subprocess.PIPE)
            print_success("GStreamer video display started")
            
        except Exception as e:
            print_warning(f"Could not start GStreamer display: {e}")
            print_warning("Video packets will be received but not displayed")
            
    def stop(self):
        """Stop video receiver"""
        self.running = False
        if hasattr(self, 'gst_process'):
            self.gst_process.terminate()
        print_status(f"Video receiver stopped. Received {self.packets_received} packets, {self.bytes_received} bytes")

class TelemetryReceiver:
    def __init__(self, port=14550, status_port=14551):
        self.port = port
        self.status_port = status_port
        self.running = False
        self.telemetry_bytes = 0
        self.telemetry_packets = 0
        self.status_messages = 0
        
    def start(self):
        """Start receiving telemetry"""
        print_status(f"Starting telemetry receiver on ports {self.port} and {self.status_port}...")
        
        try:
            # Create sockets for telemetry and status
            self.telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telem_sock.bind(('', self.port))
            self.telem_sock.settimeout(1.0)
            
            self.status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.status_sock.bind(('', self.status_port))
            self.status_sock.settimeout(1.0)
            
            print_success(f"Telemetry receiver listening on ports {self.port} and {self.status_port}")
            self.running = True
            
            # Start threads for both sockets
            telem_thread = threading.Thread(target=self._receive_telemetry)
            status_thread = threading.Thread(target=self._receive_status)
            
            telem_thread.daemon = True
            status_thread.daemon = True
            
            telem_thread.start()
            status_thread.start()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print_error(f"Failed to start telemetry receiver: {e}")
        finally:
            if hasattr(self, 'telem_sock'):
                self.telem_sock.close()
            if hasattr(self, 'status_sock'):
                self.status_sock.close()
                
    def _receive_telemetry(self):
        """Receive raw telemetry data"""
        while self.running:
            try:
                data, addr = self.telem_sock.recvfrom(1024)
                self.telemetry_bytes += len(data)
                self.telemetry_packets += 1
                
                if self.telemetry_packets % 50 == 0:
                    print_status(f"Telemetry: {self.telemetry_packets} packets, {self.telemetry_bytes} bytes from {addr}")
                    
                # Try to decode as MAVLink (basic check)
                if len(data) > 6 and data[0] == 0xFE:  # MAVLink v1 magic byte
                    print_status(f"MAVLink packet detected: length={data[1]}, seq={data[2]}")
                elif len(data) > 10 and data[0] == 0xFD:  # MAVLink v2 magic byte
                    print_status(f"MAVLink v2 packet detected: length={data[1]}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                print_error(f"Telemetry receive error: {e}")
                
    def _receive_status(self):
        """Receive status messages"""
        while self.running:
            try:
                data, addr = self.status_sock.recvfrom(1024)
                self.status_messages += 1
                
                try:
                    status = json.loads(data.decode())
                    print_status(f"Status: {status}")
                except json.JSONDecodeError:
                    print_warning(f"Invalid status JSON: {data[:50]}...")
                    
            except socket.timeout:
                continue
            except Exception as e:
                print_error(f"Status receive error: {e}")
                
    def stop(self):
        """Stop telemetry receiver"""
        self.running = False
        print_status(f"Telemetry receiver stopped. Received {self.telemetry_packets} telemetry packets, {self.status_messages} status messages")

def test_network_connectivity():
    """Test network connectivity to Pi"""
    print_status("Testing network connectivity to Pi...")
    
    pi_ip = "192.168.4.1"
    
    # Test ping
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(["ping", "-n", "1", pi_ip], 
                                  capture_output=True, text=True, timeout=10)
        else:  # Linux/Mac
            result = subprocess.run(["ping", "-c", "1", pi_ip], 
                                  capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print_success(f"Ping to {pi_ip} successful")
            return True
        else:
            print_error(f"Ping to {pi_ip} failed")
            return False
            
    except Exception as e:
        print_error(f"Network test failed: {e}")
        return False

def check_gstreamer():
    """Check if GStreamer is available"""
    print_status("Checking GStreamer availability...")
    
    try:
        result = subprocess.run(["gst-launch-1.0", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print_success("GStreamer is available")
            return True
        else:
            print_warning("GStreamer not found or not working")
            return False
    except Exception as e:
        print_warning(f"GStreamer check failed: {e}")
        return False

def main():
    print("=== Laptop Ground Station Receiver Test ===")
    print("This script tests receiving video and telemetry from the Raspberry Pi.")
    print()
    
    # Test prerequisites
    print("Step 1: Testing prerequisites...")
    
    network_ok = test_network_connectivity()
    gstreamer_ok = check_gstreamer()
    
    if not network_ok:
        print_error("Network connectivity to Pi failed")
        print("Please ensure:")
        print("1. You are connected to the Pi's WiFi hotspot (DroneGroundStation)")
        print("2. Pi is powered on and hotspot is running")
        print("3. Your laptop has IP in range 192.168.4.x")
        return False
    
    print()
    
    # Start receivers
    print("Step 2: Starting receivers...")
    
    video_receiver = VideoReceiver(5000)
    telemetry_receiver = TelemetryReceiver(14550, 14551)
    
    # Start video receiver in a thread
    video_thread = threading.Thread(target=video_receiver.start)
    video_thread.daemon = True
    video_thread.start()
    
    # Start telemetry receiver in a thread
    telemetry_thread = threading.Thread(target=telemetry_receiver.start)
    telemetry_thread.daemon = True
    telemetry_thread.start()
    
    print()
    print("Receivers started. Waiting for data from Pi...")
    print("On the Pi, run:")
    print("  python3 ~/drone_ground_station/scripts/video_streamer.py")
    print("  python3 ~/drone_ground_station/scripts/telemetry_bridge.py")
    print()
    print("Press Ctrl+C to stop")
    
    try:
        # Keep main thread alive and show periodic status
        start_time = time.time()
        while True:
            time.sleep(10)
            elapsed = time.time() - start_time
            print_status(f"Running for {elapsed:.0f}s - Video: {video_receiver.packets_received} packets, Telemetry: {telemetry_receiver.telemetry_packets} packets")
            
    except KeyboardInterrupt:
        print("\nStopping receivers...")
        video_receiver.stop()
        telemetry_receiver.stop()
        
    print_success("Test completed")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_error(f"Test failed: {e}")
        sys.exit(1)
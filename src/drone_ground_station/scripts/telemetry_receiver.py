#!/usr/bin/env python3
"""
Telemetry Receiver Node for Drone Ground Station
Receives telemetry data from Crossflight via Raspberry Pi
Publishes flight data as ROS2 messages
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32, Bool
from sensor_msgs.msg import BatteryState, Imu, NavSatFix
from geometry_msgs.msg import Twist, PoseStamped, Vector3Stamped
from nav_msgs.msg import Odometry
import socket
import json
import threading
import time
from pymavlink import mavutil
import struct

class TelemetryReceiver(Node):
    def __init__(self):
        super().__init__('telemetry_receiver')
        
        # Parameters
        self.declare_parameter('drone_ip', '192.168.4.1')
        self.declare_parameter('telemetry_port', 14550)
        self.declare_parameter('update_rate', 10.0)
        
        self.drone_ip = self.get_parameter('drone_ip').value
        self.telemetry_port = self.get_parameter('telemetry_port').value
        self.update_rate = self.get_parameter('update_rate').value
        
        # ROS2 Publishers
        self.setup_publishers()
        
        # Telemetry data storage
        self.telemetry_data = {
            'armed': False,
            'mode': 'UNKNOWN',
            'battery_voltage': 0.0,
            'battery_current': 0.0,
            'battery_remaining': 0.0,
            'altitude': 0.0,
            'ground_speed': 0.0,
            'heading': 0.0,
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'lat': 0.0,
            'lon': 0.0,
            'satellites': 0,
            'gps_fix': 0
        }
        
        # Socket for telemetry
        self.telemetry_socket = None
        self.running = True
        
        # Start telemetry receiver thread
        self.telemetry_thread = threading.Thread(target=self.telemetry_receiver_loop)
        self.telemetry_thread.daemon = True
        self.telemetry_thread.start()
        
        # Timer for publishing telemetry
        self.timer = self.create_timer(1.0/self.update_rate, self.publish_telemetry)
        
        self.get_logger().info(f'Telemetry receiver initialized for {self.drone_ip}:{self.telemetry_port}')
    
    def setup_publishers(self):
        """Setup ROS2 publishers for telemetry data"""
        self.battery_pub = self.create_publisher(BatteryState, 'drone/battery', 10)
        self.imu_pub = self.create_publisher(Imu, 'drone/imu', 10)
        self.gps_pub = self.create_publisher(NavSatFix, 'drone/gps', 10)
        self.pose_pub = self.create_publisher(PoseStamped, 'drone/pose', 10)
        self.velocity_pub = self.create_publisher(Twist, 'drone/velocity', 10)
        self.altitude_pub = self.create_publisher(Float32, 'drone/altitude', 10)
        self.heading_pub = self.create_publisher(Float32, 'drone/heading', 10)
        self.armed_pub = self.create_publisher(Bool, 'drone/armed', 10)
        self.mode_pub = self.create_publisher(String, 'drone/mode', 10)
        self.status_pub = self.create_publisher(String, 'drone/status', 10)
    
    def telemetry_receiver_loop(self):
        """Main loop for receiving telemetry data"""
        while self.running:
            try:
                self.connect_telemetry()
                self.receive_telemetry_data()
            except Exception as e:
                self.get_logger().error(f'Telemetry error: {str(e)}')
                time.sleep(5)  # Wait before reconnecting
    
    def connect_telemetry(self):
        """Connect to drone telemetry"""
        try:
            if self.telemetry_socket:
                self.telemetry_socket.close()
            
            # Create UDP socket for telemetry
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_socket.settimeout(5.0)
            self.telemetry_socket.bind(('', self.telemetry_port))
            
            self.get_logger().info(f'Telemetry socket bound to port {self.telemetry_port}')
            
        except Exception as e:
            self.get_logger().error(f'Failed to connect telemetry: {str(e)}')
            raise
    
    def receive_telemetry_data(self):
        """Receive and parse telemetry data"""
        while self.running:
            try:
                # Receive data
                data, addr = self.telemetry_socket.recvfrom(1024)
                
                if addr[0] == self.drone_ip:
                    self.parse_telemetry_data(data)
                    
            except socket.timeout:
                self.get_logger().warn('Telemetry timeout - no data received')
                continue
            except Exception as e:
                self.get_logger().error(f'Error receiving telemetry: {str(e)}')
                break
    
    def parse_telemetry_data(self, data):
        """Parse received telemetry data"""
        try:
            # Try to parse as JSON first (custom format)
            try:
                telemetry_json = json.loads(data.decode('utf-8'))
                self.update_telemetry_from_json(telemetry_json)
                return
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            
            # Try to parse as MAVLink
            try:
                self.parse_mavlink_data(data)
            except Exception:
                # If all parsing fails, log raw data
                self.get_logger().debug(f'Unknown telemetry format: {data[:50]}')
                
        except Exception as e:
            self.get_logger().error(f'Error parsing telemetry: {str(e)}')
    
    def update_telemetry_from_json(self, data):
        """Update telemetry from JSON format"""
        if 'armed' in data:
            self.telemetry_data['armed'] = data['armed']
        if 'mode' in data:
            self.telemetry_data['mode'] = data['mode']
        if 'battery' in data:
            self.telemetry_data['battery_voltage'] = data['battery'].get('voltage', 0.0)
            self.telemetry_data['battery_current'] = data['battery'].get('current', 0.0)
            self.telemetry_data['battery_remaining'] = data['battery'].get('remaining', 0.0)
        if 'attitude' in data:
            self.telemetry_data['roll'] = data['attitude'].get('roll', 0.0)
            self.telemetry_data['pitch'] = data['attitude'].get('pitch', 0.0)
            self.telemetry_data['yaw'] = data['attitude'].get('yaw', 0.0)
        if 'position' in data:
            self.telemetry_data['lat'] = data['position'].get('lat', 0.0)
            self.telemetry_data['lon'] = data['position'].get('lon', 0.0)
            self.telemetry_data['altitude'] = data['position'].get('alt', 0.0)
        if 'velocity' in data:
            self.telemetry_data['ground_speed'] = data['velocity'].get('ground_speed', 0.0)
        if 'gps' in data:
            self.telemetry_data['satellites'] = data['gps'].get('satellites', 0)
            self.telemetry_data['gps_fix'] = data['gps'].get('fix_type', 0)
    
    def parse_mavlink_data(self, data):
        """Parse MAVLink telemetry data"""
        # This would require proper MAVLink parsing
        # For now, we'll use a simplified approach
        pass
    
    def publish_telemetry(self):
        """Publish telemetry data as ROS2 messages"""
        try:
            current_time = self.get_clock().now().to_msg()
            
            # Battery state
            battery_msg = BatteryState()
            battery_msg.header.stamp = current_time
            battery_msg.voltage = self.telemetry_data['battery_voltage']
            battery_msg.current = self.telemetry_data['battery_current']
            battery_msg.percentage = self.telemetry_data['battery_remaining']
            self.battery_pub.publish(battery_msg)
            
            # GPS
            gps_msg = NavSatFix()
            gps_msg.header.stamp = current_time
            gps_msg.header.frame_id = 'gps'
            gps_msg.latitude = self.telemetry_data['lat']
            gps_msg.longitude = self.telemetry_data['lon']
            gps_msg.altitude = self.telemetry_data['altitude']
            gps_msg.status.status = self.telemetry_data['gps_fix']
            self.gps_pub.publish(gps_msg)
            
            # Altitude
            altitude_msg = Float32()
            altitude_msg.data = self.telemetry_data['altitude']
            self.altitude_pub.publish(altitude_msg)
            
            # Heading
            heading_msg = Float32()
            heading_msg.data = self.telemetry_data['heading']
            self.heading_pub.publish(heading_msg)
            
            # Armed status
            armed_msg = Bool()
            armed_msg.data = self.telemetry_data['armed']
            self.armed_pub.publish(armed_msg)
            
            # Flight mode
            mode_msg = String()
            mode_msg.data = self.telemetry_data['mode']
            self.mode_pub.publish(mode_msg)
            
            # Status summary
            status_msg = String()
            status_msg.data = json.dumps(self.telemetry_data)
            self.status_pub.publish(status_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error publishing telemetry: {str(e)}')
    
    def destroy_node(self):
        """Clean up resources"""
        self.running = False
        if self.telemetry_socket:
            self.telemetry_socket.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    
    try:
        telemetry_receiver = TelemetryReceiver()
        rclpy.spin(telemetry_receiver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'telemetry_receiver' in locals():
            telemetry_receiver.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Telemetry Receiver Node for Drone Ground Station
Receives telemetry data from Crossflight via Raspberry Pi
Publishes flight data as ROS2 messages
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from typing import Any, Dict, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32, Bool
from sensor_msgs.msg import BatteryState, Imu, NavSatFix
from geometry_msgs.msg import Twist, PoseStamped, Vector3Stamped
from nav_msgs.msg import Odometry
from pymavlink import mavutil


# MAVLink mode mapping for ArduPilot/Crossflight
MAVLINK_MODE_MAP: Dict[int, str] = {
    0: 'STABILIZE',
    1: 'ACRO',
    2: 'ALT_HOLD',
    3: 'AUTO',
    4: 'GUIDED',
    5: 'LOITER',
    6: 'RTL',
    7: 'CIRCLE',
    9: 'LAND',
    11: 'DRIFT',
    13: 'SPORT',
    14: 'FLIP',
    15: 'AUTOTUNE',
    16: 'POSHOLD',
    17: 'BRAKE',
    18: 'THROW',
    19: 'AVOID_ADSB',
    20: 'GUIDED_NOGPS',
    21: 'SMART_RTL',
}


class TelemetryReceiver(Node):
    def __init__(self) -> None:
        super().__init__('telemetry_receiver')

        # Parameters
        self.declare_parameter('drone_ip', '192.168.4.1')
        self.declare_parameter('telemetry_port', 14550)
        self.declare_parameter('update_rate', 10.0)

        self.drone_ip: str = self.get_parameter('drone_ip').value
        self.telemetry_port: int = self.get_parameter('telemetry_port').value
        self.update_rate: float = self.get_parameter('update_rate').value

        # ROS2 Publishers
        self.setup_publishers()

        # Telemetry data storage with thread lock
        self._telemetry_lock = threading.Lock()
        self.telemetry_data: Dict[str, Any] = {
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

        # MAVLink connection for parsing binary messages
        self._mav: Optional[mavutil.mavlink.MAVLink] = None
        self._mav_buf = bytearray()

        # Socket for telemetry
        self.telemetry_socket: Optional[socket.socket] = None
        self.running: bool = True

        # Start telemetry receiver thread
        self.telemetry_thread = threading.Thread(
            target=self.telemetry_receiver_loop, daemon=True
        )
        self.telemetry_thread.start()

        # Timer for publishing telemetry
        self.timer = self.create_timer(1.0 / self.update_rate, self.publish_telemetry)

        self.get_logger().info(
            f'Telemetry receiver initialized for {self.drone_ip}:{self.telemetry_port}'
        )

    def setup_publishers(self) -> None:
        """Setup ROS2 publishers for telemetry data."""
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

    def telemetry_receiver_loop(self) -> None:
        """Main loop for receiving telemetry data."""
        while self.running:
            try:
                self.connect_telemetry()
                self.receive_telemetry_data()
            except Exception as e:
                self.get_logger().error(f'Telemetry error: {str(e)}')
                time.sleep(5)

    def connect_telemetry(self) -> None:
        """Connect to drone telemetry."""
        try:
            if self.telemetry_socket:
                self.telemetry_socket.close()

            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telemetry_socket.settimeout(5.0)
            self.telemetry_socket.bind(('', self.telemetry_port))

            self.get_logger().info(
                f'Telemetry socket bound to port {self.telemetry_port}'
            )

        except Exception as e:
            self.get_logger().error(f'Failed to connect telemetry: {str(e)}')
            raise

    def receive_telemetry_data(self) -> None:
        """Receive and parse telemetry data."""
        while self.running:
            try:
                data, addr = self.telemetry_socket.recvfrom(1024)

                if addr[0] == self.drone_ip:
                    self.parse_telemetry_data(data)

            except socket.timeout:
                self.get_logger().warn('Telemetry timeout - no data received')
                continue
            except Exception as e:
                self.get_logger().error(f'Error receiving telemetry: {str(e)}')
                break

    def parse_telemetry_data(self, data: bytes) -> None:
        """Parse received telemetry data (JSON or MAVLink)."""
        try:
            # Try JSON first (custom format from our telemetry bridge)
            try:
                telemetry_json = json.loads(data.decode('utf-8'))
                self.update_telemetry_from_json(telemetry_json)
                return
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

            # Try MAVLink binary protocol
            try:
                self.parse_mavlink_data(data)
            except Exception:
                self.get_logger().debug(f'Unknown telemetry format: {data[:50]}')

        except Exception as e:
            self.get_logger().error(f'Error parsing telemetry: {str(e)}')

    def _update_field(self, key: str, value: Any) -> None:
        """Thread-safe update of a single telemetry field."""
        with self._telemetry_lock:
            self.telemetry_data[key] = value

    def _update_fields(self, updates: Dict[str, Any]) -> None:
        """Thread-safe batch update of telemetry fields."""
        with self._telemetry_lock:
            self.telemetry_data.update(updates)

    def _get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Return a thread-safe copy of current telemetry data."""
        with self._telemetry_lock:
            return dict(self.telemetry_data)

    def update_telemetry_from_json(self, data: Dict[str, Any]) -> None:
        """Update telemetry from JSON format."""
        updates: Dict[str, Any] = {}

        if 'armed' in data:
            updates['armed'] = data['armed']
        if 'mode' in data:
            updates['mode'] = data['mode']
        if 'battery' in data:
            updates['battery_voltage'] = data['battery'].get('voltage', 0.0)
            updates['battery_current'] = data['battery'].get('current', 0.0)
            updates['battery_remaining'] = data['battery'].get('remaining', 0.0)
        if 'attitude' in data:
            updates['roll'] = data['attitude'].get('roll', 0.0)
            updates['pitch'] = data['attitude'].get('pitch', 0.0)
            updates['yaw'] = data['attitude'].get('yaw', 0.0)
        if 'position' in data:
            updates['lat'] = data['position'].get('lat', 0.0)
            updates['lon'] = data['position'].get('lon', 0.0)
            updates['altitude'] = data['position'].get('alt', 0.0)
        if 'velocity' in data:
            updates['ground_speed'] = data['velocity'].get('ground_speed', 0.0)
        if 'gps' in data:
            updates['satellites'] = data['gps'].get('satellites', 0)
            updates['gps_fix'] = data['gps'].get('fix_type', 0)

        if updates:
            self._update_fields(updates)

    def parse_mavlink_data(self, data: bytes) -> None:
        """Parse MAVLink binary telemetry data.

        Feeds raw bytes into pymavlink's incremental parser and dispatches
        each decoded message to the appropriate handler.
        """
        if self._mav is None:
            # Create a MAVLink parser instance (wire protocol v2)
            self._mav = mavutil.mavlink.MAVLink(None)
            self._mav.robust_parsing = True

        # Feed bytes to parser one at a time (pymavlink API)
        msgs = []
        for byte in data:
            try:
                msg = self._mav.parse_char(bytes([byte]))
                if msg is not None:
                    msgs.append(msg)
            except Exception:
                continue

        for msg in msgs:
            self._handle_mavlink_message(msg)

    def _handle_mavlink_message(self, msg: Any) -> None:
        """Dispatch a decoded MAVLink message to update telemetry fields."""
        msg_type = msg.get_type()

        if msg_type == 'HEARTBEAT':
            base_mode = msg.base_mode
            custom_mode = msg.custom_mode
            armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            mode_name = MAVLINK_MODE_MAP.get(custom_mode, f'MODE_{custom_mode}')
            self._update_fields({'armed': armed, 'mode': mode_name})

        elif msg_type == 'SYS_STATUS':
            self._update_fields({
                'battery_voltage': msg.voltage_battery / 1000.0,  # mV -> V
                'battery_current': msg.current_battery / 100.0,   # cA -> A
                'battery_remaining': float(msg.battery_remaining),  # %
            })

        elif msg_type == 'GPS_RAW_INT':
            self._update_fields({
                'lat': msg.lat / 1e7,
                'lon': msg.lon / 1e7,
                'altitude': msg.alt / 1000.0,  # mm -> m
                'satellites': msg.satellites_visible,
                'gps_fix': msg.fix_type,
                'ground_speed': msg.vel / 100.0 if msg.vel != 65535 else 0.0,
                'heading': msg.cog / 100.0 if msg.cog != 65535 else 0.0,
            })

        elif msg_type == 'ATTITUDE':
            self._update_fields({
                'roll': msg.roll,   # radians
                'pitch': msg.pitch,
                'yaw': msg.yaw,
            })

        elif msg_type == 'GLOBAL_POSITION_INT':
            self._update_fields({
                'lat': msg.lat / 1e7,
                'lon': msg.lon / 1e7,
                'altitude': msg.relative_alt / 1000.0,
                'heading': msg.hdg / 100.0 if msg.hdg != 65535 else 0.0,
            })

        elif msg_type == 'VFR_HUD':
            self._update_fields({
                'ground_speed': msg.groundspeed,
                'altitude': msg.alt,
                'heading': float(msg.heading),
            })

        elif msg_type == 'BATTERY_STATUS':
            voltages = [v for v in msg.voltages if v != 65535]
            voltage = sum(voltages) / 1000.0 if voltages else 0.0
            self._update_fields({
                'battery_voltage': voltage,
                'battery_current': msg.current_battery / 100.0,
                'battery_remaining': float(msg.battery_remaining),
            })

    def publish_telemetry(self) -> None:
        """Publish telemetry data as ROS2 messages."""
        try:
            current_time = self.get_clock().now().to_msg()
            td = self._get_telemetry_snapshot()

            # Battery state
            battery_msg = BatteryState()
            battery_msg.header.stamp = current_time
            battery_msg.voltage = td['battery_voltage']
            battery_msg.current = td['battery_current']
            battery_msg.percentage = td['battery_remaining']
            self.battery_pub.publish(battery_msg)

            # GPS
            gps_msg = NavSatFix()
            gps_msg.header.stamp = current_time
            gps_msg.header.frame_id = 'gps'
            gps_msg.latitude = td['lat']
            gps_msg.longitude = td['lon']
            gps_msg.altitude = td['altitude']
            gps_msg.status.status = td['gps_fix']
            self.gps_pub.publish(gps_msg)

            # Altitude
            altitude_msg = Float32()
            altitude_msg.data = td['altitude']
            self.altitude_pub.publish(altitude_msg)

            # Heading
            heading_msg = Float32()
            heading_msg.data = td['heading']
            self.heading_pub.publish(heading_msg)

            # Armed status
            armed_msg = Bool()
            armed_msg.data = td['armed']
            self.armed_pub.publish(armed_msg)

            # Flight mode
            mode_msg = String()
            mode_msg.data = td['mode']
            self.mode_pub.publish(mode_msg)

            # Status summary
            status_msg = String()
            status_msg.data = json.dumps(td)
            self.status_pub.publish(status_msg)

        except Exception as e:
            self.get_logger().error(f'Error publishing telemetry: {str(e)}')

    def destroy_node(self) -> None:
        """Clean up resources."""
        self.running = False
        if self.telemetry_socket:
            self.telemetry_socket.close()
        super().destroy_node()


def main(args: Optional[list] = None) -> None:
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
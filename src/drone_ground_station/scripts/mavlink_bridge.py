#!/usr/bin/env python3
"""
MAVLink Bridge for Drone Ground Station
Bridges communication between Crossflight and MAVLink protocol
Handles command sending and telemetry conversion
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32, Bool
from geometry_msgs.msg import Twist, PoseStamped
from pymavlink import mavutil


class MAVLinkBridge(Node):
    def __init__(self) -> None:
        super().__init__('mavlink_bridge')

        # Parameters
        self.declare_parameter('drone_ip', '192.168.4.1')
        self.declare_parameter('command_port', 14551)
        self.declare_parameter('connection_timeout', 5.0)

        self.drone_ip: str = self.get_parameter('drone_ip').value
        self.command_port: int = self.get_parameter('command_port').value
        self.connection_timeout: float = self.get_parameter('connection_timeout').value

        # Command socket
        self.command_socket: Optional[socket.socket] = None
        self.connected: bool = False

        # ROS2 Subscribers for commands
        self.setup_subscribers()

        # ROS2 Publishers for status
        self.connection_status_pub = self.create_publisher(
            Bool, 'drone/connection_status', 10
        )
        self.command_ack_pub = self.create_publisher(
            String, 'drone/command_ack', 10
        )

        # Connection management
        self.connection_timer = self.create_timer(2.0, self.check_connection)

        # Thread-safe command queue using deque (O(1) popleft)
        self.command_queue: deque[Dict[str, Any]] = deque(maxlen=100)
        self.command_lock = threading.Lock()

        # Start command sender thread
        self.command_thread = threading.Thread(
            target=self.command_sender_loop, daemon=True
        )
        self.command_thread.start()

        self.get_logger().info(
            f'MAVLink bridge initialized for {self.drone_ip}:{self.command_port}'
        )

    def setup_subscribers(self) -> None:
        """Setup ROS2 subscribers for receiving commands."""
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'drone/cmd_vel', self.cmd_vel_callback, 10)
        self.arm_sub = self.create_subscription(
            Bool, 'drone/arm', self.arm_callback, 10)
        self.takeoff_sub = self.create_subscription(
            Float32, 'drone/takeoff', self.takeoff_callback, 10)
        self.land_sub = self.create_subscription(
            Bool, 'drone/land', self.land_callback, 10)
        self.mode_sub = self.create_subscription(
            String, 'drone/set_mode', self.mode_callback, 10)
        self.goto_sub = self.create_subscription(
            PoseStamped, 'drone/goto', self.goto_callback, 10)

    def check_connection(self) -> None:
        """Check and maintain connection to drone."""
        if not self.connected:
            self.connect_to_drone()

        status_msg = Bool()
        status_msg.data = self.connected
        self.connection_status_pub.publish(status_msg)

    def connect_to_drone(self) -> None:
        """Establish connection to drone."""
        try:
            if self.command_socket:
                self.command_socket.close()

            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.settimeout(self.connection_timeout)
            self.command_socket.connect((self.drone_ip, self.command_port))
            self.connected = True

            self.get_logger().info(
                f'Connected to drone at {self.drone_ip}:{self.command_port}'
            )

        except Exception as e:
            self.connected = False
            self.get_logger().warn(f'Failed to connect to drone: {str(e)}')

    def send_command(self, command_data: Dict[str, Any]) -> None:
        """Add command to queue for sending."""
        with self.command_lock:
            self.command_queue.append(command_data)

    def command_sender_loop(self) -> None:
        """Main loop for sending commands to drone."""
        while rclpy.ok():
            try:
                command: Optional[Dict[str, Any]] = None
                if self.connected:
                    with self.command_lock:
                        if self.command_queue:
                            command = self.command_queue.popleft()

                if command is not None:
                    self.send_command_to_drone(command)

                time.sleep(0.1)  # 10Hz command rate

            except Exception as e:
                self.get_logger().error(f'Error in command sender loop: {str(e)}')
                time.sleep(1.0)

    def send_command_to_drone(self, command_data: Dict[str, Any]) -> None:
        """Send command to drone via socket."""
        try:
            if not self.connected:
                return

            command_json = json.dumps(command_data)
            command_bytes = command_json.encode('utf-8')
            self.command_socket.send(command_bytes + b'\n')

            self.get_logger().debug(f'Sent command: {command_data["type"]}')

            ack_msg = String()
            ack_msg.data = f'Command sent: {command_data["type"]}'
            self.command_ack_pub.publish(ack_msg)

        except Exception as e:
            self.get_logger().error(f'Error sending command: {str(e)}')
            self.connected = False

    def cmd_vel_callback(self, msg: Twist) -> None:
        """Handle velocity commands."""
        command: Dict[str, Any] = {
            'type': 'velocity',
            'linear': {
                'x': msg.linear.x,
                'y': msg.linear.y,
                'z': msg.linear.z
            },
            'angular': {
                'x': msg.angular.x,
                'y': msg.angular.y,
                'z': msg.angular.z
            },
            'timestamp': time.time()
        }
        self.send_command(command)

    def arm_callback(self, msg: Bool) -> None:
        """Handle arm/disarm commands."""
        command: Dict[str, Any] = {
            'type': 'arm',
            'armed': msg.data,
            'timestamp': time.time()
        }
        self.send_command(command)
        self.get_logger().info(f'Arm command: {msg.data}')

    def takeoff_callback(self, msg: Float32) -> None:
        """Handle takeoff commands."""
        command: Dict[str, Any] = {
            'type': 'takeoff',
            'altitude': msg.data,
            'timestamp': time.time()
        }
        self.send_command(command)
        self.get_logger().info(f'Takeoff command: {msg.data}m')

    def land_callback(self, msg: Bool) -> None:
        """Handle landing commands."""
        command: Dict[str, Any] = {
            'type': 'land',
            'timestamp': time.time()
        }
        self.send_command(command)
        self.get_logger().info('Land command')

    def mode_callback(self, msg: String) -> None:
        """Handle flight mode changes."""
        command: Dict[str, Any] = {
            'type': 'mode',
            'mode': msg.data,
            'timestamp': time.time()
        }
        self.send_command(command)
        self.get_logger().info(f'Mode change: {msg.data}')

    def goto_callback(self, msg: PoseStamped) -> None:
        """Handle goto position commands."""
        command: Dict[str, Any] = {
            'type': 'goto',
            'position': {
                'x': msg.pose.position.x,
                'y': msg.pose.position.y,
                'z': msg.pose.position.z
            },
            'orientation': {
                'x': msg.pose.orientation.x,
                'y': msg.pose.orientation.y,
                'z': msg.pose.orientation.z,
                'w': msg.pose.orientation.w
            },
            'timestamp': time.time()
        }
        self.send_command(command)
        self.get_logger().info(
            f'Goto command: ({msg.pose.position.x}, '
            f'{msg.pose.position.y}, {msg.pose.position.z})'
        )

    def destroy_node(self) -> None:
        """Clean up resources."""
        self.connected = False
        if self.command_socket:
            self.command_socket.close()
        super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)

    try:
        mavlink_bridge = MAVLinkBridge()
        rclpy.spin(mavlink_bridge)
    except KeyboardInterrupt:
        pass
    finally:
        if 'mavlink_bridge' in locals():
            mavlink_bridge.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
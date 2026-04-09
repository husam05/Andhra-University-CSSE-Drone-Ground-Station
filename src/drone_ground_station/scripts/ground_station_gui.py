#!/usr/bin/env python3
"""
Ground Station GUI for Drone Control
Provides graphical interface for video monitoring, telemetry display, and drone control
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np
import rclpy
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image as PILImage, ImageTk
from rclpy.node import Node
from sensor_msgs.msg import Image, BatteryState, NavSatFix
from std_msgs.msg import String, Float32, Bool
from geometry_msgs.msg import Twist, PoseStamped
from cv_bridge import CvBridge


class GroundStationGUI(Node):
    def __init__(self) -> None:
        super().__init__('ground_station_gui')

        # ROS2 setup
        self.bridge = CvBridge()
        self.setup_subscribers()
        self.setup_publishers()

        # Thread-safe data storage
        self._data_lock = threading.Lock()
        self.current_image: Optional[np.ndarray] = None
        self.telemetry_data: Dict[str, Any] = {
            'armed': False,
            'mode': 'UNKNOWN',
            'battery_voltage': 0.0,
            'battery_percentage': 0.0,
            'altitude': 0.0,
            'ground_speed': 0.0,
            'gps_lat': 0.0,
            'gps_lon': 0.0,
            'gps_satellites': 0,
            'connection_status': False
        }

        # GUI setup
        self.setup_gui()

        # Start GUI update timer
        self.gui_timer = self.create_timer(0.1, self.update_gui)  # 10Hz

        self.get_logger().info('Ground Station GUI initialized')

    def setup_subscribers(self) -> None:
        """Setup ROS2 subscribers."""
        self.image_sub = self.create_subscription(
            Image, 'drone/camera/image_raw', self.image_callback, 10)
        self.battery_sub = self.create_subscription(
            BatteryState, 'drone/battery', self.battery_callback, 10)
        self.gps_sub = self.create_subscription(
            NavSatFix, 'drone/gps', self.gps_callback, 10)
        self.altitude_sub = self.create_subscription(
            Float32, 'drone/altitude', self.altitude_callback, 10)
        self.armed_sub = self.create_subscription(
            Bool, 'drone/armed', self.armed_callback, 10)
        self.mode_sub = self.create_subscription(
            String, 'drone/mode', self.mode_callback, 10)
        self.connection_sub = self.create_subscription(
            Bool, 'drone/connection_status', self.connection_callback, 10)
        self.status_sub = self.create_subscription(
            String, 'drone/status', self.status_callback, 10)

    def setup_publishers(self) -> None:
        """Setup ROS2 publishers."""
        self.cmd_vel_pub = self.create_publisher(Twist, 'drone/cmd_vel', 10)
        self.arm_pub = self.create_publisher(Bool, 'drone/arm', 10)
        self.takeoff_pub = self.create_publisher(Float32, 'drone/takeoff', 10)
        self.land_pub = self.create_publisher(Bool, 'drone/land', 10)
        self.mode_pub = self.create_publisher(String, 'drone/set_mode', 10)
        self.goto_pub = self.create_publisher(PoseStamped, 'drone/goto', 10)

    def setup_gui(self) -> None:
        """Setup the main GUI window."""
        self.root = tk.Tk()
        self.root.title('Drone Ground Station')
        self.root.geometry('1200x800')
        self.root.configure(bg='#2c3e50')

        self.create_video_frame()
        self.create_telemetry_frame()
        self.create_control_frame()
        self.create_status_frame()

        self.root.grid_rowconfigure(0, weight=3)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)

    def create_video_frame(self) -> None:
        """Create video display frame."""
        self.video_frame = tk.Frame(self.root, bg='#34495e', relief='raised', bd=2)
        self.video_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')

        self.video_label = tk.Label(
            self.video_frame, text='Video Feed',
            bg='#34495e', fg='white', font=('Arial', 12)
        )
        self.video_label.pack(pady=5)

        self.video_display = tk.Label(self.video_frame, bg='black')
        self.video_display.pack(expand=True, fill='both', padx=10, pady=10)

    def create_telemetry_frame(self) -> None:
        """Create telemetry display frame."""
        self.telemetry_frame = tk.Frame(
            self.root, bg='#34495e', relief='raised', bd=2
        )
        self.telemetry_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')

        tk.Label(
            self.telemetry_frame, text='Telemetry', bg='#34495e',
            fg='white', font=('Arial', 14, 'bold')
        ).pack(pady=5)

        self.telemetry_vars: Dict[str, tk.StringVar] = {}
        telemetry_items = [
            ('Connection', 'connection_status'),
            ('Armed', 'armed'),
            ('Mode', 'mode'),
            ('Battery', 'battery_percentage'),
            ('Voltage', 'battery_voltage'),
            ('Altitude', 'altitude'),
            ('Speed', 'ground_speed'),
            ('GPS Lat', 'gps_lat'),
            ('GPS Lon', 'gps_lon'),
            ('Satellites', 'gps_satellites')
        ]

        for label, key in telemetry_items:
            frame = tk.Frame(self.telemetry_frame, bg='#34495e')
            frame.pack(fill='x', padx=10, pady=2)

            tk.Label(
                frame, text=f'{label}:', bg='#34495e', fg='white',
                font=('Arial', 10), width=12, anchor='w'
            ).pack(side='left')

            var = tk.StringVar(value='--')
            self.telemetry_vars[key] = var
            tk.Label(
                frame, textvariable=var, bg='#34495e', fg='#3498db',
                font=('Arial', 10, 'bold'), anchor='w'
            ).pack(side='left')

    def create_control_frame(self) -> None:
        """Create control buttons frame."""
        self.control_frame = tk.Frame(
            self.root, bg='#34495e', relief='raised', bd=2
        )
        self.control_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')

        tk.Label(
            self.control_frame, text='Flight Controls', bg='#34495e',
            fg='white', font=('Arial', 14, 'bold')
        ).pack(pady=5)

        button_frame = tk.Frame(self.control_frame, bg='#34495e')
        button_frame.pack(expand=True, fill='both', padx=10, pady=10)

        self.arm_button = tk.Button(
            button_frame, text='ARM', bg='#e74c3c', fg='white',
            font=('Arial', 12, 'bold'), command=self.toggle_arm
        )
        self.arm_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        tk.Button(
            button_frame, text='TAKEOFF', bg='#27ae60', fg='white',
            font=('Arial', 12, 'bold'), command=self.takeoff
        ).grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        tk.Button(
            button_frame, text='LAND', bg='#f39c12', fg='white',
            font=('Arial', 12, 'bold'), command=self.land
        ).grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        tk.Button(
            button_frame, text='EMERGENCY', bg='#c0392b', fg='white',
            font=('Arial', 12, 'bold'), command=self.emergency_stop
        ).grid(row=0, column=3, padx=5, pady=5, sticky='ew')

        for i in range(4):
            button_frame.grid_columnconfigure(i, weight=1)

        # Movement controls
        move_frame = tk.Frame(self.control_frame, bg='#34495e')
        move_frame.pack(pady=10)

        tk.Label(
            move_frame, text='Movement Controls', bg='#34495e',
            fg='white', font=('Arial', 12, 'bold')
        ).pack()

        controls_grid = tk.Frame(move_frame, bg='#34495e')
        controls_grid.pack(pady=5)

        tk.Button(controls_grid, text='\u2191', font=('Arial', 16), width=3,
                  command=lambda: self.send_velocity(0.5, 0, 0, 0)).grid(row=0, column=1)
        tk.Button(controls_grid, text='\u2190', font=('Arial', 16), width=3,
                  command=lambda: self.send_velocity(0, 0.5, 0, 0)).grid(row=1, column=0)
        tk.Button(controls_grid, text='STOP', font=('Arial', 10), width=5,
                  command=lambda: self.send_velocity(0, 0, 0, 0)).grid(row=1, column=1)
        tk.Button(controls_grid, text='\u2192', font=('Arial', 16), width=3,
                  command=lambda: self.send_velocity(0, -0.5, 0, 0)).grid(row=1, column=2)
        tk.Button(controls_grid, text='\u2193', font=('Arial', 16), width=3,
                  command=lambda: self.send_velocity(-0.5, 0, 0, 0)).grid(row=2, column=1)

        alt_frame = tk.Frame(move_frame, bg='#34495e')
        alt_frame.pack(pady=5)

        tk.Button(alt_frame, text='UP', font=('Arial', 12), width=8,
                  command=lambda: self.send_velocity(0, 0, 0.5, 0)).pack(side='left', padx=2)
        tk.Button(alt_frame, text='DOWN', font=('Arial', 12), width=8,
                  command=lambda: self.send_velocity(0, 0, -0.5, 0)).pack(side='left', padx=2)

    def create_status_frame(self) -> None:
        """Create status display frame."""
        self.status_frame = tk.Frame(
            self.root, bg='#34495e', relief='raised', bd=2
        )
        self.status_frame.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')

        tk.Label(
            self.status_frame, text='System Status', bg='#34495e',
            fg='white', font=('Arial', 14, 'bold')
        ).pack(pady=5)

        self.status_text = tk.Text(
            self.status_frame, height=8, bg='#2c3e50',
            fg='#ecf0f1', font=('Courier', 9)
        )
        self.status_text.pack(expand=True, fill='both', padx=10, pady=10)

        scrollbar = tk.Scrollbar(self.status_text)
        scrollbar.pack(side='right', fill='y')
        self.status_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_text.yview)

    # -- ROS2 callbacks (called from ROS2 spin thread) --

    def image_callback(self, msg: Image) -> None:
        """Handle incoming video frames."""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            with self._data_lock:
                self.current_image = cv_image
        except Exception as e:
            self.get_logger().error(f'Error processing image: {str(e)}')

    def battery_callback(self, msg: BatteryState) -> None:
        """Handle battery telemetry."""
        with self._data_lock:
            self.telemetry_data['battery_voltage'] = msg.voltage
            self.telemetry_data['battery_percentage'] = msg.percentage

    def gps_callback(self, msg: NavSatFix) -> None:
        """Handle GPS telemetry."""
        with self._data_lock:
            self.telemetry_data['gps_lat'] = msg.latitude
            self.telemetry_data['gps_lon'] = msg.longitude

    def altitude_callback(self, msg: Float32) -> None:
        """Handle altitude telemetry."""
        with self._data_lock:
            self.telemetry_data['altitude'] = msg.data

    def armed_callback(self, msg: Bool) -> None:
        """Handle armed status."""
        with self._data_lock:
            self.telemetry_data['armed'] = msg.data

    def mode_callback(self, msg: String) -> None:
        """Handle flight mode."""
        with self._data_lock:
            self.telemetry_data['mode'] = msg.data

    def connection_callback(self, msg: Bool) -> None:
        """Handle connection status."""
        with self._data_lock:
            self.telemetry_data['connection_status'] = msg.data

    def status_callback(self, msg: String) -> None:
        """Handle status updates."""
        try:
            status_data = json.loads(msg.data)
            with self._data_lock:
                for key, value in status_data.items():
                    if key in self.telemetry_data:
                        self.telemetry_data[key] = value
        except json.JSONDecodeError:
            pass

    # -- GUI update (called from ROS2 timer, runs in main thread via Tkinter) --

    def update_gui(self) -> None:
        """Update GUI elements."""
        try:
            # Snapshot current state under lock
            with self._data_lock:
                image = self.current_image.copy() if self.current_image is not None else None
                td = dict(self.telemetry_data)

            # Update video display
            if image is not None:
                height, width = image.shape[:2]
                display_width = 640
                display_height = int(height * display_width / width)

                resized_image = cv2.resize(image, (display_width, display_height))
                rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
                pil_image = PILImage.fromarray(rgb_image)
                photo = ImageTk.PhotoImage(pil_image)

                self.video_display.configure(image=photo)
                self.video_display.image = photo

            # Update telemetry display
            for key, var in self.telemetry_vars.items():
                value = td.get(key, '--')
                if isinstance(value, float):
                    if key == 'battery_voltage':
                        var.set(f'{value:.2f}V')
                    elif key == 'battery_percentage':
                        var.set(f'{value:.1f}%')
                    elif key == 'altitude':
                        var.set(f'{value:.1f}m')
                    elif key == 'ground_speed':
                        var.set(f'{value:.1f}m/s')
                    elif key in ('gps_lat', 'gps_lon'):
                        var.set(f'{value:.6f}')
                    else:
                        var.set(f'{value:.2f}')
                elif isinstance(value, bool):
                    var.set('YES' if value else 'NO')
                else:
                    var.set(str(value))

            # Update arm button color
            if td['armed']:
                self.arm_button.configure(text='DISARM', bg='#e74c3c')
            else:
                self.arm_button.configure(text='ARM', bg='#27ae60')

        except Exception as e:
            self.get_logger().error(f'Error updating GUI: {str(e)}')

    # -- Command methods --

    def toggle_arm(self) -> None:
        """Toggle arm/disarm."""
        with self._data_lock:
            currently_armed = self.telemetry_data['armed']
        msg = Bool()
        msg.data = not currently_armed
        self.arm_pub.publish(msg)
        self.log_status(f'Arm command: {msg.data}')

    def takeoff(self) -> None:
        """Takeoff command."""
        msg = Float32()
        msg.data = 2.0
        self.takeoff_pub.publish(msg)
        self.log_status('Takeoff command sent')

    def land(self) -> None:
        """Land command."""
        msg = Bool()
        msg.data = True
        self.land_pub.publish(msg)
        self.log_status('Land command sent')

    def emergency_stop(self) -> None:
        """Emergency stop."""
        msg = Bool()
        msg.data = False
        self.arm_pub.publish(msg)
        self.send_velocity(0, 0, 0, 0)
        self.log_status('EMERGENCY STOP ACTIVATED')

    def send_velocity(self, x: float, y: float, z: float, yaw: float) -> None:
        """Send velocity command."""
        msg = Twist()
        msg.linear.x = x
        msg.linear.y = y
        msg.linear.z = z
        msg.angular.z = yaw
        self.cmd_vel_pub.publish(msg)

    def log_status(self, message: str) -> None:
        """Log status message."""
        timestamp = time.strftime('%H:%M:%S')
        log_message = f'[{timestamp}] {message}\n'
        self.status_text.insert(tk.END, log_message)
        self.status_text.see(tk.END)

    def run_gui(self) -> None:
        """Run the GUI main loop."""
        self.root.mainloop()

    def destroy_node(self) -> None:
        """Clean up resources."""
        if hasattr(self, 'root'):
            self.root.quit()
        super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)

    try:
        gui_node = GroundStationGUI()

        ros_thread = threading.Thread(target=lambda: rclpy.spin(gui_node))
        ros_thread.daemon = True
        ros_thread.start()

        gui_node.run_gui()

    except KeyboardInterrupt:
        pass
    finally:
        if 'gui_node' in locals():
            gui_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
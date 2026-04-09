#!/usr/bin/env python3
"""
Telemetry Bridge for Raspberry Pi Drone
Communicates with Crossflight via UART and forwards telemetry to ground station
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import struct
import sys
import time
import threading
from threading import Thread, Event
from typing import Any, Dict, Optional

import serial
from pymavlink import mavutil


class TelemetryBridge:
    def __init__(self, config_file: str = 'config.json') -> None:
        self.config: Dict[str, Any] = self.load_config(config_file)
        self.running: bool = False
        self.serial_connection: Optional[serial.Serial] = None
        self.telemetry_socket: Optional[socket.socket] = None
        self.command_socket: Optional[socket.socket] = None
        self.stop_event = Event()

        # Thread-safe telemetry data storage
        self._telemetry_lock = threading.Lock()
        self.telemetry_data: Dict[str, Any] = {
            'timestamp': 0,
            'armed': False,
            'mode': 'UNKNOWN',
            'battery': {
                'voltage': 0.0,
                'current': 0.0,
                'remaining': 0.0
            },
            'attitude': {
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.0
            },
            'position': {
                'lat': 0.0,
                'lon': 0.0,
                'alt': 0.0
            },
            'velocity': {
                'ground_speed': 0.0,
                'vertical_speed': 0.0
            },
            'gps': {
                'satellites': 0,
                'fix_type': 0,
                'hdop': 0.0
            },
            'sensors': {
                'gyro': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'accel': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'mag': {'x': 0.0, 'y': 0.0, 'z': 0.0}
            }
        }

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def _update_telemetry(self, path: str, value: Any) -> None:
        """Thread-safe update of a nested telemetry field.

        Args:
            path: Dot-separated key path (e.g. 'battery.voltage').
            value: New value to set.
        """
        keys = path.split('.')
        with self._telemetry_lock:
            target = self.telemetry_data
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value

    def _get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of current telemetry data (thread-safe)."""
        import copy
        with self._telemetry_lock:
            return copy.deepcopy(self.telemetry_data)

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        default_config: Dict[str, Any] = {
            'ground_station_ip': '192.168.4.19',
            'telemetry_port': 14550,
            'command_port': 14551,
            'serial_port': '/dev/ttyAMA0',
            'serial_baudrate': 115200,
            'telemetry_rate': 10,
            'protocol': 'msp',
            'timeout': 1.0
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                default_config.update(config)
            return default_config
        except Exception as e:
            logging.warning(f'Could not load config file: {e}. Using defaults.')
            return default_config

    def setup_serial_connection(self) -> bool:
        """Setup serial connection to Crossflight."""
        try:
            self.serial_connection = serial.Serial(
                port=self.config['serial_port'],
                baudrate=self.config['serial_baudrate'],
                timeout=self.config['timeout'],
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )

            self.logger.info(
                f'Serial connection established on {self.config["serial_port"]} '
                f'at {self.config["serial_baudrate"]} baud'
            )
            return True

        except Exception as e:
            self.logger.error(f'Failed to setup serial connection: {e}')
            return False

    def setup_network_sockets(self) -> bool:
        """Setup UDP sockets for telemetry and command communication."""
        try:
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.command_socket.bind(('', self.config['command_port']))
            self.command_socket.listen(1)

            self.logger.info(
                f'Network sockets setup - Telemetry: UDP, '
                f'Commands: TCP:{self.config["command_port"]}'
            )
            return True

        except Exception as e:
            self.logger.error(f'Failed to setup network sockets: {e}')
            return False

    def read_crossflight_telemetry(self) -> None:
        """Read telemetry data from Crossflight via MSP protocol."""
        while self.running and not self.stop_event.is_set():
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    self.request_msp_data()
                    time.sleep(1.0 / self.config['telemetry_rate'])
                else:
                    time.sleep(1.0)

            except Exception as e:
                self.logger.error(f'Error reading telemetry: {e}')
                time.sleep(1.0)

    def request_msp_data(self) -> None:
        """Request MSP data from Crossflight."""
        try:
            msp_requests = [
                100,  # MSP_STATUS
                102,  # MSP_RAW_IMU
                103,  # MSP_SERVO
                104,  # MSP_MOTOR
                105,  # MSP_RC
                106,  # MSP_RAW_GPS
                108,  # MSP_ATTITUDE
                109,  # MSP_ALTITUDE
                110,  # MSP_ANALOG
            ]

            for msg_id in msp_requests:
                self.send_msp_request(msg_id)
                response = self.read_msp_response()
                if response:
                    self.parse_msp_response(msg_id, response)
                time.sleep(0.01)

        except Exception as e:
            self.logger.error(f'Error requesting MSP data: {e}')

    def send_msp_request(self, msg_id: int) -> None:
        """Send MSP request to Crossflight."""
        try:
            data_length = 0
            checksum = data_length ^ msg_id

            message = bytearray()
            message.extend(b'$M<')
            message.append(data_length)
            message.append(msg_id)
            message.append(checksum)

            self.serial_connection.write(message)

        except Exception as e:
            self.logger.error(f'Error sending MSP request {msg_id}: {e}')

    def read_msp_response(self) -> Optional[Dict[str, Any]]:
        """Read MSP response from Crossflight."""
        try:
            header = self.serial_connection.read(3)
            if header != b'$M>':
                return None

            data_length = self.serial_connection.read(1)[0]
            msg_id = self.serial_connection.read(1)[0]
            data = self.serial_connection.read(data_length) if data_length > 0 else b''
            checksum = self.serial_connection.read(1)[0]

            calculated_checksum = data_length ^ msg_id
            for byte in data:
                calculated_checksum ^= byte

            if checksum == calculated_checksum:
                return {'msg_id': msg_id, 'data': data}
            else:
                self.logger.warning(f'MSP checksum mismatch for message {msg_id}')
                return None

        except Exception as e:
            self.logger.error(f'Error reading MSP response: {e}')
            return None

    def parse_msp_response(self, msg_id: int, response: Dict[str, Any]) -> None:
        """Parse MSP response and update telemetry data (thread-safe)."""
        try:
            data = response['data']

            if msg_id == 100:  # MSP_STATUS
                if len(data) >= 11:
                    flags = struct.unpack('<I', data[6:10])[0]
                    self._update_telemetry('armed', bool(flags & 1))

            elif msg_id == 102:  # MSP_RAW_IMU
                if len(data) >= 18:
                    acc_x = struct.unpack('<h', data[0:2])[0]
                    acc_y = struct.unpack('<h', data[2:4])[0]
                    acc_z = struct.unpack('<h', data[4:6])[0]
                    gyro_x = struct.unpack('<h', data[6:8])[0]
                    gyro_y = struct.unpack('<h', data[8:10])[0]
                    gyro_z = struct.unpack('<h', data[10:12])[0]
                    mag_x = struct.unpack('<h', data[12:14])[0]
                    mag_y = struct.unpack('<h', data[14:16])[0]
                    mag_z = struct.unpack('<h', data[16:18])[0]

                    with self._telemetry_lock:
                        self.telemetry_data['sensors']['accel'] = {
                            'x': acc_x, 'y': acc_y, 'z': acc_z
                        }
                        self.telemetry_data['sensors']['gyro'] = {
                            'x': gyro_x, 'y': gyro_y, 'z': gyro_z
                        }
                        self.telemetry_data['sensors']['mag'] = {
                            'x': mag_x, 'y': mag_y, 'z': mag_z
                        }

            elif msg_id == 106:  # MSP_RAW_GPS
                if len(data) >= 16:
                    fix = data[0]
                    num_sat = data[1]
                    lat = struct.unpack('<i', data[2:6])[0] / 10000000.0
                    lon = struct.unpack('<i', data[6:10])[0] / 10000000.0
                    alt = struct.unpack('<H', data[10:12])[0]
                    speed = struct.unpack('<H', data[12:14])[0]

                    with self._telemetry_lock:
                        self.telemetry_data['gps']['fix_type'] = fix
                        self.telemetry_data['gps']['satellites'] = num_sat
                        self.telemetry_data['position']['lat'] = lat
                        self.telemetry_data['position']['lon'] = lon
                        self.telemetry_data['position']['alt'] = alt
                        self.telemetry_data['velocity']['ground_speed'] = speed / 100.0

            elif msg_id == 108:  # MSP_ATTITUDE
                if len(data) >= 6:
                    roll = struct.unpack('<h', data[0:2])[0] / 10.0
                    pitch = struct.unpack('<h', data[2:4])[0] / 10.0
                    yaw = struct.unpack('<h', data[4:6])[0]

                    with self._telemetry_lock:
                        self.telemetry_data['attitude']['roll'] = roll
                        self.telemetry_data['attitude']['pitch'] = pitch
                        self.telemetry_data['attitude']['yaw'] = yaw

            elif msg_id == 110:  # MSP_ANALOG
                if len(data) >= 7:
                    vbat = data[0] / 10.0
                    amperage = struct.unpack('<H', data[5:7])[0]

                    with self._telemetry_lock:
                        self.telemetry_data['battery']['voltage'] = vbat
                        self.telemetry_data['battery']['current'] = amperage / 100.0

            self._update_telemetry('timestamp', time.time())

        except Exception as e:
            self.logger.error(f'Error parsing MSP response {msg_id}: {e}')

    def send_telemetry_to_ground_station(self) -> None:
        """Send telemetry data to ground station."""
        while self.running and not self.stop_event.is_set():
            try:
                if self.telemetry_socket:
                    snapshot = self._get_telemetry_snapshot()
                    telemetry_json = json.dumps(snapshot)
                    telemetry_bytes = telemetry_json.encode('utf-8')

                    self.telemetry_socket.sendto(
                        telemetry_bytes,
                        (self.config['ground_station_ip'],
                         self.config['telemetry_port'])
                    )

                time.sleep(1.0 / self.config['telemetry_rate'])

            except Exception as e:
                self.logger.error(f'Error sending telemetry: {e}')
                time.sleep(1.0)

    def handle_ground_station_commands(self) -> None:
        """Handle commands from ground station."""
        while self.running and not self.stop_event.is_set():
            try:
                if self.command_socket:
                    self.command_socket.settimeout(1.0)
                    try:
                        client_socket, addr = self.command_socket.accept()
                        self.logger.info(f'Command connection from {addr}')
                        self.process_client_commands(client_socket)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.logger.error(
                            f'Error accepting command connection: {e}'
                        )

            except Exception as e:
                self.logger.error(f'Error in command handler: {e}')
                time.sleep(1.0)

    def process_client_commands(self, client_socket: socket.socket) -> None:
        """Process commands from connected client."""
        try:
            client_socket.settimeout(1.0)
            buffer = b''

            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    buffer += data

                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            try:
                                command = json.loads(line.decode('utf-8'))
                                self.execute_command(command)
                            except json.JSONDecodeError as e:
                                self.logger.error(
                                    f'Invalid JSON command: {e}'
                                )

                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f'Error receiving command: {e}')
                    break

        finally:
            client_socket.close()

    def execute_command(self, command: Dict[str, Any]) -> None:
        """Execute received command."""
        try:
            cmd_type = command.get('type')
            self.logger.info(f'Executing command: {cmd_type}')

            if cmd_type == 'arm':
                self.send_arm_command(command.get('armed', False))
            elif cmd_type == 'velocity':
                self.send_velocity_command(command)
            elif cmd_type == 'mode':
                self.send_mode_command(command.get('mode'))
            elif cmd_type == 'takeoff':
                self.send_takeoff_command(command.get('altitude', 2.0))
            elif cmd_type == 'land':
                self.send_land_command()
            else:
                self.logger.warning(f'Unknown command type: {cmd_type}')

        except Exception as e:
            self.logger.error(f'Error executing command: {e}')

    def send_arm_command(self, armed: bool) -> None:
        """Send arm/disarm command to Crossflight."""
        self.logger.info(f'Arm command: {armed}')

    def send_velocity_command(self, command: Dict[str, Any]) -> None:
        """Send velocity command to Crossflight."""
        linear = command.get('linear', {})
        angular = command.get('angular', {})
        self.logger.info(f'Velocity command: linear={linear}, angular={angular}')

    def send_mode_command(self, mode: Optional[str]) -> None:
        """Send flight mode command to Crossflight."""
        self.logger.info(f'Mode command: {mode}')

    def send_takeoff_command(self, altitude: float) -> None:
        """Send takeoff command to Crossflight."""
        self.logger.info(f'Takeoff command: {altitude}m')

    def send_land_command(self) -> None:
        """Send land command to Crossflight."""
        self.logger.info('Land command')

    def signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.logger.info(f'Received signal {signum}, shutting down...')
        self.stop()
        sys.exit(0)

    def start(self) -> bool:
        """Start telemetry bridge."""
        self.logger.info('Starting telemetry bridge...')

        if not self.setup_serial_connection():
            return False

        if not self.setup_network_sockets():
            return False

        self.running = True

        threads = [
            Thread(target=self.read_crossflight_telemetry, name='TelemetryReader'),
            Thread(target=self.send_telemetry_to_ground_station, name='TelemetrySender'),
            Thread(target=self.handle_ground_station_commands, name='CommandHandler')
        ]

        for thread in threads:
            thread.daemon = True
            thread.start()

        self.logger.info('Telemetry bridge started successfully')
        return True

    def stop(self) -> None:
        """Stop telemetry bridge."""
        self.logger.info('Stopping telemetry bridge...')
        self.running = False
        self.stop_event.set()

        if self.serial_connection:
            self.serial_connection.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()
        if self.command_socket:
            self.command_socket.close()

        self.logger.info('Telemetry bridge stopped')

    def run(self) -> bool:
        """Main run loop."""
        if not self.start():
            return False

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Keyboard interrupt received')
        finally:
            self.stop()

        return True


def main() -> None:
    bridge = TelemetryBridge()
    bridge.run()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Telemetry Bridge for Raspberry Pi Drone
Communicates with Crossflight via UART and forwards telemetry to ground station
"""

import serial
import socket
import json
import time
import threading
import logging
import signal
import sys
import struct
from threading import Thread, Event
from pymavlink import mavutil

class TelemetryBridge:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.running = False
        self.serial_connection = None
        self.telemetry_socket = None
        self.command_socket = None
        self.stop_event = Event()
        
        # Telemetry data storage
        self.telemetry_data = {
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
    
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            'ground_station_ip': '192.168.4.19',
            'telemetry_port': 14550,
            'command_port': 14551,
            'serial_port': '/dev/ttyAMA0',
            'serial_baudrate': 115200,
            'telemetry_rate': 10,  # Hz
            'protocol': 'msp',  # msp or mavlink
            'timeout': 1.0
        }
        
        try:
            import os
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                default_config.update(config)
            return default_config
        except Exception as e:
            self.logger.warning(f'Could not load config file: {e}. Using defaults.')
            return default_config
    
    def setup_serial_connection(self):
        """Setup serial connection to Crossflight"""
        try:
            self.serial_connection = serial.Serial(
                port=self.config['serial_port'],
                baudrate=self.config['serial_baudrate'],
                timeout=self.config['timeout'],
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            self.logger.info(f'Serial connection established on {self.config["serial_port"]} at {self.config["serial_baudrate"]} baud')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to setup serial connection: {e}')
            return False
    
    def setup_network_sockets(self):
        """Setup UDP sockets for telemetry and command communication"""
        try:
            # Telemetry socket (send to ground station)
            self.telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Command socket (receive from ground station)
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.command_socket.bind(('', self.config['command_port']))
            self.command_socket.listen(1)
            
            self.logger.info(f'Network sockets setup - Telemetry: UDP, Commands: TCP:{self.config["command_port"]}')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to setup network sockets: {e}')
            return False
    
    def read_crossflight_telemetry(self):
        """Read telemetry data from Crossflight via MSP protocol"""
        while self.running and not self.stop_event.is_set():
            try:
                if self.serial_connection and self.serial_connection.is_open:
                    # Request various MSP messages
                    self.request_msp_data()
                    time.sleep(1.0 / self.config['telemetry_rate'])
                else:
                    time.sleep(1.0)
                    
            except Exception as e:
                self.logger.error(f'Error reading telemetry: {e}')
                time.sleep(1.0)
    
    def request_msp_data(self):
        """Request MSP data from Crossflight"""
        try:
            # MSP message IDs for Crossflight
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
                time.sleep(0.01)  # Small delay between requests
                
        except Exception as e:
            self.logger.error(f'Error requesting MSP data: {e}')
    
    def send_msp_request(self, msg_id):
        """Send MSP request to Crossflight"""
        try:
            # MSP v1 protocol: $M< + data_length + msg_id + data + checksum
            data_length = 0
            checksum = data_length ^ msg_id
            
            message = bytearray()
            message.extend(b'$M<')  # MSP header
            message.append(data_length)
            message.append(msg_id)
            message.append(checksum)
            
            self.serial_connection.write(message)
            
        except Exception as e:
            self.logger.error(f'Error sending MSP request {msg_id}: {e}')
    
    def read_msp_response(self):
        """Read MSP response from Crossflight"""
        try:
            # Wait for MSP header
            header = self.serial_connection.read(3)
            if header != b'$M>':
                return None
            
            # Read data length
            data_length = self.serial_connection.read(1)[0]
            
            # Read message ID
            msg_id = self.serial_connection.read(1)[0]
            
            # Read data
            data = self.serial_connection.read(data_length) if data_length > 0 else b''
            
            # Read checksum
            checksum = self.serial_connection.read(1)[0]
            
            # Verify checksum
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
    
    def parse_msp_response(self, msg_id, response):
        """Parse MSP response and update telemetry data"""
        try:
            data = response['data']
            
            if msg_id == 100:  # MSP_STATUS
                if len(data) >= 11:
                    cycle_time = struct.unpack('<H', data[0:2])[0]
                    i2c_errors = struct.unpack('<H', data[2:4])[0]
                    sensors = struct.unpack('<H', data[4:6])[0]
                    flags = struct.unpack('<I', data[6:10])[0]
                    current_set = data[10]
                    
                    self.telemetry_data['armed'] = bool(flags & 1)
                    
            elif msg_id == 102:  # MSP_RAW_IMU
                if len(data) >= 18:
                    # Accelerometer (raw values)
                    acc_x = struct.unpack('<h', data[0:2])[0]
                    acc_y = struct.unpack('<h', data[2:4])[0]
                    acc_z = struct.unpack('<h', data[4:6])[0]
                    
                    # Gyroscope (raw values)
                    gyro_x = struct.unpack('<h', data[6:8])[0]
                    gyro_y = struct.unpack('<h', data[8:10])[0]
                    gyro_z = struct.unpack('<h', data[10:12])[0]
                    
                    # Magnetometer (raw values)
                    mag_x = struct.unpack('<h', data[12:14])[0]
                    mag_y = struct.unpack('<h', data[14:16])[0]
                    mag_z = struct.unpack('<h', data[16:18])[0]
                    
                    self.telemetry_data['sensors']['accel'] = {'x': acc_x, 'y': acc_y, 'z': acc_z}
                    self.telemetry_data['sensors']['gyro'] = {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
                    self.telemetry_data['sensors']['mag'] = {'x': mag_x, 'y': mag_y, 'z': mag_z}
                    
            elif msg_id == 106:  # MSP_RAW_GPS
                if len(data) >= 16:
                    fix = data[0]
                    num_sat = data[1]
                    lat = struct.unpack('<i', data[2:6])[0] / 10000000.0
                    lon = struct.unpack('<i', data[6:10])[0] / 10000000.0
                    alt = struct.unpack('<H', data[10:12])[0]
                    speed = struct.unpack('<H', data[12:14])[0]
                    ground_course = struct.unpack('<H', data[14:16])[0]
                    
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
                    
                    self.telemetry_data['attitude']['roll'] = roll
                    self.telemetry_data['attitude']['pitch'] = pitch
                    self.telemetry_data['attitude']['yaw'] = yaw
                    
            elif msg_id == 110:  # MSP_ANALOG
                if len(data) >= 7:
                    vbat = data[0] / 10.0
                    power_meter_sum = struct.unpack('<H', data[1:3])[0]
                    rssi = struct.unpack('<H', data[3:5])[0]
                    amperage = struct.unpack('<H', data[5:7])[0]
                    
                    self.telemetry_data['battery']['voltage'] = vbat
                    self.telemetry_data['battery']['current'] = amperage / 100.0
                    
            # Update timestamp
            self.telemetry_data['timestamp'] = time.time()
            
        except Exception as e:
            self.logger.error(f'Error parsing MSP response {msg_id}: {e}')
    
    def send_telemetry_to_ground_station(self):
        """Send telemetry data to ground station"""
        while self.running and not self.stop_event.is_set():
            try:
                if self.telemetry_socket:
                    # Convert telemetry to JSON
                    telemetry_json = json.dumps(self.telemetry_data)
                    telemetry_bytes = telemetry_json.encode('utf-8')
                    
                    # Send to ground station
                    self.telemetry_socket.sendto(
                        telemetry_bytes,
                        (self.config['ground_station_ip'], self.config['telemetry_port'])
                    )
                    
                time.sleep(1.0 / self.config['telemetry_rate'])
                
            except Exception as e:
                self.logger.error(f'Error sending telemetry: {e}')
                time.sleep(1.0)
    
    def handle_ground_station_commands(self):
        """Handle commands from ground station"""
        while self.running and not self.stop_event.is_set():
            try:
                if self.command_socket:
                    # Accept connection from ground station
                    self.command_socket.settimeout(1.0)
                    try:
                        client_socket, addr = self.command_socket.accept()
                        self.logger.info(f'Command connection from {addr}')
                        
                        # Handle commands from this client
                        self.process_client_commands(client_socket)
                        
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.logger.error(f'Error accepting command connection: {e}')
                        
            except Exception as e:
                self.logger.error(f'Error in command handler: {e}')
                time.sleep(1.0)
    
    def process_client_commands(self, client_socket):
        """Process commands from connected client"""
        try:
            client_socket.settimeout(1.0)
            buffer = b''
            
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete JSON messages
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            try:
                                command = json.loads(line.decode('utf-8'))
                                self.execute_command(command)
                            except json.JSONDecodeError as e:
                                self.logger.error(f'Invalid JSON command: {e}')
                                
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f'Error receiving command: {e}')
                    break
                    
        finally:
            client_socket.close()
    
    def execute_command(self, command):
        """Execute received command"""
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
    
    def send_arm_command(self, armed):
        """Send arm/disarm command to Crossflight"""
        # Implementation depends on Crossflight MSP commands
        self.logger.info(f'Arm command: {armed}')
    
    def send_velocity_command(self, command):
        """Send velocity command to Crossflight"""
        # Implementation depends on Crossflight MSP commands
        linear = command.get('linear', {})
        angular = command.get('angular', {})
        self.logger.info(f'Velocity command: linear={linear}, angular={angular}')
    
    def send_mode_command(self, mode):
        """Send flight mode command to Crossflight"""
        self.logger.info(f'Mode command: {mode}')
    
    def send_takeoff_command(self, altitude):
        """Send takeoff command to Crossflight"""
        self.logger.info(f'Takeoff command: {altitude}m')
    
    def send_land_command(self):
        """Send land command to Crossflight"""
        self.logger.info('Land command')
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f'Received signal {signum}, shutting down...')
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start telemetry bridge"""
        self.logger.info('Starting telemetry bridge...')
        
        if not self.setup_serial_connection():
            return False
        
        if not self.setup_network_sockets():
            return False
        
        self.running = True
        
        # Start threads
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
    
    def stop(self):
        """Stop telemetry bridge"""
        self.logger.info('Stopping telemetry bridge...')
        self.running = False
        self.stop_event.set()
        
        # Close connections
        if self.serial_connection:
            self.serial_connection.close()
        if self.telemetry_socket:
            self.telemetry_socket.close()
        if self.command_socket:
            self.command_socket.close()
        
        self.logger.info('Telemetry bridge stopped')
    
    def run(self):
        """Main run loop"""
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

def main():
    bridge = TelemetryBridge()
    bridge.run()

if __name__ == '__main__':
    main()
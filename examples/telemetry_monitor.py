#!/usr/bin/env python3
"""
Telemetry Monitoring Script

This script demonstrates real-time telemetry monitoring and data analysis.
It connects to the drone's telemetry stream and provides:
1. Real-time data visualization
2. Data logging and analysis
3. Alert system for critical parameters
4. Performance metrics calculation

Usage:
    python telemetry_monitor.py --drone_ip 192.168.4.1 --log_file flight_data.csv
"""

import argparse
import asyncio
import csv
import json
import logging
import socket
import struct
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TelemetryData:
    """Structure for telemetry data."""
    timestamp: float
    battery_voltage: float
    battery_current: float
    battery_percentage: int
    altitude: float
    velocity_x: float
    velocity_y: float
    velocity_z: float
    roll: float
    pitch: float
    yaw: float
    gps_lat: float
    gps_lon: float
    gps_satellites: int
    flight_mode: str
    armed: bool
    rssi: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'battery_voltage': self.battery_voltage,
            'battery_current': self.battery_current,
            'battery_percentage': self.battery_percentage,
            'altitude': self.altitude,
            'velocity_x': self.velocity_x,
            'velocity_y': self.velocity_y,
            'velocity_z': self.velocity_z,
            'roll': self.roll,
            'pitch': self.pitch,
            'yaw': self.yaw,
            'gps_lat': self.gps_lat,
            'gps_lon': self.gps_lon,
            'gps_satellites': self.gps_satellites,
            'flight_mode': self.flight_mode,
            'armed': self.armed,
            'rssi': self.rssi
        }

class TelemetryAnalyzer:
    """Analyzes telemetry data and provides insights."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.data_history: Deque[TelemetryData] = deque(maxlen=window_size)
        self.alerts = []
        
        # Thresholds for alerts
        self.battery_low_threshold = 20  # %
        self.battery_critical_threshold = 10  # %
        self.altitude_max_threshold = 50  # meters
        self.velocity_max_threshold = 10  # m/s
        self.gps_min_satellites = 6
    
    def add_data(self, data: TelemetryData):
        """Add new telemetry data point."""
        self.data_history.append(data)
        self._check_alerts(data)
    
    def _check_alerts(self, data: TelemetryData):
        """Check for alert conditions."""
        alerts = []
        
        # Battery alerts
        if data.battery_percentage <= self.battery_critical_threshold:
            alerts.append(f"CRITICAL: Battery at {data.battery_percentage}% - Land immediately!")
        elif data.battery_percentage <= self.battery_low_threshold:
            alerts.append(f"WARNING: Battery low at {data.battery_percentage}%")
        
        # Altitude alerts
        if data.altitude > self.altitude_max_threshold:
            alerts.append(f"WARNING: High altitude {data.altitude:.1f}m")
        
        # Velocity alerts
        total_velocity = (data.velocity_x**2 + data.velocity_y**2 + data.velocity_z**2)**0.5
        if total_velocity > self.velocity_max_threshold:
            alerts.append(f"WARNING: High velocity {total_velocity:.1f} m/s")
        
        # GPS alerts
        if data.gps_satellites < self.gps_min_satellites:
            alerts.append(f"WARNING: Low GPS satellites ({data.gps_satellites})")
        
        # Log new alerts
        for alert in alerts:
            if alert not in self.alerts[-10:]:  # Avoid spam
                logger.warning(alert)
                self.alerts.append(alert)
    
    def get_statistics(self) -> Dict:
        """Calculate statistics from recent data."""
        if not self.data_history:
            return {}
        
        recent_data = list(self.data_history)
        
        # Battery statistics
        battery_voltages = [d.battery_voltage for d in recent_data]
        battery_percentages = [d.battery_percentage for d in recent_data]
        
        # Flight statistics
        altitudes = [d.altitude for d in recent_data]
        velocities = [((d.velocity_x**2 + d.velocity_y**2 + d.velocity_z**2)**0.5) for d in recent_data]
        
        # GPS statistics
        gps_satellites = [d.gps_satellites for d in recent_data]
        
        return {
            'data_points': len(recent_data),
            'time_span': recent_data[-1].timestamp - recent_data[0].timestamp if len(recent_data) > 1 else 0,
            'battery': {
                'voltage_avg': sum(battery_voltages) / len(battery_voltages),
                'voltage_min': min(battery_voltages),
                'voltage_max': max(battery_voltages),
                'percentage_avg': sum(battery_percentages) / len(battery_percentages),
                'percentage_current': recent_data[-1].battery_percentage
            },
            'flight': {
                'altitude_avg': sum(altitudes) / len(altitudes),
                'altitude_min': min(altitudes),
                'altitude_max': max(altitudes),
                'altitude_current': recent_data[-1].altitude,
                'velocity_avg': sum(velocities) / len(velocities),
                'velocity_max': max(velocities),
                'velocity_current': velocities[-1]
            },
            'gps': {
                'satellites_avg': sum(gps_satellites) / len(gps_satellites),
                'satellites_min': min(gps_satellites),
                'satellites_current': recent_data[-1].gps_satellites
            },
            'status': {
                'flight_mode': recent_data[-1].flight_mode,
                'armed': recent_data[-1].armed,
                'rssi': recent_data[-1].rssi
            }
        }

class TelemetryMonitor:
    """Main telemetry monitoring class."""
    
    def __init__(self, drone_ip: str, telemetry_port: int = 5000, log_file: Optional[str] = None):
        self.drone_ip = drone_ip
        self.telemetry_port = telemetry_port
        self.log_file = log_file
        self.socket = None
        self.is_running = False
        self.analyzer = TelemetryAnalyzer()
        self.csv_writer = None
        self.csv_file = None
        
        # Statistics
        self.packets_received = 0
        self.packets_lost = 0
        self.start_time = None
    
    async def connect(self) -> bool:
        """Connect to telemetry stream."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.telemetry_port))
            self.socket.settimeout(1.0)
            
            logger.info(f"Listening for telemetry on port {self.telemetry_port}")
            
            # Setup CSV logging if requested
            if self.log_file:
                self.csv_file = open(self.log_file, 'w', newline='')
                fieldnames = [
                    'timestamp', 'battery_voltage', 'battery_current', 'battery_percentage',
                    'altitude', 'velocity_x', 'velocity_y', 'velocity_z',
                    'roll', 'pitch', 'yaw', 'gps_lat', 'gps_lon', 'gps_satellites',
                    'flight_mode', 'armed', 'rssi'
                ]
                self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
                self.csv_writer.writeheader()
                logger.info(f"Logging telemetry data to {self.log_file}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup telemetry monitoring: {e}")
            return False
    
    def parse_telemetry(self, data: bytes) -> Optional[TelemetryData]:
        """Parse raw telemetry data."""
        try:
            # Assuming JSON format for simplicity
            # In real implementation, this would parse MSP or MAVLink packets
            json_data = json.loads(data.decode('utf-8'))
            
            return TelemetryData(
                timestamp=time.time(),
                battery_voltage=json_data.get('battery_voltage', 0.0),
                battery_current=json_data.get('battery_current', 0.0),
                battery_percentage=json_data.get('battery_percentage', 0),
                altitude=json_data.get('altitude', 0.0),
                velocity_x=json_data.get('velocity_x', 0.0),
                velocity_y=json_data.get('velocity_y', 0.0),
                velocity_z=json_data.get('velocity_z', 0.0),
                roll=json_data.get('roll', 0.0),
                pitch=json_data.get('pitch', 0.0),
                yaw=json_data.get('yaw', 0.0),
                gps_lat=json_data.get('gps_lat', 0.0),
                gps_lon=json_data.get('gps_lon', 0.0),
                gps_satellites=json_data.get('gps_satellites', 0),
                flight_mode=json_data.get('flight_mode', 'UNKNOWN'),
                armed=json_data.get('armed', False),
                rssi=json_data.get('rssi', 0)
            )
        except Exception as e:
            logger.debug(f"Failed to parse telemetry data: {e}")
            return None
    
    async def receive_telemetry(self):
        """Receive and process telemetry data."""
        while self.is_running:
            try:
                data, addr = await asyncio.get_event_loop().run_in_executor(
                    None, self.socket.recvfrom, 1024
                )
                
                telemetry = self.parse_telemetry(data)
                if telemetry:
                    self.packets_received += 1
                    self.analyzer.add_data(telemetry)
                    
                    # Log to CSV if enabled
                    if self.csv_writer:
                        self.csv_writer.writerow(telemetry.to_dict())
                        self.csv_file.flush()
                    
                    # Print status every 10 packets
                    if self.packets_received % 10 == 0:
                        self.print_status(telemetry)
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error receiving telemetry: {e}")
                self.packets_lost += 1
    
    def print_status(self, latest_data: TelemetryData):
        """Print current status to console."""
        stats = self.analyzer.get_statistics()
        
        print("\n" + "="*60)
        print(f"TELEMETRY STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # Current status
        print(f"Flight Mode: {latest_data.flight_mode} | Armed: {latest_data.armed}")
        print(f"Battery: {latest_data.battery_percentage}% ({latest_data.battery_voltage:.2f}V)")
        print(f"Altitude: {latest_data.altitude:.1f}m")
        print(f"GPS: {latest_data.gps_satellites} sats | RSSI: {latest_data.rssi}")
        
        # Velocities
        total_vel = (latest_data.velocity_x**2 + latest_data.velocity_y**2 + latest_data.velocity_z**2)**0.5
        print(f"Velocity: {total_vel:.1f} m/s (X:{latest_data.velocity_x:.1f}, Y:{latest_data.velocity_y:.1f}, Z:{latest_data.velocity_z:.1f})")
        
        # Attitude
        print(f"Attitude: R:{latest_data.roll:.1f}° P:{latest_data.pitch:.1f}° Y:{latest_data.yaw:.1f}°")
        
        # Statistics
        if stats:
            print(f"\nPackets: {self.packets_received} received, {self.packets_lost} lost")
            if self.start_time:
                uptime = time.time() - self.start_time
                print(f"Uptime: {uptime:.0f}s | Rate: {self.packets_received/uptime:.1f} Hz")
        
        # Recent alerts
        if self.analyzer.alerts:
            print("\nRECENT ALERTS:")
            for alert in self.analyzer.alerts[-3:]:
                print(f"  {alert}")
    
    async def run(self):
        """Run the telemetry monitor."""
        if not await self.connect():
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        logger.info("Telemetry monitoring started. Press Ctrl+C to stop.")
        
        try:
            await self.receive_telemetry()
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.is_running = False
        
        if self.socket:
            self.socket.close()
        
        if self.csv_file:
            self.csv_file.close()
            logger.info(f"Telemetry data saved to {self.log_file}")
        
        # Print final statistics
        if self.start_time:
            total_time = time.time() - self.start_time
            logger.info(f"Session summary: {self.packets_received} packets in {total_time:.1f}s")
            logger.info(f"Average rate: {self.packets_received/total_time:.1f} Hz")
            logger.info(f"Packet loss: {self.packets_lost} ({100*self.packets_lost/(self.packets_received+self.packets_lost):.1f}%)")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Telemetry Monitor')
    parser.add_argument('--drone_ip', default='192.168.4.1',
                       help='IP address of the drone (default: 192.168.4.1)')
    parser.add_argument('--telemetry_port', type=int, default=5000,
                       help='Telemetry port (default: 5000)')
    parser.add_argument('--log_file', type=str,
                       help='CSV file to log telemetry data')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run monitor
    monitor = TelemetryMonitor(args.drone_ip, args.telemetry_port, args.log_file)
    
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Monitor failed: {e}")

if __name__ == "__main__":
    main()
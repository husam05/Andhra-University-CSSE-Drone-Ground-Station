#!/usr/bin/env python3
"""
Drone Startup Script for Raspberry Pi
Starts video streaming and telemetry bridge services
"""

import subprocess
import time
import logging
import signal
import sys
import os
import json
from threading import Thread, Event
from pathlib import Path

class DroneStartup:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.running = False
        self.processes = {}
        self.stop_event = Event()
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        script_dir = Path(__file__).parent
        config_path = script_dir / config_file
        
        default_config = {
            'services': {
                'video_streaming': True,
                'telemetry_bridge': True,
                'wifi_hotspot': True
            },
            'startup_delay': 5,
            'restart_on_failure': True,
            'max_restart_attempts': 3,
            'restart_delay': 10
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                default_config.update(config)
            return default_config
        except Exception as e:
            print(f'Could not load config file: {e}. Using defaults.')
            return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logs directory if it doesn't exist
        log_dir = Path('/var/log/drone')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / 'drone_startup.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def check_system_requirements(self):
        """Check if system requirements are met"""
        self.logger.info('Checking system requirements...')
        
        requirements = {
            'gstreamer': ['gst-launch-1.0', '--version'],
            'python3': ['python3', '--version'],
            'serial_port': None  # Will check file existence
        }
        
        for req, cmd in requirements.items():
            if req == 'serial_port':
                # Check serial port
                serial_port = self.config.get('serial_settings', {}).get('serial_port', '/dev/ttyAMA0')
                if not os.path.exists(serial_port):
                    self.logger.warning(f'Serial port {serial_port} not found')
                else:
                    self.logger.info(f'Serial port {serial_port} available')
            else:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info(f'{req}: OK')
                    else:
                        self.logger.warning(f'{req}: Failed - {result.stderr}')
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    self.logger.error(f'{req}: Not found')
    
    def setup_wifi_hotspot(self):
        """Setup WiFi hotspot for drone communication"""
        if not self.config.get('services', {}).get('wifi_hotspot', False):
            return True
        
        self.logger.info('Setting up WiFi hotspot...')
        
        try:
            network_config = self.config.get('network_settings', {})
            ssid = network_config.get('wifi_ssid', 'DroneNetwork')
            password = network_config.get('wifi_password', 'drone123')
            ip_address = network_config.get('ip_address', '192.168.4.1')
            
            # Create hostapd configuration
            hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
            
            with open('/tmp/hostapd.conf', 'w') as f:
                f.write(hostapd_conf)
            
            # Create dnsmasq configuration
            dnsmasq_conf = f"""
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
            
            with open('/tmp/dnsmasq.conf', 'w') as f:
                f.write(dnsmasq_conf)
            
            # Configure network interface
            subprocess.run(['sudo', 'ifconfig', 'wlan0', ip_address], check=True)
            
            # Start hostapd
            hostapd_process = subprocess.Popen(
                ['sudo', 'hostapd', '/tmp/hostapd.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Start dnsmasq
            dnsmasq_process = subprocess.Popen(
                ['sudo', 'dnsmasq', '-C', '/tmp/dnsmasq.conf', '-d'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.processes['hostapd'] = hostapd_process
            self.processes['dnsmasq'] = dnsmasq_process
            
            self.logger.info(f'WiFi hotspot started: {ssid} ({ip_address})')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to setup WiFi hotspot: {e}')
            return False
    
    def start_video_streaming(self):
        """Start video streaming service"""
        if not self.config.get('services', {}).get('video_streaming', False):
            return True
        
        self.logger.info('Starting video streaming service...')
        
        try:
            script_dir = Path(__file__).parent
            video_script = script_dir / 'video_streamer.py'
            
            if not video_script.exists():
                self.logger.error(f'Video streamer script not found: {video_script}')
                return False
            
            process = subprocess.Popen(
                ['python3', str(video_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=script_dir
            )
            
            self.processes['video_streaming'] = process
            self.logger.info('Video streaming service started')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start video streaming: {e}')
            return False
    
    def start_telemetry_bridge(self):
        """Start telemetry bridge service"""
        if not self.config.get('services', {}).get('telemetry_bridge', False):
            return True
        
        self.logger.info('Starting telemetry bridge service...')
        
        try:
            script_dir = Path(__file__).parent
            telemetry_script = script_dir / 'telemetry_bridge.py'
            
            if not telemetry_script.exists():
                self.logger.error(f'Telemetry bridge script not found: {telemetry_script}')
                return False
            
            process = subprocess.Popen(
                ['python3', str(telemetry_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=script_dir
            )
            
            self.processes['telemetry_bridge'] = process
            self.logger.info('Telemetry bridge service started')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start telemetry bridge: {e}')
            return False
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        restart_attempts = {}
        max_attempts = self.config.get('max_restart_attempts', 3)
        restart_delay = self.config.get('restart_delay', 10)
        
        while self.running and not self.stop_event.is_set():
            try:
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        # Process has terminated
                        self.logger.warning(f'Process {name} has terminated with code {process.returncode}')
                        
                        if self.config.get('restart_on_failure', True):
                            attempts = restart_attempts.get(name, 0)
                            if attempts < max_attempts:
                                self.logger.info(f'Restarting {name} (attempt {attempts + 1}/{max_attempts})')
                                
                                # Wait before restart
                                time.sleep(restart_delay)
                                
                                # Restart the service
                                if name == 'video_streaming':
                                    if self.start_video_streaming():
                                        restart_attempts[name] = 0
                                    else:
                                        restart_attempts[name] = attempts + 1
                                elif name == 'telemetry_bridge':
                                    if self.start_telemetry_bridge():
                                        restart_attempts[name] = 0
                                    else:
                                        restart_attempts[name] = attempts + 1
                            else:
                                self.logger.error(f'Max restart attempts reached for {name}')
                                del self.processes[name]
                        else:
                            del self.processes[name]
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f'Error in process monitor: {e}')
                time.sleep(5)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f'Received signal {signum}, shutting down...')
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start all drone services"""
        self.logger.info('Starting drone services...')
        
        # Check system requirements
        self.check_system_requirements()
        
        # Wait for startup delay
        startup_delay = self.config.get('startup_delay', 5)
        if startup_delay > 0:
            self.logger.info(f'Waiting {startup_delay} seconds before starting services...')
            time.sleep(startup_delay)
        
        self.running = True
        
        # Start services
        services_started = 0
        
        if self.setup_wifi_hotspot():
            services_started += 1
        
        if self.start_video_streaming():
            services_started += 1
        
        if self.start_telemetry_bridge():
            services_started += 1
        
        if services_started == 0:
            self.logger.error('No services started successfully')
            return False
        
        # Start process monitor
        monitor_thread = Thread(target=self.monitor_processes, name='ProcessMonitor')
        monitor_thread.daemon = True
        monitor_thread.start()
        
        self.logger.info(f'Drone startup completed - {services_started} services running')
        return True
    
    def stop(self):
        """Stop all drone services"""
        self.logger.info('Stopping drone services...')
        self.running = False
        self.stop_event.set()
        
        # Stop all processes
        for name, process in self.processes.items():
            try:
                self.logger.info(f'Stopping {name}...')
                process.terminate()
                
                # Wait for graceful termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    process.kill()
                    process.wait()
                
                self.logger.info(f'{name} stopped')
                
            except Exception as e:
                self.logger.error(f'Error stopping {name}: {e}')
        
        self.processes.clear()
        self.logger.info('All drone services stopped')
    
    def run(self):
        """Main run loop"""
        if not self.start():
            return False
        
        try:
            # Keep running until stopped
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Keyboard interrupt received')
        finally:
            self.stop()
        
        return True

def main():
    # Check if running as root (required for WiFi hotspot)
    if os.geteuid() != 0:
        print('Warning: Not running as root. WiFi hotspot may not work.')
    
    startup = DroneStartup()
    startup.run()

if __name__ == '__main__':
    main()
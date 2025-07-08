#!/usr/bin/env python3
"""
Video Streamer for Raspberry Pi Drone
Captures video from camera and streams to ground station via GStreamer
"""

import subprocess
import time
import logging
import signal
import sys
import json
import os
from threading import Thread, Event

class VideoStreamer:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.streaming = False
        self.gstreamer_process = None
        self.stop_event = Event()
        
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
            'video_port': 5600,
            'camera_width': 1280,
            'camera_height': 720,
            'framerate': 30,
            'bitrate': 2000000,
            'camera_device': '/dev/video0',
            'flip_method': 0,
            'exposure_mode': 'auto'
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                default_config.update(config)
            return default_config
        except Exception as e:
            self.logger.warning(f'Could not load config file: {e}. Using defaults.')
            return default_config
    
    def detect_camera_type(self):
        """Detect if using Raspberry Pi camera or USB camera"""
        # Check for Raspberry Pi camera
        try:
            result = subprocess.run(['vcgencmd', 'get_camera'], 
                                  capture_output=True, text=True, timeout=5)
            if 'detected=1' in result.stdout:
                self.logger.info('Raspberry Pi camera detected')
                return 'rpi_camera'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check for USB camera
        if os.path.exists(self.config['camera_device']):
            self.logger.info('USB camera detected')
            return 'usb_camera'
        
        self.logger.error('No camera detected')
        return None
    
    def build_gstreamer_pipeline(self, camera_type):
        """Build GStreamer pipeline based on camera type"""
        ground_station_ip = self.config['ground_station_ip']
        video_port = self.config['video_port']
        width = self.config['camera_width']
        height = self.config['camera_height']
        framerate = self.config['framerate']
        bitrate = self.config['bitrate']
        
        if camera_type == 'rpi_camera':
            # Raspberry Pi camera pipeline
            pipeline = [
                'gst-launch-1.0',
                'libcamerasrc',
                '!', f'video/x-raw,width={width},height={height},framerate={framerate}/1',
                '!', 'videoconvert',
                '!', 'x264enc', f'bitrate={bitrate//1000}', 'speed-preset=ultrafast', 'tune=zerolatency',
                '!', 'rtph264pay', 'config-interval=1', 'pt=96',
                '!', f'udpsink', f'host={ground_station_ip}', f'port={video_port}'
            ]
        elif camera_type == 'usb_camera':
            # USB camera pipeline
            device = self.config['camera_device']
            pipeline = [
                'gst-launch-1.0',
                'v4l2src', f'device={device}',
                '!', f'video/x-raw,width={width},height={height},framerate={framerate}/1',
                '!', 'videoconvert',
                '!', 'x264enc', f'bitrate={bitrate//1000}', 'speed-preset=ultrafast', 'tune=zerolatency',
                '!', 'rtph264pay', 'config-interval=1', 'pt=96',
                '!', f'udpsink', f'host={ground_station_ip}', f'port={video_port}'
            ]
        else:
            return None
        
        return pipeline
    
    def start_streaming(self):
        """Start video streaming"""
        if self.streaming:
            self.logger.warning('Streaming already active')
            return False
        
        camera_type = self.detect_camera_type()
        if not camera_type:
            self.logger.error('No camera available for streaming')
            return False
        
        pipeline = self.build_gstreamer_pipeline(camera_type)
        if not pipeline:
            self.logger.error('Failed to build GStreamer pipeline')
            return False
        
        try:
            self.logger.info(f'Starting video stream to {self.config["ground_station_ip"]}:{self.config["video_port"]}')
            self.logger.info(f'Pipeline: {" ".join(pipeline)}')
            
            self.gstreamer_process = subprocess.Popen(
                pipeline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            self.streaming = True
            
            # Start monitoring thread
            monitor_thread = Thread(target=self.monitor_stream)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            self.logger.info('Video streaming started successfully')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to start video streaming: {e}')
            return False
    
    def stop_streaming(self):
        """Stop video streaming"""
        if not self.streaming:
            return
        
        self.logger.info('Stopping video streaming')
        self.streaming = False
        self.stop_event.set()
        
        if self.gstreamer_process:
            try:
                # Terminate gracefully
                self.gstreamer_process.terminate()
                
                # Wait for process to terminate
                try:
                    self.gstreamer_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.gstreamer_process.kill()
                    self.gstreamer_process.wait()
                
                self.gstreamer_process = None
                self.logger.info('Video streaming stopped')
                
            except Exception as e:
                self.logger.error(f'Error stopping video stream: {e}')
    
    def monitor_stream(self):
        """Monitor streaming process"""
        while self.streaming and not self.stop_event.is_set():
            if self.gstreamer_process:
                poll = self.gstreamer_process.poll()
                if poll is not None:
                    # Process has terminated
                    self.logger.error(f'GStreamer process terminated with code {poll}')
                    
                    # Read error output
                    if self.gstreamer_process.stderr:
                        stderr_output = self.gstreamer_process.stderr.read().decode('utf-8')
                        if stderr_output:
                            self.logger.error(f'GStreamer error: {stderr_output}')
                    
                    self.streaming = False
                    break
            
            time.sleep(1)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f'Received signal {signum}, shutting down...')
        self.stop_streaming()
        sys.exit(0)
    
    def run(self):
        """Main run loop"""
        self.logger.info('Video streamer starting...')
        
        if not self.start_streaming():
            self.logger.error('Failed to start video streaming')
            return False
        
        try:
            # Keep running until stopped
            while self.streaming:
                time.sleep(1)
                
                # Check if we need to restart streaming
                if not self.streaming:
                    self.logger.info('Attempting to restart streaming...')
                    time.sleep(5)  # Wait before restart
                    self.start_streaming()
                    
        except KeyboardInterrupt:
            self.logger.info('Keyboard interrupt received')
        finally:
            self.stop_streaming()
        
        return True

def main():
    streamer = VideoStreamer()
    streamer.run()

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Video Stream Analyzer

This script demonstrates real-time video stream analysis for drone footage.
It provides:
1. Real-time video processing and analysis
2. Object detection and tracking
3. Video quality metrics
4. Recording and frame extraction
5. Performance monitoring

Usage:
    python video_analyzer.py --drone_ip 192.168.4.1 --save_frames --detect_objects
"""

import argparse
import cv2
import logging
import numpy as np
import os
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoQualityAnalyzer:
    """Analyzes video quality metrics."""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.frame_sizes = deque(maxlen=window_size)
        self.blur_scores = deque(maxlen=window_size)
        self.brightness_scores = deque(maxlen=window_size)
        
    def analyze_frame(self, frame: np.ndarray, frame_size: int) -> Dict:
        """Analyze a single frame for quality metrics."""
        current_time = time.time()
        self.frame_times.append(current_time)
        self.frame_sizes.append(frame_size)
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate blur score using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        self.blur_scores.append(blur_score)
        
        # Calculate brightness
        brightness = np.mean(gray)
        self.brightness_scores.append(brightness)
        
        # Calculate FPS
        fps = 0
        if len(self.frame_times) > 1:
            time_diff = self.frame_times[-1] - self.frame_times[0]
            if time_diff > 0:
                fps = (len(self.frame_times) - 1) / time_diff
        
        return {
            'fps': fps,
            'blur_score': blur_score,
            'brightness': brightness,
            'frame_size': frame_size,
            'resolution': f"{frame.shape[1]}x{frame.shape[0]}"
        }
    
    def get_statistics(self) -> Dict:
        """Get quality statistics over the window."""
        if not self.frame_times:
            return {}
        
        # FPS calculation
        fps = 0
        if len(self.frame_times) > 1:
            time_diff = self.frame_times[-1] - self.frame_times[0]
            if time_diff > 0:
                fps = (len(self.frame_times) - 1) / time_diff
        
        return {
            'avg_fps': fps,
            'avg_blur_score': np.mean(self.blur_scores) if self.blur_scores else 0,
            'avg_brightness': np.mean(self.brightness_scores) if self.brightness_scores else 0,
            'avg_frame_size': np.mean(self.frame_sizes) if self.frame_sizes else 0,
            'frame_count': len(self.frame_times)
        }

class SimpleObjectDetector:
    """Simple object detection using OpenCV."""
    
    def __init__(self):
        # Initialize background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True, varThreshold=50
        )
        
        # Initialize cascade classifiers (if available)
        self.face_cascade = None
        self.car_cascade = None
        
        try:
            # Try to load Haar cascades
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            logger.info("Face detection enabled")
        except Exception as e:
            logger.warning(f"Face detection not available: {e}")
    
    def detect_motion(self, frame: np.ndarray) -> Tuple[List[Tuple], np.ndarray]:
        """Detect motion in the frame."""
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        motion_objects = []
        min_area = 500  # Minimum area for motion detection
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                motion_objects.append((x, y, w, h))
        
        return motion_objects, fg_mask
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple]:
        """Detect faces in the frame."""
        if self.face_cascade is None:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """Analyze frame for objects and motion."""
        results = {
            'motion_objects': [],
            'faces': [],
            'total_detections': 0
        }
        
        # Detect motion
        motion_objects, _ = self.detect_motion(frame)
        results['motion_objects'] = motion_objects
        
        # Detect faces
        faces = self.detect_faces(frame)
        results['faces'] = faces
        
        results['total_detections'] = len(motion_objects) + len(faces)
        
        return results

class VideoStreamAnalyzer:
    """Main video stream analyzer."""
    
    def __init__(self, drone_ip: str, video_port: int = 5600, 
                 save_frames: bool = False, detect_objects: bool = False,
                 output_dir: str = "video_analysis"):
        self.drone_ip = drone_ip
        self.video_port = video_port
        self.save_frames = save_frames
        self.detect_objects = detect_objects
        self.output_dir = output_dir
        
        # Create output directory
        if self.save_frames:
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Saving frames to {self.output_dir}")
        
        # Initialize analyzers
        self.quality_analyzer = VideoQualityAnalyzer()
        self.object_detector = SimpleObjectDetector() if detect_objects else None
        
        # Video capture
        self.cap = None
        self.is_running = False
        
        # Statistics
        self.frame_count = 0
        self.start_time = None
        self.last_save_time = 0
        self.save_interval = 5.0  # Save frame every 5 seconds
    
    def setup_video_capture(self) -> bool:
        """Setup video capture from drone stream."""
        try:
            # GStreamer pipeline for receiving H.264 stream
            gst_pipeline = (
                f"udpsrc port={self.video_port} ! "
                "application/x-rtp,encoding-name=H264,payload=96 ! "
                "rtph264depay ! h264parse ! avdec_h264 ! "
                "videoconvert ! appsink"
            )
            
            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            
            if not self.cap.isOpened():
                logger.error("Failed to open video stream")
                return False
            
            logger.info(f"Video stream opened successfully on port {self.video_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup video capture: {e}")
            return False
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single frame."""
        processed_frame = frame.copy()
        current_time = time.time()
        
        # Calculate frame size
        frame_size = frame.nbytes
        
        # Analyze video quality
        quality_metrics = self.quality_analyzer.analyze_frame(frame, frame_size)
        
        # Object detection if enabled
        detection_results = {}
        if self.object_detector:
            detection_results = self.object_detector.analyze_frame(frame)
            
            # Draw motion objects
            for (x, y, w, h) in detection_results.get('motion_objects', []):
                cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(processed_frame, 'MOTION', (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Draw faces
            for (x, y, w, h) in detection_results.get('faces', []):
                cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(processed_frame, 'FACE', (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # Add overlay information
        self.add_overlay(processed_frame, quality_metrics, detection_results)
        
        # Save frame if enabled
        if self.save_frames and (current_time - self.last_save_time) > self.save_interval:
            self.save_frame(frame)
            self.last_save_time = current_time
        
        return processed_frame
    
    def add_overlay(self, frame: np.ndarray, quality_metrics: Dict, detection_results: Dict):
        """Add information overlay to the frame."""
        height, width = frame.shape[:2]
        
        # Background for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Text information
        y_offset = 30
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        color = (255, 255, 255)
        thickness = 1
        
        # Quality metrics
        cv2.putText(frame, f"FPS: {quality_metrics.get('fps', 0):.1f}",
                   (15, y_offset), font, font_scale, color, thickness)
        y_offset += 20
        
        cv2.putText(frame, f"Resolution: {quality_metrics.get('resolution', 'Unknown')}",
                   (15, y_offset), font, font_scale, color, thickness)
        y_offset += 20
        
        cv2.putText(frame, f"Blur Score: {quality_metrics.get('blur_score', 0):.1f}",
                   (15, y_offset), font, font_scale, color, thickness)
        y_offset += 20
        
        cv2.putText(frame, f"Brightness: {quality_metrics.get('brightness', 0):.1f}",
                   (15, y_offset), font, font_scale, color, thickness)
        y_offset += 20
        
        # Detection results
        if detection_results:
            cv2.putText(frame, f"Detections: {detection_results.get('total_detections', 0)}",
                       (15, y_offset), font, font_scale, color, thickness)
        
        # Frame counter
        cv2.putText(frame, f"Frame: {self.frame_count}",
                   (width - 150, 30), font, font_scale, color, thickness)
        
        # Timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        cv2.putText(frame, timestamp,
                   (width - 150, height - 20), font, font_scale, color, thickness)
    
    def save_frame(self, frame: np.ndarray):
        """Save frame to disk."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"frame_{timestamp}_{self.frame_count:06d}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            logger.debug(f"Saved frame: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
    
    def print_statistics(self):
        """Print current statistics."""
        if not self.start_time:
            return
        
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        quality_stats = self.quality_analyzer.get_statistics()
        
        print("\n" + "="*50)
        print(f"VIDEO ANALYSIS STATISTICS - {datetime.now().strftime('%H:%M:%S')}")
        print("="*50)
        
        print(f"Frames Processed: {self.frame_count}")
        print(f"Elapsed Time: {elapsed_time:.1f}s")
        print(f"Average FPS: {self.frame_count / elapsed_time:.1f}")
        
        if quality_stats:
            print(f"Stream FPS: {quality_stats.get('avg_fps', 0):.1f}")
            print(f"Average Blur Score: {quality_stats.get('avg_blur_score', 0):.1f}")
            print(f"Average Brightness: {quality_stats.get('avg_brightness', 0):.1f}")
            print(f"Average Frame Size: {quality_stats.get('avg_frame_size', 0):.0f} bytes")
    
    def run(self):
        """Run the video analyzer."""
        if not self.setup_video_capture():
            return
        
        self.is_running = True
        self.start_time = time.time()
        last_stats_time = time.time()
        
        logger.info("Video analysis started. Press 'q' to quit, 's' to save current frame.")
        
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame")
                    continue
                
                self.frame_count += 1
                
                # Process frame
                processed_frame = self.process_frame(frame)
                
                # Display frame
                cv2.imshow('Drone Video Analysis', processed_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    self.save_frame(frame)
                    logger.info("Frame saved manually")
                
                # Print statistics every 10 seconds
                current_time = time.time()
                if current_time - last_stats_time > 10.0:
                    self.print_statistics()
                    last_stats_time = current_time
        
        except KeyboardInterrupt:
            logger.info("Analysis stopped by user")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.is_running = False
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        # Print final statistics
        self.print_statistics()
        
        if self.save_frames:
            logger.info(f"Frames saved to {self.output_dir}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Video Stream Analyzer')
    parser.add_argument('--drone_ip', default='192.168.4.1',
                       help='IP address of the drone (default: 192.168.4.1)')
    parser.add_argument('--video_port', type=int, default=5600,
                       help='Video port (default: 5600)')
    parser.add_argument('--save_frames', action='store_true',
                       help='Save frames to disk')
    parser.add_argument('--detect_objects', action='store_true',
                       help='Enable object detection')
    parser.add_argument('--output_dir', default='video_analysis',
                       help='Output directory for saved frames')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run analyzer
    analyzer = VideoStreamAnalyzer(
        args.drone_ip, args.video_port, args.save_frames,
        args.detect_objects, args.output_dir
    )
    
    try:
        analyzer.run()
    except KeyboardInterrupt:
        logger.info("Analyzer stopped by user")
    except Exception as e:
        logger.error(f"Analyzer failed: {e}")

if __name__ == "__main__":
    main()
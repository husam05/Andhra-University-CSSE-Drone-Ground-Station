#!/usr/bin/env python3
"""
Video Receiver Node for Drone Ground Station
Receives video stream from Raspberry Pi camera via GStreamer
Publishes video frames as ROS2 sensor_msgs/Image
"""

from __future__ import annotations

import threading
from typing import Optional

import cv2
import gi
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

gi.require_version('Gst', '1.0')
from gi.repository import Gst


class VideoReceiver(Node):
    def __init__(self) -> None:
        super().__init__('video_receiver')

        # Parameters
        self.declare_parameter('drone_ip', '192.168.4.1')
        self.declare_parameter('video_port', 5600)
        self.declare_parameter('frame_rate', 30)
        self.declare_parameter('video_width', 1280)
        self.declare_parameter('video_height', 720)

        self.drone_ip: str = self.get_parameter('drone_ip').value
        self.video_port: int = self.get_parameter('video_port').value
        self.frame_rate: int = self.get_parameter('frame_rate').value
        self.video_width: int = self.get_parameter('video_width').value
        self.video_height: int = self.get_parameter('video_height').value

        # ROS2 setup
        self.image_publisher = self.create_publisher(Image, 'drone/camera/image_raw', 10)
        self.bridge = CvBridge()

        # GStreamer setup
        Gst.init(None)
        self.pipeline: Optional[Gst.Pipeline] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        # Initialize GStreamer pipeline
        self.setup_gstreamer_pipeline()

        # Timer for publishing frames
        self.timer = self.create_timer(1.0 / self.frame_rate, self.publish_frame)

        self.get_logger().info(
            f'Video receiver initialized for {self.drone_ip}:{self.video_port}'
        )

    def setup_gstreamer_pipeline(self) -> bool:
        """Setup GStreamer pipeline for receiving H.264 video stream."""
        try:
            pipeline_str = (
                f'udpsrc port={self.video_port} '
                f'caps="application/x-rtp,payload=96" ! '
                'rtph264depay ! h264parse ! avdec_h264 ! '
                'videoconvert ! video/x-raw,format=BGR ! '
                'appsink name=sink emit-signals=true sync=false '
                'max-buffers=2 drop=true'
            )

            self.get_logger().info(f'Creating GStreamer pipeline: {pipeline_str}')
            self.pipeline = Gst.parse_launch(pipeline_str)

            self.appsink = self.pipeline.get_by_name('sink')
            self.appsink.connect('new-sample', self.on_new_sample)

            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                self.get_logger().error('Failed to start GStreamer pipeline')
                return False

            self.get_logger().info('GStreamer pipeline started successfully')
            return True

        except Exception as e:
            self.get_logger().error(
                f'Error setting up GStreamer pipeline: {str(e)}'
            )
            return False

    def on_new_sample(self, appsink: Gst.Element) -> Gst.FlowReturn:
        """Callback for new video frame from GStreamer."""
        try:
            sample = appsink.emit('pull-sample')
            if sample:
                buffer = sample.get_buffer()
                caps = sample.get_caps()

                success, map_info = buffer.map(Gst.MapFlags.READ)
                if success:
                    frame_data = np.frombuffer(map_info.data, dtype=np.uint8)

                    structure = caps.get_structure(0)
                    width = structure.get_int('width')[1]
                    height = structure.get_int('height')[1]

                    frame = frame_data.reshape((height, width, 3))

                    with self.frame_lock:
                        self.latest_frame = frame.copy()

                    buffer.unmap(map_info)

        except Exception as e:
            self.get_logger().error(f'Error processing video frame: {str(e)}')

        return Gst.FlowReturn.OK

    def publish_frame(self) -> None:
        """Publish the latest video frame as ROS2 Image message."""
        try:
            with self.frame_lock:
                if self.latest_frame is not None:
                    image_msg = self.bridge.cv2_to_imgmsg(
                        self.latest_frame, encoding='bgr8'
                    )
                    image_msg.header.stamp = self.get_clock().now().to_msg()
                    image_msg.header.frame_id = 'drone_camera'
                    self.image_publisher.publish(image_msg)

        except Exception as e:
            self.get_logger().error(f'Error publishing video frame: {str(e)}')

    def destroy_node(self) -> None:
        """Clean up resources."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)

    try:
        video_receiver = VideoReceiver()
        rclpy.spin(video_receiver)
    except KeyboardInterrupt:
        pass
    finally:
        if 'video_receiver' in locals():
            video_receiver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
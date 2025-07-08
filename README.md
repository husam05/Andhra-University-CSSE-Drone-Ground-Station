# Drone Ground Station with ROS2

**Andhra University**  
**Department of Computer Science & Systems Engineering**

A comprehensive ground station system for communicating with a Raspberry Pi 3 based drone equipped with camera and Crossflight flight controller.

This project demonstrates the integration of ROS2, computer vision, and drone control systems for educational and research purposes.

## System Architecture

- **Drone Board**: Raspberry Pi 3 + Camera + Crossflight FC (UART connection)
- **Ground Station**: Windows PC with ROS2
- **Communication**: WiFi (192.168.4.1)
- **Video**: GStreamer pipeline via ROS2
- **Telemetry**: MAVLink protocol via ROS2

## Features

- Real-time video streaming from drone camera
- Telemetry data reception and display
- Flight control commands
- Mission planning interface
- Data logging and recording

## Prerequisites

- ROS2 Humble (Windows)
- GStreamer 1.0+
- Python 3.8+
- OpenCV
- PyMAVLink

## Installation

```bash
# Install ROS2 packages
colcon build
source install/setup.bash

# Launch ground station
ros2 launch drone_ground_station ground_station.launch.py
```

## Network Configuration

- Drone IP: 192.168.4.1
- Ground Station: 192.168.4.19
- Video Port: 5600
- Telemetry Port: 14550

## Usage

1. Connect to drone WiFi network
2. Launch ground station: `ros2 launch drone_ground_station ground_station.launch.py`
3. Monitor video feed and telemetry data
4. Send commands via GUI interface

## Academic Information

**Institution**: Andhra University  
**Department**: Computer Science & Systems Engineering  
**Project Type**: Research & Development  

This project serves as a practical implementation of:
- Distributed systems communication
- Real-time data processing
- Computer vision applications
- Autonomous vehicle control systems
- ROS2 framework utilization

## Contributing

This project is maintained by the Department of Computer Science & Systems Engineering at Andhra University. For academic inquiries or collaboration opportunities, please contact the department.

## License

This project is developed for educational and research purposes at Andhra University.
<p align="center">
  <img src="https://img.shields.io/badge/Andhra_University-CSSE_Department-1a237e?style=for-the-badge&logo=graduation-cap" alt="AU CSSE"/>
</p>

<h1 align="center">Drone Ground Station</h1>

<p align="center">
  <em>A ROS2-powered ground control system for real-time drone telemetry, video streaming, and flight command — built for education and research</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/ROS2-Humble-22314e?style=flat-square&logo=ros&logoColor=white" alt="ROS2"/>
  <img src="https://img.shields.io/badge/GStreamer-1.0+-ee3124?style=flat-square" alt="GStreamer"/>
  <img src="https://img.shields.io/badge/MAVLink-2.0-00979d?style=flat-square" alt="MAVLink"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=flat-square" alt="Platform"/>
</p>

---

## Table of Contents

- [System Architecture](#-system-architecture)
- [Network Topology](#-network-topology)
- [ROS2 Topic Graph](#-ros2-topic-graph)
- [Data Flow](#-data-flow)
- [Flight State Machine](#-flight-state-machine)
- [Software Stack](#-software-stack)
- [Hardware Wiring](#-hardware-wiring)
- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [GUI Layout](#-gui-layout)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Performance](#-performance)
- [Safety Systems](#-safety-systems)
- [Troubleshooting](#-troubleshooting)
- [Documentation](#-documentation)
- [Contributing](#contributing)
- [License](#license)

---

## System Architecture

```mermaid
graph TB
    subgraph GS["Ground Station (Windows/Linux PC)"]
        direction TB
        GUI["Ground Station GUI<br/><i>Tkinter - Video + Telemetry + Controls</i>"]
        VR["Video Receiver<br/><i>GStreamer H.264 Decoder</i>"]
        TR["Telemetry Receiver<br/><i>MAVLink + JSON Parser</i>"]
        MB["MAVLink Bridge<br/><i>Command Sender</i>"]

        GUI <-->|"sensor_msgs/Image"| VR
        GUI <-->|"BatteryState, NavSatFix,<br/>Float32, Bool, String"| TR
        GUI -->|"Twist, Bool, Float32,<br/>String, PoseStamped"| MB
    end

    subgraph WIFI["WiFi Link (192.168.4.x)"]
        direction LR
        UDP1["UDP :5600<br/><i>H.264 RTP Video</i>"]
        UDP2["UDP :14550<br/><i>JSON Telemetry</i>"]
        TCP1["TCP :14551<br/><i>JSON Commands</i>"]
    end

    subgraph DRONE["Raspberry Pi 3 Model B+ (Drone)"]
        direction TB
        VS["Video Streamer<br/><i>GStreamer H.264 Encoder</i>"]
        TBR["Telemetry Bridge<br/><i>MSP Parser + JSON Sender</i>"]
        DS["Drone Startup<br/><i>Service Manager</i>"]
        CAM["Camera Module<br/><i>CSI / USB</i>"]
        FC["Crossflight FC<br/><i>Flight Controller</i>"]

        DS --> VS
        DS --> TBR
        CAM --> VS
        FC <-->|"UART 115200 baud<br/>MSP Protocol"| TBR
    end

    VS -->|"H.264 RTP Stream"| UDP1
    UDP1 -->|"Decode & Publish"| VR
    TBR -->|"JSON Telemetry"| UDP2
    UDP2 -->|"Parse & Publish"| TR
    MB -->|"JSON Commands"| TCP1
    TCP1 -->|"Execute on FC"| TBR

    style GS fill:#1a237e,stroke:#5c6bc0,color:#fff
    style DRONE fill:#1b5e20,stroke:#66bb6a,color:#fff
    style WIFI fill:#e65100,stroke:#ff9800,color:#fff
    style GUI fill:#283593,stroke:#5c6bc0,color:#fff
    style VR fill:#283593,stroke:#5c6bc0,color:#fff
    style TR fill:#283593,stroke:#5c6bc0,color:#fff
    style MB fill:#283593,stroke:#5c6bc0,color:#fff
    style VS fill:#2e7d32,stroke:#66bb6a,color:#fff
    style TBR fill:#2e7d32,stroke:#66bb6a,color:#fff
    style DS fill:#2e7d32,stroke:#66bb6a,color:#fff
    style CAM fill:#4a148c,stroke:#ab47bc,color:#fff
    style FC fill:#4a148c,stroke:#ab47bc,color:#fff
```

---

## Network Topology

```mermaid
graph LR
    subgraph DRONE_NET["Drone — WiFi AP"]
        PI["Raspberry Pi 3<br/>192.168.4.1"]
    end

    subgraph GS_NET["Ground Station — WiFi Client"]
        PC["Windows/Linux PC<br/>192.168.4.19"]
    end

    PI -- "UDP :5600<br/>H.264 RTP Video<br/>~2 Mbps ➜" --> PC
    PI -- "UDP :14550<br/>JSON Telemetry<br/>10 Hz ➜" --> PC
    PC -- "TCP :14551<br/>JSON Commands<br/>10 Hz ➜" --> PI
    PI -. "DHCP :67-68<br/>hostapd + dnsmasq" .-> PC

    style DRONE_NET fill:#1b5e20,stroke:#66bb6a,color:#fff
    style GS_NET fill:#1a237e,stroke:#5c6bc0,color:#fff
    style PI fill:#2e7d32,stroke:#a5d6a7,color:#fff
    style PC fill:#283593,stroke:#9fa8da,color:#fff
```

---

## ROS2 Topic Graph

```mermaid
graph LR
    subgraph Publishers
        VR["video_receiver"]
        TR["telemetry_receiver"]
        MB["mavlink_bridge"]
    end

    subgraph Topics
        T1["/drone/camera/image_raw<br/><small>sensor_msgs/Image</small>"]
        T2["/drone/battery<br/><small>sensor_msgs/BatteryState</small>"]
        T3["/drone/gps<br/><small>sensor_msgs/NavSatFix</small>"]
        T4["/drone/imu<br/><small>sensor_msgs/Imu</small>"]
        T5["/drone/altitude<br/><small>std_msgs/Float32</small>"]
        T6["/drone/heading<br/><small>std_msgs/Float32</small>"]
        T7["/drone/armed<br/><small>std_msgs/Bool</small>"]
        T8["/drone/mode<br/><small>std_msgs/String</small>"]
        T9["/drone/status<br/><small>std_msgs/String</small>"]
        T10["/drone/connection_status<br/><small>std_msgs/Bool</small>"]
        C1["/drone/cmd_vel<br/><small>geometry_msgs/Twist</small>"]
        C2["/drone/arm<br/><small>std_msgs/Bool</small>"]
        C3["/drone/takeoff<br/><small>std_msgs/Float32</small>"]
        C4["/drone/land<br/><small>std_msgs/Bool</small>"]
        C5["/drone/set_mode<br/><small>std_msgs/String</small>"]
        C6["/drone/goto<br/><small>geometry_msgs/PoseStamped</small>"]
    end

    subgraph Subscriber
        GUI["ground_station_gui"]
    end

    VR --> T1
    TR --> T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9
    MB --> T10

    T1 & T2 & T3 & T5 & T7 & T8 & T9 & T10 --> GUI

    GUI --> C1 & C2 & C3 & C4 & C5 & C6
    C1 & C2 & C3 & C4 & C5 & C6 --> MB

    style VR fill:#e65100,color:#fff
    style TR fill:#e65100,color:#fff
    style MB fill:#e65100,color:#fff
    style GUI fill:#1565c0,color:#fff
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant CAM as Camera
    participant VS as Video Streamer (Pi)
    participant NET as WiFi Network
    participant VR as Video Receiver (GS)
    participant TR as Telemetry Receiver
    participant GUI as Ground Station GUI
    participant MB as MAVLink Bridge
    participant TB as Telemetry Bridge (Pi)
    participant FC as Crossflight FC

    Note over CAM,FC: Video Streaming Pipeline
    CAM->>VS: Raw frames (CSI/USB)
    VS->>VS: GStreamer encode H.264
    VS->>NET: RTP/UDP :5600
    NET->>VR: H.264 packets
    VR->>VR: GStreamer decode → OpenCV
    VR->>GUI: /drone/camera/image_raw

    Note over CAM,FC: Telemetry Pipeline
    FC->>TB: MSP binary (UART 115200)
    TB->>TB: Parse MSP → Python dict
    TB->>NET: JSON/UDP :14550
    NET->>TR: JSON telemetry
    TR->>TR: Parse JSON + MAVLink
    TR->>GUI: /drone/battery, /gps, /altitude...

    Note over CAM,FC: Command Pipeline
    GUI->>MB: /drone/cmd_vel, /arm, /takeoff...
    MB->>NET: JSON/TCP :14551
    NET->>TB: Command JSON
    TB->>FC: MSP command (UART)
    FC-->>TB: MSP ACK
```

---

## Flight State Machine

```mermaid
stateDiagram-v2
    [*] --> DISCONNECTED

    DISCONNECTED --> CONNECTING: WiFi detected
    CONNECTING --> CONNECTED: Handshake OK
    CONNECTING --> DISCONNECTED: Timeout

    CONNECTED --> ARMED: ARM command<br/>Pre-flight checks pass
    CONNECTED --> DISCONNECTED: Connection lost

    ARMED --> TAKEOFF: Takeoff command<br/>altitude = 2m
    ARMED --> CONNECTED: DISARM command

    TAKEOFF --> FLYING: Target altitude reached
    TAKEOFF --> EMERGENCY_LAND: Sensor failure

    FLYING --> LANDING: Land command
    FLYING --> FLYING: Velocity commands
    FLYING --> EMERGENCY_LAND: Low battery < 20%
    FLYING --> EMERGENCY_LAND: Geofence breach
    FLYING --> EMERGENCY_LAND: Connection timeout

    LANDING --> LANDED: Ground contact
    EMERGENCY_LAND --> LANDED: Ground contact

    LANDED --> CONNECTED: DISARM command
    LANDED --> [*]

    state FLYING {
        [*] --> STABILIZE
        STABILIZE --> ALT_HOLD: Mode change
        ALT_HOLD --> LOITER: Mode change
        LOITER --> RTL: Mode change
        RTL --> STABILIZE: Mode change
        STABILIZE --> GUIDED: Goto command
        GUIDED --> STABILIZE: Mode change
    }
```

---

## Software Stack

```mermaid
graph TB
    subgraph L5["Application Layer"]
        GUI2["Tkinter GUI<br/>Video | Telemetry | Controls"]
        DEMO["Examples & Demos<br/>flight_demo | monitor | analyzer"]
    end

    subgraph L4["ROS2 Node Layer"]
        N1["video_receiver"]
        N2["telemetry_receiver"]
        N3["mavlink_bridge"]
        N4["ground_station_gui"]
    end

    subgraph L3["Middleware Layer"]
        ROS["ROS2 Humble<br/>DDS pub/sub"]
        GST["GStreamer 1.0<br/>Media pipeline"]
        MAV["PyMAVLink 2.4<br/>Protocol library"]
    end

    subgraph L2["OS & Runtime"]
        PY["Python 3.8+"]
        CV["OpenCV 4.5+"]
        NP["NumPy"]
        PIL["Pillow"]
    end

    subgraph L1["Hardware & Network"]
        NIC["WiFi NIC"]
        USB["USB Camera"]
        UART2["UART/GPIO"]
        SER["Serial Port"]
    end

    L5 --> L4 --> L3 --> L2 --> L1

    style L5 fill:#1565c0,color:#fff
    style L4 fill:#283593,color:#fff
    style L3 fill:#4527a0,color:#fff
    style L2 fill:#6a1b9a,color:#fff
    style L1 fill:#880e4f,color:#fff
```

---

## Hardware Wiring

```
  ┌──────────────────────────────────────────────────────────────┐
  │                    RASPBERRY PI 3 MODEL B+                   │
  │                                                              │
  │  ┌──────────────┐   CSI Ribbon    ┌───────────────────────┐  │
  │  │ Camera Module │◄══════════════►│ CSI Port              │  │
  │  │ (v2 / USB)   │   Cable         │                       │  │
  │  └──────────────┘                 │   ┌─────────────────┐ │  │
  │                                   │   │   BCM2837B0     │ │  │
  │                                   │   │   ARM Cortex-A53│ │  │
  │  ┌──────────────┐                 │   │   1.4 GHz       │ │  │
  │  │ WiFi Module  │◄───────────────►│   │                 │ │  │
  │  │ (AP Mode)    │  Internal       │   └─────────────────┘ │  │
  │  │ 192.168.4.1  │                 │                       │  │
  │  └──────────────┘                 │   GPIO Header         │  │
  │                                   │   ┌─────────────────┐ │  │
  │                                   │   │ Pin 8  (TXD) ──────────┐  │
  │                                   │   │ Pin 10 (RXD) ──────────┤  │
  │                                   │   │ Pin 6  (GND) ──────────┤  │
  │                                   │   └─────────────────┘ │  │
  │                                   └───────────────────────┘  │
  └──────────────────────────────────────────────────────────────┘
                                              │  │  │
                                   UART       │  │  │  115200 baud
                                   3.3V TTL   │  │  │  8N1
                                              │  │  │
  ┌──────────────────────────────────────────────────────────────┐
  │                    CROSSFLIGHT FC                             │
  │                                                              │
  │   ┌─────────────────┐         ┌──────────────────────────┐  │
  │   │ UART Port       │         │ Flight Controller MCU    │  │
  │   │ TX  ◄───────────────────── Pin 8 (Pi TXD)           │  │
  │   │ RX  ────────────────────►  Pin 10 (Pi RXD)          │  │
  │   │ GND ◄───────────────────── Pin 6 (Pi GND)           │  │
  │   └─────────────────┘         │                          │  │
  │                               │ MSP Protocol Handler     │  │
  │   ┌─────────────────┐        │ • Attitude estimation    │  │
  │   │ Sensors         │        │ • GPS processing        │  │
  │   │ • Gyroscope     │────────│ • Motor mixing          │  │
  │   │ • Accelerometer │        │ • PID control           │  │
  │   │ • Magnetometer  │        │ • Battery monitoring    │  │
  │   │ • Barometer     │        └──────────────────────────┘  │
  │   │ • GPS Module    │                                      │
  │   └─────────────────┘                                      │
  └──────────────────────────────────────────────────────────────┘
```

---

## Features

### Video System

| Feature | Status | Details |
|---------|--------|---------|
| H.264 Streaming | **Active** | GStreamer RTP pipeline |
| Resolution | **1280x720** | Configurable via YAML |
| Frame Rate | **30 FPS** | Adaptive drop under load |
| Bitrate | **2 Mbps** | Configurable per-flight |
| Low-latency Decode | **Active** | `avdec_h264` with `sync=false` |
| Frame Buffer | **2 frames** | Prevents memory buildup |

### Telemetry System

| Feature | Status | Details |
|---------|--------|---------|
| JSON Telemetry | **Active** | Custom format from Pi bridge |
| MAVLink Parsing | **Active** | HEARTBEAT, SYS_STATUS, GPS_RAW_INT, ATTITUDE, VFR_HUD, BATTERY_STATUS, GLOBAL_POSITION_INT |
| Update Rate | **10 Hz** | Configurable |
| GPS Tracking | **Active** | Lat/Lon/Alt + satellite count |
| IMU Data | **Active** | Roll/Pitch/Yaw |
| Battery Monitor | **Active** | Voltage/Current/Remaining % |
| Thread-Safe Access | **Active** | Locks on all shared state |

### Flight Control

| Feature | Status | Details |
|---------|--------|---------|
| Arm / Disarm | **Active** | Safety-gated |
| Takeoff | **Active** | Configurable altitude (default 2m) |
| Land | **Active** | Controlled descent |
| Emergency Stop | **Active** | Immediate disarm + zero velocity |
| Velocity Control | **Active** | 6-DOF via `cmd_vel` |
| Flight Modes | **Active** | STABILIZE, ALT_HOLD, LOITER, RTL, GUIDED |
| Goto Waypoint | **Active** | Position + orientation |

### Safety Systems

| Feature | Status | Details |
|---------|--------|---------|
| Geofence | **Active** | Max altitude 120m, max distance 500m |
| Low Battery Alert | **Active** | Threshold: 20% |
| Auto-Land | **Active** | On low battery trigger |
| Connection Watchdog | **Active** | 5s timeout → failsafe |
| Emergency Stop | **Active** | GUI button + keyboard shortcut |

---

## Installation

### Ground Station (Windows/Linux)

```bash
# 1. Install ROS2 Humble
# Follow: https://docs.ros.org/en/humble/Installation.html

# 2. Install Python dependencies
pip install pymavlink opencv-python Pillow numpy PyGObject pyyaml psutil

# 3. Install GStreamer
# Windows: https://gstreamer.freedesktop.org/download/
# Ubuntu: sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav

# 4. Clone and build
git clone https://github.com/husam05/Andhra-University-CSSE-Drone-Ground-Station.git
cd Andhra-University-CSSE-Drone-Ground-Station
cd src && colcon build && source install/setup.bash

# 5. Launch
ros2 launch drone_ground_station ground_station.launch.py
```

### Raspberry Pi 3

```bash
# 1. Flash Raspberry Pi OS Lite (64-bit)

# 2. Run automated setup
scp scripts/raspberry_pi_setup.sh pi@192.168.4.1:~/
ssh pi@192.168.4.1 'bash ~/raspberry_pi_setup.sh'

# 3. Install Python dependencies
pip install -r raspberry_pi_requirements.txt

# 4. Configure WiFi hotspot
sudo bash scripts/pi_network_fix.sh

# 5. Start drone services
cd raspberry_pi_scripts && python3 drone_startup.py
```

---

## Configuration

### Ground Station Parameters (`config/ground_station_params.yaml`)

| Section | Parameter | Type | Default | Description |
|---------|-----------|------|---------|-------------|
| `drone_connection` | `ip` | string | `192.168.4.1` | Drone WiFi IP |
| | `video_port` | int | `5600` | Video stream port |
| | `telemetry_port` | int | `14550` | Telemetry data port |
| | `command_port` | int | `14551` | Command channel port |
| | `connection_timeout` | float | `5.0` | Connection timeout (seconds) |
| `video_streaming` | `frame_rate` | int | `30` | Target FPS |
| | `video_width` | int | `1280` | Frame width (pixels) |
| | `video_height` | int | `720` | Frame height (pixels) |
| | `codec` | string | `h264` | Video codec |
| | `bitrate` | int | `2000000` | Bitrate (bps) |
| `telemetry` | `update_rate` | float | `10.0` | Publish rate (Hz) |
| | `timeout` | float | `2.0` | Data timeout (seconds) |
| | `protocol` | string | `mavlink` | `mavlink` or `json` |
| `flight_control` | `max_velocity.linear_x` | float | `5.0` | Max forward speed (m/s) |
| | `max_velocity.linear_z` | float | `3.0` | Max vertical speed (m/s) |
| | `default_takeoff_altitude` | float | `2.0` | Default takeoff height (m) |
| `safety` | `enable_geofence` | bool | `true` | Enable geofence |
| | `max_altitude` | float | `120.0` | Altitude ceiling (m) |
| | `max_distance` | float | `500.0` | Max range (m) |
| | `low_battery_threshold` | int | `20` | Battery alarm (%) |
| | `auto_land_on_low_battery` | bool | `true` | Auto-land trigger |

---

## GUI Layout

```
┌────────────────────────────────────────────────────────────────────┐
│                    Drone Ground Station                             │
├──────────────────────────────────┬─────────────────────────────────┤
│                                  │  TELEMETRY                      │
│                                  │  ─────────────────────────────  │
│        VIDEO FEED                │  Connection:  YES / NO          │
│                                  │  Armed:       YES / NO          │
│    ┌────────────────────────┐    │  Mode:        STABILIZE         │
│    │                        │    │  Battery:     85.0%             │
│    │   Live Camera Feed     │    │  Voltage:     12.60V            │
│    │   640 x 480 viewport   │    │  Altitude:    25.0m             │
│    │                        │    │  Speed:       3.5m/s            │
│    │   (H.264 decoded)      │    │  GPS Lat:     17.730000         │
│    │                        │    │  GPS Lon:     83.300000         │
│    └────────────────────────┘    │  Satellites:  12                │
│                                  │                                 │
├──────────────────────────────────┼─────────────────────────────────┤
│  FLIGHT CONTROLS                 │  SYSTEM STATUS                  │
│  ─────────────────────────────   │  ─────────────────────────────  │
│  [ ARM ] [TAKEOFF] [ LAND ]     │  [12:34:56] Connected to drone  │
│          [EMERGENCY]             │  [12:34:57] Telemetry OK        │
│                                  │  [12:35:01] Armed               │
│  Movement:    Altitude:          │  [12:35:02] Takeoff 2.0m        │
│      [↑]      [UP  ]            │  [12:35:10] Altitude reached    │
│   [←][■][→]   [DOWN]            │  [12:36:45] Land command sent   │
│      [↓]                        │  [12:36:52] Landed              │
│                                  │                                 │
└──────────────────────────────────┴─────────────────────────────────┘
```

---

## API Reference

### Published Topics (Ground Station → ROS2)

| Topic | Message Type | Rate | Description |
|-------|-------------|------|-------------|
| `/drone/camera/image_raw` | `sensor_msgs/Image` | 30 Hz | Decoded video frames (BGR8) |
| `/drone/battery` | `sensor_msgs/BatteryState` | 10 Hz | Voltage, current, remaining % |
| `/drone/gps` | `sensor_msgs/NavSatFix` | 10 Hz | Latitude, longitude, altitude |
| `/drone/imu` | `sensor_msgs/Imu` | 10 Hz | Orientation and angular velocity |
| `/drone/altitude` | `std_msgs/Float32` | 10 Hz | Relative altitude (meters) |
| `/drone/heading` | `std_msgs/Float32` | 10 Hz | Heading (degrees) |
| `/drone/armed` | `std_msgs/Bool` | 10 Hz | Armed state |
| `/drone/mode` | `std_msgs/String` | 10 Hz | Flight mode name |
| `/drone/status` | `std_msgs/String` | 10 Hz | Full telemetry JSON |
| `/drone/connection_status` | `std_msgs/Bool` | 0.5 Hz | TCP connection state |
| `/drone/command_ack` | `std_msgs/String` | Event | Command acknowledgment |

### Subscribed Topics (ROS2 → Ground Station)

| Topic | Message Type | Description |
|-------|-------------|-------------|
| `/drone/cmd_vel` | `geometry_msgs/Twist` | Velocity command (6-DOF) |
| `/drone/arm` | `std_msgs/Bool` | Arm (`true`) / Disarm (`false`) |
| `/drone/takeoff` | `std_msgs/Float32` | Takeoff to altitude (meters) |
| `/drone/land` | `std_msgs/Bool` | Land command |
| `/drone/set_mode` | `std_msgs/String` | Set flight mode |
| `/drone/goto` | `geometry_msgs/PoseStamped` | Navigate to position |

---

## Project Structure

```
Andhra-University-CSSE-Drone-Ground-Station/
├── src/drone_ground_station/           # ROS2 Package
│   ├── scripts/
│   │   ├── video_receiver.py           # GStreamer H.264 decoder node
│   │   ├── telemetry_receiver.py       # MAVLink + JSON telemetry node
│   │   ├── mavlink_bridge.py           # Command sender node
│   │   └── ground_station_gui.py       # Tkinter GUI node
│   ├── launch/
│   │   └── ground_station.launch.py    # ROS2 launch configuration
│   ├── config/
│   │   └── ground_station_params.yaml  # System parameters
│   ├── drone_ground_station/
│   │   └── __init__.py
│   ├── setup.py                        # Python package setup
│   ├── package.xml                     # ROS2 package manifest
│   └── CMakeLists.txt                  # Build configuration
│
├── raspberry_pi_scripts/               # Drone-side (Raspberry Pi 3)
│   ├── video_streamer.py               # Camera → H.264 → UDP
│   ├── telemetry_bridge.py             # FC ↔ UART ↔ UDP bridge
│   ├── drone_startup.py                # Boot service manager
│   └── config.json                     # Pi configuration
│
├── scripts/                            # Setup & testing utilities
│   ├── raspberry_pi_setup.sh           # Pi OS provisioning
│   ├── pi_network_fix.sh              # WiFi hotspot setup
│   ├── laptop_setup.py                 # Windows GS setup
│   ├── quick_start.py                  # Interactive wizard
│   ├── system_integration_test.py      # E2E system tests
│   └── remote_pi_setup.py             # Remote Pi provisioning
│
├── examples/                           # Demo scripts
│   ├── basic_flight_demo.py            # Flight command examples
│   ├── telemetry_monitor.py            # Real-time data viewer
│   ├── video_analyzer.py               # Stream analysis
│   └── integration_test.py             # Integration tests
│
├── Documentation/                      # Extended docs
│   ├── ARCHITECTURE.md                 # Deep architecture reference
│   ├── API_REFERENCE.md                # Complete API documentation
│   ├── DIAGRAMS.md                     # Visual diagram gallery
│   └── ...
│
├── requirements.txt                    # GS Python dependencies
├── raspberry_pi_requirements.txt       # Pi Python dependencies
├── deploy.py                           # Deployment automation
├── test_system.py                      # System test suite
├── CONTRIBUTING.md                     # Contribution guide
├── CHANGELOG.md                        # Version history
└── README.md                           # This file
```

---

## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Video Resolution | 1280 x 720 | Configurable |
| Video Frame Rate | 30 FPS | At source; display at 30 FPS |
| Video Bitrate | 2 Mbps | H.264 ultrafast preset |
| Video Latency | ~100-200 ms | End-to-end (camera → GUI) |
| Telemetry Rate | 10 Hz | Configurable up to 50 Hz |
| Command Rate | 10 Hz | TCP with JSON serialization |
| GUI Refresh | 10 Hz | Tkinter update cycle |
| WiFi Range | ~50-100 m | Depends on Pi antenna |
| Serial Baud Rate | 115200 | UART to Crossflight FC |
| MSP Cycle | ~100 ms | 9 MSP requests per cycle |

---

## Safety Systems

### Geofence

The system enforces a virtual boundary around the takeoff point:
- **Maximum altitude**: 120 meters (configurable)
- **Maximum horizontal distance**: 500 meters (configurable)
- **Breach action**: Automatic RTL (Return to Launch)

### Battery Protection

```mermaid
flowchart TD
    A["Battery Monitor<br/>10 Hz polling"] --> B{Voltage < 20%?}
    B -- No --> A
    B -- Yes --> C{Auto-land enabled?}
    C -- Yes --> D["Initiate Auto-Land<br/>Descent rate: 2 m/s"]
    C -- No --> E["Alert Operator<br/>GUI warning + log"]
    D --> F["Monitor descent"]
    F --> G{Landed?}
    G -- No --> F
    G -- Yes --> H["Disarm motors"]

    style A fill:#1565c0,color:#fff
    style B fill:#f57f17,color:#fff
    style D fill:#c62828,color:#fff
    style H fill:#2e7d32,color:#fff
```

### Emergency Stop Sequence

1. GUI "EMERGENCY" button pressed
2. Disarm command sent immediately (`armed: false`)
3. All velocity commands zeroed
4. Command queue flushed
5. Status logged: `EMERGENCY STOP ACTIVATED`

### Connection Watchdog

- Telemetry timeout: **5 seconds**
- On timeout: log warning, attempt reconnect
- Persistent loss (>15s): trigger RTL if armed

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No video feed | GStreamer not installed | Install `gstreamer1.0-plugins-good gstreamer1.0-libav` |
| Video black screen | Wrong port or firewall | Check UDP 5600 is open, verify Pi IP |
| Telemetry timeout | Pi not streaming | SSH to Pi, check `telemetry_bridge.py` is running |
| Connection refused (TCP) | Command port blocked | Check TCP 14551, verify Pi firewall |
| GUI not launching | Missing Tkinter | `sudo apt install python3-tk` |
| `No camera detected` | Camera not connected | Check CSI ribbon cable or USB device |
| MSP checksum errors | Wiring issue | Verify TX↔RX crossover, check baud rate |
| Import error: `pymavlink` | Missing dependency | `pip install pymavlink>=2.4.0` |
| ROS2 topic not found | Node not running | `ros2 node list` to verify nodes |
| High latency video | Bitrate too high | Reduce `bitrate` in YAML config |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Deep technical architecture, thread models, protocol details |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API — ROS2 topics, MAVLink, MSP, JSON schemas |
| [DIAGRAMS.md](DIAGRAMS.md) | Visual gallery of 20+ Mermaid diagrams |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute to this project |
| [CHANGELOG.md](CHANGELOG.md) | Version history and changes |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation guide |
| [QUICK_START.md](QUICK_START.md) | Quick launch procedures |
| [HARDWARE_WIRING_GUIDE.md](HARDWARE_WIRING_GUIDE.md) | Physical wiring reference |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Pre-flight verification |

---

## Academic Information

| | |
|---|---|
| **Institution** | Andhra University |
| **Department** | Computer Science & Systems Engineering (CSSE) |
| **Project Type** | Research & Development |
| **Domains** | Distributed Systems, Computer Vision, Autonomous Vehicles, ROS2 |

This project serves as a practical implementation of:
- **Distributed systems** — ROS2 pub/sub across networked devices
- **Real-time data processing** — 30 FPS video + 10 Hz telemetry
- **Computer vision** — GStreamer/OpenCV pipeline
- **Embedded systems** — Raspberry Pi + UART + flight controller
- **Protocol engineering** — MAVLink, MSP, JSON, RTP
- **Safety-critical systems** — Geofencing, watchdogs, failsafes

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues, features, and pull requests.

---

## License

This project is licensed under the MIT License — developed for educational and research purposes at **Andhra University, Department of Computer Science & Systems Engineering**.

---

<p align="center">
  <strong>Andhra University — Department of Computer Science & Systems Engineering</strong><br/>
  <em>Building the future of autonomous systems, one drone at a time</em>
</p>
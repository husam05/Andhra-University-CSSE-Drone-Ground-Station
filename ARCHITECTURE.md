# Architecture Reference

> Deep technical architecture documentation for the Drone Ground Station system.

---

## 1. System Overview (C4 Model)

```mermaid
graph TB
    subgraph Context["System Context"]
        PILOT["Pilot / Operator"]
        GS_SYS["Ground Station System"]
        DRONE_SYS["Drone System"]
    end

    PILOT -->|"Monitor & Control"| GS_SYS
    GS_SYS <-->|"WiFi 802.11n"| DRONE_SYS

    subgraph Container["Container Diagram — Ground Station"]
        direction TB
        GUI_C["GUI Container<br/><i>Tkinter Application</i><br/>Video display, telemetry dashboard,<br/>flight controls, status log"]
        VID_C["Video Container<br/><i>GStreamer Pipeline</i><br/>H.264 RTP decode,<br/>frame extraction"]
        TEL_C["Telemetry Container<br/><i>UDP Listener</i><br/>JSON + MAVLink parsing,<br/>ROS2 topic publishing"]
        CMD_C["Command Container<br/><i>TCP Client</i><br/>JSON command serialization,<br/>queue management"]
        ROS_C["ROS2 Middleware<br/><i>DDS Transport</i><br/>Topic pub/sub, parameter server,<br/>node lifecycle"]
    end

    subgraph Container2["Container Diagram — Drone"]
        direction TB
        VID_D["Video Streamer<br/><i>GStreamer Pipeline</i><br/>Camera capture, H.264 encode,<br/>RTP/UDP stream"]
        TEL_D["Telemetry Bridge<br/><i>Serial ↔ Network</i><br/>MSP protocol, JSON conversion,<br/>UDP sender"]
        BOOT_D["Startup Manager<br/><i>Service Supervisor</i><br/>WiFi AP, process monitor,<br/>auto-restart"]
        FC_D["Crossflight FC<br/><i>Flight Controller</i><br/>Attitude estimation, GPS,<br/>motor control, MSP server"]
    end

    GUI_C <--> ROS_C
    VID_C --> ROS_C
    TEL_C --> ROS_C
    CMD_C <--> ROS_C

    VID_D -->|"UDP :5600"| VID_C
    TEL_D -->|"UDP :14550"| TEL_C
    CMD_C -->|"TCP :14551"| TEL_D
    FC_D <-->|"UART MSP"| TEL_D

    style Context fill:#0d47a1,color:#fff
    style Container fill:#1a237e,color:#fff
    style Container2 fill:#1b5e20,color:#fff
```

---

## 2. Component Deep Dive

### 2.1 TelemetryReceiver (Ground Station)

**Purpose**: Receive and parse telemetry data from drone, publish as ROS2 messages.

**Internal Architecture**:
```mermaid
classDiagram
    class TelemetryReceiver {
        -_telemetry_lock: threading.Lock
        -telemetry_data: Dict
        -telemetry_socket: socket
        -_mav: MAVLink
        -running: bool
        +setup_publishers()
        +telemetry_receiver_loop()
        +connect_telemetry()
        +receive_telemetry_data()
        +parse_telemetry_data(data: bytes)
        +update_telemetry_from_json(data: Dict)
        +parse_mavlink_data(data: bytes)
        -_handle_mavlink_message(msg)
        -_update_field(key, value)
        -_update_fields(updates: Dict)
        -_get_telemetry_snapshot() Dict
        +publish_telemetry()
    }

    class MAVLinkParser {
        +parse_char(byte) msg
        +robust_parsing: bool
    }

    class ThreadModel {
        +main_thread: ROS2 spin
        +telemetry_thread: UDP receiver
        +timer_callback: publish at 10Hz
    }

    TelemetryReceiver --> MAVLinkParser : uses
    TelemetryReceiver --> ThreadModel : threading
```

**Thread Model**:
- **Main thread**: ROS2 executor (`rclpy.spin`) — runs timer callbacks
- **Telemetry thread** (daemon): Blocks on `socket.recvfrom()`, parses data, updates shared state
- **Lock**: `_telemetry_lock` protects `telemetry_data` dict

**Supported MAVLink Messages**:

| Message | ID | Fields Extracted |
|---------|-----|-----------------|
| HEARTBEAT | 0 | `base_mode` (armed flag), `custom_mode` (flight mode) |
| SYS_STATUS | 1 | `voltage_battery`, `current_battery`, `battery_remaining` |
| GPS_RAW_INT | 24 | `lat`, `lon`, `alt`, `satellites_visible`, `fix_type`, `vel`, `cog` |
| ATTITUDE | 30 | `roll`, `pitch`, `yaw` (radians) |
| GLOBAL_POSITION_INT | 33 | `lat`, `lon`, `relative_alt`, `hdg` |
| VFR_HUD | 74 | `groundspeed`, `alt`, `heading` |
| BATTERY_STATUS | 147 | `voltages[]`, `current_battery`, `battery_remaining` |

### 2.2 MAVLinkBridge (Ground Station)

**Purpose**: Receive flight commands from ROS2 topics, serialize as JSON, send to drone via TCP.

```mermaid
classDiagram
    class MAVLinkBridge {
        -command_queue: deque~maxlen=100~
        -command_lock: threading.Lock
        -command_socket: socket
        -connected: bool
        +setup_subscribers()
        +check_connection()
        +connect_to_drone()
        +send_command(data: Dict)
        +command_sender_loop()
        +send_command_to_drone(data: Dict)
        +cmd_vel_callback(msg: Twist)
        +arm_callback(msg: Bool)
        +takeoff_callback(msg: Float32)
        +land_callback(msg: Bool)
        +mode_callback(msg: String)
        +goto_callback(msg: PoseStamped)
    }
```

**Thread Model**:
- **Main thread**: ROS2 spin — handles subscription callbacks, enqueues commands
- **Command sender thread** (daemon): Dequeues and sends at 10 Hz
- **Lock**: `command_lock` protects `command_queue`
- **Queue**: `deque(maxlen=100)` — bounded, O(1) popleft, drops oldest on overflow

### 2.3 VideoReceiver (Ground Station)

```mermaid
classDiagram
    class VideoReceiver {
        -pipeline: Gst.Pipeline
        -latest_frame: np.ndarray
        -frame_lock: threading.Lock
        +setup_gstreamer_pipeline() bool
        +on_new_sample(appsink) FlowReturn
        +publish_frame()
    }
```

**GStreamer Pipeline**:
```
udpsrc port=5600 caps="application/x-rtp,payload=96"
  → rtph264depay
  → h264parse
  → avdec_h264
  → videoconvert
  → video/x-raw,format=BGR
  → appsink name=sink emit-signals=true sync=false max-buffers=2 drop=true
```

### 2.4 TelemetryBridge (Raspberry Pi)

```mermaid
classDiagram
    class TelemetryBridge {
        -_telemetry_lock: threading.Lock
        -telemetry_data: Dict
        -serial_connection: Serial
        -telemetry_socket: socket~UDP~
        -command_socket: socket~TCP~
        +setup_serial_connection() bool
        +setup_network_sockets() bool
        +read_crossflight_telemetry()
        +request_msp_data()
        +send_msp_request(msg_id: int)
        +read_msp_response() Dict
        +parse_msp_response(msg_id, response)
        -_update_telemetry(path: str, value)
        -_get_telemetry_snapshot() Dict
        +send_telemetry_to_ground_station()
        +handle_ground_station_commands()
        +process_client_commands(socket)
        +execute_command(command: Dict)
    }
```

**Thread Model (3 daemon threads)**:
```mermaid
graph LR
    subgraph TelemetryBridge
        T1["TelemetryReader<br/>Serial UART → MSP parse<br/>→ update telemetry_data"]
        T2["TelemetrySender<br/>telemetry_data → JSON<br/>→ UDP to GS"]
        T3["CommandHandler<br/>TCP accept → JSON parse<br/>→ execute_command"]
        LOCK["_telemetry_lock<br/>protects telemetry_data"]
    end

    T1 -->|"write"| LOCK
    T2 -->|"read"| LOCK
    T3 -.->|"indirect"| LOCK

    style LOCK fill:#c62828,color:#fff
```

---

## 3. Communication Architecture

### 3.1 Full Data Path — Video

```mermaid
sequenceDiagram
    participant Sensor as Camera Sensor
    participant V4L as V4L2 / libcamera
    participant Enc as x264enc (Pi)
    participant RTP as rtph264pay
    participant UDP_S as UDP Socket (Pi:ephemeral)
    participant UDP_R as UDP Socket (GS:5600)
    participant Depay as rtph264depay
    participant Dec as avdec_h264
    participant CV as videoconvert → BGR
    participant Sink as appsink
    participant Node as VideoReceiver Node
    participant Topic as /drone/camera/image_raw
    participant GUI as GUI Video Display

    Sensor->>V4L: Raw Bayer / YUV
    V4L->>Enc: video/x-raw 1280x720@30fps
    Enc->>RTP: H.264 NAL units
    RTP->>UDP_S: RTP packets (payload=96)
    UDP_S->>UDP_R: UDP datagrams → GS:5600
    UDP_R->>Depay: RTP → H.264 stream
    Depay->>Dec: H.264 → raw frames
    Dec->>CV: YUV → BGR conversion
    CV->>Sink: numpy array (720×1280×3)
    Sink->>Node: on_new_sample callback
    Node->>Topic: cv_bridge → Image msg
    Topic->>GUI: subscription callback
    GUI->>GUI: resize → PIL → Tkinter
```

### 3.2 Full Data Path — Telemetry

```mermaid
sequenceDiagram
    participant IMU as Sensors (Gyro/Accel/Mag/GPS)
    participant FC as Crossflight FC
    participant UART as UART /dev/ttyAMA0
    participant Bridge as TelemetryBridge
    participant JSON as JSON Serializer
    participant UDP as UDP :14550
    participant Recv as TelemetryReceiver
    participant Topics as ROS2 Topics (11)
    participant GUI as GUI Telemetry Panel

    IMU->>FC: Analog/Digital sensor data
    FC->>FC: Attitude estimation + filtering
    Note over Bridge: MSP Request Cycle (100ms)
    Bridge->>UART: $M< 0 100 100 (MSP_STATUS request)
    UART->>FC: MSP request
    FC->>UART: $M> 11 100 [data] [checksum]
    UART->>Bridge: MSP response bytes
    Bridge->>Bridge: struct.unpack → Python dict
    Bridge->>JSON: telemetry_data → json.dumps
    JSON->>UDP: UTF-8 bytes → sendto(GS:14550)
    UDP->>Recv: recvfrom → parse JSON
    Recv->>Recv: update_telemetry_from_json()
    Recv->>Topics: publish battery, gps, altitude...
    Topics->>GUI: subscription callbacks
    GUI->>GUI: update StringVar displays
```

### 3.3 Full Data Path — Commands

```mermaid
sequenceDiagram
    participant Pilot as Operator
    participant Button as GUI Button
    participant Pub as ROS2 Publisher
    participant Topic as /drone/cmd_vel etc.
    participant Sub as MAVLinkBridge
    participant Queue as deque(maxlen=100)
    participant TCP as TCP :14551
    participant Bridge as TelemetryBridge (Pi)
    participant FC as Crossflight FC

    Pilot->>Button: Click "TAKEOFF"
    Button->>Pub: Float32(data=2.0)
    Pub->>Topic: /drone/takeoff
    Topic->>Sub: takeoff_callback
    Sub->>Queue: {'type':'takeoff','altitude':2.0}
    Note over Queue: command_sender_loop @ 10Hz
    Queue->>TCP: json.dumps + '\n'
    TCP->>Bridge: recv → JSON parse
    Bridge->>Bridge: execute_command
    Bridge->>FC: MSP command via UART
    FC-->>Bridge: MSP ACK
```

---

## 4. Protocol Details

### 4.1 MSP v1 Packet Format

```
Request:  $  M  <  [data_length]  [msg_id]  [checksum]
          24 4D 3C     00            64         64

Response: $  M  >  [data_length]  [msg_id]  [payload...]  [checksum]
          24 4D 3E     0B            64       [11 bytes]      XX

Checksum = data_length XOR msg_id XOR payload[0] XOR ... XOR payload[N-1]
```

### 4.2 MSP Commands Used

| MSP ID | Name | Response Length | Data Fields |
|--------|------|----------------|-------------|
| 100 | MSP_STATUS | 11 bytes | cycle_time(u16), i2c_errors(u16), sensors(u16), flags(u32), current_set(u8) |
| 102 | MSP_RAW_IMU | 18 bytes | acc_xyz(i16×3), gyro_xyz(i16×3), mag_xyz(i16×3) |
| 106 | MSP_RAW_GPS | 16 bytes | fix(u8), sats(u8), lat(i32), lon(i32), alt(u16), speed(u16), course(u16) |
| 108 | MSP_ATTITUDE | 6 bytes | roll(i16/10°), pitch(i16/10°), yaw(i16°) |
| 110 | MSP_ANALOG | 7 bytes | vbat(u8/10V), power(u16), rssi(u16), amperage(u16/100A) |

### 4.3 JSON Telemetry Schema

```json
{
    "timestamp": 1712678400.0,
    "armed": true,
    "mode": "STABILIZE",
    "battery": {
        "voltage": 12.6,
        "current": 5.0,
        "remaining": 85.0
    },
    "attitude": {
        "roll": 0.1,
        "pitch": -0.2,
        "yaw": 1.5
    },
    "position": {
        "lat": 17.73,
        "lon": 83.30,
        "alt": 25.0
    },
    "velocity": {
        "ground_speed": 3.5,
        "vertical_speed": 0.0
    },
    "gps": {
        "satellites": 12,
        "fix_type": 3,
        "hdop": 1.2
    },
    "sensors": {
        "gyro":  {"x": 0, "y": 0, "z": 0},
        "accel": {"x": 0, "y": 0, "z": 512},
        "mag":   {"x": 100, "y": -50, "z": 300}
    }
}
```

### 4.4 JSON Command Schemas

**Arm/Disarm**:
```json
{"type": "arm", "armed": true, "timestamp": 1712678400.0}
```

**Velocity**:
```json
{"type": "velocity", "linear": {"x": 1.0, "y": 0.0, "z": 0.5}, "angular": {"x": 0.0, "y": 0.0, "z": 0.3}, "timestamp": 1712678400.0}
```

**Takeoff**:
```json
{"type": "takeoff", "altitude": 2.0, "timestamp": 1712678400.0}
```

**Land**:
```json
{"type": "land", "timestamp": 1712678400.0}
```

**Mode Change**:
```json
{"type": "mode", "mode": "LOITER", "timestamp": 1712678400.0}
```

**Goto**:
```json
{"type": "goto", "position": {"x": 17.73, "y": 83.30, "z": 25.0}, "orientation": {"x": 0, "y": 0, "z": 0, "w": 1}, "timestamp": 1712678400.0}
```

---

## 5. Safety Architecture

### 5.1 Failsafe Decision Tree

```mermaid
flowchart TD
    START["Monitor Loop (10 Hz)"] --> BAT{Battery < 20%?}

    BAT -- Yes --> AUTO{Auto-land<br/>enabled?}
    AUTO -- Yes --> LAND["Initiate Auto-Land"]
    AUTO -- No --> WARN1["WARN: Low Battery"]

    BAT -- No --> GEO{Geofence<br/>breached?}
    GEO -- Yes --> RTL["Initiate RTL"]
    GEO -- No --> CONN{Connection<br/>timeout > 5s?}

    CONN -- Yes --> PERSIST{Timeout<br/>> 15s?}
    PERSIST -- Yes --> RTL
    PERSIST -- No --> WARN2["WARN: Connection Lost"]

    CONN -- No --> OK["All Systems Normal"]
    OK --> START

    LAND --> DISARM["Disarm on Ground"]
    RTL --> LAND

    style START fill:#1565c0,color:#fff
    style LAND fill:#c62828,color:#fff
    style RTL fill:#e65100,color:#fff
    style OK fill:#2e7d32,color:#fff
    style WARN1 fill:#f57f17,color:#000
    style WARN2 fill:#f57f17,color:#000
```

---

## 6. Network Bandwidth Analysis

| Stream | Protocol | Packet Size | Rate | Bandwidth |
|--------|----------|-------------|------|-----------|
| Video | RTP/UDP | ~1400 bytes (MTU) | ~178 pkt/s | **2.0 Mbps** |
| Telemetry | JSON/UDP | ~500 bytes | 10 Hz | **40 Kbps** |
| Commands | JSON/TCP | ~150 bytes | 10 Hz | **12 Kbps** |
| WiFi Overhead | 802.11n | ~40 bytes/pkt | varies | ~200 Kbps |
| **Total** | | | | **~2.3 Mbps** |

WiFi 802.11n theoretical max: 72 Mbps. Operating at **~3% capacity**.

---

## 7. Deployment Architecture

### 7.1 Pi Boot Sequence

```mermaid
sequenceDiagram
    participant Boot as systemd
    participant DS as drone_startup.py
    participant WiFi as hostapd + dnsmasq
    participant VS as video_streamer.py
    participant TB as telemetry_bridge.py
    participant Mon as Process Monitor

    Boot->>DS: Service start
    DS->>DS: Load config.json
    DS->>DS: Check requirements (GStreamer, Python, Serial)
    DS->>DS: Wait startup_delay (5s)

    DS->>WiFi: Configure wlan0 as AP (192.168.4.1)
    WiFi-->>DS: Hotspot active

    DS->>VS: subprocess.Popen(video_streamer.py)
    VS-->>DS: PID registered

    DS->>TB: subprocess.Popen(telemetry_bridge.py)
    TB-->>DS: PID registered

    DS->>Mon: Start monitor thread (5s interval)

    loop Every 5 seconds
        Mon->>Mon: Check process.poll()
        alt Process died
            Mon->>Mon: Restart (max 3 attempts)
        end
    end
```

---

*This document is part of the Andhra University CSSE Drone Ground Station project.*
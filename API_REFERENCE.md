# API Reference

> Complete protocol and interface reference for the Drone Ground Station system.

---

## 1. ROS2 Topics — Published

| # | Topic | Message Type | Publisher | Rate | Description |
|---|-------|-------------|-----------|------|-------------|
| 1 | `/drone/camera/image_raw` | `sensor_msgs/Image` | video_receiver | 30 Hz | Decoded video frames (BGR8, 1280×720) |
| 2 | `/drone/battery` | `sensor_msgs/BatteryState` | telemetry_receiver | 10 Hz | Voltage (V), current (A), remaining (%) |
| 3 | `/drone/gps` | `sensor_msgs/NavSatFix` | telemetry_receiver | 10 Hz | Latitude, longitude, altitude (WGS84) |
| 4 | `/drone/imu` | `sensor_msgs/Imu` | telemetry_receiver | 10 Hz | Orientation and angular velocity |
| 5 | `/drone/altitude` | `std_msgs/Float32` | telemetry_receiver | 10 Hz | Relative altitude in meters |
| 6 | `/drone/heading` | `std_msgs/Float32` | telemetry_receiver | 10 Hz | Heading in degrees (0-360) |
| 7 | `/drone/armed` | `std_msgs/Bool` | telemetry_receiver | 10 Hz | `true` = motors armed |
| 8 | `/drone/mode` | `std_msgs/String` | telemetry_receiver | 10 Hz | Flight mode name (e.g., "STABILIZE") |
| 9 | `/drone/status` | `std_msgs/String` | telemetry_receiver | 10 Hz | Full telemetry as JSON string |
| 10 | `/drone/connection_status` | `std_msgs/Bool` | mavlink_bridge | 0.5 Hz | TCP connection state |
| 11 | `/drone/command_ack` | `std_msgs/String` | mavlink_bridge | Event | Command acknowledgment message |

## 2. ROS2 Topics — Subscribed (Commands)

| # | Topic | Message Type | Subscriber | Description |
|---|-------|-------------|------------|-------------|
| 1 | `/drone/cmd_vel` | `geometry_msgs/Twist` | mavlink_bridge | 6-DOF velocity command |
| 2 | `/drone/arm` | `std_msgs/Bool` | mavlink_bridge | Arm (`true`) / Disarm (`false`) |
| 3 | `/drone/takeoff` | `std_msgs/Float32` | mavlink_bridge | Takeoff to altitude (meters) |
| 4 | `/drone/land` | `std_msgs/Bool` | mavlink_bridge | Initiate landing |
| 5 | `/drone/set_mode` | `std_msgs/String` | mavlink_bridge | Set flight mode by name |
| 6 | `/drone/goto` | `geometry_msgs/PoseStamped` | mavlink_bridge | Navigate to position + orientation |

---

## 3. MAVLink Message Reference

### Supported Messages

| Message | ID | Direction | Fields |
|---------|-----|-----------|--------|
| **HEARTBEAT** | 0 | FC → GS | `base_mode` (uint8), `custom_mode` (uint32) |
| **SYS_STATUS** | 1 | FC → GS | `voltage_battery` (mV, uint16), `current_battery` (cA, int16), `battery_remaining` (%, int8) |
| **GPS_RAW_INT** | 24 | FC → GS | `lat` (degE7, int32), `lon` (degE7, int32), `alt` (mm, int32), `vel` (cm/s, uint16), `cog` (cdeg, uint16), `satellites_visible` (uint8), `fix_type` (uint8) |
| **ATTITUDE** | 30 | FC → GS | `roll` (rad, float), `pitch` (rad, float), `yaw` (rad, float) |
| **GLOBAL_POSITION_INT** | 33 | FC → GS | `lat` (degE7), `lon` (degE7), `relative_alt` (mm), `hdg` (cdeg) |
| **VFR_HUD** | 74 | FC → GS | `groundspeed` (m/s, float), `alt` (m, float), `heading` (deg, int16) |
| **BATTERY_STATUS** | 147 | FC → GS | `voltages[10]` (mV, uint16), `current_battery` (cA, int16), `battery_remaining` (%, int8) |

### Unit Conversions

| Field | Raw Unit | Conversion | Result Unit |
|-------|----------|------------|-------------|
| `voltage_battery` | millivolts | `÷ 1000` | Volts |
| `current_battery` | centi-Amps | `÷ 100` | Amps |
| `lat` / `lon` | degE7 | `÷ 1e7` | Degrees |
| `alt` (GPS_RAW_INT) | millimeters | `÷ 1000` | Meters |
| `relative_alt` | millimeters | `÷ 1000` | Meters |
| `vel` | cm/s | `÷ 100` | m/s |
| `cog` / `hdg` | centi-degrees | `÷ 100` | Degrees |

### Flight Mode Map (custom_mode)

| ID | Mode | Description |
|----|------|-------------|
| 0 | STABILIZE | Manual angle control |
| 1 | ACRO | Rate control |
| 2 | ALT_HOLD | Altitude hold |
| 3 | AUTO | Autonomous waypoints |
| 4 | GUIDED | Position control via commands |
| 5 | LOITER | GPS position hold |
| 6 | RTL | Return to launch |
| 7 | CIRCLE | Orbit around point |
| 9 | LAND | Controlled descent |
| 16 | POSHOLD | Position hold (simplified) |
| 21 | SMART_RTL | Smart return to launch |

### GPS Fix Types

| Value | Meaning |
|-------|---------|
| 0 | No fix |
| 1 | No fix |
| 2 | 2D fix |
| 3 | 3D fix |
| 4 | DGPS |
| 5 | RTK Float |
| 6 | RTK Fixed |

---

## 4. MSP Protocol Reference

### Packet Format

**Request** (Ground/Pi → FC):
```
Byte:  0    1    2    3           4        5
Data: '$'  'M'  '<'  data_len   msg_id   checksum
Hex:  24   4D   3C   00         XX       XX
```

**Response** (FC → Pi):
```
Byte:  0    1    2    3           4        5..N+4     N+5
Data: '$'  'M'  '>'  data_len   msg_id   payload    checksum
Hex:  24   4D   3E   XX         XX       [...]      XX
```

**Checksum**: `data_length XOR msg_id XOR payload[0] XOR ... XOR payload[N-1]`

### MSP Commands

#### MSP_STATUS (100) — 11 bytes

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 2 | uint16_le | cycle_time (microseconds) |
| 2 | 2 | uint16_le | i2c_error_count |
| 4 | 2 | uint16_le | active_sensors (bitmask) |
| 6 | 4 | uint32_le | flags (bit 0 = armed) |
| 10 | 1 | uint8 | current_profile_set |

#### MSP_RAW_IMU (102) — 18 bytes

| Offset | Size | Type | Field | Unit |
|--------|------|------|-------|------|
| 0 | 2 | int16_le | acc_x | raw |
| 2 | 2 | int16_le | acc_y | raw |
| 4 | 2 | int16_le | acc_z | raw (≈512 at 1g) |
| 6 | 2 | int16_le | gyro_x | raw |
| 8 | 2 | int16_le | gyro_y | raw |
| 10 | 2 | int16_le | gyro_z | raw |
| 12 | 2 | int16_le | mag_x | raw |
| 14 | 2 | int16_le | mag_y | raw |
| 16 | 2 | int16_le | mag_z | raw |

#### MSP_RAW_GPS (106) — 16 bytes

| Offset | Size | Type | Field | Unit |
|--------|------|------|-------|------|
| 0 | 1 | uint8 | fix_type | enum |
| 1 | 1 | uint8 | num_satellites | count |
| 2 | 4 | int32_le | latitude | degrees × 10^7 |
| 6 | 4 | int32_le | longitude | degrees × 10^7 |
| 10 | 2 | uint16_le | altitude | meters |
| 12 | 2 | uint16_le | ground_speed | cm/s |
| 14 | 2 | uint16_le | ground_course | degrees × 10 |

#### MSP_ATTITUDE (108) — 6 bytes

| Offset | Size | Type | Field | Unit |
|--------|------|------|-------|------|
| 0 | 2 | int16_le | roll | degrees × 10 |
| 2 | 2 | int16_le | pitch | degrees × 10 |
| 4 | 2 | int16_le | yaw | degrees |

#### MSP_ANALOG (110) — 7 bytes

| Offset | Size | Type | Field | Unit |
|--------|------|------|-------|------|
| 0 | 1 | uint8 | vbat | volts × 10 |
| 1 | 2 | uint16_le | power_meter | mAh |
| 3 | 2 | uint16_le | rssi | 0-1023 |
| 5 | 2 | uint16_le | amperage | centi-Amps |

---

## 5. JSON Telemetry Schema

```json
{
    "timestamp": 1712678400.0,
    "armed": false,
    "mode": "STABILIZE",
    "battery": {
        "voltage": 12.6,
        "current": 5.0,
        "remaining": 85.0
    },
    "attitude": {
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0
    },
    "position": {
        "lat": 17.73,
        "lon": 83.30,
        "alt": 0.0
    },
    "velocity": {
        "ground_speed": 0.0,
        "vertical_speed": 0.0
    },
    "gps": {
        "satellites": 0,
        "fix_type": 0,
        "hdop": 0.0
    },
    "sensors": {
        "gyro":  {"x": 0.0, "y": 0.0, "z": 0.0},
        "accel": {"x": 0.0, "y": 0.0, "z": 0.0},
        "mag":   {"x": 0.0, "y": 0.0, "z": 0.0}
    }
}
```

### Field Reference

| Path | Type | Unit | Range | Description |
|------|------|------|-------|-------------|
| `timestamp` | float | Unix epoch | > 0 | Time of data collection |
| `armed` | bool | — | true/false | Motor arming state |
| `mode` | string | — | see mode table | Current flight mode |
| `battery.voltage` | float | Volts | 0-25.2 | Battery voltage (3S: 9.0-12.6V) |
| `battery.current` | float | Amps | 0-100 | Current draw |
| `battery.remaining` | float | % | 0-100 | Remaining capacity |
| `attitude.roll` | float | degrees | -180 to 180 | Roll angle |
| `attitude.pitch` | float | degrees | -90 to 90 | Pitch angle |
| `attitude.yaw` | float | degrees | 0-360 | Yaw heading |
| `position.lat` | float | degrees | -90 to 90 | WGS84 latitude |
| `position.lon` | float | degrees | -180 to 180 | WGS84 longitude |
| `position.alt` | float | meters | 0-120 | Altitude AGL |
| `velocity.ground_speed` | float | m/s | 0-50 | Ground speed |
| `gps.satellites` | int | count | 0-30 | Visible satellites |
| `gps.fix_type` | int | enum | 0-6 | GPS fix quality |

---

## 6. JSON Command Protocol

All commands are JSON objects terminated by `\n`, sent over TCP port 14551.

### Arm / Disarm

```json
{"type": "arm", "armed": true, "timestamp": 1712678400.0}
```
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | yes | Always `"arm"` |
| `armed` | bool | yes | `true` = arm, `false` = disarm |
| `timestamp` | float | yes | Unix timestamp |

### Velocity

```json
{
    "type": "velocity",
    "linear": {"x": 1.0, "y": 0.0, "z": 0.5},
    "angular": {"x": 0.0, "y": 0.0, "z": 0.3},
    "timestamp": 1712678400.0
}
```
| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `linear.x` | float | m/s | Forward (+) / Backward (-) |
| `linear.y` | float | m/s | Left (+) / Right (-) |
| `linear.z` | float | m/s | Up (+) / Down (-) |
| `angular.z` | float | rad/s | Yaw left (+) / right (-) |

### Takeoff

```json
{"type": "takeoff", "altitude": 2.0, "timestamp": 1712678400.0}
```
| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `altitude` | float | meters | Target takeoff altitude |

### Land

```json
{"type": "land", "timestamp": 1712678400.0}
```

### Mode Change

```json
{"type": "mode", "mode": "LOITER", "timestamp": 1712678400.0}
```
| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Target flight mode name |

### Goto Position

```json
{
    "type": "goto",
    "position": {"x": 17.73, "y": 83.30, "z": 25.0},
    "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
    "timestamp": 1712678400.0
}
```

---

## 7. GStreamer Pipeline Reference

### Sender (Raspberry Pi)

```
libcamerasrc / v4l2src device=/dev/video0
! video/x-raw,width=1280,height=720,framerate=30/1
! videoconvert
! x264enc bitrate=2000 speed-preset=ultrafast tune=zerolatency
! rtph264pay config-interval=1 pt=96
! udpsink host=192.168.4.19 port=5600
```

| Element | Purpose |
|---------|---------|
| `libcamerasrc` / `v4l2src` | Camera capture source |
| `videoconvert` | Color space conversion |
| `x264enc` | H.264 software encoder |
| `rtph264pay` | RTP packetization (RFC 6184) |
| `udpsink` | UDP network output |

### Receiver (Ground Station)

```
udpsrc port=5600 caps="application/x-rtp,payload=96"
! rtph264depay
! h264parse
! avdec_h264
! videoconvert
! video/x-raw,format=BGR
! appsink name=sink emit-signals=true sync=false max-buffers=2 drop=true
```

| Element | Purpose |
|---------|---------|
| `udpsrc` | UDP network input |
| `rtph264depay` | RTP depacketization |
| `h264parse` | H.264 stream parsing |
| `avdec_h264` | FFmpeg H.264 decoder |
| `videoconvert` | Convert to BGR for OpenCV |
| `appsink` | Application access to frames |

---

## 8. Configuration Reference

### Ground Station (`ground_station_params.yaml`)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `drone_connection.ip` | string | `192.168.4.1` | valid IP | Drone IP address |
| `drone_connection.video_port` | int | `5600` | 1024-65535 | Video stream port |
| `drone_connection.telemetry_port` | int | `14550` | 1024-65535 | Telemetry port |
| `drone_connection.command_port` | int | `14551` | 1024-65535 | Command port |
| `drone_connection.connection_timeout` | float | `5.0` | 1.0-30.0 | Timeout (seconds) |
| `video_streaming.frame_rate` | int | `30` | 1-60 | FPS |
| `video_streaming.video_width` | int | `1280` | 320-1920 | Frame width |
| `video_streaming.video_height` | int | `720` | 240-1080 | Frame height |
| `video_streaming.bitrate` | int | `2000000` | 500000-8000000 | Bitrate (bps) |
| `telemetry.update_rate` | float | `10.0` | 1.0-50.0 | Publish rate (Hz) |
| `safety.enable_geofence` | bool | `true` | — | Enable geofence |
| `safety.max_altitude` | float | `120.0` | 10-500 | Max altitude (m) |
| `safety.max_distance` | float | `500.0` | 50-5000 | Max range (m) |
| `safety.low_battery_threshold` | int | `20` | 5-50 | Battery alarm (%) |

### Raspberry Pi (`config.json`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ground_station_ip` | string | `192.168.4.19` | GS IP address |
| `telemetry_port` | int | `14550` | Telemetry destination port |
| `command_port` | int | `14551` | Command listen port |
| `serial_port` | string | `/dev/ttyAMA0` | FC serial device |
| `serial_baudrate` | int | `115200` | UART baud rate |
| `telemetry_rate` | int | `10` | Telemetry send rate (Hz) |
| `camera_width` | int | `1280` | Capture width |
| `camera_height` | int | `720` | Capture height |
| `framerate` | int | `30` | Capture FPS |
| `bitrate` | int | `2000000` | H.264 bitrate (bps) |

---

## 9. Network Specifications

### Port Allocation

| Port | Protocol | Direction | Purpose | Payload |
|------|----------|-----------|---------|---------|
| 5600 | UDP | Pi → GS | Video stream | H.264 RTP packets |
| 14550 | UDP | Pi → GS | Telemetry | JSON UTF-8 |
| 14551 | TCP | GS → Pi | Commands | JSON UTF-8 + `\n` |
| 67-68 | UDP | Pi → GS | DHCP | IP assignment |

### Protocol Selection Rationale

| Channel | Protocol | Why |
|---------|----------|-----|
| Video | UDP | Low-latency; dropped frames acceptable; no retransmit overhead |
| Telemetry | UDP | High-frequency updates; stale data disposable; fire-and-forget |
| Commands | TCP | Reliability required; ordered delivery; acknowledgment needed |

### Bandwidth Budget

| Stream | Bandwidth | % of WiFi |
|--------|-----------|-----------|
| Video (H.264) | 2.0 Mbps | 2.8% |
| Telemetry (JSON) | 40 Kbps | 0.05% |
| Commands (JSON) | 12 Kbps | 0.02% |
| Protocol overhead | ~200 Kbps | 0.3% |
| **Total** | **~2.3 Mbps** | **~3.1%** |

WiFi 802.11n max throughput: ~72 Mbps (single stream, 20 MHz).

---

## 10. Code Examples

### Subscribe to Telemetry (Python)

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState, NavSatFix
from std_msgs.msg import Float32, Bool, String

class MyTelemetryListener(Node):
    def __init__(self):
        super().__init__('my_listener')
        self.create_subscription(BatteryState, 'drone/battery', self.on_battery, 10)
        self.create_subscription(NavSatFix, 'drone/gps', self.on_gps, 10)
        self.create_subscription(Float32, 'drone/altitude', self.on_altitude, 10)
        self.create_subscription(Bool, 'drone/armed', self.on_armed, 10)

    def on_battery(self, msg):
        print(f'Battery: {msg.voltage:.1f}V, {msg.percentage:.0f}%')

    def on_gps(self, msg):
        print(f'GPS: {msg.latitude:.6f}, {msg.longitude:.6f}')

    def on_altitude(self, msg):
        print(f'Altitude: {msg.data:.1f}m')

    def on_armed(self, msg):
        print(f'Armed: {msg.data}')

rclpy.init()
rclpy.spin(MyTelemetryListener())
```

### Send a Command (Python)

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String

class MyCommander(Node):
    def __init__(self):
        super().__init__('my_commander')
        self.arm_pub = self.create_publisher(Bool, 'drone/arm', 10)
        self.takeoff_pub = self.create_publisher(Float32, 'drone/takeoff', 10)
        self.land_pub = self.create_publisher(Bool, 'drone/land', 10)

    def arm(self):
        msg = Bool()
        msg.data = True
        self.arm_pub.publish(msg)

    def takeoff(self, altitude=2.0):
        msg = Float32()
        msg.data = altitude
        self.takeoff_pub.publish(msg)

    def land(self):
        msg = Bool()
        msg.data = True
        self.land_pub.publish(msg)

rclpy.init()
cmd = MyCommander()
cmd.arm()
cmd.takeoff(5.0)
# ... fly ...
cmd.land()
```

---

*API Reference — Andhra University CSSE Drone Ground Station*

# Changelog

All notable changes to the Drone Ground Station project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.1.0] - 2026-04-09

### Added
- Full MAVLink binary protocol parsing in `telemetry_receiver.py` — supports HEARTBEAT, SYS_STATUS, GPS_RAW_INT, ATTITUDE, GLOBAL_POSITION_INT, VFR_HUD, BATTERY_STATUS
- Thread-safe telemetry data access with `threading.Lock` in all modules
- Helper methods `_update_field()`, `_update_fields()`, `_get_telemetry_snapshot()` for consistent concurrent access
- Type hints (PEP 484) across all 7 source files
- `ARCHITECTURE.md` — deep technical architecture with C4 model, thread diagrams, protocol specs
- `API_REFERENCE.md` — complete ROS2 topic, MAVLink, MSP, JSON schema reference
- `DIAGRAMS.md` — visual gallery of 20 Mermaid diagrams (system, network, state machines, class diagrams)
- `CONTRIBUTING.md` — professional contribution guide with code style, testing, PR checklist
- `CHANGELOG.md` — this file
- Comprehensive `README.md` with Mermaid diagrams, badges, tables, hardware wiring, GUI layout

### Changed
- Command queue in `mavlink_bridge.py` from `list` to `deque(maxlen=100)` — O(1) popleft, bounded memory
- GUI callbacks in `ground_station_gui.py` now use `_data_lock` for thread-safe image and telemetry updates
- Pi `telemetry_bridge.py` MSP response parsing now uses `_telemetry_lock` for all shared state writes

### Fixed
- Race conditions in `telemetry_data` dict accessed from multiple threads without synchronization
- `parse_mavlink_data()` stub replaced with full MAVLink parser using `pymavlink.mavutil`
- GUI `toggle_arm()` now reads armed state under lock before toggling

---

## [1.0.0] - 2026-04-09

### Added
- ROS2 Humble ground station with 4 nodes: video_receiver, telemetry_receiver, mavlink_bridge, ground_station_gui
- H.264 video streaming via GStreamer (1280x720 @ 30fps, 2 Mbps)
- Telemetry reception with JSON format parsing (10 Hz)
- MAVLink command bridge with TCP connection (10 Hz)
- Tkinter GUI with dark theme — video feed, telemetry panel, flight controls, status log
- Raspberry Pi video streamer with camera auto-detection (CSI / USB)
- Raspberry Pi telemetry bridge with MSP v1 protocol (UART 115200 baud)
- Raspberry Pi startup manager with process monitoring and auto-restart
- ROS2 launch file with configurable parameters
- YAML configuration for ground station parameters
- JSON configuration for Raspberry Pi settings
- WiFi hotspot setup scripts (hostapd + dnsmasq)
- Automated deployment script (`deploy.py`)
- System integration test suite (`test_system.py`)
- Interactive quick-start wizard (`quick_start.py`)
- Remote Pi setup via SSH (`remote_pi_setup.py`)
- Example scripts: flight demo, telemetry monitor, video analyzer
- Safety features: geofencing, battery monitoring, emergency stop, connection watchdog
- Comprehensive documentation: installation, quick start, hardware wiring, deployment checklist

---

*Andhra University — Department of Computer Science & Systems Engineering*

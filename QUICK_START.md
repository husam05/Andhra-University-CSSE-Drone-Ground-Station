# Quick Start Guide

This guide helps you get the drone ground station system running quickly after completing the full installation.

## Prerequisites

✅ Completed full installation (see INSTALLATION.md)
✅ Raspberry Pi 3 with camera and Crossflight FC connected
✅ Windows PC with ROS2 and dependencies installed
✅ Both systems configured and tested

## Quick Launch Steps

### Step 1: Power On Drone

1. Power on your Raspberry Pi 3 drone
2. Wait 30-60 seconds for boot and WiFi hotspot activation
3. Look for WiFi network: `DroneNetwork`

### Step 2: Connect Ground Station

1. On Windows PC, connect to drone WiFi:
   - **SSID**: `DroneNetwork`
   - **Password**: `drone123`

2. Verify connection:
```powershell
ping 192.168.4.1
```

### Step 3: Launch Ground Station

1. Open PowerShell as Administrator

2. Navigate to project directory:
```powershell
cd "C:\Users\hussa\OneDrive\Desktop\drone with GR"
```

3. Setup ROS2 environment:
```powershell
C:\dev\ros2_humble\local_setup.ps1
.\install\setup.ps1
```

4. Launch the ground station:
```powershell
ros2 launch drone_ground_station ground_station.launch.py
```

### Step 4: Verify Operation

You should see:
- ✅ Video feed from drone camera
- ✅ Telemetry data (battery, GPS, attitude)
- ✅ Connection status: "Connected"
- ✅ Ground station GUI interface

## Alternative Launch Methods

### Method 1: Launch Individual Components

```powershell
# Terminal 1 - Video Receiver
ros2 run drone_ground_station video_receiver

# Terminal 2 - Telemetry Receiver
ros2 run drone_ground_station telemetry_receiver

# Terminal 3 - MAVLink Bridge
ros2 run drone_ground_station mavlink_bridge

# Terminal 4 - GUI (optional)
ros2 run drone_ground_station ground_station_gui
```

### Method 2: Launch with Custom Parameters

```powershell
# Custom drone IP
ros2 launch drone_ground_station ground_station.launch.py drone_ip:=192.168.4.1

# Without GUI
ros2 launch drone_ground_station ground_station.launch.py use_gui:=false

# Custom video port
ros2 launch drone_ground_station ground_station.launch.py video_port:=5600
```

### Method 3: RViz Visualization

```powershell
# Launch with RViz
rviz2 -d config/ground_station.rviz
```

## Quick Tests

### Test Video Stream

```powershell
# Test GStreamer directly
gst-launch-1.0 udpsrc port=5600 ! application/x-rtp,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### Test Telemetry

```powershell
# Check ROS2 topics
ros2 topic list
ros2 topic echo /drone/battery_status
ros2 topic echo /drone/gps
```

### Test Commands

```powershell
# Send test command
ros2 topic pub /drone/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

## Common Quick Fixes

### No Video Feed

1. Check drone camera:
```bash
# SSH to drone
ssh pi@192.168.4.1
# Check camera
libcamera-hello --timeout 5000
```

2. Restart video service:
```bash
sudo systemctl restart drone.service
```

### No Telemetry

1. Check Crossflight connection:
```bash
# On drone
ls /dev/ttyAMA0
python3 -c "import serial; s=serial.Serial('/dev/ttyAMA0', 115200); print('OK')"
```

2. Restart telemetry:
```bash
sudo systemctl restart drone.service
```

### Connection Issues

1. Reset WiFi connection:
```powershell
# Disconnect and reconnect to DroneNetwork
```

2. Check IP configuration:
```powershell
ipconfig
# Should show 192.168.4.x address
```

### ROS2 Issues

1. Re-source environment:
```powershell
C:\dev\ros2_humble\local_setup.ps1
.\install\setup.ps1
```

2. Rebuild package:
```powershell
colcon build --packages-select drone_ground_station
```

## Flight Operations

### Pre-flight Checklist

- [ ] Drone powered and connected
- [ ] Video feed active
- [ ] Telemetry receiving
- [ ] Battery level > 20%
- [ ] GPS signal acquired (if applicable)
- [ ] Flight area clear
- [ ] Emergency stop ready

### Basic Flight Commands

1. **Arm Motors**:
   - Click "ARM" in GUI
   - Or: `ros2 service call /drone/arm std_srvs/srv/SetBool "{data: true}"`

2. **Takeoff**:
   - Click "TAKEOFF" in GUI
   - Or: `ros2 service call /drone/takeoff std_srvs/srv/Trigger`

3. **Manual Control**:
   - Use velocity sliders in GUI
   - Or publish to `/drone/cmd_vel`

4. **Land**:
   - Click "LAND" in GUI
   - Or: `ros2 service call /drone/land std_srvs/srv/Trigger`

5. **Emergency Stop**:
   - Click "EMERGENCY STOP" in GUI
   - Or: `ros2 service call /drone/emergency_stop std_srvs/srv/Trigger`

### Post-flight

1. Disarm motors
2. Power down drone
3. Disconnect from WiFi
4. Close ground station software

## Monitoring and Logs

### Real-time Monitoring

```powershell
# Monitor all topics
ros2 topic list
ros2 topic hz /drone/camera/image_raw
ros2 topic hz /drone/telemetry
```

### Check Logs

```powershell
# ROS2 logs
ros2 log list

# Drone logs (SSH to drone)
ssh pi@192.168.4.1
journalctl -u drone.service -f
```

## Performance Tips

### Optimize Video Quality

1. Edit `config/ground_station_params.yaml`:
```yaml
video:
  resolution: "1280x720"  # Lower for better performance
  framerate: 20           # Reduce if needed
  bitrate: 1000000       # Adjust based on network
```

2. Restart services after changes

### Reduce Latency

1. Use wired connection if possible
2. Reduce video resolution/framerate
3. Optimize GStreamer pipeline
4. Use faster SD card on Pi

## Emergency Procedures

### Lost Connection

1. **Immediate**: Press Emergency Stop
2. Check WiFi connection
3. Attempt to reconnect
4. Manual recovery if needed

### System Crash

1. **Immediate**: Cut drone power if safe
2. Restart ground station
3. Reconnect to drone
4. Check logs for errors

## Support Commands

```powershell
# System info
ros2 doctor
ros2 wtf

# Network diagnostics
ping 192.168.4.1
telnet 192.168.4.1 5600

# Process monitoring
tasklist | findstr python
```

---

**🚁 Happy Flying!**

For detailed troubleshooting, see INSTALLATION.md
For system architecture, see README.md
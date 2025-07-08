# Hardware Wiring and Connection Guide
# Raspberry Pi 3 Drone Ground Station

This guide provides detailed wiring diagrams and connection instructions for setting up the Raspberry Pi 3 with your drone's flight controller and peripherals.

## Overview

```
Drone System Architecture:

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Flight        │    │  Raspberry Pi 3  │    │    Laptop       │
│  Controller     │◄──►│   (Onboard)      │◄──►│ Ground Station  │
│ (Crossflight)   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
   ┌─────────┐            ┌─────────────┐         ┌─────────────┐
   │ Motors  │            │   Camera    │         │    GUI      │
   │ & ESCs  │            │   Module    │         │  & Control  │
   └─────────┘            └─────────────┘         └─────────────┘
```

## Raspberry Pi 3 GPIO Pinout Reference

```
Raspberry Pi 3 GPIO Layout (40-pin header):

    3V3  (1) (2)  5V
  GPIO2  (3) (4)  5V
  GPIO3  (5) (6)  GND
  GPIO4  (7) (8)  GPIO14 (TXD)
    GND  (9) (10) GPIO15 (RXD)
 GPIO17 (11) (12) GPIO18
 GPIO27 (13) (14) GND
 GPIO22 (15) (16) GPIO23
    3V3 (17) (18) GPIO24
 GPIO10 (19) (20) GND
  GPIO9 (21) (22) GPIO25
 GPIO11 (23) (24) GPIO8
    GND (25) (26) GPIO7
  GPIO0 (27) (28) GPIO1
  GPIO5 (29) (30) GND
  GPIO6 (31) (32) GPIO12
 GPIO13 (33) (34) GND
 GPIO19 (35) (36) GPIO16
 GPIO26 (37) (38) GPIO20
    GND (39) (40) GPIO21
```

## Connection Diagrams

### 1. Flight Controller to Raspberry Pi UART Connection

```
Crossflight Flight Controller    Raspberry Pi 3
┌─────────────────────────┐    ┌─────────────────────────┐
│                         │    │                         │
│  UART1/UART2 Port:     │    │     GPIO Header:        │
│                         │    │                         │
│  ┌─────┐ ┌─────┐ ┌───┐  │    │  ┌───┐ ┌─────┐ ┌─────┐  │
│  │ TX  │ │ RX  │ │GND│  │    │  │GND│ │ RXD │ │ TXD │  │
│  └──┬──┘ └──┬──┘ └─┬─┘  │    │  └─┬─┘ └──┬──┘ └──┬──┘  │
└─────┼──────┼──────┼────┘    └────┼──────┼──────┼─────┘
      │      │      │                │      │      │
      │      │      └────────────────┼──────┼──────┘
      │      │                       │      │
      │      └───────────────────────┼──────┘
      │                              │
      └──────────────────────────────┘

Connections:
FC TX   ──► Pi RXD (GPIO 15, Pin 10)
FC RX   ──► Pi TXD (GPIO 14, Pin 8)
FC GND  ──► Pi GND (Pin 6, 9, 14, 20, 25, 30, 34, or 39)
```

**Important Notes:**
- Ensure voltage compatibility (3.3V logic)
- Use a logic level converter if FC uses 5V logic
- Double-check TX/RX crossover connections

### 2. Camera Module Connection

```
Raspberry Pi Camera Module v2:

┌─────────────────────────┐
│    Raspberry Pi 3       │
│                         │
│  ┌─────────────────┐    │
│  │   Camera Port   │    │
│  │   (CSI Port)    │    │
│  └─────────────────┘    │
│           │             │
└───────────┼─────────────┘
            │
            │ Ribbon Cable
            │ (contacts away from ethernet)
            │
┌───────────▼─────────────┐
│   Camera Module v2      │
│                         │
│  ┌─────────────────┐    │
│  │    8MP Sensor   │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

**Alternative: USB Camera**
```
USB Camera ──► Any USB Port on Raspberry Pi
```

### 3. Power Supply Connections

```
Power Distribution Options:

Option 1: Separate 5V BEC
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Battery   │───►│  5V BEC     │───►│ Raspberry   │
│   (LiPo)    │    │ (3A min)    │    │ Pi 3        │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │ Flight      │
                   │ Controller  │
                   └─────────────┘

Option 2: USB Power Bank
┌─────────────┐    ┌─────────────┐
│ USB Power   │───►│ Raspberry   │
│ Bank        │    │ Pi 3        │
│ (10000mAh+) │    │ (via USB)   │
└─────────────┘    └─────────────┘

Option 3: Direct Battery with Regulator
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Battery   │───►│ 5V/3A       │───►│ Raspberry   │
│ (2S-6S LiPo)│    │ Regulator   │    │ Pi 3        │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 4. Complete Wiring Diagram

```
Complete Drone Wiring Setup:

                    ┌─────────────────────────────────┐
                    │        Raspberry Pi 3           │
                    │                                 │
    Camera ────────►│ CSI Port                        │
                    │                                 │
                    │ GPIO 14 (TXD) ◄─────────────────┼──── FC RX
                    │ GPIO 15 (RXD) ◄─────────────────┼──── FC TX
                    │ GND           ◄─────────────────┼──── FC GND
                    │                                 │
    5V Power ──────►│ Micro USB                       │
                    │                                 │
                    │ WiFi Antenna (built-in)         │
                    └─────────────────────────────────┘
                                    │
                                    │ WiFi Hotspot
                                    │ (192.168.4.1)
                                    │
                    ┌───────────────▼─────────────────┐
                    │           Laptop                │
                    │      Ground Station             │
                    │                                 │
                    │  ┌─────────────────────────┐    │
                    │  │    ROS2 Nodes:         │    │
                    │  │  • Video Receiver      │    │
                    │  │  • Telemetry Monitor   │    │
                    │  │  • Command Interface   │    │
                    │  │  • GUI Application     │    │
                    │  └─────────────────────────┘    │
                    └─────────────────────────────────┘
```

## Detailed Connection Instructions

### Step 1: Prepare the Raspberry Pi

1. **Install Heat Sinks** (recommended)
   ```
   Apply heat sinks to:
   - CPU (largest chip)
   - RAM chip
   - Network/USB controller
   ```

2. **Insert MicroSD Card**
   ```
   - Use 32GB+ Class 10 card
   - Flash with Raspberry Pi OS Lite
   - Enable SSH and WiFi before first boot
   ```

### Step 2: Camera Connection

1. **Raspberry Pi Camera Module**
   ```
   Steps:
   1. Power off Raspberry Pi
   2. Locate CSI camera port (between HDMI and audio jack)
   3. Lift the plastic clip gently
   4. Insert ribbon cable with contacts facing away from ethernet port
   5. Push plastic clip down to secure
   6. Connect other end to camera module
   ```

2. **USB Camera (Alternative)**
   ```
   Steps:
   1. Simply plug into any USB port
   2. Verify detection: lsusb
   3. Test: fswebcam test.jpg
   ```

### Step 3: UART Connection to Flight Controller

1. **Identify Flight Controller UART Pins**
   ```
   Common FC UART locations:
   - Dedicated UART pads on PCB
   - Through-hole pins labeled UART1/UART2
   - JST connector with TX/RX/GND
   ```

2. **Prepare Wires**
   ```
   Required:
   - 3 jumper wires (Male-to-Male or Male-to-Female)
   - Colors: Red (5V), Black (GND), White/Yellow (Signal)
   - Length: 10-15cm recommended
   ```

3. **Make Connections**
   ```
   Flight Controller → Raspberry Pi
   TX (Transmit)     → GPIO 15 (RXD, Pin 10)
   RX (Receive)      → GPIO 14 (TXD, Pin 8)
   GND (Ground)      → GND (Pin 6)
   
   DO NOT CONNECT 5V - Pi uses 3.3V logic!
   ```

4. **Voltage Level Considerations**
   ```
   If FC uses 5V logic levels:
   
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ Flight      │    │ Logic Level │    │ Raspberry   │
   │ Controller  │◄──►│ Converter   │◄──►│ Pi 3        │
   │ (5V logic)  │    │ (5V ↔ 3.3V) │    │ (3.3V logic)│
   └─────────────┘    └─────────────┘    └─────────────┘
   
   Recommended: Bi-directional logic level converter
   Example: SparkFun BOB-12009 or similar
   ```

### Step 4: Power Supply Setup

1. **Calculate Power Requirements**
   ```
   Raspberry Pi 3 Power Consumption:
   - Idle: ~1.4A @ 5V (7W)
   - Load: ~2.5A @ 5V (12.5W)
   - Peak: ~3.0A @ 5V (15W)
   
   Recommended: 5V 3A power supply minimum
   ```

2. **Power Supply Options**

   **Option A: Dedicated 5V BEC**
   ```
   Advantages:
   - Clean, regulated power
   - Efficient
   - Lightweight
   
   Wiring:
   Battery + ──► BEC +IN
   Battery - ──► BEC -IN
   BEC +OUT ──► Pi 5V (via micro USB or GPIO)
   BEC -OUT ──► Pi GND
   ```

   **Option B: USB Power Bank**
   ```
   Advantages:
   - Easy to implement
   - Built-in protection
   - Can be charged separately
   
   Requirements:
   - 10,000mAh+ capacity
   - 2.4A+ output
   - Quality brand (Anker, RAVPower, etc.)
   ```

   **Option C: Direct Battery Connection**
   ```
   Advantages:
   - Single power source
   - Longest flight time
   
   Requirements:
   - Step-down regulator (Buck converter)
   - Input: 7-25V (2S-6S LiPo)
   - Output: 5V 3A minimum
   - Efficiency: >85%
   ```

### Step 5: Mounting and Mechanical Setup

1. **Raspberry Pi Mounting**
   ```
   Options:
   - 3D printed case with camera mount
   - Carbon fiber plate with standoffs
   - Foam padding for vibration isolation
   
   Considerations:
   - Protect from propwash
   - Allow airflow for cooling
   - Secure all connections
   - Easy access to SD card
   ```

2. **Cable Management**
   ```
   Best Practices:
   - Use short, flexible wires
   - Secure with zip ties or velcro
   - Avoid interference with moving parts
   - Label all connections
   - Use different colors for different signals
   ```

## Testing and Verification

### Step 1: Basic Hardware Test

1. **Power-On Test**
   ```bash
   # Check if Pi boots properly
   # Look for:
   # - Green LED activity (SD card access)
   # - Red LED solid (power good)
   # - HDMI output (if connected)
   ```

2. **GPIO Test**
   ```bash
   # Test GPIO functionality
   gpio readall
   
   # Test UART
   sudo minicom -D /dev/serial0 -b 115200
   ```

3. **Camera Test**
   ```bash
   # Pi Camera
   raspistill -o test.jpg
   
   # USB Camera
   fswebcam -r 640x480 test.jpg
   ```

### Step 2: Communication Test

1. **UART Loopback Test**
   ```bash
   # Connect GPIO 14 to GPIO 15 temporarily
   # Send data and verify reception
   echo "test" > /dev/serial0
   cat /dev/serial0
   ```

2. **Flight Controller Communication**
   ```bash
   # Use MSP test script
   python3 test_msp_communication.py
   ```

### Step 3: Network Test

1. **WiFi Hotspot Test**
   ```bash
   # Check hotspot status
   sudo systemctl status hostapd
   sudo systemctl status dnsmasq
   
   # Check connected devices
   cat /var/lib/dhcp/dhcpd.leases
   ```

2. **Data Transmission Test**
   ```bash
   # Test video stream
   gst-launch-1.0 libcamerasrc ! videoconvert ! x264enc ! rtph264pay ! udpsink host=192.168.4.2 port=5600
   
   # Test telemetry
   python3 telemetry_test.py
   ```

## Troubleshooting Common Issues

### Power Issues

1. **Insufficient Power**
   ```
   Symptoms:
   - Random reboots
   - WiFi disconnections
   - Camera not working
   - Under-voltage warning
   
   Solutions:
   - Use higher capacity power supply (3A minimum)
   - Check all connections
   - Measure voltage at Pi GPIO pins
   ```

2. **Power Supply Noise**
   ```
   Symptoms:
   - Video interference
   - Erratic behavior
   - Communication errors
   
   Solutions:
   - Add capacitors (1000µF, 100µF)
   - Use linear regulator for final stage
   - Separate analog and digital grounds
   ```

### Communication Issues

1. **UART Not Working**
   ```
   Check:
   - /boot/config.txt: enable_uart=1
   - /boot/cmdline.txt: remove console=serial0,115200
   - Wiring: TX→RX, RX→TX crossover
   - Baud rate match (115200 typical)
   - Ground connection
   ```

2. **WiFi Problems**
   ```
   Check:
   - Antenna not blocked
   - Channel interference (try different channel)
   - Power supply adequate
   - hostapd configuration
   - iptables rules
   ```

### Performance Issues

1. **Video Lag**
   ```
   Solutions:
   - Reduce resolution/bitrate
   - Optimize GStreamer pipeline
   - Check network bandwidth
   - Increase GPU memory split
   ```

2. **High CPU Usage**
   ```
   Solutions:
   - Enable hardware acceleration
   - Optimize code (use numpy, cython)
   - Reduce processing frequency
   - Monitor with htop
   ```

## Safety Checklist

### Pre-Flight Checks

- [ ] All connections secure
- [ ] Power supply adequate
- [ ] Camera functioning
- [ ] UART communication working
- [ ] WiFi hotspot active
- [ ] Ground station connected
- [ ] Emergency stop tested
- [ ] Battery levels checked
- [ ] Backup communication method available

### During Flight

- [ ] Monitor power consumption
- [ ] Check communication link quality
- [ ] Watch for overheating
- [ ] Maintain visual line of sight
- [ ] Be ready for manual override

### Post-Flight

- [ ] Download flight logs
- [ ] Check for loose connections
- [ ] Inspect for damage
- [ ] Charge batteries
- [ ] Update software if needed

---

**Warning**: Always follow local regulations and safety guidelines when operating drones. Test all systems thoroughly before flight.
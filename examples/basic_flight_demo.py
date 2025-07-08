#!/usr/bin/env python3
"""
Basic Flight Demonstration Script

This script demonstrates basic flight operations using the drone ground station system.
It shows how to:
1. Connect to the drone
2. Perform basic flight maneuvers
3. Monitor telemetry data
4. Handle emergency situations

Usage:
    python basic_flight_demo.py --drone_ip 192.168.4.1
"""

import argparse
import asyncio
import json
import logging
import socket
import struct
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DroneController:
    """Simple drone controller for demonstration purposes."""
    
    def __init__(self, drone_ip: str, command_port: int = 5001):
        self.drone_ip = drone_ip
        self.command_port = command_port
        self.socket = None
        self.is_connected = False
        self.telemetry_data = {}
        
    async def connect(self) -> bool:
        """Connect to the drone."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.connect, (self.drone_ip, self.command_port)
            )
            self.is_connected = True
            logger.info(f"Connected to drone at {self.drone_ip}:{self.command_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to drone: {e}")
            return False
    
    async def send_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Send a command to the drone."""
        if not self.is_connected:
            logger.error("Not connected to drone")
            return False
        
        try:
            message = {
                "command": command,
                "params": params or {},
                "timestamp": time.time()
            }
            data = json.dumps(message).encode('utf-8')
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.send, data
            )
            logger.info(f"Sent command: {command}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command {command}: {e}")
            return False
    
    async def arm(self) -> bool:
        """Arm the drone."""
        return await self.send_command("arm")
    
    async def disarm(self) -> bool:
        """Disarm the drone."""
        return await self.send_command("disarm")
    
    async def takeoff(self, altitude: float = 2.0) -> bool:
        """Take off to specified altitude."""
        return await self.send_command("takeoff", {"altitude": altitude})
    
    async def land(self) -> bool:
        """Land the drone."""
        return await self.send_command("land")
    
    async def set_velocity(self, vx: float, vy: float, vz: float, vyaw: float = 0.0) -> bool:
        """Set velocity in body frame."""
        return await self.send_command("velocity", {
            "vx": vx, "vy": vy, "vz": vz, "vyaw": vyaw
        })
    
    async def hover(self) -> bool:
        """Hover in place."""
        return await self.set_velocity(0, 0, 0, 0)
    
    def disconnect(self):
        """Disconnect from the drone."""
        if self.socket:
            self.socket.close()
            self.is_connected = False
            logger.info("Disconnected from drone")

class FlightDemo:
    """Demonstration of basic flight operations."""
    
    def __init__(self, drone_ip: str):
        self.controller = DroneController(drone_ip)
        self.is_flying = False
    
    async def pre_flight_check(self) -> bool:
        """Perform pre-flight safety checks."""
        logger.info("Starting pre-flight checks...")
        
        # Check connection
        if not await self.controller.connect():
            logger.error("Pre-flight check failed: Cannot connect to drone")
            return False
        
        # Add more checks here (battery, GPS, etc.)
        logger.info("Pre-flight checks completed successfully")
        return True
    
    async def basic_flight_pattern(self):
        """Execute a basic flight pattern."""
        try:
            logger.info("Starting basic flight demonstration...")
            
            # Arm the drone
            logger.info("Arming drone...")
            if not await self.controller.arm():
                raise Exception("Failed to arm drone")
            
            await asyncio.sleep(2)
            
            # Take off
            logger.info("Taking off...")
            if not await self.controller.takeoff(2.0):
                raise Exception("Failed to take off")
            
            self.is_flying = True
            await asyncio.sleep(5)  # Wait for takeoff to complete
            
            # Hover for a moment
            logger.info("Hovering...")
            await self.controller.hover()
            await asyncio.sleep(3)
            
            # Move forward
            logger.info("Moving forward...")
            await self.controller.set_velocity(1.0, 0, 0)  # 1 m/s forward
            await asyncio.sleep(3)
            
            # Stop and hover
            logger.info("Stopping and hovering...")
            await self.controller.hover()
            await asyncio.sleep(2)
            
            # Move backward
            logger.info("Moving backward...")
            await self.controller.set_velocity(-1.0, 0, 0)  # 1 m/s backward
            await asyncio.sleep(3)
            
            # Stop and hover
            logger.info("Stopping and hovering...")
            await self.controller.hover()
            await asyncio.sleep(2)
            
            # Move right
            logger.info("Moving right...")
            await self.controller.set_velocity(0, 1.0, 0)  # 1 m/s right
            await asyncio.sleep(2)
            
            # Move left
            logger.info("Moving left...")
            await self.controller.set_velocity(0, -1.0, 0)  # 1 m/s left
            await asyncio.sleep(2)
            
            # Return to center and hover
            logger.info("Returning to center...")
            await self.controller.hover()
            await asyncio.sleep(3)
            
            # Land
            logger.info("Landing...")
            if not await self.controller.land():
                raise Exception("Failed to land")
            
            self.is_flying = False
            await asyncio.sleep(5)  # Wait for landing to complete
            
            # Disarm
            logger.info("Disarming...")
            await self.controller.disarm()
            
            logger.info("Flight demonstration completed successfully!")
            
        except Exception as e:
            logger.error(f"Flight demonstration failed: {e}")
            await self.emergency_land()
    
    async def emergency_land(self):
        """Emergency landing procedure."""
        logger.warning("Executing emergency landing...")
        
        if self.is_flying:
            try:
                await self.controller.land()
                await asyncio.sleep(5)
                await self.controller.disarm()
                self.is_flying = False
                logger.info("Emergency landing completed")
            except Exception as e:
                logger.error(f"Emergency landing failed: {e}")
    
    async def run(self):
        """Run the complete demonstration."""
        try:
            # Pre-flight checks
            if not await self.pre_flight_check():
                return
            
            # Execute flight pattern
            await self.basic_flight_pattern()
            
        except KeyboardInterrupt:
            logger.warning("Demonstration interrupted by user")
            await self.emergency_land()
        
        except Exception as e:
            logger.error(f"Demonstration failed: {e}")
            await self.emergency_land()
        
        finally:
            self.controller.disconnect()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Basic Flight Demonstration')
    parser.add_argument('--drone_ip', default='192.168.4.1',
                       help='IP address of the drone (default: 192.168.4.1)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run demonstration
    demo = FlightDemo(args.drone_ip)
    
    try:
        asyncio.run(demo.run())
    except KeyboardInterrupt:
        logger.info("Demonstration stopped by user")
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")

if __name__ == "__main__":
    main()
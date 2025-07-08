#!/usr/bin/env python3
"""
Launch file for Drone Ground Station
Starts all necessary nodes for video streaming, telemetry, and control
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Launch arguments
    drone_ip_arg = DeclareLaunchArgument(
        'drone_ip',
        default_value='192.168.4.1',
        description='IP address of the drone'
    )
    
    video_port_arg = DeclareLaunchArgument(
        'video_port',
        default_value='5600',
        description='Port for video streaming'
    )
    
    telemetry_port_arg = DeclareLaunchArgument(
        'telemetry_port',
        default_value='14550',
        description='Port for telemetry data'
    )
    
    command_port_arg = DeclareLaunchArgument(
        'command_port',
        default_value='14551',
        description='Port for sending commands'
    )
    
    gui_enabled_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Enable GUI interface'
    )
    
    # Get launch configurations
    drone_ip = LaunchConfiguration('drone_ip')
    video_port = LaunchConfiguration('video_port')
    telemetry_port = LaunchConfiguration('telemetry_port')
    command_port = LaunchConfiguration('command_port')
    gui_enabled = LaunchConfiguration('gui')
    
    # Video receiver node
    video_receiver_node = Node(
        package='drone_ground_station',
        executable='video_receiver.py',
        name='video_receiver',
        parameters=[
            {'drone_ip': drone_ip},
            {'video_port': video_port},
            {'frame_rate': 30},
            {'video_width': 1280},
            {'video_height': 720}
        ],
        output='screen',
        emulate_tty=True
    )
    
    # Telemetry receiver node
    telemetry_receiver_node = Node(
        package='drone_ground_station',
        executable='telemetry_receiver.py',
        name='telemetry_receiver',
        parameters=[
            {'drone_ip': drone_ip},
            {'telemetry_port': telemetry_port},
            {'update_rate': 10.0}
        ],
        output='screen',
        emulate_tty=True
    )
    
    # MAVLink bridge node
    mavlink_bridge_node = Node(
        package='drone_ground_station',
        executable='mavlink_bridge.py',
        name='mavlink_bridge',
        parameters=[
            {'drone_ip': drone_ip},
            {'command_port': command_port},
            {'connection_timeout': 5.0}
        ],
        output='screen',
        emulate_tty=True
    )
    
    # Ground station GUI node (conditional)
    gui_node = Node(
        package='drone_ground_station',
        executable='ground_station_gui.py',
        name='ground_station_gui',
        condition=IfCondition(gui_enabled),
        output='screen',
        emulate_tty=True
    )
    
    # RViz for visualization (optional)
    rviz_config_file = os.path.join(
        get_package_share_directory('drone_ground_station'),
        'config',
        'ground_station.rviz'
    )
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        condition=IfCondition(gui_enabled),
        output='screen'
    )
    
    return LaunchDescription([
        # Launch arguments
        drone_ip_arg,
        video_port_arg,
        telemetry_port_arg,
        command_port_arg,
        gui_enabled_arg,
        
        # Nodes
        video_receiver_node,
        telemetry_receiver_node,
        mavlink_bridge_node,
        gui_node,
        # rviz_node,  # Uncomment if you want RViz
    ])
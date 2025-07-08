from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'drone_ground_station'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # Config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*')),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'std_msgs',
        'sensor_msgs',
        'geometry_msgs',
        'nav_msgs',
        'cv_bridge',
        'image_transport',
        'tf2_ros',
        'tf2_geometry_msgs',
        'opencv-python',
        'Pillow',
        'numpy',
        'PyGObject',
        'pymavlink',
        'pyyaml',
        'psutil',
    ],
    zip_safe=True,
    maintainer='Drone Developer',
    maintainer_email='user@example.com',
    description='Ground station for drone communication with video streaming and telemetry',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'video_receiver = drone_ground_station.scripts.video_receiver:main',
            'telemetry_receiver = drone_ground_station.scripts.telemetry_receiver:main',
            'mavlink_bridge = drone_ground_station.scripts.mavlink_bridge:main',
            'ground_station_gui = drone_ground_station.scripts.ground_station_gui:main',
        ],
    },
)
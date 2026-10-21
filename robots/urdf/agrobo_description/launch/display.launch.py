"""RViz + joint sliders: ros2 launch agrobo_description display.launch.py"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("agrobo_description")
    urdf = open(os.path.join(share, "urdf", "agrobo_harvester.urdf")).read()
    return LaunchDescription([
        Node(package="robot_state_publisher", executable="robot_state_publisher", parameters=[{"robot_description": urdf}]),
        Node(package="joint_state_publisher_gui", executable="joint_state_publisher_gui"),
        Node(package="rviz2", executable="rviz2"),
    ])

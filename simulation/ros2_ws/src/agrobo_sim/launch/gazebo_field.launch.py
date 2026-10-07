"""Gazebo Harmonic farm world + ROS 2 bridge + physics-in-the-loop row-following check.

ros2 launch agrobo_sim gazebo_field.launch.py headless:=true lanes:=2
(headless:=false opens the gz GUI on a workstation.)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    world = os.path.join(get_package_share_directory("agrobo_sim"), "worlds", "farm.sdf")
    args = [DeclareLaunchArgument("world", default_value=world), DeclareLaunchArgument("headless", default_value="true"),
            DeclareLaunchArgument("lanes", default_value="2"),
            DeclareLaunchArgument("localization", default_value="rtk_imu"),
            DeclareLaunchArgument("output", default_value="results/gazebo/row_follow.json")]
    gz_server = ExecuteProcess(cmd=["gz", "sim", "-s", "-r", "-v", "2", LC("world")], output="log",
                               condition=IfCondition(LC("headless")))
    gz_gui = ExecuteProcess(cmd=["gz", "sim", "-r", LC("world")], output="log", condition=UnlessCondition(LC("headless")))
    r = "ugv_alpha"
    bridge = Node(package="ros_gz_bridge", executable="parameter_bridge", output="log", arguments=[
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        f"/model/{r}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        f"/model/{r}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        f"/{r}/navsat@sensor_msgs/msg/NavSatFix[gz.msgs.NavSat",
        f"/{r}/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
        f"/model/{r}/pose@geometry_msgs/msg/Pose[gz.msgs.Pose"])
    follower = Node(package="agrobo_sim", executable="gz_row_follower", output="screen",
                    parameters=[{"use_sim_time": True, "robot": r, "lanes": ParameterValue(LC("lanes"), value_type=int),
                                 "localization": LC("localization"),
                                 "output": LC("output")}])
    stop = RegisterEventHandler(OnProcessExit(target_action=follower, on_exit=[EmitEvent(event=Shutdown())]))
    return LaunchDescription(args + [gz_server, gz_gui, bridge, follower, stop])

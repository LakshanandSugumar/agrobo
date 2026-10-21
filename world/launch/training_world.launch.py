"""Agrobo training field in Gazebo Harmonic + ROS 2 Jazzy bridge for the drivable sensor robot.

  ros2 launch /path/to/agrobo-world/launch/training_world.launch.py                     # headless server
  ros2 launch .../training_world.launch.py headless:=false world:=/abs/path/my_world.sdf # with GUI

ROS topics (all under /agrobo_trainer): cmd_vel (in), odometry, imu, navsat, camera/image, camera/camera_info,
depth/image, segmentation/{semantic,instance}/{colored_map,labels_map}, boxes (vision_msgs/Detection2DArray),
lidar/points. Label ids: 1 ripe, 2 turning, 3 unripe fruit, 4 weed, 5 plant, 6 UGV, 7 UAV.
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_launch_description():
    r = "agrobo_trainer"
    topics = [
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        f"/{r}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        f"/{r}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        f"/{r}/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
        f"/{r}/navsat@sensor_msgs/msg/NavSatFix[gz.msgs.NavSat",
        f"/{r}/camera/image@sensor_msgs/msg/Image[gz.msgs.Image",
        f"/{r}/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
        f"/{r}/depth/image@sensor_msgs/msg/Image[gz.msgs.Image",
        f"/{r}/boxes@vision_msgs/msg/Detection2DArray[gz.msgs.AnnotatedAxisAligned2DBox_V",
        f"/{r}/lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
    ] + [f"/{r}/segmentation/{k}/{m}@sensor_msgs/msg/Image[gz.msgs.Image"
         for k in ("semantic", "instance") for m in ("colored_map", "labels_map")]
    return LaunchDescription([
        DeclareLaunchArgument("world", default_value=os.path.join(ROOT, "worlds", "agrobo_field.sdf")),
        DeclareLaunchArgument("headless", default_value="true"),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", os.path.join(ROOT, "models") + os.pathsep + os.environ.get("GZ_SIM_RESOURCE_PATH", "")),
        ExecuteProcess(cmd=["gz", "sim", "-s", "-r", "--headless-rendering", "-v", "2", LC("world")], output="log", condition=IfCondition(LC("headless"))),
        ExecuteProcess(cmd=["gz", "sim", "-r", LC("world")], output="log", condition=UnlessCondition(LC("headless"))),
        Node(package="ros_gz_bridge", executable="parameter_bridge", arguments=topics, output="log",
             parameters=[{"use_sim_time": True}]),
    ])

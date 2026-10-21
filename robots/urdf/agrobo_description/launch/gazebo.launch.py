"""Spawn the harvester in Gazebo Harmonic with ros2_control + sensor bridges.

ros2 launch agrobo_description gazebo.launch.py [world:=/path/to/world.sdf] [headless:=true] [headless_rendering:=false]
Drive (Jazzy diff_drive takes TwistStamped):
  ros2 topic pub -r 20 /base_controller/cmd_vel geometry_msgs/msg/TwistStamped "{twist: {linear: {x: 0.5}}}"
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("agrobo_description")
    urdf = open(os.path.join(share, "urdf", "agrobo_harvester.urdf")).read()
    urdf = urdf.replace("$(find agrobo_description)", share)
    world = LaunchConfiguration("world")
    headless = LaunchConfiguration("headless")
    egl = LaunchConfiguration("headless_rendering")
    ns = "agrobo_harvester"
    bridge = [f"/{ns}/lidar/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
              f"/{ns}/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
              f"/{ns}/navsat@sensor_msgs/msg/NavSatFix[gz.msgs.NavSat",
              "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"]
    for cam in ("zed_left", "zed_right", "left_d405", "right_d405"):
        bridge += [f"/{ns}/{cam}/image@sensor_msgs/msg/Image[gz.msgs.Image",
                   f"/{ns}/{cam}/depth_image@sensor_msgs/msg/Image[gz.msgs.Image",
                   f"/{ns}/{cam}/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo"]
    controllers = ["joint_state_broadcaster", "base_controller", "left_arm_controller", "right_arm_controller",
                   "left_gripper_controller", "right_gripper_controller"]
    return LaunchDescription([
        DeclareLaunchArgument("world", default_value="empty.sdf"),
        DeclareLaunchArgument("headless", default_value="false"),
        DeclareLaunchArgument("headless_rendering", default_value="true",
                              description="EGL off-screen sensors when headless (needs a GPU); set false under Xvfb"),
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", os.path.dirname(share)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
            launch_arguments={"gz_args": PythonExpression(["'-r ' + ('-s ' if '", headless, "' == 'true' else '') + ('--headless-rendering ' if '", headless,
                                                   "' == 'true' and '", egl, "' == 'true' else '') + '", world, "'"])}.items()),
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": urdf, "use_sim_time": True}]),
        Node(package="ros_gz_sim", executable="create", arguments=["-topic", "robot_description", "-name", ns, "-z", "0.05"]),
        Node(package="ros_gz_bridge", executable="parameter_bridge", arguments=bridge),
        TimerAction(period=5.0, actions=[Node(package="controller_manager", executable="spawner",   # one spawner: no lock contention
                                              arguments=controllers + ["--controller-manager-timeout", "120"])]),
    ])

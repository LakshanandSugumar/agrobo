# agrobo_description

Agrobo HM-1 harvester (AB-1 base, 2x FR5-class arms, EE-1 grippers). GENERATED from `cad/src/params.py` by `urdf/generate_urdf.py`.

- `urdf/agrobo_harvester.urdf`: package:// meshes, ros2_control (gz_ros2_control) and Gazebo sensors. Use with ROS 2 / Gazebo.
- `agrobo_harvester.relative.urdf`: relative mesh paths, no Gazebo tags. Use with Isaac Lab, PyBullet, MuJoCo or yourdfpy.
- `launch/gazebo.launch.py` (args: `world`, `headless`, `headless_rendering`), `launch/display.launch.py` (RViz + sliders).
- `worlds/aisle_test.sdf`: two Florida beds on 1.83 m centres, stakes, tomatoes. GNSS origin is near Immokalee, FL.

| Group | Joints | Notes |
|---|---|---|
| Wheels | `{front,rear}_{left,right}_wheel_joint` | continuous, +vel = forward on both sides; r 0.254 m, track 0.58 m |
| Arms | `{left,right}_arm_{shoulder_pan,shoulder_lift,elbow,wrist_1,wrist_2,wrist_3}_joint` | FR5 datasheet ranges: ±175, +85/-265, ±160, +85/-265, ±175, ±175 deg |
| Gripper | `{side}_ee_finger_{1,2,3}_joint` | 0 open .. 0.45 rad closed; no mimic, so command all three |
| Suction | `{side}_ee_suction_joint` | prismatic -0.065..0 m (0 = lip just past fingertips, -0.065 = retracted, fruit seated) |

Frames: `{side}_ee_tcp` (grasp centre, 0.205 m from the flange), `{side}_ee_camera_link` (D405, x forward), `zed_{left,right}_link`, `lidar_link`, `imu_link`, `gnss_{left,right}_link`.
Controllers: `base_controller` (diff_drive; Jazzy expects TwistStamped on `/base_controller/cmd_vel`), `{side}_arm_controller` (JointTrajectoryController), `{side}_gripper_controller` (forward position: 3 fingers + suction).
Sensor topics: `/agrobo_harvester/{zed_left,zed_right,left_d405,right_d405}/{image,depth_image,camera_info}`, `/agrobo_harvester/lidar/points`, `/agrobo_harvester/imu`, `/agrobo_harvester/navsat`.
IK with the same kinematics: `cad/src/kin.py` (`kin.ik("left", target_xyz, approach_axis)`).

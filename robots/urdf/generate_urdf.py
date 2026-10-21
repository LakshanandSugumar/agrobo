"""Generate the Agrobo HM-1 harvester URDF from cad/src/params.py.

Run: python urdf/generate_urdf.py      (after cad/src/build.py has written the meshes)
Writes:
  agrobo_description/urdf/agrobo_harvester.urdf     package:// mesh URIs (ROS 2, RViz, Gazebo via gz_ros2_control)
  agrobo_description/agrobo_harvester.relative.urdf  relative mesh paths (Isaac Lab URDF importer, PyBullet, yourdfpy)
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "src"))
from params import WHEEL, BASE, ARM, MAST, TOTES, EE   # noqa: E402

PKG = "agrobo_description"
FR5_EFFORT = [150, 150, 150, 28, 28, 28]       # N m, FR5-class (verify vs vendor datasheet)
FR5_VEL = [math.radians(v) for v in (180, 180, 180, 180, 180, 180)]
LIM = math.radians(175)


def f(*v):
    return " ".join(f"{x:.6g}" for x in v)


def box_inertia(m, x, y, z):
    return m * (y * y + z * z) / 12, m * (x * x + z * z) / 12, m * (x * x + y * y) / 12


def cyl_inertia(m, r, h, axis="z"):
    a, b = m * (3 * r * r + h * h) / 12, m * r * r / 2
    return {"x": (b, a, a), "y": (a, b, a), "z": (a, a, b)}[axis]


class U:
    def __init__(self, mesh_prefix):
        self.mp, self.s = mesh_prefix, []

    def mesh(self, name):
        return f'<mesh filename="{self.mp}{name}"/>'

    def link(self, name, mass=None, com=(0, 0, 0), inertia=None, visual=None, collisions=(), color=None):
        x = [f'  <link name="{name}">']
        if mass:
            ixx, iyy, izz = inertia
            x.append(f'    <inertial><origin xyz="{f(*com)}"/><mass value="{mass:.4g}"/>'
                     f'<inertia ixx="{ixx:.5g}" iyy="{iyy:.5g}" izz="{izz:.5g}" ixy="0" ixz="0" iyz="0"/></inertial>')
        if visual:
            mat = f'<material name="{color[0]}"><color rgba="{color[1]}"/></material>' if color else ""
            x.append(f'    <visual><geometry>{self.mesh(visual)}</geometry>{mat}</visual>')
        for xyz, rpy, geom in collisions:
            x.append(f'    <collision><origin xyz="{f(*xyz)}" rpy="{f(*rpy)}"/><geometry>{geom}</geometry></collision>')
        x.append("  </link>")
        self.s += x

    def joint(self, name, typ, parent, child, xyz=(0, 0, 0), rpy=(0, 0, 0), axis=None, lim=None, mimic=None):
        x = [f'  <joint name="{name}" type="{typ}"><parent link="{parent}"/><child link="{child}"/>'
             f'<origin xyz="{f(*xyz)}" rpy="{f(*rpy)}"/>']
        if axis:
            x.append(f'    <axis xyz="{f(*axis)}"/>')
        if lim:
            lo, hi, eff, vel = lim
            x.append(f'    <limit lower="{lo:.5g}" upper="{hi:.5g}" effort="{eff}" velocity="{vel:.4g}"/>'
                     '<dynamics damping="0.5" friction="0.1"/>')
        if mimic:
            x.append(f'    <mimic joint="{mimic}" multiplier="1" offset="0"/>')
        x.append("  </joint>")
        self.s += x


def B(x, y, z):
    return f'<box size="{f(x, y, z)}"/>'


def CY(r, l):
    return f'<cylinder radius="{r:.4g}" length="{l:.4g}"/>'


def build(mesh_prefix):
    u = U(mesh_prefix)
    GREY, DARK, WHITE, BLUE = ("grey", "0.78 0.8 0.82 1"), ("dark", "0.15 0.15 0.16 1"), ("white", "0.93 0.93 0.91 1"), ("blue", "0.1 0.45 0.7 1")
    u.link("base_footprint")
    k = BASE["keel"]
    zt = BASE["deck_top_z"]
    u.link("base_link", 95 + 78 + 28 + 12, (0, 0, 0.42), box_inertia(213, 1.5, 0.6, 0.45), "base_chassis.stl",
           [((0, 0, zt - 0.02), (0, 0, 0), B(BASE["deck_length"] + 0.1, BASE["deck_width"], 0.04)),
            ((0, 0, k["z_bottom"] + k["height"] / 2), (0, 0, 0), B(k["length"], k["width"], k["height"])),
            ((0, 0, BASE["enclosure"]["z_top"] - 0.075), (0, 0, 0), B(*BASE["enclosure"]["size"])),
            ((BASE["deck_length"] / 2 + 0.03, 0, zt - 0.12), (0, 0, 0), B(0.06, BASE["deck_width"] - 0.04, 0.09)),
            ((-BASE["deck_length"] / 2 - 0.03, 0, zt - 0.12), (0, 0, 0), B(0.06, BASE["deck_width"] - 0.04, 0.09))]
           + [((s * BASE["leg_x"], t * BASE["inner_rail_y"], 0.39), (0, 0, 0), B(0.16, 0.05, 0.38)) for s in (1, -1) for t in (1, -1)],
           GREY)
    u.joint("base_footprint_joint", "fixed", "base_footprint", "base_link")
    # wheels
    r, w = WHEEL["radius"], WHEEL["width"]
    for nx, sx in (("front", 1), ("rear", -1)):
        for ny, sy in (("left", 1), ("right", -1)):
            n = f"{nx}_{ny}_wheel"
            u.link(n, 19.5, (0, 0, 0), cyl_inertia(19.5, r, w, "y"), "wheel.stl",
                   [((0, 0, 0), (math.pi / 2, 0, 0), CY(r, w))], DARK)
            u.joint(f"{n}_joint", "continuous", "base_link", n, (sx * BASE["wheelbase"] / 2, sy * BASE["track"] / 2, r),
                    (0, 0, 0), axis=(0, 1, 0))   # +velocity = forward on both sides
    # implement: mast + totes
    H = MAST["height"]
    u.link("harvester_mast", 28, (0, 0, 1.2), box_inertia(28, 0.4, 0.7, 1.2), "harvester_mast.stl",
           [((x, 0, (zt + H) / 2), (0, 0, 0), B(0.04, 0.08, H - zt)) for x in MAST["post_x"]]
           + [((0, 0, ARM["mount_z"]), (0, 0, 0), B(0.38, 2 * ARM["mount_y"], 0.26)),
              ((0, 0, MAST["sensor_bar_z"] + 0.04), (0, 0, 0), B(0.1, 0.7, 0.06)),
              ((0, 0, H + 0.03), (0, 0, 0), CY(0.035, 0.08))], GREY)
    u.joint("mast_joint", "fixed", "base_link", "harvester_mast")
    tx, ty, th = TOTES["size"]
    u.link("harvester_totes", 6, (0, 0, zt + th / 2), box_inertia(6, 1.4, 0.6, th), "harvester_totes.stl",
           [((x, 0, zt + 0.003 + th / 2), (0, 0, 0), B(tx, ty, th)) for x in TOTES["x"]], ("tote", "0.15 0.35 0.62 1"))
    u.joint("totes_joint", "fixed", "base_link", "harvester_totes")
    # sensors (frames only; Gazebo sensors attached below)
    zs = MAST["sensor_bar_z"]
    sens = [("lidar_link", (0, 0, H + 0.032), (0, 0, 0)),
            ("imu_link", (0, 0, BASE["enclosure"]["z_top"] - 0.075), (0, 0, 0)),
            ("gnss_left_link", (0, 0.30, zs + 0.07), (0, 0, 0)),
            ("gnss_right_link", (0, -0.30, zs + 0.07), (0, 0, 0)),
            ("zed_left_link", (0, 0.325, zs - 0.045), (0, math.radians(20), math.pi / 2)),
            ("zed_right_link", (0, -0.325, zs - 0.045), (0, math.radians(20), -math.pi / 2))]
    for n, xyz, rpy in sens:
        u.link(n)
        u.joint(n.replace("_link", "_joint"), "fixed", "base_link", n, xyz, rpy)
    # arms
    d1, a2, a3, d4, d5, d6 = (ARM[k] for k in ("d1", "a2", "a3", "d4", "d5", "d6"))
    chain = [((0, 0, d1), (0, 0, 0)), ((0, 0, 0), (math.pi / 2, 0, 0)), ((a2, 0, 0), (0, 0, 0)),
             ((a3, 0, d4), (0, 0, 0)), ((0, -d5, 0), (math.pi / 2, 0, 0)), ((0, d6, 0), (math.pi / 2, math.pi, math.pi))]
    links = ["shoulder", "upper_arm", "forearm", "wrist_1", "wrist_2", "wrist_3"]
    jn = ["shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"]
    lm = [(4.0, 0.065, 0.14), (6.5, 0.05, 0.43), (3.5, 0.04, 0.40), (1.6, 0.045, 0.10), (1.6, 0.045, 0.10), (0.8, 0.042, 0.04)]
    coll = {
        "shoulder": [((0, 0, 0), (0, 0, 0), CY(0.062, 0.14))],
        "upper_arm": [((a2 / 2, 0, 0.135), (0, math.pi / 2, 0), CY(0.046, abs(a2))), ((0, 0, 0.07), (0, 0, 0), CY(0.062, 0.14)),
                      ((a2, 0, 0.07), (0, 0, 0), CY(0.055, 0.14))],
        "forearm": [((a3 / 2, 0, 0.02), (0, math.pi / 2, 0), CY(0.038, abs(a3))), ((a3, 0, 0.03), (0, 0, 0), CY(0.045, 0.09))],
        "wrist_1": [((0, 0, 0), (0, 0, 0), CY(0.045, 0.09))],
        "wrist_2": [((0, 0, 0), (0, 0, 0), CY(0.045, 0.09))],
        "wrist_3": [((0, 0, -0.02), (0, 0, 0), CY(0.042, 0.04))],
    }
    for side, s in (("left", 1), ("right", -1)):
        p = f"{side}_arm_"
        u.link(p + "base", 2.0, (0, 0, 0.045), cyl_inertia(2.0, 0.075, 0.09), "arm_arm_base.stl",
               [((0, 0, 0.045), (0, 0, 0), CY(0.075, 0.09))], DARK)
        u.joint(p + "mount_joint", "fixed", "harvester_mast", p + "base", (ARM["mount_x"], s * ARM["mount_y"], ARM["mount_z"]),
                (-s * math.pi / 2, 0, 0))
        parent = p + "base"
        for i, (ln, (xyz, rpy), (m, rr, hh)) in enumerate(zip(links, chain, lm)):
            u.link(p + ln, m, (0, 0, 0), cyl_inertia(m, rr, hh), f"arm_{ln}.stl", coll[ln],
                   WHITE if ln in ("upper_arm", "forearm") else DARK)
            u.joint(p + jn[i] + "_joint", "revolute", parent, p + ln, xyz, rpy, (0, 0, 1),
                    (math.radians(ARM["limits_deg"][i][0]), math.radians(ARM["limits_deg"][i][1]), FR5_EFFORT[i], FR5_VEL[i]))
            parent = p + ln
        u.link(p + "tool0")
        u.joint(p + "tool0_joint", "fixed", parent, p + "tool0")
        # end-effector
        e = p.replace("arm_", "ee_")
        u.link(e + "body", EE["mass"] - 0.15, (0, 0, 0.08), cyl_inertia(0.95, 0.045, 0.16), "ee_body.stl",
               [((0, 0, 0.073), (0, 0, 0), CY(EE["body_d"] / 2, 0.146)), ((0.067, 0, 0.12), (0, 0, 0), B(0.03, 0.03, 0.06))], GREY)
        u.joint(e + "mount_joint", "fixed", p + "tool0", e + "body")
        fz = 0.018 + EE["body_len"] + 0.022
        for i in range(3):
            a = math.radians(90 + 120 * i)
            fn = f"{e}finger_{i+1}"
            u.link(fn, 0.05, (0, 0, 0.04), box_inertia(0.05, 0.03, 0.028, 0.095), "ee_finger.stl",
                   [((0, 0, EE["finger_len"] / 2), (0, 0, 0), B(0.024, EE["finger_w"], EE["finger_len"]))], BLUE)
            u.joint(fn + "_joint", "revolute", e + "body", fn,
                    (0.038 * math.cos(a), 0.038 * math.sin(a), fz), (0, 0, a),
                    (0, -1, 0), (-0.15, 0.45, 2.0, 2.0), mimic=None)   # no mimic: ros2_control forbids commanding mimic joints; send the same value to all 3
        u.link(e + "suction_cup", 0.04, (0, 0, 0.02), cyl_inertia(0.04, 0.02, 0.04),
               None, [((0, 0, 0.02), (0, 0, 0), CY(EE["cup_d"] / 2, 0.02))])
        # q = 0: cup lip just past the fingertips (first contact); q = -cup_stroke: retracted, fruit seated between the fingers
        u.joint(e + "suction_joint", "prismatic", e + "body", e + "suction_cup", (0, 0, fz + EE["finger_len"] - 0.015), (0, 0, 0), (0, 0, 1),
                (-EE["cup_stroke"], 0.0, 40.0, 0.25))
        u.link(e + "camera_link")
        tilt = math.atan2(EE["cam_x"], EE["tcp_z"] - EE["cam_z"])
        u.joint(e + "camera_joint", "fixed", e + "body", e + "camera_link", (EE["cam_x"], 0, EE["cam_z"] + 0.012),
                (0, -math.pi / 2 - tilt, 0))   # camera x-axis looks along the tool, aimed at the TCP
        u.link(e + "tcp")
        u.joint(e + "tcp_joint", "fixed", e + "body", e + "tcp", (0, 0, EE["tcp_z"]))
    return u.s


def gazebo_and_control(ns="agrobo_harvester"):
    wheels = [f"{a}_{b}_wheel_joint" for a in ("front", "rear") for b in ("left", "right")]
    x = ['  <ros2_control name="AgroboHarvester" type="system">',
         '    <hardware><plugin>gz_ros2_control/GazeboSimSystem</plugin></hardware>']
    for w in wheels:
        x.append(f'    <joint name="{w}"><command_interface name="velocity"/><state_interface name="position"/><state_interface name="velocity"/></joint>')
    for side in ("left", "right"):
        for j in ("shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"):
            x.append(f'    <joint name="{side}_arm_{j}_joint"><command_interface name="position"/>'
                     '<state_interface name="position"><param name="initial_value">0.0</param></state_interface><state_interface name="velocity"/></joint>')
        for j in ("finger_1_joint", "finger_2_joint", "finger_3_joint", "suction_joint"):
            x.append(f'    <joint name="{side}_ee_{j}"><command_interface name="position"/><state_interface name="position"/><state_interface name="velocity"/></joint>')
    x.append("  </ros2_control>")
    x.append(f'''  <gazebo><plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find agrobo_description)/config/ros2_controllers.yaml</parameters></plugin>
    <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher"/>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin></gazebo>''')
    for w in wheels:   # skid steer: low lateral friction so the robot can turn (same trick as the prototype sim)
        x.append(f'  <gazebo reference="{w.replace("_joint", "")}"><mu1>1.0</mu1><mu2>0.35</mu2><fdir1>1 0 0</fdir1></gazebo>')

    def cam(link, name, w, h, hfov, rate, far, depth=True):
        s = f'''  <gazebo reference="{link}"><sensor name="{name}" type="{'rgbd_camera' if depth else 'camera'}"><always_on>1</always_on><update_rate>{rate}</update_rate>
    <topic>{ns}/{name}</topic><gz_frame_id>{link}</gz_frame_id><camera><horizontal_fov>{hfov}</horizontal_fov><image><width>{w}</width><height>{h}</height></image>
    <clip><near>{0.07 if 'd405' in name else 0.3}</near><far>{far}</far></clip><noise><type>gaussian</type><mean>0</mean><stddev>0.007</stddev></noise></camera></sensor></gazebo>'''
        return s
    x.append(cam("zed_left_link", "zed_left", 960, 600, 1.92, 15, 15))
    x.append(cam("zed_right_link", "zed_right", 960, 600, 1.92, 15, 15))
    x.append(cam("left_ee_camera_link", "left_d405", 640, 480, 1.52, 15, 0.5))
    x.append(cam("right_ee_camera_link", "right_d405", 640, 480, 1.52, 15, 0.5))
    x.append(f'''  <gazebo reference="lidar_link"><sensor name="lidar" type="gpu_lidar"><always_on>1</always_on><update_rate>10</update_rate>
    <topic>{ns}/lidar</topic><gz_frame_id>lidar_link</gz_frame_id><lidar><scan><horizontal><samples>900</samples><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal>
    <vertical><samples>32</samples><min_angle>-0.1222</min_angle><max_angle>0.9076</max_angle></vertical></scan><range><min>0.1</min><max>40</max></range>
    <noise><type>gaussian</type><mean>0</mean><stddev>0.02</stddev></noise></lidar></sensor></gazebo>''')
    x.append(f'''  <gazebo reference="imu_link"><sensor name="imu" type="imu"><always_on>1</always_on><update_rate>200</update_rate><topic>{ns}/imu</topic>
    <gz_frame_id>imu_link</gz_frame_id></sensor></gazebo>''')
    x.append(f'''  <gazebo reference="gnss_left_link"><sensor name="navsat" type="navsat"><always_on>1</always_on><update_rate>10</update_rate><topic>{ns}/navsat</topic>
    <gz_frame_id>gnss_left_link</gz_frame_id></sensor></gazebo>''')
    return x


def write(path, mesh_prefix, with_gazebo):
    body = build(mesh_prefix)
    xml = ['<?xml version="1.0"?>',
           '<!-- Agrobo HM-1 harvester on AB-1 base. GENERATED by urdf/generate_urdf.py from cad/src/params.py. Do not hand-edit. -->',
           '<robot name="agrobo_harvester">'] + body + (gazebo_and_control() if with_gazebo else []) + ["</robot>", ""]
    s = "\n".join(xml).replace("<visual><geometry>None</geometry></visual>", "")
    s = s.replace(f'<mesh filename="{mesh_prefix}None"/>', "")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(s)
    print("wrote", path)


if __name__ == "__main__":
    root = os.path.join(HERE, PKG)
    write(os.path.join(root, "urdf", "agrobo_harvester.urdf"), f"package://{PKG}/meshes/", True)
    write(os.path.join(root, "agrobo_harvester.relative.urdf"), "meshes/", False)

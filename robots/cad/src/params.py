"""Single source of truth for Agrobo robot geometry (SI units: metres, kg).

CAD (cadquery), URDF generation and the design calculations all import this file,
so a change here propagates to STEP/STL, the URDF used for training, and the calcs.
Frame: x forward, y left, z up. Origin = ground point under the geometric centre of the 4 wheels.
"""

# ---------------------------------------------------------------- field (SW Florida staked tomato)
FIELD = dict(
    bed_centres=1.83,        # 6 ft bed centres (UF/IFAS typical; confirm per grower)
    bed_top_width=0.81,      # 32 in
    bed_base_width=0.95,
    bed_height=0.20,         # 8 in raised, plastic-mulched
    plant_spacing=0.51,      # 20 in in-row
    canopy_half_width=0.35,  # staked + tied canopy, measured from row centre
    canopy_top=1.45,         # above ground
    fruit_z=(0.45, 1.40),    # fruit band above ground (bed top + 0.25 .. 1.2)
)

# ---------------------------------------------------------------- AB-1 base platform
WHEEL = dict(radius=0.254, width=0.203,          # 20x8.00-10 turf tyre on 10 in rim
             model="OZO 3000 W 48 V hub motor ref 000500 + 20x8.00-10 turf tyre")
BASE = dict(
    track=0.58,            # wheel centre to wheel centre (y)
    wheelbase=1.10,        # x
    deck_length=1.50,
    deck_width=0.76,
    deck_top_z=0.600,      # top of deck frame
    ext=0.0381,            # 80/20 1515 profile, 1.5 in square
    inner_rail_y=0.17,     # inner longitudinal rails (legs hang from these)
    leg_x=0.55,            # = wheelbase/2
    keel=dict(length=0.68, width=0.29, height=0.25, z_bottom=0.15),   # LFP pack, 16S2P EVE LF105
    enclosure=dict(size=(0.60, 0.28, 0.15), z_top=0.555),            # IP66 box slung under deck, shaded
    mass_frame=95.0, mass_battery=78.0, mass_wheel_motor=12.5 + 7.0,   # motor + tyre/rim
    mass_enclosure=28.0,
)

# ---------------------------------------------------------------- HM-1 harvester implement
ARM = dict(
    model="Fairino FR5 (IP54 arm, DC MINI controller 30-60 VDC)",
    reach=0.922, payload=5.0, mass=22.0,
    # UR-style DH (FR5 v6, from vendor URDF frcobot_ros2; verify against vendor file before cutting metal)
    d1=0.152, a2=-0.425, a3=-0.395, d4=0.102, d5=0.102, d6=0.100,
    # joint ranges deg (FR5 datasheet, top3dshop.com/product/fairino-fr5); check sign convention vs vendor URDF zero
    limits_deg=((-175, 175), (-265, 85), (-160, 160), (-265, 85), (-175, 175), (-175, 175)),
    mount_z=0.95, mount_y=0.22, mount_x=0.0,    # arm base flange plane; base axis points +/-y (side mounted)
)
MAST = dict(height=1.85, post_x=(-0.15, 0.15), sensor_bar_z=1.60)   # two 1530 posts, lidar on top
TOTES = dict(size=(0.50, 0.60, 0.35), x=(0.47, -0.47))  # 600x500 stacking totes (x,y,h), front + rear, ~35 kg fruit each
HARVESTER_MASS = dict(arms=2 * 22.0, controllers=2 * 2.5, mast=18.0, crates_full=2 * 35.0 + 2 * 3.0,
                      ee=2 * 1.1, sensors=6.0, lights=4.0)

# ---------------------------------------------------------------- EE-1 end-effector
EE = dict(
    flange="ISO 9409-1-50-4-M6",
    body_d=0.090, body_len=0.110,
    finger_len=0.095, finger_w=0.028, n_fingers=3, grip_open_d=0.120, grip_closed_d=0.045,
    cup_d=0.040, cup_stroke=0.065,   # rest: lip just past fingertips; retracts 65 mm to seat a 70-80 mm fruit between the fingers
    mass=1.10,
    tcp_z=0.205,          # flange to grasp centre
    cam_x=0.080, cam_z=0.065,   # D405 optical centre, aimed at the TCP (keeps fingers in the lower image edge)
)

# ================================================================ REV B: made-in-USA sourcing (Laksh, 2026-11-01)
# Rev B swaps parts for US sources. Values below are what the new parts force; items marked TODO need the vendor
# drawing before CAD/URDF are regenerated (build.py and generate_urdf.py still model rev A.1 geometry).
REV = "B"
ARM_REVB = dict(
    model="Standard Bots Spark (designed and assembled in Glen Cove, NY)",
    payload=7.0, reach=0.95, mass=21.0, ip="IP65 (design)", power="AC mains controller; no DC input stated -> 48 V to 120 VAC inverter",
    peak_w=1500, typical_w=200, base_dia=0.200,
    kinematics="TODO: vendor URDF; joint ranges not published. FR5 DH kept as placeholder in ARM.",
)
DRIVE_REVB = dict(   # no confirmed US-made hub motor: inboard motor + right-angle reducer per wheel
    type="inboard BLDC + Winsmith RD right-angle reducer, 12:1, wheel on reducer output shaft",
    ratio=12.0, motor_cont_Nm=4.6, motor_peak_Nm=13.8, motor_rpm_at_1p5ms=680,
    reducer_envelope=(0.20, 0.16, 0.18),   # TODO confirm from Winsmith RD catalogue (x, y, z) m
    mass_per_wheel=12.5 + 7.0 + 4.0,      # motor + reducer + tyre/rim; +4 kg vs hub motor (estimate)
    note="Reducer sits inboard of each wheel at the leg: axle plate becomes a reducer mount; keel width (0.29 m) still clears.",
)
LIDAR_REVB = dict(model="Ouster OS0-64 (made in US and Thailand; specify US-built units)", dia=0.087, height=0.074, mass=0.45, vfov_deg=90)
STEREO_REVB = dict(model="Carnegie Robotics MultiSense S27 (built in USA)", interface="GbE", baseline=0.27,
                   note="27 cm baseline vs 12 cm ZED X: wider camera bar at sensor_bar_z; TODO dims from datasheet")

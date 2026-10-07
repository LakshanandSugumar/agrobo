#!/usr/bin/env python3
"""Generate the Gazebo (gz-sim Harmonic) farm world: terrain, tomato rows by growth stage,
a modular UGV with diff-drive, IMU and RTK-style NavSat, and the hub building.

    python3 generate_farm_world.py --rows 10 --plants 48 --stage fruiting -o farm.sdf

Growth stage changes plant geometry (height, canopy radius, fruit count/colour), so the
same generator renders any day of the season from /field/state snapshots.
Terrain: a gently undulating, collision-enabled mesh-free surface built from tilted
box tiles (1.5 m pitch, +-2 % slope noise) so wheel-terrain contact and odometry drift
are exercised without needing a rendering-backed heightmap in headless CI.
"""
import argparse
import math
import random

STAGES = {  # height m, canopy radius m, fruit per plant, ripe fraction
    "seedling": (0.15, 0.06, 0, 0.0),
    "vegetative": (0.45, 0.18, 0, 0.0),
    "flowering": (0.7, 0.25, 0, 0.0),
    "fruiting": (1.0, 0.3, 8, 0.4),
}


def plant_sdf(i, x, y, stage, rng):
    h, r, nf, ripe = STAGES[stage]
    fruit = []
    for k in range(nf):
        a = rng.uniform(0, 2 * math.pi)
        fz = rng.uniform(0.25, h * 0.9)
        col = "0.85 0.1 0.08 1" if rng.random() < ripe else "0.35 0.65 0.2 1"
        fruit.append(f"""
        <visual name="fruit_{k}"><pose>{0.8 * r * math.cos(a):.3f} {0.8 * r * math.sin(a):.3f} {fz:.3f} 0 0 0</pose>
          <geometry><sphere><radius>0.035</radius></sphere></geometry>
          <material><diffuse>{col}</diffuse><ambient>{col}</ambient></material></visual>""")
    return f"""
    <model name="tomato_{i}"><static>true</static><pose>{x:.3f} {y:.3f} 0 0 0 0</pose>
      <link name="plant">
        <visual name="stem"><pose>0 0 {h / 2:.3f} 0 0 0</pose>
          <geometry><cylinder><radius>0.012</radius><length>{h:.3f}</length></cylinder></geometry>
          <material><diffuse>0.25 0.45 0.15 1</diffuse></material></visual>
        <visual name="canopy"><pose>0 0 {h * 0.65:.3f} 0 0 0</pose>
          <geometry><sphere><radius>{r:.3f}</radius></sphere></geometry>
          <material><diffuse>0.18 0.5 0.15 1</diffuse></material></visual>
        <collision name="stake"><pose>0 0 {h / 2:.3f} 0 0 0</pose>
          <geometry><cylinder><radius>0.03</radius><length>{h:.3f}</length></cylinder></geometry></collision>{''.join(fruit)}
      </link></model>"""


def terrain_sdf(L, W, rng, pitch=1.5):
    tiles = []
    nx, ny = int(math.ceil((L + 8) / pitch)), int(math.ceil((W + 8) / pitch))
    for i in range(nx):
        for j in range(ny):
            x, y = -4 + (i + 0.5) * pitch, -4 + (j + 0.5) * pitch
            rx, ry = rng.gauss(0, 0.012), rng.gauss(0, 0.012)
            tiles.append(f"""
        <collision name="t{i}_{j}"><pose>{x:.2f} {y:.2f} -0.05 {rx:.4f} {ry:.4f} 0</pose>
          <geometry><box><size>{pitch + 0.02} {pitch + 0.02} 0.1</size></box></geometry>
          <surface><friction><ode><mu>0.8</mu><mu2>0.7</mu2></ode></friction></surface></collision>""")
    return f"""
    <model name="field_terrain"><static>true</static>
      <link name="ground">{''.join(tiles)}
        <visual name="soil"><pose>{L / 2:.2f} {W / 2:.2f} -0.001 0 0 0</pose>
          <geometry><plane><normal>0 0 1</normal><size>{L + 8} {W + 8}</size></plane></geometry>
          <material><diffuse>0.42 0.3 0.2 1</diffuse></material></visual>
      </link></model>"""


def ugv_sdf(name, x, y):
    wheels, joints = [], []
    for wn, wx, wy in (("fl", 0.28, 0.33), ("fr", 0.28, -0.33), ("rl", -0.28, 0.33), ("rr", -0.28, -0.33)):
        wheels.append(f"""
      <link name="wheel_{wn}"><pose>{wx} {wy} 0.18 -1.5708 0 0</pose>
        <inertial><mass>4</mass><inertia><ixx>0.04</ixx><iyy>0.04</iyy><izz>0.065</izz></inertia></inertial>
        <collision name="c"><geometry><cylinder><radius>0.18</radius><length>0.1</length></cylinder></geometry>
          <!-- skid-steer: low lateral friction along the wheel axis (fdir1), full longitudinal grip -->
          <surface><friction><ode><mu>0.3</mu><mu2>1.0</mu2><fdir1>0 0 1</fdir1></ode></friction></surface></collision>
        <visual name="v"><geometry><cylinder><radius>0.18</radius><length>0.1</length></cylinder></geometry>
          <material><diffuse>0.1 0.1 0.1 1</diffuse></material></visual></link>""")
        joints.append(f"""
      <joint name="j_{wn}" type="revolute"><parent>chassis</parent><child>wheel_{wn}</child>
        <axis><xyz>0 0 1</xyz></axis></joint>""")
    return f"""
    <model name="{name}"><pose>{x} {y} 0.05 0 0 0</pose>
      <link name="chassis"><pose>0 0 0.35 0 0 0</pose>
        <inertial><mass>120</mass><inertia><ixx>6</ixx><iyy>10</iyy><izz>12</izz></inertia></inertial>
        <collision name="c"><geometry><box><size>1.0 0.5 0.3</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>1.0 0.5 0.3</size></box></geometry>
          <material><diffuse>0.95 0.55 0.1 1</diffuse></material></visual>
        <visual name="mast"><pose>0.3 0 0.45 0 0 0</pose><geometry><cylinder><radius>0.03</radius><length>0.6</length></cylinder></geometry></visual>
        <sensor name="imu" type="imu"><always_on>1</always_on><update_rate>100</update_rate><topic>/{name}/imu</topic>
          <imu><angular_velocity><z><noise type="gaussian"><stddev>0.002</stddev></noise></z></angular_velocity></imu></sensor>
        <sensor name="gnss" type="navsat"><always_on>1</always_on><update_rate>10</update_rate><topic>/{name}/navsat</topic>
          <!-- gz applies horizontal NavSat noise in degrees: 1.35e-7 deg = 1.5 cm (RTK fixed) -->
          <navsat><position_sensing><horizontal><noise type="gaussian"><stddev>1.35e-7</stddev></noise></horizontal>
          <vertical><noise type="gaussian"><stddev>0.03</stddev></noise></vertical></position_sensing></navsat></sensor>
      </link>{''.join(wheels)}{''.join(joints)}
      <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
        <left_joint>j_fl</left_joint><left_joint>j_rl</left_joint>
        <right_joint>j_fr</right_joint><right_joint>j_rr</right_joint>
        <wheel_separation>0.66</wheel_separation><wheel_radius>0.18</wheel_radius>
        <max_linear_acceleration>0.8</max_linear_acceleration>
        <topic>/model/{name}/cmd_vel</topic><odom_topic>/model/{name}/odometry</odom_topic>
        <frame_id>{name}/odom</frame_id><child_frame_id>{name}/base_link</child_frame_id>
        <odom_publish_frequency>30</odom_publish_frequency></plugin>
      <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
        <publish_link_pose>false</publish_link_pose><publish_model_pose>true</publish_model_pose>
        <use_pose_vector_msg>false</use_pose_vector_msg><update_frequency>20</update_frequency></plugin>
    </model>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=10)
    ap.add_argument("--plants", type=int, default=48)
    ap.add_argument("--row-spacing", type=float, default=1.5)
    ap.add_argument("--plant-spacing", type=float, default=0.5)
    ap.add_argument("--stage", default="fruiting", choices=list(STAGES))
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("-o", "--out", default="farm.sdf")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    L, W = a.plants * a.plant_spacing, a.rows * a.row_spacing
    plants = [plant_sdf(r * a.plants + k + 1, (k + 0.5) * a.plant_spacing, (r + 0.5) * a.row_spacing, a.stage, rng)
              for r in range(a.rows) for k in range(a.plants)]
    sdf = f"""<?xml version="1.0"?>
<!-- generated by generate_farm_world.py: {a.rows} rows x {a.plants} plants, stage={a.stage} -->
<sdf version="1.9">
  <world name="agrobo_farm">
    <physics name="1ms" type="ignored"><max_step_size>0.002</max_step_size><real_time_factor>0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>
    <spherical_coordinates><surface_model>EARTH_WGS84</surface_model><world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>35.9519</latitude_deg><longitude_deg>-119.8804</longitude_deg><elevation>95</elevation><heading_deg>0</heading_deg>
    </spherical_coordinates>
    <gravity>0 0 -9.8</gravity>
    <light type="directional" name="sun"><cast_shadows>false</cast_shadows><pose>0 0 10 0 0 0</pose>
      <diffuse>1 1 1 1</diffuse><direction>-0.4 0.2 -0.9</direction></light>
    {terrain_sdf(L, W, rng)}
    <model name="hub"><static>true</static><pose>-15 -10 1.5 0 0 0</pose><link name="b">
      <collision name="c"><geometry><box><size>8 6 3</size></box></geometry></collision>
      <visual name="v"><geometry><box><size>8 6 3</size></box></geometry><material><diffuse>0.8 0.8 0.85 1</diffuse></material></visual>
    </link></model>
    {ugv_sdf("ugv_alpha", -2.0, 0.0)}
    {''.join(plants)}
  </world>
</sdf>
"""
    with open(a.out, "w") as f:
        f.write(sdf)
    print(f"wrote {a.out}: {len(plants)} plants, field {L:.1f} x {W:.1f} m")


if __name__ == "__main__":
    main()

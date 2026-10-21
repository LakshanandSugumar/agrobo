#!/usr/bin/env python3
"""Generate a randomised Gazebo (Harmonic, SDF 1.9) tomato-field world from the exported Agrobo models.

Every option is a domain-randomisation knob for training: change --seed to get a new field.
  python3 generate_world.py --rows 8 --plants 30 --stage mixed --weeds 0.3 --ripe 0.4 --seed 7 -o ../worlds/agrobo_field_s7.sdf
"""
import argparse, json, math, os, random

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', type=int, default=8); ap.add_argument('--plants', type=int, default=30)
    ap.add_argument('--row-gap', type=float, default=1.6); ap.add_argument('--spacing', type=float, default=0.5)
    ap.add_argument('--stage', choices=['seedling', 'vegetative', 'fruiting', 'mixed'], default='fruiting')
    ap.add_argument('--weeds', type=float, default=0.25, help='weeds per metre of furrow')
    ap.add_argument('--ripe', type=float, default=0.4, help='loose fruit on the ground/benches for pick training: share that is red')
    ap.add_argument('--loose-fruit', type=int, default=0, help='number of free (dynamic) fruit placed in furrows for grasp drills')
    ap.add_argument('--sun-elev', type=float, default=None, help='sun elevation deg (random 10-70 if omitted)')
    ap.add_argument('--robots', default='tiller,laser,uav', help='comma list of robots to place as static props (tiller,laser,uav)')
    ap.add_argument('--no-trainer', action='store_true', help='leave out the drivable sensor robot agrobo_trainer')
    ap.add_argument('--seed', type=int, default=1); ap.add_argument('-o', '--out', default='../worlds/agrobo_field.sdf')
    a = ap.parse_args(); R = random.Random(a.seed)
    elev = math.radians(a.sun_elev if a.sun_elev is not None else R.uniform(10, 70)); az = R.uniform(0, 2 * math.pi)
    sun = (-math.cos(elev) * math.cos(az), -math.cos(elev) * math.sin(az), -math.sin(elev))
    L = a.plants * a.spacing; inc = []; gt = {'fruit': [], 'weeds': [], 'loose_fruit': []}
    def include(uri, name, x, y, z=0, yaw=0):
        inc.append(f'    <include><uri>model://{uri}</uri><name>{name}</name><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.3f}</pose></include>')
    beds = []
    for r in range(a.rows):
        y = r * a.row_gap
        beds.append(f'''        <collision name="bed{r}"><pose>{L / 2 - .25:.2f} {y:.2f} 0.08 0 0 0</pose><geometry><box><size>{L + 1:.2f} 0.8 0.16</size></box></geometry></collision>
        <visual name="bed{r}"><pose>{L / 2 - .25:.2f} {y:.2f} 0.08 0 0 0</pose><geometry><box><size>{L + 1:.2f} 0.8 0.16</size></box></geometry>
          <material><ambient>0.16 0.11 0.07 1</ambient><diffuse>0.24 0.16 0.1 1</diffuse></material></visual>
        <visual name="tape{r}"><pose>{L / 2 - .25:.2f} {y + .12:.2f} 0.165 0 1.5708 0</pose><geometry><cylinder><radius>0.012</radius><length>{L + 1:.2f}</length></cylinder></geometry>
          <material><diffuse>0.02 0.02 0.02 1</diffuse></material></visual>''')
        for i in range(a.plants):
            st = a.stage if a.stage != 'mixed' else R.choice(['seedling', 'vegetative', 'fruiting'])
            pm = f'tomato_plant_{st}_{R.randrange(3)}'; px, py, yaw = i * a.spacing + R.uniform(-.04, .04), y + R.uniform(-.03, .03), R.uniform(0, 6.28)
            include(pm, f'plant_r{r}_p{i}', px, py, .16, yaw)
            # fruit on the vine are separate models sharing the plant pose: one box / instance each, plus ground truth
            fj = f'{MODELS}/{pm}/fruit.json'
            for f in (json.load(open(fj)) if os.path.exists(fj) else []):
                fname = f'plant_r{r}_p{i}_' + f['model'].rsplit('_', 2)[-2] + '_' + f['model'].rsplit('_', 1)[-1]
                include(f['model'], fname, px, py, .16, yaw); fx, fy, fz = f['xyz']
                gt['fruit'].append({'name': fname, 'class': f['class'], 'label': f['label'], 'plant': f'plant_r{r}_p{i}',
                                    'xyz': [round(px + fx * math.cos(yaw) - fy * math.sin(yaw), 4), round(py + fx * math.sin(yaw) + fy * math.cos(yaw), 4), round(.16 + fz, 4)]})
    k = 0
    for r in range(a.rows - 1):
        yf = r * a.row_gap + a.row_gap / 2
        for _ in range(int(a.weeds * L)):
            wx, wy = R.uniform(0, L), yf + R.uniform(-.3, .3); include('weed_seedling', f'weed_{k}', wx, wy, 0, R.uniform(0, 6.28))
            gt['weeds'].append({'name': f'weed_{k}', 'xyz': [round(wx, 4), round(wy, 4), 0]}); k += 1
    for j in range(a.loose_fruit):
        c = 'red' if R.random() < a.ripe else R.choice(['green', 'turning'])
        lx, ly = R.uniform(0, L), R.randrange(max(1, a.rows - 1)) * a.row_gap + a.row_gap / 2 + R.uniform(-.2, .2)
        include(f'tomato_fruit_{c}', f'fruit_{j}', lx, ly, .05)
        gt['loose_fruit'].append({'name': f'fruit_{j}', 'class': {'red': 'ripe', 'turning': 'turning', 'green': 'unripe'}[c], 'xyz': [round(lx, 4), round(ly, 4), .05]})
    robots = [s for s in a.robots.split(',') if s]
    if 'tiller' in robots: include('agrobo_ugv_tiller', 'ugv_tiller', -3, -1.5, 0, 0)
    if 'laser' in robots: include('agrobo_ugv_laser', 'ugv_laser', 1, a.row_gap * 2.5, 0, 0)
    if 'uav' in robots: include('agrobo_scout_uav', 'scout_uav', 3, a.row_gap * 1.5, 4, 0)
    # drivable sensor robot on the headland, lined up with the first furrow (wheels ride the bed shoulders)
    if not a.no_trainer: include('agrobo_trainer', 'agrobo_trainer', -2.5, a.row_gap / 2, 0.17, 0)
    sdf = f'''<?xml version="1.0"?>
<!-- generated by agrobo-world/tools/generate_world.py: rows={a.rows} plants={a.plants} stage={a.stage} weeds/m={a.weeds} seed={a.seed} -->
<sdf version="1.9">
  <world name="agrobo_field">
    <physics name="2ms" type="ignored"><max_step_size>0.002</max_step_size><real_time_factor>1</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>
    <spherical_coordinates><surface_model>EARTH_WGS84</surface_model><world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>35.9519</latitude_deg><longitude_deg>-119.8804</longitude_deg><elevation>95</elevation><heading_deg>0</heading_deg></spherical_coordinates>
    <scene><ambient>0.45 0.45 0.45 1</ambient><background>0.62 0.75 0.9 1</background><shadows>true</shadows></scene>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>0 0 30 0 0 0</pose>
      <diffuse>1 0.96 0.88 1</diffuse><specular>0.3 0.3 0.3 1</specular><direction>{sun[0]:.3f} {sun[1]:.3f} {sun[2]:.3f}</direction></light>
    <model name="ground"><static>true</static>
      <link name="link">
        <collision name="plane"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
          <surface><friction><ode><mu>0.8</mu><mu2>0.7</mu2></ode></friction></surface></collision>
        <visual name="plane"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
          <material><ambient>0.12 0.09 0.06 1</ambient><diffuse>0.2 0.15 0.1 1</diffuse></material></visual>
{chr(10).join(beds)}
      </link>
    </model>
{chr(10).join(inc)}
  </world>
</sdf>
'''
    open(a.out, 'w').write(sdf)
    gt_path = os.path.splitext(a.out)[0] + '.truth.json'; gt.update(seed=a.seed, sun_elev_deg=round(math.degrees(elev), 1))
    json.dump(gt, open(gt_path, 'w'), indent=1)
    print(f'wrote {a.out}: {a.rows * a.plants} plants, {len(gt["fruit"])} fruit on the vine, {k} weeds, {a.loose_fruit} loose fruit, '
          f'sun elev {math.degrees(elev):.0f} deg; ground truth in {gt_path}')

if __name__ == '__main__': main()

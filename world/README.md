# Agrobo training world

The same 3D tomato farm as the Agrobo film, packaged so robots can be trained on it. There are two ways in:

1. **Gazebo Harmonic + ROS 2 Jazzy world.** A drivable Agrobo UGV streams RGB, depth, semantic and instance segmentation, per-tomato 2D boxes, lidar, IMU and GNSS. Every world comes with a ground-truth file that gives each tomato's 3D position and ripeness.
2. **Photoreal synthetic dataset generator (Blender Cycles).** It writes path-traced images with pixel-exact instance masks and COCO annotations, for training the ripeness and weed detectors.

Both use one label scheme:

| id | class |
|---|---|
| 1 | tomato_ripe |
| 2 | tomato_turning |
| 3 | tomato_unripe |
| 4 | weed |
| 5 | plant (foliage) |
| 6 | UGV |
| 7 | UAV |

COCO files contain ids 1 to 4.

Tested on 2026-10-10 with Gazebo Sim 8.10 and ROS 2 Jazzy from RoboStack, headless. The robot drove down the first furrow, and every topic below published. `preview/gazebo-sensors.jpg` shows what that run captured: the RGB image, depth, the semantic map, and the boxes drawn over the RGB image.

## Layout
```
models/    Gazebo models (SDF 1.9, OBJ meshes)
           tomato_plant_{seedling,vegetative,fruiting}_{0,1,2}: foliage, stem collision, label 5
           tomato_plant_fruiting_*_fruit_<k>: each tomato on the vine, its own model, label 1/2/3
           tomato_fruit_{red,turning,green}: loose dynamic fruit (0.12 kg) for grasp drills
           weed_seedling, agrobo_ugv_{tiller,laser}, agrobo_scout_uav: static props
           agrobo_trainer: drivable UGV with the sensor stack below
worlds/    agrobo_field.sdf (+ .truth.json), agrobo_field_training_s7.sdf (+ .truth.json)
launch/    training_world.launch.py: Gazebo + ROS 2 bridge
scenes/    lib.py, field.py: procedural farm scene code shared with the film
tools/     export_assets.py (Blender -> models), split_meshes.py, generate_world.py
synth/     generate_dataset.py, sample_dataset/ (2 samples)
preview/   gazebo-sensors.jpg, labelled-samples.jpg
```

## Run the world
```bash
export GZ_SIM_RESOURCE_PATH=/path/to/agrobo-world/models
gz sim worlds/agrobo_field.sdf                       # GUI
# or with the ROS 2 bridge (sets the resource path itself):
ros2 launch /path/to/agrobo-world/launch/training_world.launch.py               # headless
ros2 launch /path/to/agrobo-world/launch/training_world.launch.py headless:=false world:=/abs/path/to/world.sdf
# drive down the furrow
ros2 topic pub -r 10 /agrobo_trainer/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}}"
# record a training run
ros2 bag record /agrobo_trainer/camera/image /agrobo_trainer/depth/image /agrobo_trainer/boxes \
  /agrobo_trainer/segmentation/semantic/labels_map /agrobo_trainer/odometry /agrobo_trainer/navsat
```
On a machine without ROS installed, RoboStack works (this is how it was tested):
`micromamba create -p ~/ros -c robostack-jazzy -c conda-forge ros-jazzy-ros-base ros-jazzy-ros-gz ros-jazzy-vision-msgs python=3.12`.

### Robot `agrobo_trainer` topics (ROS side)

All topics sit under `/agrobo_trainer/`. All cameras share one pose and 960×720 intrinsics, so their pixels line up.

| topic | type | notes |
|---|---|---|
| `cmd_vel` | geometry_msgs/Twist | input; diff drive, max 1.5 m/s |
| `odometry` | nav_msgs/Odometry | |
| `imu`, `navsat` | Imu, NavSatFix | world is geo-referenced to the agrobo_sim farm (35.9519, -119.8804) |
| `camera/image`, `camera/camera_info` | Image (rgb8), CameraInfo | 10 Hz |
| `depth/image` | Image (32FC1, metres) | |
| `segmentation/semantic/labels_map` | Image | pixel value = class id above |
| `segmentation/instance/{labels_map,colored_map}` | Image | one instance per model, so per tomato |
| `boxes` | vision_msgs/Detection2DArray | class_id = label; one box per tomato |
| `lidar/points` | PointCloud2 | 16 × 720 beams |

The robot spawns on the headland lined up with the first furrow. Its wheels ride the bed shoulders, and plants only collide at the stem, so it can brush through foliage the way a real UGV does.

### Ground truth
`generate_world.py` writes `<world>.truth.json` next to every world. For each tomato on the vine it records `name`, `class`, `label`, `plant` and world `xyz` (m). It also records the weed positions, the loose-fruit positions, the seed and the sun elevation. Use it to supervise pick-point regression, or to score a detector against the Gazebo model names.

### New randomized worlds
```bash
python3 tools/generate_world.py --rows 8 --plants 30 --stage mixed --weeds 0.4 \
        --loose-fruit 40 --ripe 0.5 --sun-elev 25 --seed 42 -o worlds/field_s42.sdf
```

| option | what it sets |
|---|---|
| `--rows`, `--plants` | field size |
| `--row-gap`, `--spacing` | row and plant spacing (m) |
| `--stage` | growth stage: seedling, vegetative, fruiting or mixed |
| `--weeds` | weeds per metre of furrow |
| `--loose-fruit`, `--ripe` | loose fruit for grasping, and the share that is ripe |
| `--sun-elev` | sun elevation; random 10 to 70° if omitted |
| `--robots` | static props |
| `--no-trainer` | leave out the drivable robot |

Each seed gives a different field, which is the domain randomization for training.

## Photoreal synthetic dataset
```bash
python synth/generate_dataset.py --n 5000 --out dataset --res 960 720 --spp 16 --seed 0
```
This needs Blender as a Python module (`pip install bpy`, Python 3.13) plus Pillow and NumPy.

Each sample randomizes:

- plant growth, ripeness mix and weed density;
- sun angle;
- camera, either a robot-eye view or an overhead drone view.

Outputs:

- `images/NNNNNN.png`: path-traced RGB.
- `masks/NNNNNN.png`: R + 256·G = instance index, B = class id. Values are exact, with no anti-aliasing.
- `annotations.json`: COCO, with bbox, area and `instance_value` linking each annotation to its mask colour.

Runs are resumable: existing samples are skipped. On CPU it takes about 15 s per 640×480 sample at 8 spp. `preview/labelled-samples.jpg` shows the two samples with their boxes.

## Rebuilding the models
`tools/export_assets.py` runs under the same bpy and rebuilds every model from the procedural scene code in `scenes/` (the same code that renders the film). It then runs `split_meshes.py`, which:

- makes leaves double-sided, because Gazebo culls back faces;
- turns each tomato into its own labeled model, and writes `fruit.json` per plant for the world generator.

## Limits, stated plainly
- Gazebo uses rasterized rendering, which is clearly simpler than the Cycles film look. Use the synth generator when photorealism matters for perception, and Gazebo for closed-loop driving, navigation and pick-point training. Mixing the two is the usual sim-to-real recipe.
- Tomatoes on the vine are static. They can be detected and localized but not physically detached. The loose `tomato_fruit_*` models are dynamic, for grasp drills.
- The UGV visual mesh's wheels don't spin. Collision wheels drive it.

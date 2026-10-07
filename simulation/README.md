# Agrobo: autonomous end-to-end farm, ROS 2 simulation prototype

This repository simulates the whole tomato lifecycle as a set of ROS 2 nodes on Jazzy, with Gazebo Harmonic for the physics check:

- **Sourcing:** GIS parcel and crop selection.
- **Prep:** clearing, RTK layout, tillage and drip irrigation.
- **Cultivation:** UAV scouting, laser weeding and per-plant nitrogen micro-dosing.
- **Robotic harvest:** picking plus hauling to the hub.
- **Post-harvest:** hyperspectral grading, cold chain and B2B selling.

A py_trees behaviour tree orchestrates the season. A plant-level digital twin (the Field Ledger) drives every work order.

- Architecture matrix, node/topic/action spec, BT design, moat and KPIs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Measured results, twin vs no-twin ablation over 3 seeds: [`results/REPORT.md`](results/REPORT.md)

## Layout

```
ros2_ws/src/
  agrobo_interfaces/      msgs (PlantState, FieldState, SensorFrame, DetectionArray, HarvestLot, ...),
                          srvs (FieldInteract, GetFieldState, AdvanceDay, PlanCoverage, EvaluateParcels),
                          actions (PrepField, Transplant, ScoutField, WeedZone, DoseNutrients,
                                   HarvestRows, HaulToHub, ProcessLot, SellInventory)
  agrobo_sim/
    agrobo_sim/core/      ROS-free models: agronomy, perception error, twin, planning,
                          post-harvest, market, strategy, economics
    agrobo_sim/*.py       16 nodes (field_world, mission_orchestrator, ugv_platform, ...)
    launch/               season.launch.py (full season), gazebo_field.launch.py (physics check)
    worlds/               generate_farm_world.py -> farm.sdf
scripts/                  run_experiments.sh, make_report.py
results/                  REPORT.md, kpi_summary.json, charts/, runs/, gazebo/
```

## Run it

RoboStack (conda) works without root. `apt install ros-jazzy-desktop ros-jazzy-ros-gz python3-py-trees` works too.

```bash
mamba create -p ~/ros -c robostack-jazzy -c conda-forge python=3.12 ros-jazzy-ros-base ros-jazzy-py-trees \
    ros-jazzy-ros-gz ros-jazzy-rosidl-default-generators ros-jazzy-ament-cmake colcon-common-extensions \
    cmake compilers pkg-config make matplotlib
conda activate ~/ros
cd ros2_ws && colcon build && source install/setup.bash

# full 125-day season, all 5 phases (headless, ~1-2 min)
ros2 launch agrobo_sim season.launch.py twin_guided:=true run_name:=demo output_dir:=../results/runs
# ablation: same robots, no twin
ros2 launch agrobo_sim season.launch.py twin_guided:=false run_name:=demo_notwin output_dir:=../results/runs

# live behaviour-tree status while it runs
ros2 topic echo /mission_orchestrator/bt_snapshot --field data

# Gazebo physics check (headless; headless:=false opens the GUI)
ros2 launch agrobo_sim gazebo_field.launch.py lanes:=4 localization:=rtk_imu

# all seeds and the report
../scripts/run_experiments.sh ../results/runs 7 11 23
python3 ../scripts/make_report.py ../results/runs ../results
```

## What is modelled vs. measured

The ROS graph, interfaces, behaviour tree, planning, allocation, logistics and market logic are real code that would run on the robots and hub.

The rest are calibrated stand-ins to be replaced with pilot data:
- crop physiology
- perception network accuracy (`core/perception.py`)
- grasp success, cycle-time constants and bruising
- prices and costs (`core/market.py`, `core/economics.py`)

Each perception node keeps its topic contract, so a TensorRT model drops in by replacing `infer()`.

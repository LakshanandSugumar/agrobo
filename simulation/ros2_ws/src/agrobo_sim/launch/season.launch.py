"""Full-season, five-phase Agrobo simulation (headless, kinematic motion backend).

ros2 launch agrobo_sim season.launch.py twin_guided:=true run_name:=agrobo season_days:=125
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration as LC
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    args = [DeclareLaunchArgument(n, default_value=v) for n, v in [
        ("twin_guided", "true"), ("run_name", "agrobo"), ("season_days", "125"), ("output_dir", "results"),
        ("seed", "7"), ("p_outage", "0.12"), ("rows", "10"), ("plants_per_row", "48")]]
    b = lambda n: ParameterValue(LC(n), value_type=bool)
    i = lambda n: ParameterValue(LC(n), value_type=int)
    N = lambda exe, name=None, **p: Node(package="agrobo_sim", executable=exe, name=name or exe, output="log",
                                         parameters=[p] if p else [])
    kpi = Node(package="agrobo_sim", executable="kpi_recorder", output="screen",
               parameters=[{"output_dir": LC("output_dir"), "run_name": LC("run_name")}])
    nodes = [
        N("field_world", seed=i("seed"), rows=i("rows"), plants_per_row=i("plants_per_row")),
        N("strategy_engine"),
        N("fleet_path_planner"),
        N("cloud_sync", p_outage=ParameterValue(LC("p_outage"), value_type=float)),
        N("prep_ugv"),
        N("scout_uav"),
        N("perception_weed_classifier"),
        N("perception_ripeness_estimator"),
        N("perception_crop_health"),
        N("ugv_platform", "ugv_alpha", robot_id="ugv_alpha", dock_y=0.0, seed=5),
        N("ugv_platform", "ugv_beta", robot_id="ugv_beta", dock_y=15.0, seed=6),
        N("hauler_ugv"),
        N("hub_grading_station"),
        N("market_engine"),
        Node(package="agrobo_sim", executable="mission_orchestrator", output="screen",
             parameters=[{"twin_guided": b("twin_guided"), "season_days": i("season_days"),
                          "run_name": LC("run_name"), "rows": i("rows"), "plants_per_row": i("plants_per_row")}]),
        kpi,
    ]
    stop = RegisterEventHandler(OnProcessExit(target_action=kpi, on_exit=[EmitEvent(event=Shutdown())]))
    return LaunchDescription(args + nodes + [stop])

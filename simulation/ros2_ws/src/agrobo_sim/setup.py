from glob import glob

from setuptools import find_packages, setup

pkg = "agrobo_sim"
nodes = {
    "field_world": "field_world:main",
    "strategy_engine": "strategy_engine:main",
    "fleet_path_planner": "fleet_path_planner:main",
    "prep_ugv": "prep_ugv:main",
    "scout_uav": "scout_uav:main",
    "perception_weed_classifier": "perception_nodes:main_weeds",
    "perception_ripeness_estimator": "perception_nodes:main_ripeness",
    "perception_crop_health": "perception_nodes:main_health",
    "ugv_platform": "ugv_platform:main",
    "hauler_ugv": "hauler_ugv:main",
    "hub_grading_station": "hub_grading_station:main",
    "market_engine": "market_engine:main",
    "cloud_sync": "cloud_sync:main",
    "mission_orchestrator": "mission_orchestrator:main",
    "kpi_recorder": "kpi_recorder:main",
    "gz_row_follower": "gz_row_follower:main",
}
setup(
    name=pkg,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{pkg}"]),
        (f"share/{pkg}", ["package.xml"]),
        (f"share/{pkg}/launch", glob("launch/*.py")),
        (f"share/{pkg}/worlds", glob("worlds/*")),
        (f"share/{pkg}/config", glob("config/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    entry_points={"console_scripts": [f"{k} = {pkg}.{v}" for k, v in nodes.items()]},
)

std_msgs/Header header
string robot_id
string robot_type      # uav_scout, ugv_weeder, ugv_doser, ugv_picker, ugv_hauler, ugv_prep
string task            # idle, scouting, weeding, dosing, harvesting, hauling, prep, charging
float64 x
float64 y
float64 battery_soc
float64 odometer_m
float64 energy_kwh
bool link_up           # mesh / LTE connectivity to the farm hub

# What a camera pass physically "sees" (ground truth inside the FOV, before perception noise).
# Perception nodes turn this into DetectionArray with model-calibrated noise.
std_msgs/Header header
string robot_id
string sensor            # rgb_multispectral_uav | rgb_d_ugv
float64 altitude_m
PlantState[] plants
Weed[] weeds
Fruit[] fruit
bool end_of_pass

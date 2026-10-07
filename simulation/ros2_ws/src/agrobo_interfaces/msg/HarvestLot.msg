string lot_id
string picked_by
uint32 day_harvested
uint32 fruit_count
float64 mass_kg
float64 mean_ripeness
float64 bruise_rate
float64 first_pick_hour   # sim hour-of-day of the first fruit in the bin
float64 delivered_hour    # sim hour-of-day the lot reached the hub cold room
float64 pick_to_cool_h
float64 shelf_life_d
# per-fruit ground truth that travels with the bin (consumed by the hub grader)
float64[] ripeness
float64[] mass_g
bool[] bruised
# filled by the hub
string[] grade
float64 kg_grade_a
float64 kg_grade_b
float64 kg_grade_c
float64 kg_rejected
bool graded
bool packed

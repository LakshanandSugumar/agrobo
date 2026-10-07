# Edge-perception output; class_name in {weed, crop, fruit, chlorosis}
uint32 target_id      # id of matched ground-truth entity, 0 if false positive
string class_name
float64 confidence
float64 x
float64 y
float64 value         # class-specific: ripeness for fruit, size_cm for weed, stress for chlorosis

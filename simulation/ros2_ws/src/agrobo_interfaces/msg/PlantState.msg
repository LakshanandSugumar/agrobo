# Ground-truth (or twin-estimated) state of one tomato plant.
uint32 plant_id
uint16 row
uint16 col
float64 x
float64 y
uint8 STAGE_EMPTY=0
uint8 STAGE_SEEDLING=1
uint8 STAGE_VEGETATIVE=2
uint8 STAGE_FLOWERING=3
uint8 STAGE_FRUITING=4
uint8 STAGE_SENESCENT=5
uint8 stage
float64 gdd_accum          # growing degree days since transplant
float64 biomass_g
float64 nitrogen_stress    # 0 = none, 1 = severe
float64 water_stress       # 0 = none, 1 = severe
float64 weed_competition   # 0..1
uint16 fruit_green
uint16 fruit_ripe          # ripeness in [0.75, 1.0)
uint16 fruit_overripe      # ripeness >= 1.0 (lost value)
bool alive

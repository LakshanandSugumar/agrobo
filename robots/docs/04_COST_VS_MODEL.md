# Real BOM vs the prototype's modelled fleet capex ($77k/ha)

The prototype simulation priced the fleet at **$76.7k/ha**: 1.23 modular UGVs/ha × $55k ("chassis + 3 implements + 2 arms"), plus shared UAV, hauler, hub and prep UGV. This file replaces those placeholder unit costs with the real BOM (`bom/Agrobo_BOM.xlsx`) and recomputes. Run `python calc/fleet_capex.py`.

## Unit costs from the BOM

| Unit | Pilot (1-5 units) | 100 units (est.) |
|---|---:|---:|
| AB-1 base platform | $24.5k | $17.8k |
| HM-1 harvester implement | $21.2k | $16.8k |
| EE-1 end-effector (×2) | $2.6k | $1.7k |
| **Harvester robot (base + HM-1 + 2 EE)** | **$48.3k** (+$3.6k assembly and test) | **$36.4k** (+$1.5k) |
| LW-1 laser weeder (2 heads) | $30.7k | |
| LW-1M mechanical aisle cultivator | $4.0k | |
| SP-1 spot sprayer | $5.4k | |
| HL-1 hauler | $29.3k | |
| SU-1 UAV | $11.0k | |
| DK-1 dock (per 2 UGVs) | $7.6k | |

The two FR5 arms ($14k) and the Jetson ($3.5k, after NVIDIA's July 2026 price rise of up to 101 %) are the largest single lines.

## Fleet capex per hectare

Implement pool assumption: 0.5 weeders and 0.33 sprayers per UGV (they are only needed in the vegetative weeks and swap at the dock), plus 1 dock per 2 UGVs. Prep is contracted, so it has no capex.

| Scenario | UGV/ha | $/UGV incl. share of implements + dock | **Total $/ha** | vs model |
|---|---:|---:|---:|---:|
| Prototype model | 1.23 | 55,000 | **76,710** | 0 % |
| Real BOM, pilot prices, sim cycle time, mechanical weeder | 1.24 | 59,524 | **81,553** | +6 % |
| Real BOM, pilot prices, sim cycle time, laser weeder | 1.24 | 72,874 | **98,158** | +28 % |
| Real BOM, 100-unit prices, sim cycle time, mechanical weeder | 1.24 | 43,580 | **60,781** | −21 % |
| Real BOM, 100-unit prices, design-target cycle time (5.3 s), mechanical weeder | 0.82 | 43,580 | **42,486** | −45 % |

Full breakdown by asset: `calc/fleet_capex.md`.

## What this means

1. **The model's $55k per UGV was about right for a pilot build if we weed mechanically.** Real pilot cost lands 6 % above the model.
2. **A laser on every robot breaks the budget (+28 %).** Florida plastic mulch confines weeds to the aisles and planting holes, so a $4k cultivator does most of the job. Lasers stay as a premium module for nutsedge and planting holes.
3. **Volume brings it 21 % under the model.** The big levers are the arms (a purpose-built 4-5 DoF arm could be ~$4k vs $7k) and the compute.
4. **Pick speed is worth more than any part price.** UGV count per hectare scales with seconds per fruit. Hitting the 9 s/arm bench target (5.3 s/fruit per robot) instead of the sim's 8.0 s cuts fleet capex by a further third. That is why the training thread and the EE design matter most.
5. Duty cycle with dock charging is 17.8 h/day vs the modelled 18 h/day, so dropping battery hot-swap costs about 1 % more robots. That is worth it for the simpler mechanics.

All prices were checked on 2026-10-21. Lines marked "quote" are public list prices with the URL in the BOM; lines marked "est" are engineering estimates and need supplier quotes before ordering.

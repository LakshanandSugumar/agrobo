# Agrobo: Full-Stack Architecture & ROS 2 Simulation Blueprint

First crop: open-field, fresh-market tomato. Simulator: ROS 2 Jazzy + Gazebo Harmonic (gz-sim 8). Measured results are in [`../results/REPORT.md`](../results/REPORT.md).

---

## 1. Full-Stack Architecture Matrix

### Phase 1: Sourcing & Strategy

| Layer | Specification |
|---|---|
| **Hardware / Robotics** | Survey UAV (RTK multispectral, 5-band + RGB, 120 m AGL orthomosaics). Soil-probe UGV with a hydraulic core sampler (0-60 cm), an in-situ VIS-NIR spectrometer and EC/pH probes, sampling on a 30 m stratified grid. RTK base station (±1.5 cm). |
| **Edge AI / Models** | Pedotransfer regressors (VIS-NIR spectra to N, OM, pH, CEC; PLSR plus a 1D-CNN ensemble). Gaussian-process kriging for soil maps with per-cell variance. Slope and drainage from the DEM (UAV photogrammetry). |
| **Cloud / SaaS** | GIS ingest of SSURGO/SoilGrids, USGS 3DEP, NOAA frost-free days, county parcels and land prices. FAO-style fuzzy land-suitability scoring (weighted geometric mean, where any zero factor kills a parcel). Crop matrix: demand × farm-gate margin × **automation fit**. 5-year NPV / IRR per parcel-crop pair. Output: a parcel ranking API and investment memo. *Sim: `/strategy_engine`, `core/strategy.py`.* |

### Phase 2: Infrastructure & Prep

| Layer | Specification |
|---|---|
| **Hardware / Robotics** | Heavy prep UGV (≈40 kWh, electric, 3-pt hitch with ISOBUS). Implements: flail mulcher (clearing), rotary tiller / bed shaper, drip-tape layer with plastic-mulch applicator. RTK-GNSS plus dual-antenna heading. 3D LiDAR (Ouster OS1-64) for obstacle and stump detection. |
| **Edge AI / Models** | LiDAR obstacle segmentation (PointPillars) for stumps, rocks and debris. Traversability costmap (slope, roughness, soil moisture). Implement-load anomaly detection (draft-force time series, isolation forest). |
| **Cloud / SaaS** | Field-layout generator (bed and row geometry, headlands, drip hydraulic zoning). Coverage planner API (boustrophedon with turn-radius-aware headland turns). Digital as-built map: every plant site is geo-tagged at survey time and becomes the primary key of the Field Ledger. *Sim: `/prep_ugv` (`PrepField`, `Transplant`), `/fleet_path_planner`.* |

### Phase 3: Cultivation & Maintenance

| Layer | Specification |
|---|---|
| **Hardware / Robotics** | Scout UAV (8 m AGL, RGB plus 5-band MS, GSD ≈4 mm, RTK). **Modular field UGV** (12 kWh swappable pack, auto-coupler) with three implements: (a) laser weeder, 2 × 150 W CO₂ galvo heads with a close-range RGB-D verify camera; (b) micro-doser, per-plant root-zone liquid N injection; (c) picker arm (see Phase 4). Transplanter on the prep UGV. |
| **Edge AI / Models** | **YOLO11n-seg** crop/weed instance segmentation (TensorRT INT8, Jetson Orin NX, ~25 ms per 1280² tile). Species head for resistant weeds such as *Amaranthus palmeri*. NDRE/red-edge regressor for N stress (chlorosis), calibrated against leaf SPAD. Close-range verify classifier on the weeder that vetoes false targets before firing. Ripeness regressor (see Phase 4) runs on every scout pass. |
| **Cloud / SaaS** | **Field Ledger** (plant-level digital twin; see §3). Per-target work orders: weed geo-targets, per-plant N doses. Scouting cadence scheduler. Agronomic dashboards (weed pressure, stress heatmaps). *Sim: `/scout_uav`, `/perception_weed_classifier`, `/perception_crop_health`, `/ugv_alpha` and `/ugv_beta` (`WeedZone`, `DoseNutrients`).* |

### Phase 4: Robotic Harvesting

| Layer | Specification |
|---|---|
| **Hardware / Robotics** | Picker implement on the modular UGV: 2 × 6-DoF arms (UR5e-class, IP54), soft 3-finger grippers with a tactile skin (force-controlled at 3.6 ± 0.55 N), a peduncle-snap wrist and a vacuum assist. Eye-in-hand stereo (global shutter) plus a mast stereo pair. Bin handling. **Hauler UGV** (150 kg payload, 1.5 m/s) shuttles bins on the headland track to the hub. |
| **Edge AI / Models** | Fruit instance segmentation (Mask R-CNN-lite / YOLO11-seg) with a **ripeness regression head** (USDA colour stages mapped to a 0-1 ripeness value, σ 0.03 close-range). 6D fruit and peduncle pose estimation. Grasp policy: an analytic approach planner with an **RL residual** (SAC trained in Isaac Lab on a deformable-fruit model) for the detach motion. Occlusion-aware next-best-view for the arm camera. |
| **Cloud / SaaS** | Harvest planner fed by Field Ledger ripeness *forecasts* (which fruit will be ripe on which day, on which plant, at what height). Robot-to-row allocation. Bin traceability (lot ID per bin, linked to its plant IDs). *Sim: `/ugv_*` `HarvestRows` (component `CropPickerManipulator`), `/hauler_ugv` (`HaulToHub`).* |

### Phase 5: Post-Harvest & Market

| Layer | Specification |
|---|---|
| **Hardware / Robotics** | Hub: singulating conveyor, **line-scan hyperspectral camera** (400-1000 nm, with the 970 nm water band for sub-surface bruise detection), delta-robot packer into 5 kg flats, forced-air pre-cooler, 10-12 °C cold room with an IoT temperature/RH logger per pallet. |
| **Edge AI / Models** | PLS / 1D-CNN on spectra for lycopene and chlorophyll (ripeness), firmness and bruise detection, giving grades A, B, C and reject. Shelf-life model: base life minus a field-heat penalty from pick-to-cool time. |
| **Cloud / SaaS** | **B2B algorithmic selling engine**: retail forward contracts sized from the Field Ledger D+3 yield forecast (hedged at 80 %), food-service spot, wholesale and processor channels. FEFO allocation, a price-dip hold rule and contract-shortfall penalty accounting. Buyer portal, EDI/ASN, lot-level traceability (FSMA 204). *Sim: `/hub_grading_station` (`ProcessLot`), `/market_engine` (`SellInventory`).* |

---

## 2. ROS 2 Simulation Blueprint (November Milestone)

### 2.1 Simulation environment: multi-fidelity

One physics engine cannot simulate a 125-day season at plant level. We run two fidelity tiers behind the same ROS 2 interfaces:

| Tier | Engine | What it proves | Wall time |
|---|---|---|---|
| **Season tier** (default) | ROS 2 nodes with a numpy agronomy model and kinematic motion/energy | All 5 phases end to end: agronomy, perception error, task logic, logistics, market, KPIs | ~1-2 min per season |
| **Physics tier** | **Gazebo Harmonic** (`gz sim`, DART) via `ros_gz_bridge` | Wheel-terrain contact, diff-drive control, RTK/IMU noise, row keeping (cross-track error) | real time or faster, headless |
| **Manipulation tier** (next) | Isaac Sim / Isaac Lab | Deformable-fruit grasping, RL residual policy training | GPU cluster |

The kinematic motion model in the season tier is calibrated against the physics tier (speed, lane-change cost, cross-track error). The same action servers can be pointed at Gazebo `cmd_vel`.

**Terrain.** `worlds/generate_farm_world.py` builds a collision surface from 1.5 m tilted tiles (±1.2 % slope noise, μ = 0.8), so wheel slip and odometry drift appear without a rendering-backed heightmap in headless CI. A WGS84 `spherical_coordinates` origin at the chosen parcel feeds the NavSat sensor.

**Crop growth states.** `core/agronomy.py` is the ground-truth model:
- **Thermal time.** GDD has base 10 °C and a 30 °C cap. Stages are seedling (0), vegetative (150), flowering (450), fruiting (620) and senescent (1750 GDD).
- **Vigour.** A multiplicative stress product: `(1 − 0.65·N_stress)(1 − 0.5·water_stress)(1 − 0.55·weed_competition)(1 − damage)`. It scales development, biomass and fruit set.
- **Fruit.** Each fruit has its own ripening rate per GDD (~45 days set to ripe). Ripeness ≥ 0.75 is harvestable, ≥ 1.0 is overripe, and ≥ 1.25 drops as a field loss. Mass depends on vigour at set, and 35 % of fruit are canopy-occluded.
- **Soil.** N varies spatially (Gaussian-blob field, CV 30 %). It depletes through stage-dependent uptake and is partly replaced by OM mineralisation. Soil moisture is drip-controlled.
- **Weeds.** Poisson emergence, suppressed by tillage and canopy closure. Growth is species-specific, and competition comes from weeds within 0.5 m. Weeds above 30 cm can set seed.
- **Rendering.** The Gazebo generator renders any growth stage (plant height, canopy and fruit colour) from a `/field/state` snapshot.

**Sensor noise.** Every perception network is replaced by a calibrated error model (`core/perception.py`) with the same topic contract. To swap in a real network, replace `infer()`.

| Model | Noise model |
|---|---|
| Weed detector | Recall is a sigmoid of weed size (50 % at 1.2 cm), max 0.96, minus 35 % under full canopy. False positives: 1.2 % of crop plants per pass. Localisation σ 2.5 cm. |
| Ripeness | UAV visibility 0.45 (0.15 if occluded), σ 0.07. UGV visibility 0.92 (0.70 if occluded), σ 0.03. |
| Chlorosis (NDRE) | σ 0.07, detection threshold 0.22. |
| Weeder verification | 98.5 % recall on true weeds. 92 % of false targets rejected; the remaining 8 % misfire, risking crop damage. |
| GNSS / IMU (Gazebo) | 1.5 cm horizontal, 3 cm vertical; gyro z σ 0.002 rad/s. |

### 2.2 ROS node architecture

| Node | Phase | Role |
|---|---|---|
| `/field_world` | all | Ground-truth farm: growth, weeds, soil, weather. The only node that mutates the world. |
| `/strategy_engine` | 1 | GIS suitability, crop matrix, NPV; publishes the chosen parcel, which configures soil. |
| `/fleet_path_planner` | 2-4 | Boustrophedon coverage and lane-constrained TSP (NN + 2-opt) for target tours. |
| `/prep_ugv` | 2-3 | Clear, RTK layout, till, lay drip; precision transplanting. |
| `/scout_uav` | 3-4 | Lawnmower survey; publishes `SensorFrame` per strip. |
| `/perception_weed_classifier` | 3 | Frames to weed detections. |
| `/perception_crop_health` | 3 | Frames to N-stress (chlorosis) detections. |
| `/perception_ripeness_estimator` | 4 | Frames to fruit detections with a plant anchor and ripeness. |
| `/ugv_alpha`, `/ugv_beta` | 3-4 | Modular UGVs with an implement state machine (laser_weeder, micro_doser, picker_arm). Each hosts the `CropPickerManipulator` component. |
| `/hauler_ugv` | 4 | Bin logistics from field to hub; stamps delivery time. |
| `/hub_grading_station` | 5 | Hyperspectral grading, cold-chain packing, shelf-life. |
| `/market_engine` | 5 | Contracts, spot, wholesale and processor allocation; trades. |
| `/cloud_sync` | all | Rural LTE outage model and store-and-forward replication of the event log. |
| `/mission_orchestrator` | all | Season behaviour tree plus the **Field Ledger** twin; work-order auction. |
| `/kpi_recorder` | all | Event bus to `kpis.json`. |
| `/gz_row_follower` | physics tier | Pure pursuit on Gazebo odometry; cross-track report. |

### 2.3 Topics, services, actions (`agrobo_interfaces`)

**Topics**

| Topic | Type | QoS | Producer to consumer |
|---|---|---|---|
| `/field/state` | `FieldState` (PlantState[], Weed[]) | latched | field_world to orchestrator, viz |
| `/scout_uav/frames` | `SensorFrame` | reliable | scout_uav to perception nodes |
| `/perception/weeds`, `/perception/fruit`, `/perception/chlorosis` | `DetectionArray` | reliable; `frame_id="eop"` closes a pass | perception nodes to orchestrator (Field Ledger) |
| `/harvest/lots` | `HarvestLot` | reliable | ugv picker to hauler |
| `/harvest/lot_delivered` | `HarvestLot` | reliable | hauler to hub |
| `/hub/inventory` | `HarvestLot` (graded) | reliable | hub to market |
| `/farm_twin/yield_forecast` | `Float64MultiArray [day, kg_A]` | reliable | orchestrator to market (forward contracts) |
| `/market/trades` | `MarketTrade` | reliable | market to SaaS |
| `/fleet/status` | `RobotStatus` | best effort, 1 Hz | all robots to fleet telemetry |
| `/cloud/link_up` | `std_msgs/Bool` | latched | cloud_sync to robots, market, orchestrator |
| `/agrobo/events` | `std_msgs/String` (JSON) | latched, depth 5000 | all nodes to kpi_recorder, cloud_sync |
| `/mission_orchestrator/bt_snapshot` | `std_msgs/String` | 0.5 Hz | live BT status tree |

**Services**

| Service | Type | Purpose |
|---|---|---|
| `/strategy/evaluate_parcels` | `EvaluateParcels` | Phase 1 decision |
| `/field/get_state` | `GetFieldState` | Robot-side "what the sensors physically see" (ground truth) |
| `/field/interact` | `FieldInteract` | Every physical effect: TILL, CLEAR, DEPLOY_IRRIGATION, TRANSPLANT, KILL_WEED, LASER_MISFIRE, DOSE_NITROGEN, PICK_FRUIT |
| `/field/advance_day` | `AdvanceDay` | Sim clock (day step) |
| `/fleet_path_planner/plan` | `PlanCoverage` | Coverage and TSP |

**Actions**

| Action | Server | Goal, result |
|---|---|---|
| `PrepField` | `/prep_ugv/prep_field` | Rows and spacing → area, distance, kWh, hours |
| `Transplant` | `/prep_ugv/transplant` | Plant ids → planted, hours |
| `ScoutField` | `/scout_uav/scout_field` | Altitude → frames, objects in FOV |
| `WeedZone` | `/<ugv>/weed_zone` | Geo-targets → killed, missed, false targets rejected, crop damage, cleared targets |
| `DoseNutrients` | `/<ugv>/dose_nutrients` | Plant ids and g N → dosed |
| `HarvestRows` | `/<ugv>/harvest_rows` | Predicted fruit ids, plants, `twin_guided` → picked ids, bruised, kg, s/fruit, lot |
| `HaulToHub` | `/hauler_ugv/haul_to_hub` | Lot ids → trips, delivered hours |
| `ProcessLot` | `/hub/process_lot` | Lot → grade mix, shelf life |
| `SellInventory` | `/market/sell_inventory` | Day → trades, revenue, spoilage |

### 2.4 Orchestration: behaviour tree (py_trees, ticked at 100 Hz on the edge hub)

```
agrobo_season [Sequence*]
├─ phase1_sourcing [?]  sourced? | evaluate_parcels (srv)
├─ phase2_prep [?]      prepped? | (wait parcel_applied → prep_field (action))
├─ phase3_establish [?] planted? | transplant (action)
├─ season_loop [Repeat until day == season_days]
│  └─ daily_cycle [Sequence*]
│     ├─ start_day
│     ├─ scouting [?]        not(scout_due?) | (scout_field → perception_settled)
│     ├─ plan_work           Field Ledger → work orders → swap-minimising auction
│     ├─ field_ops [Parallel: SuccessOnAll]
│     │   ├─ lane_ugv_alpha   per-robot task queue
│     │   └─ lane_ugv_beta    per-robot task queue
│     ├─ logistics [?]       not(lots_today?) | (haul_to_hub → queue_lots → hub_process_lots)
│     ├─ cloud_gate [?]      (link_up? → publish_yield_forecast) | edge_only_mode
│     ├─ sell_inventory (action)
│     └─ advance_day (srv)   → ledger.on_day(GDD)
└─ season_complete
```
`*` marks a composite with memory. `[?]` is a Selector (fallback).

**How a robot moves from scouting to weeding to harvesting.** There are no hard-coded modes. Each day, `plan_work` turns the Field Ledger into prioritised work orders:
- **Harvest** has the highest priority because fruit is perishable. It triggers when ≥ 25 fruit are forecast ripe, or when it has been 3 days since the last harvest. Large harvests split by row band across both UGVs.
- **Weed** triggers at ≥ 12 tracks, or when the oldest track is 4 days old.
- **Dose** triggers when the chlorosis estimate is ≥ 0.22, at most once per plant every 10 days.

A swap-minimising auction (cost = queued tasks + 0.6 if an implement swap is needed) assigns orders to UGVs. Each `lane_<ugv>` runs that robot's queue as a state machine: IDLE, then TOOL_SWAP (dock, 6 min), then HARVEST, WEED or DOSE, and back to IDLE. The UAV is always the scout. Battery state is handled inside each robot: at SoC < 15 % it returns to the dock for a hot swap and resumes.

**Connectivity.** The tree and the Field Ledger run on the edge hub, so field operations never depend on the cloud. During an LTE outage, `cloud_gate` falls back to `edge_only_mode`: forward contracts pause, contracted deliveries still execute, and events are buffered and replicated when the link returns.

---

## 3. The "YC Killer Hook" & Tech Moat

### The hardest problem: harvesting at commercial throughput

Delicate fruit picking is the open problem of agricultural robotics. Search (finding the fruit under occlusion), ripeness judgment, and gentle detachment together set cycle time. Published research pickers run at 10-25 s/fruit against ~3-4 s for a human. Speeding up the arm alone has hit diminishing returns.

### The moat: "Predict-then-Pick" on a plant-level Field Ledger

The idea is to move the expensive part of picking (search, ripeness inference, pose estimation) **off the picker and into time it would otherwise waste**:

1. **The Field Ledger is a persistent, per-plant, per-fruit twin.** The primary key is the RTK-surveyed plant site from Phase 2. Every UAV pass adds fruit tracks with anchor plant, height and ripeness. Ripeness is **forecast forward in thermal time**: a per-fruit rate is learned from repeat observations and blended Kalman-style with each new measurement.
2. **Harvest orders are fruit-level predictions.** The picker visits *only* plants with predicted-ripe fruit, arrives with a pose prior, and spends ~1.2 s confirming instead of a ~7 s multi-view search plus ~2.5 s per-fruit localisation. While there, it still picks any other ripe fruit it sees.
3. **The same forecast sells the crop before it is picked.** The D+3 Grade-A forecast is hedged into retail forward contracts at a premium over spot, with shortfall penalties as the honesty check on forecast quality.
4. **The same twin replaces zone treatments with per-target ones.** Weeds become geo-targets for a laser (zero herbicide). Nitrogen becomes per-plant micro-doses driven by NDRE.
5. **It runs at the edge.** The twin and the behaviour tree live on the hub, the cloud is a replicated append-only log, and a rural LTE outage degrades contracting, not field operations.

**Why it is defensible.** The data asset compounds. Every season adds labelled growth trajectories (plant × GDD × stress → fruit-level ripening), which improve forecasts. Better forecasts mean fewer plant visits, faster picks, larger hedges and better prices. A competitor with a better arm but no longitudinal per-plant data cannot replicate the forecast, and a competitor with a twin but no own-fleet actuation cannot close the loop. The simulation includes an ablation (`twin_guided:=false`) with the same robots and the same field, so the value of the twin is measured, not asserted.

### Three KPIs the November simulation must prove

| # | KPI | Definition (as computed by `/kpi_recorder`) | Commercial meaning |
|---|---|---|---|
| 1 | **Chemical elimination at parity weed control** | Herbicide L/ha vs a 5.5 L/ha baseline. Weed-control efficacy = killed / (killed + alive at season end). Crop-damage rate. N kg/ha vs a 220 kg/ha uniform baseline. | Eliminates input cost and regulatory exposure (resistant weeds, residue MRLs); sells into organic and residue-free premiums. |
| 2 | **Harvest capture & cycle time** | Capture rate = harvested / (harvested + field drops + ripe left on plants). Seconds per fruit. Grade-A share. Bruise rate. Pick-to-cool hours. Twin vs no-twin delta. | Shows the picker is economic: throughput per robot-hour and quality decide fleet size, which decides capex per hectare. |
| 3 | **Unit economics (OpEx $/kg) & revenue per kg** | Agrobo OpEx (energy, maintenance, supervision, amortised fleet, inputs) vs conventional (labour, machinery, inputs), per kg harvested. Labour hours eliminated. Algorithmic revenue vs ungraded wholesale baseline. | The investable number: cost per kg below the conventional farm, with revenue per kg above it. |

Supporting autonomy metrics: human interventions, robot-hours, kWh, battery swaps, implement swaps, cloud-outage days survived and offline events buffered.

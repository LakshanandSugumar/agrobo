# Build and test plan: first harvester (AB-1 + HM-1 + 2× EE-1)

## 1. Procurement (order in this sequence; long lead first)

| Lead time (typical, confirm) | Items |
|---|---|
| 6-10 weeks | FAIRINO FR5 × 2 (confirm DC MINI controller + IP65 option), LFP cells (EVE LF105 × 32, ship by sea or air with UN38.3 docs), OZO hub motors × 4 (from France) |
| 2-4 weeks | Jetson AGX Orin dev kit, ZED X × 2 + ZED Link Duo, D405 × 2, Livox Mid-360, ArduSimple heading kit, MicroStrain CV7, Orion BMS, Pilz PNOZ s4, wireless E-stop, safety edges, TEC cooler |
| 1 week | 80/20 profile cut to length (`cad/cut_list_1515.csv`), laser-cut plates (SendCutSend from `cad/dxf/`), CNC parts (Xometry from `cad/step/`), MJF EE housings, DIN components, harness materials |
| In-house | TPU fingers (FDM, 95A, 100 % infill on the contact face), tote liners |

All quantities and part numbers: `bom/Agrobo_BOM.xlsx`. "est" prices need quotes before ordering.

## 2. Assembly sequence (two technicians, about 8 working days)

1. **Frame (day 1):** bolt the deck frame square (diagonals within 2 mm), then the legs, gussets and axle plates. Fit the deck plate last. Torque M8 to 20 N·m with threadlocker.
2. **Drive (day 2):** mount the hub motors in the shaft clamps (check flats and torque arms), fit tyres at 10 psi, then the VESC box. Bench-spin each motor on a 48 V lab supply before connecting the pack. Run VESC motor detection and set the battery current limit to 35 A.
3. **Battery (days 2-3):** build the 16S2P pack in a compression fixture (300 kgf), fit busbars, sense leads and thermistors, set the BMS. Capacity-test one full cycle on the bench before it goes in the keel.
4. **Power and safety wiring (days 3-4):** follow E-01, E-02 and `electrical/harness.csv`. **Commission the safety chain before any motor moves:** each E-stop, the wireless stop and both bumpers must drop K1 and K2. Record the stop times.
5. **Compute and sensors (day 5):** mount the enclosure, Jetson, switch, router, Teensy, lidar, GNSS antennas (0.60 m baseline, measure it), IMU at the enclosure centre. Survey the sensor offsets against `urdf/agrobo_harvester.urdf` and update `params.py` if they differ.
6. **Mast and arms (day 6):** mast posts and arm plates. Check the FR5 base bolt pattern against the vendor drawing **before** machining HM1-101. Fit the arms, dress packs and covers. Teach the zero pose and check it against the URDF zero (arm stretched toward the rear).
7. **End-effectors (day 7):** press the bearings, fit the servo and cam ring, O-rings and fingers, mount the D405, connect the vacuum. Bench-test the grip force with a load cell and set the servo current limit for 3.6 N.
8. **Tote deck and bumpers (day 8):** roller zones, totes, beacon, lights.

## 3. Bring-up and acceptance tests

| # | Test | Pass criterion |
|---|---|---|
| T1 | Safety chain | Every input drops K1 within 50 ms and K2 within 1.1 s; no restart without manual reset |
| T2 | Insulation | > 1 MΩ from the pack to chassis at 500 V DC |
| T3 | Drive, flat yard | 1.5 m/s top speed; stops from 1.5 m/s in < 1.0 m; zero-radius turn on dry sand |
| T4 | Traction, wet sand furrow (hose down a test aisle) | Climbs out of a 10 cm rut from standstill; no wheel above 70 °C after 1 h |
| T5 | RTK row following | Cross-track RMS < 3 cm at 0.5 m/s over 100 m (prototype sim: 2.7 cm) |
| T6 | Stability tilt table / bed shoulder | No wheel lift at 20° roll with one arm fully out holding 1 kg |
| T7 | Endurance | 8 h of picking motions + crawl drive on one charge; enclosure < 50 °C internal at 35 °C ambient in sun |
| T8 | Charge | Docks on its own 20/20 times; 15-85 % charge in < 2.5 h |
| T9 | Pick bench (potted plants / clamped trusses) | ≥ 90 % detach success, < 3 % bruise or puncture, ≤ 12 s/fruit/arm in rev A, trending to 9 s |
| T10 | Rain | 30 min at 10 mm/h simulated rain: no ingress in the enclosure or EE housing; arms keep working under covers |
| T11 | Field pilot (one Florida grower, 0.5 ha) | 2 weeks of harvest with interventions < 1 per robot-hour by week 2; Field Ledger capture-rate KPI logged |

## 4. Timeline to a field pilot

| Weeks | Milestone |
|---|---|
| 0-2 | Place long-lead orders; finalise rev A drawings from vendor STEP files (FR5, OZO, ZED X) |
| 2-8 | Fabrication; EE prototypes printed and bench-tested on store-bought mature-green fruit |
| 8-10 | Assembly, T1-T8 |
| 10-12 | T9-T10 on potted plants; policy trained in sim (training thread) and transferred |
| 12-16 | Field pilot T11 on a partner farm in SW Florida (fall season runs Oct-Dec, spring Mar-Jun) |

Budget for the first robot including spares and test fixtures: about **$60k** (BOM $48.3k + spare fingers, cups and one spare EE + tools, fixtures and the test aisle + 20 % contingency on "est" lines).

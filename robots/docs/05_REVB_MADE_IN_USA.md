# Rev B: US-sourced harvester (2026-11-01)

Laksh, 2026-11-01: "focus in made in us only whatever the price it is". Rev B swaps every rev A.1 part that has a US-made or US-assembled option. Files:
- `bom/build_bom_revB.py` (run it to regenerate)
- `bom/Agrobo_BOM_revB.xlsx` (colour-coded by origin, with a Summary sheet)
- `bom/revB_us_sourced.csv` (all 71 lines)
- `bom/revB_no_us_source.csv`
- `bom/revB_summary.json`

The design values live in `cad/src/params.py`, in the rev B section (`ARM_REVB`, `DRIVE_REVB`, `LIDAR_REVB`, `STEREO_REVB`).

## Headline

| | Rev A.1 (imported) | **Rev B (US-sourced)** |
|---|---:|---:|
| Harvester robot, pilot qty | $48,342 | **$125,395** |
| + assembly and test (US labour) | $3,600 | $4,500 |
| **Per robot, built** | **$51,942** | **$129,895 (+150 %)** |

The two arms account for **$59k of the $77k increase**. Standard Bots Spark is the only 6-axis cobot that is designed and assembled in the US at this size; the FAIRINO FR5 was $7k.

## Origin codes and value shares (rev B, by $)

| Code | Meaning | Share of BOM $ |
|---|---|---:|
| US | Vendor states it is made in the USA | 8.6 % |
| US? | US maker, origin of the unit not confirmed. Get a country-of-origin letter before ordering | 28.3 % |
| US-ASSY | Assembled in the US from imported subparts (Spark arms, Ouster lidar) | 56.6 % |
| NONE | No US-made source today | 6.4 % |

## Main swaps

| Rev A.1 part (origin) | Rev B part | Supplier, location | Ext $ | Lead time |
|---|---|---|---:|---|
| 2 × FAIRINO FR5 (CN) | 2 × Standard Bots Spark, 7 kg / 950 mm | Standard Bots, Glen Cove NY | 59,000 | 2-6 wk |
| (none, FR5 took 48 V DC) | 2 × 48 V to 120 VAC 2 kW inverter for the Spark controllers | Magnum Energy, Everett WA | 2,800 | 2-4 wk |
| Livox Mid-360 (CN) | Ouster OS0-64. Specify US-built units, because Ouster also builds in Thailand | Ouster, San Francisco | 12,000 | 4-8 wk |
| 2 × ZED X (FR) | 2 × Carnegie Robotics MultiSense S27, GbE | Carnegie Robotics, Pittsburgh PA | 3,990 | quote |
| 4 × OZO hub motor (FR) | 4 × inboard BLDC + Winsmith 12:1 right-angle reducer | Motenergy, Hartford WI; Winsmith, Springville NY | 6,000 | 1-4 wk |
| VESC (CN) | Roboteq dual-channel controllers | Roboteq/Nidec, US | 1,800 | 2-4 wk |
| ArduSimple RTK (ES) | Hemisphere Vector VR1000 | Hemisphere, Tempe AZ | 4,500 | 2-4 wk |
| MicroStrain CV7 | VectorNav VN-100 | VectorNav, Dallas TX | 1,200 | 1 day |
| Pilz PNOZ (DE) | Banner XS26 safety controller | Banner, Minneapolis MN | quote | 1-2 wk |
| Wireless E-stop (EU) | FORT Robotics wireless E-stop | FORT, Philadelphia PA | 2,500 | 4-6 wk |
| Roller zones (EU) | Hytrol MDR roller zones | Hytrol, Jonesboro AR | 3,000 | 4-6 wk |
| DYNAMIXEL XM430 (KR) | Teknic ClearPath NEMA 23 | Teknic, Victor NY | 700 | 1-2 wk |
| Actuonix L16 (CA/CN) | Ultra Motion Digit linear actuator | Ultra Motion, Cutchogue NY | 900 | 2-3 wk |

The profile (80/20, Columbia City IN), plates (SendCutSend, Reno NV), MJF prints, harness, pumps (Gast), valves (Clippard), cups (Anver) and enclosure were already US or are now specified US. The full list with prices, price basis (list/quote/est) and URLs is in the xlsx.

## No US-made source today (6.4 % of $)

| Part | Why there is no US source | Path to US |
|---|---|---|
| LFP cells, 32 × 105 Ah | US LFP cell plants (LGES Lansing, Ford BlueOval Marshall, AESC) sell to automakers and grid, not in small volume | LGES Lansing ESS cells from H2 2027; meanwhile a US-assembled pack (e.g. a US pack builder) gives US-ASSY |
| Jetson AGX Orin + NVMe SSD | NVIDIA modules are built in Asia; no US-made edge AI computer exists at this level | None near term. It is a small share of $ but a visible one |
| 5G router | Digi IX25 is a US company and TAA-compliant, but the unit is not US-made | Accept it |
| D405 eye-in-hand depth, ToF sensor, USB hub and cables | No US-made short-range depth camera | Carnegie Robotics has short-range units, but they are too large for the wrist. Accept it |
| Turf tyres 20x8.00-10 | US makers (Titan, Carlisle) build this size offshore | Ask Titan for a US-made ag tyre in a near size |
| Vacuum switch | No US maker identified yet | Probably solvable with a quote round |

## Mechanical changes rev B forces (not yet in CAD/URDF)

`build.py` and `generate_urdf.py` still model the rev A.1 geometry. These changes need a CAD pass before metal is cut:

1. **Drive.** The hub motor becomes an inboard BLDC with a right-angle reducer, and the wheel mounts on the reducer output shaft. The axle plate (AB1-104) becomes a reducer mount. The reducer envelope is about 0.20 × 0.16 × 0.18 m per wheel and sits inboard; the 0.29 m battery keel still clears. Unsprung mass rises from about 18 kg to about 23.5 kg per corner, and the robot gains about 22 kg in total.
2. **Arm mount.** The Spark needs a new base bolt pattern and flange (HM1-101), and a 21 kg arm instead of 22 kg, so the stability margins hold. **Spark joint ranges and kinematics are not published.** The FR5 DH model stays in the URDF as a placeholder until Standard Bots sends a URDF.
3. **Arm power.** Two inverters (about 6 kg each) go under the deck beside the enclosure. That adds about 50-80 W idle loss, which is about 0.4 h less run time per charge (to be re-checked in `calc/`).
4. **Stereo bar.** The MultiSense S27 has a 27 cm baseline against 12 cm for the ZED X. The mast camera bracket gets wider, which needs a clash check against the light bar.
5. **Lidar.** It needs an 87 mm pedestal for the OS0-64; the mast top plate changes.
6. **EE housing.** The housing grows from Ø90 to Ø110 mm (+0.5 kg) to fit the ClearPath servo. Re-check the wrist payload: 7 kg on the Spark gives more margin than 5 kg on the FR5.
7. **Network.** The cameras are now on GbE, so the switch needs 10+ ports, and the ZED Link Duo capture card is dropped.

## FTC "Made in USA" assessment

The FTC rule (16 CFR Part 323) allows an unqualified "Made in USA" claim only when **all or virtually all** of the product is made in the US. That means:
- final assembly in the US, and
- all significant parts and processing of US origin, with only negligible foreign content.

Imported major parts disqualify the claim even if they are a small share of cost. That includes compute, cells and the arm internals.

**Rev B does not qualify for an unqualified "Made in USA" claim.**
- 6.4 % of its value has no US source.
- 56.6 % is US-assembled from imported subparts. Arm gearboxes and servo drives, and the lidar's lasers and chips, are mostly imported.
- 28.3 % still needs a country-of-origin letter.

What rev B can claim honestly:
- **"Assembled in USA"**, if Agrobo does final assembly in the US. The FTC allows this when the last substantial transformation happens in the US.
- A **qualified claim**, e.g. "Made in USA with US and imported parts", or "Made in USA, 94 % of parts by value from US companies". Only the second form holds if every US? line is confirmed.

What it would take to get to "virtually all":
- US-built cells. LGES Lansing ESS cells (H2 2027) or a US cell partner.
- An in-house arm built from US motors and gearboxes. This was already the v2 cost-down item, and it now does both jobs.
- Accepting that edge AI compute will be imported for the foreseeable future. That alone probably blocks an unqualified claim.

For the YC "Robots Made in America" framing, the defensible line is **"designed and assembled in the USA, with US-made arms, sensors and drivetrain"**.

## Before ordering

1. Get country-of-origin letters for every US? line, and quotes for every "est" price.
2. Get the Spark URDF, base drawing and IP rating from Standard Bots, and ask whether it can take DC input, which would remove the inverters.
3. Confirm that Ouster can ship US-built OS0 units.
4. Do a CAD pass for the 7 mechanical changes above, then re-run `calc/` (mass, stability, energy).
5. Fleet capex. At rev B robot cost, fleet capex is roughly $170k/ha at pilot prices, against $82k for rev A.1. That is a rough figure: the robot price changes, and the other modules are still at rev A sourcing.

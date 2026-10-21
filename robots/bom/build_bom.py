"""Agrobo bill of materials -> bom/*.csv, bom/Agrobo_BOM.xlsx, bom/cost_summary.json

Prices are USD at pilot quantity (1-5 units), checked 2026-10-21 where a source is given ("quote"),
otherwise engineering estimates ("est"). vol = expected multiplier at 100-unit volume.
"""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__))

SRC = {
    "fr5": "https://top3dshop.com/product/fairino-fr5-robotic-arm",
    "orin": "https://www.cnx-software.com/2026/07/22/nvidia-increases-the-price-of-jetson-modules-and-devkits-by-up-to-101/",
    "mid360": "https://www.livoxtech.com/news/mid360_launch",
    "ozo": "https://ozo-electric.com/en/agricultural-construction-wheel-motors/558692-brushless-electric-hub-motor-3000w-130nm-45kmh-48v-to-72v.html",
    "zedx": "https://stereolabs.com/store/products/zed-x-stereo-camera",
}

# (part_no, subsystem, description, manufacturer, model / MPN, qty, unit_usd, basis, vol, notes)
AB1 = [
    ("AB1-101", "Frame", "T-slot profile 1.5 in square, cut to length (see cut list)", "80/20 Inc.", "1515 (or 1515-LITE for cross members)", 1, 980, "est", 0.6, "~21 m total incl. mast; welded 6061 frame at volume"),
    ("AB1-102", "Frame", "Fastener kit: T-nuts, anchors, 90 deg gussets, M8 SS hardware", "80/20 Inc. / McMaster-Carr", "assorted", 1, 650, "est", 0.5, "stainless or zinc-nickel, coastal FL"),
    ("AB1-201", "Frame", "Deck plate 3 mm 5052-H32, laser cut", "SendCutSend", "cad/dxf/AB1-201", 1, 260, "est", 0.5, "DXF provided"),
    ("AB1-202", "Frame", "Axle plate 10 mm 6061-T6, laser cut + shaft clamp slot", "SendCutSend", "cad/dxf/AB1-202", 4, 55, "est", 0.5, "DXF provided"),
    ("AB1-203", "Frame", "Leg gusset plate 10 mm 6061-T6", "SendCutSend", "cad/step (from frame)", 4, 35, "est", 0.5, ""),
    ("AB1-204", "Frame", "Shaft clamp block, 6061 CNC, 30 mm bore", "Xometry", "cad/step", 4, 70, "est", 0.4, "confirm hub motor shaft dia + flats"),
    ("AB1-205", "Frame", "Powder coat / hard anodise frame parts", "local", "", 1, 400, "est", 0.6, "salt air + fertiliser exposure"),
    ("AB1-301", "Drive", "Brushless hub motor 3 kW, 48 V, 130 N m nom / 200 N m peak, IP65", "OZO Electric", "ref 000500", 4, 465, "quote", 0.8, "EUR 399 incl. tax " + SRC["ozo"]),
    ("AB1-302", "Drive", "Turf tyre 20x8.00-10 on 10 in steel rim, 4x100", "Carlisle / Kenda", "Turf Saver 20x8.00-10", 4, 95, "est", 0.8, "flotation on sand"),
    ("AB1-303", "Drive", "FOC motor controller 75 V 100 A, CAN, hall + sensorless", "Flipsky", "FSESC 75100 (VESC 6 fw)", 4, 165, "est", 0.7, "potted in AB1-403 box; ros2 vesc driver"),
    ("AB1-401", "Power", "LFP prismatic cell 3.2 V 105 Ah (16S2P = 51.2 V 210 Ah, 10.75 kWh)", "EVE Energy", "LF105", 32, 52, "est", 0.7, "grade A, matched; UN38.3 for shipping"),
    ("AB1-402", "Power", "BMS 16S with CAN, contactor + precharge control", "Orion / Ewert Energy", "Orion BMS 2 (24-cell)", 1, 950, "est", 0.6, ""),
    ("AB1-403", "Power", "Keel pack enclosure 5052 sheet, IP67 gasket, cell compression plates", "local sheet-metal", "cad/step keel", 1, 650, "est", 0.5, ""),
    ("AB1-404", "Power", "Busbars, cell fuses, thermistors, sense harness", "assorted", "", 1, 250, "est", 0.6, ""),
    ("AB1-405", "Power", "Main contactor 500 A, 12 V coil, sealed", "TE Kilovac", "EV200AAANA", 1, 165, "est", 0.8, ""),
    ("AB1-406", "Power", "Precharge relay + 50 ohm 50 W resistor", "assorted", "", 1, 60, "est", 0.8, ""),
    ("AB1-407", "Power", "Main fuse 200 A Class T + holder", "Littelfuse / Blue Sea", "JLLN200 + 5502", 1, 95, "est", 0.8, ""),
    ("AB1-408", "Power", "Manual battery disconnect (lockout)", "Blue Sea", "9003e", 1, 70, "est", 0.8, "LOTO point for service"),
    ("AB1-409", "Power", "Battery connector 8 mm, 200 A, IP67, keyed pair", "Amphenol", "SurLok Plus", 1, 90, "est", 0.8, ""),
    ("AB1-410", "Power", "DC-DC 48->24 V 480 W DIN rail", "MEAN WELL", "DDR-480C-24", 1, 120, "est", 0.8, "33.6-67.2 V input"),
    ("AB1-411", "Power", "DC-DC 48->12 V 240 W DIN rail", "MEAN WELL", "DDR-240C-12", 1, 80, "est", 0.8, "Jetson + router"),
    ("AB1-412", "Power", "Fused distribution: DIN fuse blocks, breakers, terminals", "Phoenix Contact", "assorted", 1, 260, "est", 0.7, ""),
    ("AB1-413", "Power", "Charge inlet: spring dock contacts 2x 150 A + pilot pin", "Staubli / REMA", "MC / DIN 160A", 1, 380, "est", 0.6, "dock side in DK-1"),
    ("AB1-501", "Safety", "Safety relay, dual-channel E-stop + reset, PL d", "Pilz", "PNOZ s4 24VDC (750104)", 1, 310, "est", 0.9, ""),
    ("AB1-502", "Safety", "E-stop mushroom, IP69K, 2NC, yellow housing", "IDEC / Schneider", "XW1E / XB4", 4, 45, "est", 0.8, "4 corners"),
    ("AB1-503", "Safety", "Wireless E-stop transmitter + receiver, 1 km", "Humanistic Robotics", "HRI Wireless Emergency Stop", 1, 1950, "est", 0.8, "one handheld per field tech"),
    ("AB1-504", "Safety", "Pressure-sensitive safety edge bumper + controller", "Mayser / ASO", "SENTIR edge + SG-EFS", 2, 480, "est", 0.8, "front + rear"),
    ("AB1-505", "Safety", "Safety contactors (drive bus + arm bus cut)", "Schneider", "TeSys D LC1D25BD", 2, 120, "est", 0.9, ""),
    ("AB1-506", "Safety", "Stack light / beacon IP67, RGB + buzzer", "Banner", "TL50 Pro", 1, 180, "est", 0.8, ""),
    ("AB1-601", "Compute", "Edge computer 275 TOPS, 64 GB", "NVIDIA", "Jetson AGX Orin 64GB Developer Kit", 1, 3499, "quote", 0.85, "post-July-2026 price " + SRC["orin"] + "; rugged carrier at volume"),
    ("AB1-602", "Compute", "NVMe SSD 2 TB industrial (logging, Field Ledger cache)", "Innodisk / Samsung", "PM9A3-class", 1, 220, "est", 0.8, ""),
    ("AB1-603", "Compute", "Real-time I/O MCU + 3x CAN-FD (micro-ROS)", "PJRC + SK Pang", "Teensy 4.1 + triple CAN board", 1, 95, "est", 0.6, "motors, BMS, safety status"),
    ("AB1-606", "Comms", "Industrial unmanaged Ethernet switch 8x GbE, 12-48 VDC", "Moxa", "EDS-208A-T", 1, 220, "est", 0.8, "lidar, 2 arms, router, Teensy"),
    ("AB1-607", "Compute", "Powered industrial USB3 hub, 4 port, locking", "StarTech / Advantech", "ST4300USB3GB-class", 1, 160, "est", 0.8, "2x D405, GNSS, IMU"),
    ("AB1-604", "Comms", "5G/LTE industrial router, dual SIM, Wi-Fi 6", "Teltonika", "RUTX50", 1, 520, "est", 0.8, ""),
    ("AB1-605", "Comms", "Roof antennas 5G MIMO + Wi-Fi, IP67", "Taoglas / Poynting", "MA1508 / OMNI-402", 1, 160, "est", 0.8, ""),
    ("AB1-701", "Sensing", "3D lidar 360x59 deg, 70 m, IP67", "Livox", "Mid-360", 1, 749, "quote", 0.8, SRC["mid360"]),
    ("AB1-702", "Sensing", "Dual-antenna RTK GNSS heading kit (2x ZED-F9P + 2 antennas)", "ArduSimple", "simpleRTK2B Heading kit", 1, 650, "est", 0.8, "FDOT FPRN NTRIP corrections (free in FL)"),
    ("AB1-703", "Sensing", "Tactical-grade AHRS IMU", "HBK MicroStrain", "3DM-CV7-AHRS", 1, 1000, "est", 0.8, ""),
    ("AB1-801", "Enclosure", "IP66 enclosure ~600x300x150, polycarbonate, under deck", "Fibox / Hammond", "ARCA / 1414 series", 1, 260, "est", 0.7, ""),
    ("AB1-802", "Enclosure", "Thermoelectric enclosure cooler 24 V, ~120 W cooling", "EIC Solutions", "ThermoTEC AAC-141-4XT (24 VDC)", 1, 1100, "est", 0.7, "Florida summer: 35 C ambient + sun"),
    ("AB1-803", "Harness", "Wire, Deutsch DT/DTM connectors, M12, glands, loom, labels", "TE / Amphenol / Lapp", "see electrical/harness.csv", 1, 650, "est", 0.6, ""),
    ("AB1-804", "Lighting", "LED work/flood light 24 V 40 W IP68", "Rigid Industries", "D-Series Pro flood", 4, 180, "est", 0.6, "night picking (18 h/day)"),
]

HM1 = [
    ("HM1-001", "Arms", "6-axis cobot 5 kg / 922 mm, IP54 arm, DC MINI controller 30-60 VDC", "FAIRINO", "FR5 (DC controller)", 2, 6999, "quote", 0.85, SRC["fr5"] + "; confirm DC controller price + IP65 option"),
    ("HM1-002", "Arms", "Arm dress pack + cable carrier (vacuum, RS485, 24 V, USB3)", "igus", "triflex R TRE.40", 2, 250, "est", 0.7, ""),
    ("HM1-003", "Arms", "Arm rain/dust cover, breathable PTFE fabric", "RoboSuits / Roboworld", "custom FR5", 2, 450, "est", 0.6, "keeps the IP54 arm usable in FL rain"),
    ("HM1-101", "Mast", "Arm mount plate 20 mm 6061, machined", "Xometry", "cad/dxf/HM1-101", 2, 140, "est", 0.5, "verify FR5 base bolt pattern from vendor drawing"),
    ("HM1-102", "Mast", "1530 profile posts + beams (in AB1-101 cut list) + gussets", "80/20 Inc.", "1530", 1, 520, "est", 0.6, ""),
    ("HM1-201", "Perception", "Stereo camera, global shutter, GMSL2, IP67, wide lens", "Stereolabs", "ZED X (ZED-311110)", 2, 599, "quote", 0.85, SRC["zedx"]),
    ("HM1-202", "Perception", "GMSL2 capture card, 2 ports, for AGX Orin", "Stereolabs", "ZED Link Duo", 1, 379, "quote", 0.85, SRC["zedx"]),
    ("HM1-203", "Perception", "GMSL2 Fakra cable 5 m", "Stereolabs", "", 2, 45, "quote", 0.8, ""),
    ("HM1-301", "Vacuum", "Diaphragm vacuum pump 24 V, -75 kPa, 10 L/min", "Parker / Thomas", "BTC-IIS / 2002 series", 2, 220, "est", 0.7, "one per arm"),
    ("HM1-302", "Vacuum", "3/2 solenoid valve 24 V + blow-off", "SMC", "VQ110 / SYJ3000", 2, 60, "est", 0.8, ""),
    ("HM1-303", "Vacuum", "Digital vacuum switch (seal / contact detect)", "SMC", "ZSE20A", 2, 110, "est", 0.8, ""),
    ("HM1-401", "Logistics", "Stacking tote 600x500x350, food-grade, foam liner", "ORBIS", "Stak-N-Nest equiv.", 2, 75, "est", 0.8, "35 kg fruit each"),
    ("HM1-402", "Logistics", "Tote transfer deck: 24 V MDR roller zone + driver card", "Interroll", "EC5000 + DriveControl 20", 2, 1200, "est", 0.6, "rolls totes sideways to the hauler at the headland"),
]

EE1 = [
    ("EE1-001", "Mechanical", "ISO 9409-1-50-4-M6 flange adapter, 6061 CNC", "Xometry", "cad/step/EE1-001", 1, 85, "est", 0.4, ""),
    ("EE1-002", "Mechanical", "Sealed housing, MJF PA12 + O-ring grooves (IP65 target)", "Xometry / HP MJF", "cad/stl/EE1-002", 1, 120, "est", 0.3, "injection mould at volume"),
    ("EE1-003", "Mechanical", "Front plate with 3 finger clevises, MJF PA12", "Xometry", "cad/stl/EE1-003", 1, 45, "est", 0.3, ""),
    ("EE1-004", "Mechanical", "Fin-Ray finger TPU 95A (3 fitted + 3 spare)", "in-house FDM / Shore 95A", "cad/stl/EE1-004", 6, 8, "est", 0.5, "food-contact TPU; consumable, swap weekly"),
    ("EE1-005", "Mechanical", "D405 bracket, 6061", "Xometry", "cad/step/EE1-005", 1, 45, "est", 0.4, ""),
    ("EE1-006", "Mechanical", "Lead-screw cam ring, bearings, lip seal, O-rings, pins", "McMaster-Carr", "assorted", 1, 60, "est", 0.6, ""),
    ("EE1-101", "Actuation", "Smart servo, current-based force control, RS485", "ROBOTIS", "DYNAMIXEL XM430-W350-R", 1, 290, "est", 0.8, "grip force via current limit"),
    ("EE1-102", "Actuation", "Bellows suction cup 40 mm, 1.5 folds, food-grade silicone", "Piab", "BX40P-class", 1, 35, "est", 0.8, ""),
    ("EE1-103", "Actuation", "Micro linear actuator 100 mm (used 65 mm), position feedback, 12 V", "Actuonix", "L16-100-63-12-P", 1, 90, "est", 0.7, "retracts the suction cup 65 mm to seat the fruit"),
    ("EE1-104", "Actuation", "Cup rod guide: linear bushing + PTFE wiper seal", "Misumi / igus", "assorted", 1, 30, "est", 0.7, ""),
    ("EE1-201", "Sensing", "Short-range stereo depth camera (7-50 cm), global shutter", "RealSense", "D405", 1, 272, "est", 0.85, "+ rugged 3 m USB-C"),
    ("EE1-202", "Sensing", "ToF proximity sensor in palm (fruit contact distance)", "ST", "VL53L4CD", 1, 15, "est", 0.8, ""),
    ("EE1-203", "Lighting", "LED ring light 24 V, diffused, IP65", "Advanced Illumination / generic", "", 1, 60, "est", 0.6, "constant lighting day + night"),
    ("EE1-301", "Electrical", "M12 8-pin tool connector, RS485 interface, wiring", "Lumberg / ROBOTIS", "U2D2-class", 1, 90, "est", 0.6, ""),
    ("EE1-302", "Electrical", "Active USB3 cable 3 m, rugged", "Newnex / generic", "", 1, 45, "est", 0.8, ""),
]

# Other implements / platforms at design-estimate level (see docs/04_other_modules.md)
OTHER = {
    "LW-1 laser weeder implement (2 heads)": [
        ("Sealed RF CO2 laser 100 W, air-cooled", 2, 9000), ("10.6 um galvo scan head + F-theta", 2, 3500),
        ("Light-tight hood with brush skirt + interlocks (Class 4)", 1, 1500), ("Global-shutter RGB cameras + strobe", 2, 800),
        ("Cooling, frame, auto-coupler, harness", 1, 2600)],
    "LW-1M mechanical aisle cultivator (alternative)": [
        ("Electric rotary hoe 0.7 m (aisle between plastic beds), 48 V 1.5 kW", 1, 2600), ("Depth wheels, guard, coupler, harness", 1, 1400)],
    "SP-1 spot sprayer implement (replaces micro-doser)": [
        ("100 L tank, 48 V pump, 12 PWM nozzles with per-plant targeting", 1, 3800), ("Cameras + frame + coupler", 1, 1600)],
    "HL-1 hauler (AB-1 base + tote rack, no arms)": [
        ("AB-1 base (see AB-1 sheet, less nothing)", 1, None), ("8-tote rack with 4 MDR roller zones", 1, 5200)],
    "SU-1 scout UAV (ArduPilot quad, multispectral)": [
        ("Holybro X650 frame + motors + ESCs", 1, 900), ("Pixhawk 6X + power module", 1, 450), ("Holybro H-RTK F9P (rover)", 1, 600),
        ("Multispectral camera (MicaSense RedEdge-P class)", 1, 7500), ("6S 10 Ah batteries x4 + charger", 1, 1100), ("Telemetry + LTE companion (Pi 5)", 1, 450)],
    "DK-1 dock/charger (serves ~2 UGVs)": [
        ("LFP charger 3.5 kW 48 V, CAN (Delta-Q IC3500 class)", 1, 1800), ("Dock contacts, guide rails, concrete pad", 1, 1500),
        ("Shade/rain shelter (steel carport kit)", 1, 2500), ("Implement-swap stand with locating cones", 2, 900)],
}


def write_sheet(name, rows):
    path = os.path.join(HERE, f"{name}.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part_no", "subsystem", "description", "manufacturer", "model_mpn", "qty", "unit_usd", "ext_usd",
                    "price_basis", "vol100_factor", "ext_usd_at_100_units", "notes"])
        for r in rows:
            pn, ss, d, m, mpn, q, u, b, v, n = r
            w.writerow([pn, ss, d, m, mpn, q, u, q * u, b, v, round(q * u * v), n])
    return sum(r[5] * r[6] for r in rows), sum(r[5] * r[6] * r[8] for r in rows)


def main():
    totals = {}
    for name, rows in (("AB-1_base", AB1), ("HM-1_harvester_implement", HM1), ("EE-1_end_effector", EE1)):
        totals[name] = write_sheet(name, rows)
    base_pilot, base_vol = totals["AB-1_base"]
    other = {}
    with open(os.path.join(HERE, "other_modules_estimate.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["module", "line", "qty", "unit_usd", "ext_usd"])
        for mod, lines in OTHER.items():
            t = 0
            for d, q, u in lines:
                u = round(base_pilot) if u is None else u
                w.writerow([mod, d, q, u, q * u]); t += q * u
            other[mod] = t
    ee_p, ee_v = totals["EE-1_end_effector"]
    hm_p, hm_v = totals["HM-1_harvester_implement"]
    harvester_pilot = base_pilot + hm_p + 2 * ee_p
    harvester_vol = base_vol + hm_v + 2 * ee_v
    summary = dict(
        base_pilot=round(base_pilot), base_vol100=round(base_vol),
        hm1_pilot=round(hm_p), hm1_vol100=round(hm_v), ee1_pilot=round(ee_p), ee1_vol100=round(ee_v),
        harvester_robot_pilot=round(harvester_pilot), harvester_robot_vol100=round(harvester_vol),
        other_modules_pilot={k: round(v) for k, v in other.items()},
    )
    json.dump(summary, open(os.path.join(HERE, "cost_summary.json"), "w"), indent=1)

    # xlsx with live formulas
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws0 = wb.active; ws0.title = "Summary"
    hdr = Font(bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="2F5D3A")
    sheets = []
    for name in ("AB-1_base", "HM-1_harvester_implement", "EE-1_end_effector", "other_modules_estimate"):
        ws = wb.create_sheet(name[:31])
        rows = list(csv.reader(open(os.path.join(HERE, f"{name}.csv"))))
        for i, r in enumerate(rows, 1):
            for j, v in enumerate(r, 1):
                try:
                    v = float(v) if "." in v else int(v)
                except ValueError:
                    pass
                ws.cell(i, j, v)
        if name != "other_modules_estimate":
            n = len(rows)
            for i in range(2, n + 1):
                ws.cell(i, 8, f"=F{i}*G{i}"); ws.cell(i, 11, f"=ROUND(H{i}*J{i},0)")
            ws.cell(n + 1, 7, "TOTAL").font = Font(bold=True)
            ws.cell(n + 1, 8, f"=SUM(H2:H{n})").font = Font(bold=True)
            ws.cell(n + 1, 11, f"=SUM(K2:K{n})").font = Font(bold=True)
            sheets.append((name, ws.title, n + 1))
        for c in ws[1]:
            c.font = hdr; c.fill = fill
        for col, wdt in zip("ABCDEFGHIJKL", (10, 12, 58, 24, 30, 5, 10, 10, 8, 8, 12, 60)):
            ws.column_dimensions[col].width = wdt
        ws.freeze_panes = "A2"
    ws0["A1"] = "Agrobo robot BOM summary (USD)"; ws0["A1"].font = Font(bold=True, size=14)
    ws0.append([]); ws0.append(["Item", "Pilot qty (1-5)", "At 100 units"])
    for c in ws0[3]:
        c.font = hdr; c.fill = fill
    ref = {s[0]: s for s in sheets}
    def tot(nm, col):
        _, t, r = ref[nm]; return f"='{t}'!{col}{r}"
    ws0.append(["AB-1 base platform", tot("AB-1_base", "H"), tot("AB-1_base", "K")])
    ws0.append(["HM-1 harvester implement", tot("HM-1_harvester_implement", "H"), tot("HM-1_harvester_implement", "K")])
    ws0.append(["EE-1 end-effector (x2)", "=2*" + tot("EE-1_end_effector", "H")[1:], "=2*" + tot("EE-1_end_effector", "K")[1:]])
    ws0.append(["Harvester robot total", "=SUM(B4:B6)", "=SUM(C4:C6)"])
    ws0["A7"].font = ws0["B7"].font = ws0["C7"].font = Font(bold=True)
    ws0.append([])
    ws0.append(["Other modules (pilot, design estimate)", "", ""])
    for k, v in other.items():
        ws0.append([k, v, ""])
    ws0.append([]); ws0.append(["Prices checked 2026-10-21. 'quote' = public list price (URL in notes); 'est' = engineering estimate, get quotes before ordering."])
    ws0.column_dimensions["A"].width = 52; ws0.column_dimensions["B"].width = 16; ws0.column_dimensions["C"].width = 14
    for row in ws0.iter_rows(min_row=4, max_col=3):
        for c in row[1:]:
            c.number_format = '"$"#,##0'
    wb.save(os.path.join(HERE, "Agrobo_BOM.xlsx"))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

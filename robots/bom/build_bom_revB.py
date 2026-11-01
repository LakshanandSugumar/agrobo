"""Rev B harvester BOM: US-made sourcing (Laksh, 2026-11-01: "made in US only, whatever the price").

Writes bom/revB_us_sourced.csv, bom/revB_no_us_source.csv, bom/revB_summary.json and a "Rev B US" sheet set in
bom/Agrobo_BOM_revB.xlsx. Prices USD at pilot quantity; "quote" = published price (URL in notes), "est" = estimate.

origin codes (per line):
  US       vendor states the part is made/built in the USA (URL in notes)
  US?      US manufacturer with US plants, but the page read does not state this product's origin: get a
           country-of-origin (COO) letter before claiming it
  US-ASSY  final assembly in the USA, major components imported (vendor says "designed and assembled")
  NONE     no US-made source found today; imported part kept
"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "src"))
from params import ARM_REVB, DRIVE_REVB, LIDAR_REVB, STEREO_REVB   # noqa: E402

U = {
    "spark": "https://standardbots.com/products/spark",
    "ouster": "https://en.wikipedia.org/wiki/Ouster_(company)",
    "ouster_price": "https://mylidarstore.com/products/os0-os1-os2",
    "s27": "https://www.carnegierobotics.com/multisense-s27",
    "winsmith": "https://winsmith.com/products/rd-series/",
    "vectornav": "https://www.vectornav.com/products/detail/vn-100",
    "hemisphere": "https://www.hemispheregnss.com/products/receivers/",
    "digi": "https://www.digi.com/products/networking/cellular-routers/industrial",
    "motenergy": "https://www.motenergy.com/info.html",
    "roboteq": "https://www.roboteq.com/",
    "lfp": "https://www.teslarati.com/tesla-us-lfp-battery-supply-lg-deal-report/",
}

# (part_no, revA part, rev B description, supplier (location), model, origin, qty, unit_usd, basis, lead, mech_change, notes)
L = [
    # ---------------- AB-1 base
    ("AB1-101", "80/20 1515", "T-slot profile, cut to length", "80/20 Inc. (Columbia City, IN)", "1515", "US?", 1, 980, "est", "1 wk", "", ""),
    ("AB1-102", "assorted", "Fasteners, T-nuts, gussets: US-made stainless", "80/20 + US fastener mills", "assorted", "US?", 1, 900, "est", "1-2 wk", "", "specify DFARS/US-melt stainless"),
    ("AB1-201", "SendCutSend", "Deck plate 3 mm 5052, laser cut, US-mill aluminium", "SendCutSend (NV/CA/TX)", "cad/dxf/AB1-201", "US?", 1, 310, "est", "1 wk", "", "request US-melted sheet"),
    ("AB1-202", "SendCutSend", "Reducer mount plate 12 mm 6061 (was axle plate)", "SendCutSend / US CNC shop", "TODO redraw", "US?", 4, 95, "est", "1-2 wk", "YES: becomes a reducer mount", ""),
    ("AB1-203", "SendCutSend", "Leg gusset plate 10 mm 6061", "SendCutSend", "cad/step", "US?", 4, 40, "est", "1 wk", "", ""),
    ("AB1-205", "local", "Powder coat / anodise", "local FL shop", "", "US", 1, 400, "est", "1 wk", "", "service"),
    ("AB1-301", "OZO hub motor (France)", f"BLDC motor 48 V ~2 kW, inboard ({DRIVE_REVB['motor_cont_Nm']} N m cont at motor)", "Motenergy (Hartford, WI; distributor)", "ME17xx series", "US?", 4, 650, "est", "2-4 wk",
     "YES: hub motor replaced by inboard motor + reducer", "origin of motor not stated, " + U["motenergy"]),
    ("AB1-301b", "(in hub motor)", f"Right-angle reducer {DRIVE_REVB['ratio']:.0f}:1, wheel on output shaft", "Winsmith (Springville NY / GA / NC)", "RD series", "US", 4, 850, "est", "5 days",
     "YES: new part per wheel, ~+4 kg/wheel", "'manufactured at US facilities' " + U["winsmith"]),
    ("AB1-301c", "-", "Wheel hub adapter + output-shaft bearing", "Timken / US CNC", "", "US?", 4, 120, "est", "2 wk", "YES", ""),
    ("AB1-302", "Carlisle Turf Saver", "Turf tyre 20x8.00-10 on steel rim", "US tyre maker TBD (Titan, Quincy IL?)", "20x8.00-10", "NONE", 4, 120, "est", "2 wk", "", "no confirmed US-built small turf tyre; get COO"),
    ("AB1-303", "Flipsky VESC (China)", "Brushless controller 60 V dual channel, CAN", "Roboteq / Nidec (St. Louis, MO HQ)", "FBL/GBL dual", "US?", 2, 900, "est", "2-4 wk", "", "manufacture location not stated, " + U["roboteq"]),
    ("AB1-401", "EVE LF105 (China)", "LFP cell 3.2 V 105 Ah (16S2P)", "imported (no US small-volume source)", "EVE LF105", "NONE", 32, 52, "est", "6-10 wk", "",
     "US LFP plants (Tesla NV, LGES Lansing H2 2027) sell to OEM/ESS only, " + U["lfp"]),
    ("AB1-402", "Orion BMS 2", "BMS 16S with CAN", "Ewert Energy Systems (US)", "Orion BMS 2", "US?", 1, 950, "est", "1-2 wk", "", ""),
    ("AB1-403", "local", "Pack enclosure, US sheet metal", "local FL fabricator", "cad/step keel", "US", 1, 650, "est", "2 wk", "", ""),
    ("AB1-404", "assorted", "Busbars, fuses, sense harness", "US distributors", "", "US?", 1, 300, "est", "1 wk", "", ""),
    ("AB1-405", "TE Kilovac EV200", "Main contactor 500 A sealed", "TE Kilovac (CA)", "EV200AAANA", "US?", 1, 165, "est", "2 wk", "", ""),
    ("AB1-406", "assorted", "Precharge relay + resistor", "US distributors", "", "US?", 1, 70, "est", "1 wk", "", ""),
    ("AB1-407", "Littelfuse", "Main fuse 200 A Class T + holder", "Mersen (Newburyport, MA)", "A3T200 + holder", "US?", 1, 110, "est", "1 wk", "", ""),
    ("AB1-408", "Blue Sea 9003e", "Lockout disconnect", "Blue Sea Systems (Bellingham, WA)", "9003e", "US?", 1, 70, "est", "1 wk", "", ""),
    ("AB1-409", "Amphenol SurLok", "Battery connector 200 A keyed", "Anderson Power Products (Sterling, MA)", "SB175", "US?", 1, 90, "est", "1 wk", "", ""),
    ("AB1-410", "MEAN WELL (Taiwan)", "DC-DC 48->24 V 500 W module + carrier", "Vicor (Andover, MA)", "DCM4623 + board", "US?", 1, 420, "est", "4-8 wk", "small: new carrier board", ""),
    ("AB1-411", "MEAN WELL (Taiwan)", "DC-DC 48->12 V 300 W module + carrier", "Vicor (Andover, MA)", "DCM3623 + board", "US?", 1, 300, "est", "4-8 wk", "", ""),
    ("AB1-412", "Phoenix Contact", "Fused distribution blocks", "Eaton Bussmann (US)", "assorted", "US?", 1, 320, "est", "1 wk", "", ""),
    ("AB1-413", "Staubli (CH)", "Dock charge contacts 2x 175 A", "Anderson Power Products (MA)", "SBX / custom", "US?", 1, 250, "est", "2 wk", "small: contact block footprint", ""),
    ("AB1-501", "Pilz PNOZ s4 (DE)", "Safety controller, dual-channel, PL d/e", "Banner Engineering (Minneapolis, MN)", "XS26-2DE", "US?", 1, 650, "est", "1-2 wk", "", ""),
    ("AB1-502", "IDEC (JP)", "E-stop button IP69K", "Banner Engineering", "SSA-EB1PL", "US?", 4, 90, "est", "1-2 wk", "", ""),
    ("AB1-503", "HRI (Canada)", "Wireless E-stop", "FORT Robotics (Philadelphia, PA)", "Wireless Safety Controller", "US?", 1, 2500, "est", "4-6 wk", "", "origin not confirmed"),
    ("AB1-504", "Mayser (DE)", "Safety edge bumper + controller", "Miller Edge (West Grove, PA)", "ME series + controller", "US?", 2, 520, "est", "2-3 wk", "", ""),
    ("AB1-505", "Schneider", "Safety contactors", "Eaton (US)", "XTCE025", "US?", 2, 140, "est", "1 wk", "", ""),
    ("AB1-506", "Banner TL50", "Beacon", "Banner Engineering", "TL50 Pro", "US?", 1, 180, "est", "1 wk", "", ""),
    ("AB1-601", "Jetson AGX Orin", "Edge AI computer 64 GB", "NVIDIA (made in Asia)", "Jetson AGX Orin 64GB", "NONE", 1, 3499, "quote", "2-4 wk", "",
     "no US-made AI compute module exists at this class"),
    ("AB1-602", "NVMe SSD", "Industrial NVMe 2 TB", "imported", "", "NONE", 1, 220, "est", "1 wk", "", ""),
    ("AB1-603", "Teensy 4.1", "Real-time I/O MCU + CAN board", "PJRC (Sherwood, OR) + US CAN carrier", "Teensy 4.1", "US?", 1, 95, "est", "1 wk", "", ""),
    ("AB1-604", "Teltonika RUTX50 (LT)", "5G industrial router", "Digi International (MN)", "IX25 (TAA compliant)", "NONE", 1, 1100, "est", "2-4 wk", "",
     "TAA-compliant is not US-made; no US-built 5G router found, " + U["digi"]),
    ("AB1-605", "Taoglas/Poynting", "5G + Wi-Fi antennas", "PCTEL (Bloomingdale, IL)", "", "US?", 1, 200, "est", "2 wk", "", ""),
    ("AB1-606", "Moxa (TW)", "Industrial Ethernet switch, 10+ ports (cameras now on GbE)", "Red Lion (York, PA)", "NT-series", "US?", 1, 450, "est", "2 wk", "small: more ports", ""),
    ("AB1-607", "USB hub", "Powered USB3 hub (D405s only)", "imported", "", "NONE", 1, 160, "est", "1 wk", "", ""),
    ("AB1-701", "Livox Mid-360 (China)", "3D lidar 90 deg VFOV", "Ouster (San Francisco)", LIDAR_REVB["model"], "US-ASSY", 1, 12000, "quote", "4-8 wk",
     "small: 87 mm puck, new pedestal", "made in US and Thailand per " + U["ouster"] + "; price from " + U["ouster_price"] + " (sold out, get quote)"),
    ("AB1-702", "ArduSimple (ES)", "Dual-antenna RTK heading receiver", "Hemisphere GNSS (Tempe, AZ)", "Vector VR1000", "US?", 1, 4500, "est", "2-4 wk",
     "small: larger receiver + antennas", "designs and manufactures; plant not stated, " + U["hemisphere"]),
    ("AB1-703", "MicroStrain CV7", "AHRS IMU", "VectorNav", "VN-100 Rugged", "US", 1, 1200, "est", "1 day", "", "'Made in the USA' " + U["vectornav"]),
    ("AB1-801", "Fibox (FI)", "IP66 enclosure ~600x300x150", "nVent Hoffman (Anoka, MN)", "", "US?", 1, 420, "est", "2 wk", "", ""),
    ("AB1-802", "EIC ThermoTEC", "Enclosure TEC cooler 24 V", "EIC Solutions (Warminster, PA)", "AAC-141", "US?", 1, 1100, "est", "2-4 wk", "", ""),
    ("AB1-803", "TE/Amphenol", "Harness: wire, connectors, glands", "US wire + Amphenol/ITT US lines", "", "US?", 1, 900, "est", "2 wk", "", ""),
    ("AB1-804", "Rigid Industries", "LED flood 24 V", "Rigid Industries (Gilbert, AZ)", "D-Series Pro", "US?", 4, 180, "est", "1 wk", "", ""),
    # ---------------- HM-1
    ("HM1-001", "FAIRINO FR5 (China)", f"6-axis cobot {ARM_REVB['payload']:.0f} kg / {ARM_REVB['reach']*1000:.0f} mm, {ARM_REVB['ip']}", "Standard Bots (Glen Cove, NY)",
     "Spark", "US-ASSY", 2, 29500, "quote", "2-6 wk", "YES: new base bolt pattern, new kinematics, AC power",
     "'designed and assembled in Glen Cove, NY' " + U["spark"]),
    ("HM1-001b", "-", "48 V DC to 120 VAC pure-sine inverter 2 kW (arm controller supply)", "Magnum Energy (Everett, WA)", "MS2012-class", "US?", 2, 1400, "est", "2-4 wk",
     "YES: 2x ~10 kg inverters + ventilation under deck", "Spark lists no DC input; ask Standard Bots for a DC controller first"),
    ("HM1-002", "igus", "Arm dress pack", "igus (East Providence, RI plant)", "triflex R", "US?", 2, 250, "est", "2 wk", "", ""),
    ("HM1-003", "cover", "Arm rain cover (Spark IP65 design, keep cover for fertiliser spray)", "US sewn", "", "US", 2, 600, "est", "3 wk", "", ""),
    ("HM1-101", "plate", "Arm mount plate 20 mm 6061", "US CNC", "TODO Spark bolt pattern", "US?", 2, 160, "est", "1-2 wk", "YES", ""),
    ("HM1-102", "80/20 1530", "Mast profile + gussets", "80/20 Inc.", "1530", "US?", 1, 520, "est", "1 wk", "", ""),
    ("HM1-201", "ZED X (made abroad)", "Outdoor stereo camera, GbE", "Carnegie Robotics (Pittsburgh, PA)", STEREO_REVB["model"], "US", 2, 1995, "quote", "TBD",
     "YES: 27 cm baseline, wider camera bar", "'Built with pride in the USA' " + U["s27"]),
    ("HM1-301", "Parker/Thomas", "Diaphragm vacuum pump 24 V", "Gast (Benton Harbor, MI)", "DOA/ D-series", "US?", 2, 350, "est", "2 wk", "", ""),
    ("HM1-302", "SMC (JP)", "Solenoid valve 24 V", "Clippard (Cincinnati, OH)", "ET-3", "US?", 2, 70, "est", "1 wk", "", ""),
    ("HM1-303", "SMC ZSE20", "Vacuum switch", "US maker TBD", "", "NONE", 2, 150, "est", "2 wk", "", "no confirmed US-made digital vacuum switch"),
    ("HM1-401", "ORBIS", "Stacking tote + liner", "ORBIS (Oconomowoc, WI)", "", "US?", 2, 75, "est", "2 wk", "", ""),
    ("HM1-402", "Interroll (CH)", "MDR roller zone + driver", "Hytrol (Jonesboro, AR)", "E24 MDR", "US?", 2, 1500, "est", "4-6 wk", "small: roller pitch", ""),
    # ---------------- EE-1 (x2 per robot: qty already doubled)
    ("EE1-001", "CNC", "Tool flange adapter (Spark flange TODO)", "US CNC", "", "US?", 2, 95, "est", "1-2 wk", "YES: flange pattern", ""),
    ("EE1-002", "MJF", "Sealed housing, enlarged for NEMA 23 servo", "US MJF bureau", "", "US?", 2, 130, "est", "1 wk", "YES: dia 90 -> 110 mm, +0.5 kg", ""),
    ("EE1-003", "MJF", "Front plate", "US MJF bureau", "", "US?", 2, 50, "est", "1 wk", "", ""),
    ("EE1-004", "TPU", "Fin-Ray fingers, US filament (3 + 3 spare per EE)", "NinjaTek filament (Lititz, PA)", "", "US?", 12, 9, "est", "in-house", "", ""),
    ("EE1-005", "bracket", "Camera bracket", "US CNC", "", "US?", 2, 50, "est", "1 wk", "", ""),
    ("EE1-006", "assorted", "Bearings, seals, cam ring", "US distributors", "", "US?", 2, 90, "est", "1 wk", "", ""),
    ("EE1-101", "DYNAMIXEL (KR)", "Integrated servo, torque mode", "Teknic (Victor, NY)", "ClearPath-MC NEMA 23", "US?", 2, 350, "est", "1-2 wk", "YES: larger motor, step/dir+torque I/O", ""),
    ("EE1-102", "Piab (SE)", "Bellows suction cup 40 mm silicone", "Anver (Hudson, MA)", "", "US?", 2, 40, "est", "1 wk", "", ""),
    ("EE1-103", "Actuonix (CA)", "Linear actuator 65 mm stroke", "Ultra Motion (Cutchogue, NY)", "Digit series", "US?", 2, 450, "est", "2-4 wk", "small: body length", ""),
    ("EE1-104", "guide", "Cup rod guide", "US distributors", "", "US?", 2, 35, "est", "1 wk", "", ""),
    ("EE1-201", "RealSense D405", "Short-range depth camera 7-50 cm", "RealSense (imported)", "D405", "NONE", 2, 272, "est", "2 wk", "",
     "no US-made depth camera works at 0.1 m (Carnegie MultiSense starts ~0.5 m)"),
    ("EE1-202", "ST VL53L4CD", "ToF proximity sensor", "imported", "", "NONE", 2, 15, "est", "1 wk", "", ""),
    ("EE1-203", "ring light", "LED ring light 24 V", "Advanced Illumination (Rochester, VT)", "", "US?", 2, 180, "est", "2 wk", "", ""),
    ("EE1-301", "M12/RS485", "Tool connector + I/O wiring", "US distributors", "", "US?", 2, 120, "est", "1 wk", "", ""),
    ("EE1-302", "USB3 cable", "Active USB3 cable 3 m", "imported", "", "NONE", 2, 45, "est", "1 wk", "", ""),
]


def main():
    cols = ["part_no", "rev_a_part", "rev_b_description", "supplier", "model", "origin", "qty", "unit_usd", "ext_usd",
            "price_basis", "lead_time", "mechanical_change", "notes"]
    rows = [r[:6] + (r[6], r[7], r[6] * r[7]) + r[8:] for r in L]
    with open(os.path.join(HERE, "revB_us_sourced.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    with open(os.path.join(HERE, "revB_no_us_source.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows([r for r in rows if r[5] == "NONE"])
    by = {}
    for r in rows:
        by[r[5]] = by.get(r[5], 0) + r[8]
    total = sum(by.values())
    assembly = 4500   # US assembly + test labour, first units
    out = dict(revB_robot_pilot=round(total), revB_assembly=assembly, revB_robot_pilot_incl_assembly=round(total + assembly),
               by_origin_usd={k: round(v) for k, v in by.items()},
               by_origin_share={k: round(v / total, 3) for k, v in by.items()},
               revA1_robot_pilot=48342, revA1_robot_pilot_incl_assembly=48342 + 3600)
    out["delta_vs_revA1_pct"] = round(100 * (out["revB_robot_pilot_incl_assembly"] / out["revA1_robot_pilot_incl_assembly"] - 1))
    json.dump(out, open(os.path.join(HERE, "revB_summary.json"), "w"), indent=1)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Rev B US-sourced"
    ws.append(cols)
    for r in rows:
        ws.append(list(r))
    n = len(rows) + 1
    for i in range(2, n + 1):
        ws.cell(i, 9, f"=G{i}*H{i}")
    ws.cell(n + 1, 8, "TOTAL").font = Font(bold=True); ws.cell(n + 1, 9, f"=SUM(I2:I{n})").font = Font(bold=True)
    fills = {"US": "C6E0B4", "US?": "FFF2CC", "US-ASSY": "FCE4D6", "NONE": "F4B6B6"}
    for i in range(2, n + 1):
        ws.cell(i, 6).fill = PatternFill("solid", fgColor=fills[ws.cell(i, 6).value])
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, wdt in zip("ABCDEFGHIJKLM", (10, 20, 50, 34, 26, 9, 5, 9, 10, 8, 9, 34, 70)):
        ws.column_dimensions[col].width = wdt
    ws.freeze_panes = "A2"
    s = wb.create_sheet("Summary")
    s.append(["Origin", "USD", "Share"])
    for k in ("US", "US?", "US-ASSY", "NONE"):
        s.append([k, round(by.get(k, 0)), round(by.get(k, 0) / total, 3)])
    s.append(["Parts total", round(total)]); s.append(["US assembly + test", assembly]); s.append(["Robot total", round(total + assembly)])
    s.append([]); s.append(["US = vendor states made in USA; US? = US maker, get a country-of-origin letter; US-ASSY = assembled in US from imported parts; NONE = no US source today"])
    wb.save(os.path.join(HERE, "Agrobo_BOM_revB.xlsx"))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

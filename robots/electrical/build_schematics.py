"""Electrical drawings for AB-1 + HM-1. Run: python electrical/build_schematics.py
Writes E-01 power single-line, E-02 safety circuit, E-03 data/comms architecture (SVG + PDF) and harness.csv.
These are system-level schematics for a pilot build on COTS modules (no custom PCB in v1)."""
import csv, os
import schemdraw
import schemdraw.elements as elm
from schemdraw import flow
import matplotlib
matplotlib.use("Agg")

HERE = os.path.dirname(os.path.abspath(__file__))
schemdraw.config(fontsize=10, lw=1.4)


def title(d, t, sub):
    d += elm.Label().at((0, 1.6)).label(t, fontsize=15, loc="right", halign="left")
    d += elm.Label().at((0, 1.0)).label(sub, fontsize=9, loc="right", halign="left", color="#555")


def save(d, name):
    d.save(os.path.join(HERE, name + ".svg"))
    d.save(os.path.join(HERE, name + ".pdf"))


# ------------------------------------------------------------------ E-01 power single-line
def e01():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=2.2)
        title(d, "E-01  AB-1 / HM-1 power distribution (single line)",
              "51.2 V LFP 16S2P 210 Ah | all DC | wire sizes are copper, 105 C insulation | Agrobo rev A 2026-10-21")
        d += elm.BatteryCell().up().at((0, -6)).label("BT1  16S2P LFP\n51.2 V 10.75 kWh\nEVE LF105 x32\nBT- to shunt", loc="bottom")
        top = d.here
        d += elm.Line().up(0.5)
        d += elm.Fuse().right().label("F1 200 A\nClass T", loc="top")
        d += elm.Switch().right().label("S1 lockout\ndisconnect", loc="top")
        d += elm.Line().right(0.5)
        j0 = d.here
        d += elm.Dot()
        d += elm.Line().right(1.5)
        d += elm.Switch(action="close").right().label("K0 main contactor\nEV200 (BMS controlled)", loc="top")
        bus = d.here
        d += elm.Dot()
        d.push()
        d += elm.Line().at(j0).down(1.6)
        d += elm.Resistor().right().label("R1 50 ohm\nprecharge", loc="bottom")
        d += elm.Switch(action="close").right(2.2).label("K0p", loc="bottom")
        d += elm.Line().up(1.6).to(bus)
        d.pop()
        d += elm.Line().right(1.0)
        b = d.here
        d += elm.Label().at((b[0] + 19.5, b[1])).label("+48 V BUS\n(2 AWG busbar)", loc="right", halign="left")
        # branches
        def branch(x, label, fuse, load, contactor=None):
            d.add(elm.Line().at(b).right(x))
            p = d.here
            d.add(elm.Dot())
            d.add(elm.Line().down(0.6))
            d.add(elm.Fuse().down().label(fuse, loc="right"))
            if contactor:
                d.add(elm.Switch(action="close").down().label(contactor, loc="right"))
            d.add(elm.Line().down(0.4))
            d.add(flow.Box(w=3.2, h=1.2).anchor("N").label(load, fontsize=8.5))
        branch(1.0, "", "F2-F5 4x 40 A\n(8 AWG)", "4x VESC 75100\nI_batt limit 35 A\n-> 4x OZO hub motor", "K1 drive\nsafety contactor")
        branch(5.6, "", "F6, F7 2x 30 A\n(10 AWG)", "2x FAIRINO FR5\nDC MINI controller\n30-60 V in", "K2 arm\nsafety contactor")
        branch(10.2, "", "F8 20 A\n(12 AWG)", "PS1 DDR-480C-24\n48->24 V 20 A")
        branch(14.4, "", "F9 10 A\n(14 AWG)", "PS2 DDR-240C-12\n48->12 V 20 A")
        branch(18.6, "", "F10 2 A", "BMS sense +\nTeensy I/O (always on)")
        d += elm.Line().at(b).right(18.6)
        # 24 V and 12 V load lists
        d += flow.Box(w=5.2, h=3.6).at((b[0] + 10.2, -10.4)).anchor("N").label(
            "24 V loads (fused DIN block)\nF11 3 A  safety relay PNOZ s4 + K1/K2 coils\nF12 10 A enclosure TEC cooler\n"
            "F13 6 A  4x LED flood (40 W)\nF14 4 A  2x vacuum pump + valves\nF15 3 A  2x EE servo + ring light\n"
            "F16 2 A  lidar, GNSS, IMU, beacon\nF17 3 A  ZED Link (PoC) + spare", fontsize=7.6)
        d += flow.Box(w=4.6, h=2.0).at((b[0] + 15.6, -10.4)).anchor("N").label(
            "12 V loads\nF18 8 A  Jetson AGX Orin (MAXN 60 W)\nF19 3 A  RUTX50 router\nF20 2 A  Ethernet switch", fontsize=7.6)
        # charge path
        d += elm.Line().at((b[0] + 10.2, -7.7)).to((b[0] + 10.2, -10.4))
        d += elm.Line().at((b[0] + 14.4, -7.7)).to((b[0] + 14.4, -9.0))
        d += elm.Line().to((b[0] + 15.6, -9.0))
        d += elm.Line().to((b[0] + 15.6, -10.4))
        d += elm.Label().at((-0.4, -15.2)).label("BT- via 500 A shunt (BMS current sense) to chassis-isolated return.\n"
                                               "Charge: dock contacts J1 (+/-) -> F21 125 A -> K3 charge contactor (BMS) -> BUS.\n"
                                               "Chassis bonded to BT- through 100 kohm + insulation monitor (IMD) input on BMS.",
                                               fontsize=8, loc="right", halign="left")
    save(d, "E-01_power_single_line")


# ------------------------------------------------------------------ E-02 safety circuit
def e02():
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=1.8)
        title(d, "E-02  Safety chain -> PNOZ s4 -> K1 drive / K2 arms",
              "Dual channel, cross-monitored, Cat 3 / PL d target (ISO 13849-1). Stop category 0 for drive, cat 1 for arms (controlled stop then K2).")
        y0 = 0
        for ch, y in (("CH1 (S11-S12)", -1.5), ("CH2 (S21-S22)", -4.5)):
            d += elm.Label().at((-2.2, y)).label(ch, fontsize=9)
            d += elm.Line().at((0, y)).right(0.6)
            for name in ("ES1 front L", "ES2 front R", "ES3 rear L", "ES4 rear R", "WES1 wireless\nrx relay", "SE1/SE2\nbumper edges"):
                d += elm.Button(nc=True).right().label(name, loc="top", fontsize=7.5)
            d += elm.Line().to((14.6, y))
        d += flow.Box(w=3.6, h=5.0).at((14.6, -0.5)).anchor("NW").label(
            "SR1  Pilz PNOZ s4\n24 VDC\n\nS11-S12 / S21-S22 inputs\nS33-S34 reset (monitored)\n\n13-14  -> K1 coil (drive)\n23-24  -> K2 coil via\n           1.0 s delay (cat 1)\n33-34  -> K1/K2 aux\n           feedback (EDM)", fontsize=8)
        d += elm.Button().at((14.6, -6.6)).left().label("RS1 reset (blue)\nat rear panel", loc="bottom", fontsize=8)
        d += elm.Label().at((0, -7.6)).label(
            "Also wired into SR1 inputs in series: FR5 controller safety I/O (each arm reports protective stop), BMS fault relay.\n"
            "Software stop (non-safety) path: Jetson -> Teensy -> VESC zero current + FR5 'stop' over Ethernet; used for normal pauses.\n"
            "Geofence + speed limit (0.5 m/s near people detected by perception) are software functions and are NOT counted as safety functions in v1.\n"
            "Production: add SICK outdoorScan3 safety laser scanner zones (protective field 1.5 m at 1.5 m/s) to reach ISO 18497 people-detection.",
            fontsize=8, loc="right", halign="left")
    save(d, "E-02_safety_circuit")


# ------------------------------------------------------------------ E-03 data / comms
def e03():
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    B = {  # name: (cx, cy, label, colour)
        "jet": (8.0, 4.0, "Jetson AGX Orin 64GB\nROS 2 Jazzy | Nav2 | MoveIt 2\nTensorRT perception\nField Ledger edge cache", "#dce9dd"),
        "sw": (8.0, 7.2, "ETH SW1  Moxa EDS-208A\n8x GbE, 12-48 V", "#e8e8e8"),
        "lid": (1.6, 9.6, "Livox Mid-360\nGbE + PTP", "#fff"), "frl": (5.0, 9.6, "FR5 left controller\nGbE", "#fff"),
        "frr": (8.4, 9.6, "FR5 right controller\nGbE", "#fff"), "rtr": (11.8, 9.6, "RUTX50 5G router\nuplink + Wi-Fi", "#fff"),
        "tee": (14.6, 7.2, "Teensy 4.1 I/O\nmicro-ROS over GbE", "#fff"),
        "lnk": (3.4, 4.0, "ZED Link Duo\nGMSL2 capture (PCIe)", "#e8e8e8"),
        "zl": (0.7, 5.3, "ZED X left\nGMSL2", "#fff"), "zr": (0.7, 2.7, "ZED X right\nGMSL2", "#fff"),
        "d1": (4.4, 0.8, "D405 left EE\nUSB3", "#fff"), "d2": (6.8, 0.8, "D405 right EE\nUSB3", "#fff"),
        "gn": (9.2, 0.8, "simpleRTK2B heading\nUSB", "#fff"), "imu": (11.6, 0.8, "MicroStrain CV7\nUSB", "#fff"),
        "c1": (17.4, 8.6, "CAN1  4x VESC 75100\n500 kbit/s", "#fff"), "c2": (17.4, 7.2, "CAN2  Orion BMS\n+ dock charger", "#fff"),
        "c3": (17.4, 5.8, "CAN3  pumps, valves,\nRS485 bridge to EE servos", "#fff"),
    }
    E = [("jet", "sw", "GbE"), ("sw", "lid", ""), ("sw", "frl", ""), ("sw", "frr", ""), ("sw", "rtr", ""), ("sw", "tee", ""),
         ("jet", "lnk", "PCIe"), ("lnk", "zl", ""), ("lnk", "zr", ""), ("jet", "d1", ""), ("jet", "d2", ""), ("jet", "gn", ""),
         ("jet", "imu", ""), ("tee", "c1", ""), ("tee", "c2", ""), ("tee", "c3", "")]
    fig, ax = plt.subplots(figsize=(15, 9))
    for a_, b_, lab in E:
        (x0, y0), (x1, y1) = B[a_][:2], B[b_][:2]
        ax.plot([x0, x1], [y0, y1], color="#333", lw=1.2, zorder=1)
        if lab:
            ax.text((x0 + x1) / 2 + 0.1, (y0 + y1) / 2 + 0.1, lab, fontsize=9, color="#2f5d3a")
    for k, (x, y, lab, c) in B.items():
        w, h = (3.4, 1.7) if k == "jet" else (2.6, 0.95)
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.05", fc=c, ec="#222", lw=1.2, zorder=2))
        ax.text(x, y, lab, ha="center", va="center", fontsize=8.5, zorder=3)
    ax.text(0, 11.3, "E-03  Data and communications architecture", fontsize=15)
    ax.text(0, 10.85, "Ethernet backbone + GMSL2 + USB3 + CAN-FD | ROS 2 Jazzy on Jetson, micro-ROS on Teensy | Agrobo rev A 2026-10-21", fontsize=9, color="#555")
    ax.text(0, -0.9, "RTK corrections: FDOT Florida Permanent Reference Network (FPRN) NTRIP over 5G; fallback = farm base station on a 900 MHz radio.\n"
            "Time sync: PTP grandmaster on the Jetson to lidar + switch; ZED X pair hardware-triggered by the ZED Link card.\n"
            "Offline-first: the robot runs its day plan from the local Field Ledger cache; telemetry is buffered and synced when 5G returns.", fontsize=9, va="top")
    ax.set_xlim(-0.8, 19.2); ax.set_ylim(-2.2, 11.8); ax.axis("off")
    for ext in ("svg", "pdf"):
        fig.savefig(os.path.join(HERE, f"E-03_data_comms.{ext}"), bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ harness / wire list
HARNESS = [
    # id, from, to, signal, wire, AWG, fuse, connector_from, connector_to, length_m
    ("W001", "BT1 +", "F1", "BAT+", "single core", "2", "200 A", "SurLok Plus 8 mm", "M8 lug", 0.4),
    ("W002", "F1", "S1 disconnect", "BAT+", "single core", "2", "", "M8 lug", "M10 lug", 0.3),
    ("W003", "S1", "K0 main contactor", "BAT+", "single core", "2", "", "M10 lug", "M8 lug", 0.4),
    ("W004", "K0", "+48 V busbar", "BUS+", "single core", "2", "", "M8 lug", "M8 lug", 0.3),
    ("W005", "BT1 -", "shunt -> -48 V busbar", "BUS-", "single core", "2", "", "SurLok Plus 8 mm", "M8 lug", 0.6),
    ("W010-013", "busbar F2-F5 via K1", "VESC 1-4 B+/B-", "DRIVE", "2-core", "8", "40 A each", "M6 lug", "XT90 / lug", 1.4),
    ("W014-017", "VESC 1-4", "hub motor 1-4", "3-phase", "3x single + hall", "10 + 24", "", "MR60 / Deutsch DT06-6S", "motor leads", 1.2),
    ("W020-021", "busbar F6/F7 via K2", "FR5 DC controller L/R", "ARM PWR", "2-core", "10", "30 A each", "M6 lug", "controller terminal", 2.0),
    ("W030", "busbar F8", "PS1 48->24 V", "48 V", "2-core", "12", "20 A", "ferrule", "ferrule", 0.4),
    ("W031", "busbar F9", "PS2 48->12 V", "48 V", "2-core", "14", "10 A", "ferrule", "ferrule", 0.4),
    ("W040", "PS1 24 V block F11", "SR1 PNOZ s4 A1/A2", "24 V", "2-core", "18", "3 A", "ferrule", "ferrule", 0.3),
    ("W041", "SR1 13-14", "K1 coil", "SAFE OUT 1", "2-core", "18", "", "ferrule", "ferrule", 0.4),
    ("W042", "SR1 23-24", "K2 coil", "SAFE OUT 2", "2-core", "18", "", "ferrule", "ferrule", 0.4),
    ("W043", "SR1 S11-S12 chain", "ES1..ES4, WES1, SE1/SE2", "ESTOP CH1", "4-core shielded", "20", "", "M12 A-coded 4p", "M12 A-coded 4p", 7.0),
    ("W044", "SR1 S21-S22 chain", "ES1..ES4, WES1, SE1/SE2", "ESTOP CH2", "(same cable)", "20", "", "", "", 0.0),
    ("W050", "PS2 12 V F18", "Jetson DC in", "12 V", "2-core", "16", "8 A", "ferrule", "5.5x2.5 barrel (locking)", 0.5),
    ("W051", "PS2 12 V F19", "RUTX50", "12 V", "2-core", "20", "3 A", "ferrule", "4-pin Molex", 0.5),
    ("W060", "ETH SW1", "Livox Mid-360", "GbE + 24 V", "M12 X-coded + power", "Cat6A", "2 A", "M12 X 8p", "Livox M12 aviation", 2.5),
    ("W061-062", "ETH SW1", "FR5 L/R controller", "GbE", "Cat6A outdoor", "", "", "RJ45 IP67", "RJ45", 2.0),
    ("W070-071", "ZED Link Duo", "ZED X L/R", "GMSL2 + PoC", "Fakra coax 5 m", "", "", "Fakra Z", "Fakra Z", 5.0),
    ("W080-081", "Jetson USB3", "D405 L/R (through arm dress pack)", "USB3", "active USB3, 3 m", "", "", "USB-A locking", "USB-C screw lock", 3.0),
    ("W082-083", "PS1 24 V F15 + RS485", "EE L/R tool connector", "24 V + RS485 + ring light", "8-core shielded, hi-flex", "24", "3 A", "M12 A 8p", "M12 A 8p", 3.0),
    ("W084-085", "vacuum pump L/R", "EE suction cup", "vacuum", "PU tube 6/4 mm", "", "", "push-in", "push-in", 3.0),
    ("W090", "Teensy CAN1", "VESC 1-4 CAN", "CAN-FD", "2x2 twisted shielded, 120 ohm ends", "22", "", "Deutsch DTM-4", "JST-PH", 2.5),
    ("W091", "Teensy CAN2", "Orion BMS + dock charger", "CAN", "2x2 twisted shielded", "22", "", "Deutsch DTM-4", "Molex", 1.5),
    ("W100", "J1 dock contacts", "F21 -> K3 charge contactor", "CHG+", "single core", "4", "125 A", "M8 lug", "M8 lug", 1.2),
]


def harness():
    with open(os.path.join(HERE, "harness.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wire_id", "from", "to", "signal", "cable", "awg", "fuse", "connector_from", "connector_to", "length_m"])
        w.writerows(HARNESS)


if __name__ == "__main__":
    e01(); e02(); e03(); harness()
    print("schematics written")

"""Parametric CAD for the Agrobo AB-1 base, HM-1 harvester implement and EE-1 end-effector.

Run:  python cad/src/build.py
Writes STEP (assemblies + fabricated parts), STL (print parts + URDF meshes), DXF (laser-cut plates)
and a GLB of the full harvester for the web viewer / renders.
All dimensions come from params.py. CadQuery works in mm here; params are metres.
"""
import math, os, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from params import FIELD, WHEEL, BASE, ARM, MAST, TOTES, EE

ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT_STEP, OUT_STL, OUT_DXF = (os.path.join(ROOT, d) for d in ("step", "stl", "dxf"))
MESH = os.path.abspath(os.path.join(ROOT, "..", "urdf", "agrobo_description", "meshes"))
for d in (OUT_STEP, OUT_STL, OUT_DXF, MESH):
    os.makedirs(d, exist_ok=True)

mm = 1000.0
E = BASE["ext"] * mm  # 38.1 mm profile

C = dict(  # display colours
    alu=cq.Color(0.78, 0.80, 0.82), dark=cq.Color(0.16, 0.17, 0.18), green=cq.Color(0.20, 0.42, 0.25),
    tyre=cq.Color(0.08, 0.08, 0.08), rim=cq.Color(0.55, 0.56, 0.58), orange=cq.Color(0.93, 0.47, 0.12),
    white=cq.Color(0.93, 0.93, 0.91), red=cq.Color(0.80, 0.08, 0.06), tpu=cq.Color(0.10, 0.45, 0.70),
    yellow=cq.Color(0.95, 0.78, 0.10), glass=cq.Color(0.15, 0.20, 0.25), tote=cq.Color(0.15, 0.35, 0.62),
)


# ---------------------------------------------------------------------------------- primitives
def profile_1515(length, axis="x"):
    """80/20 1515-style 1.5 in T-slot profile (simplified: square, 4 slots, centre bore)."""
    s = E
    sk = cq.Workplane("XY").rect(s, s).extrude(length)
    slot_w, slot_d = 8.4, 6.0
    for ang in (0, 90, 180, 270):
        cut = (cq.Workplane("XY").rect(slot_w, slot_d * 2).extrude(length)
               .translate((0, s / 2, 0)).rotate((0, 0, 0), (0, 0, 1), ang))
        sk = sk.cut(cut)
    sk = sk.cut(cq.Workplane("XY").circle(5.0).extrude(length))
    if axis == "x":
        sk = sk.rotate((0, 0, 0), (0, 1, 0), 90)
    elif axis == "y":
        sk = sk.rotate((0, 0, 0), (1, 0, 0), -90)
    return sk


CUTS = []   # (length_mm) of every profile created while CUT_TAG is set


CUT_TAG = None


def bar(p0, p1):
    """1515 profile between two points that differ along one axis (mm)."""
    (x0, y0, z0), (x1, y1, z1) = p0, p1
    if CUT_TAG:
        CUTS.append((CUT_TAG, round(max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))))
    if abs(x1 - x0) > 1e-6:
        return profile_1515(abs(x1 - x0), "x").translate((min(x0, x1), y0, z0))
    if abs(y1 - y0) > 1e-6:
        return profile_1515(abs(y1 - y0), "y").translate((x0, min(y0, y1), z0))
    return profile_1515(abs(z1 - z0), "z").translate((x0, y0, min(z0, z1)))


def box(cx, cy, cz, lx, ly, lz):
    return cq.Workplane("XY").box(lx, ly, lz).translate((cx, cy, cz))


def cyl_y(cx, cy, cz, r, length):
    return cq.Workplane("XZ").circle(r).extrude(length / 2, both=True).translate((cx, cy, cz))


def cyl_z(cx, cy, cz, r, length):
    return cq.Workplane("XY").circle(r).extrude(length / 2, both=True).translate((cx, cy, cz))


# ---------------------------------------------------------------------------------- AB-1 base
def wheel_assembly():
    """20x8.00-10 turf tyre on a 10 in rim around an OZO hub motor. Built about the wheel origin, axis = y."""
    r, w = WHEEL["radius"] * mm, WHEEL["width"] * mm
    tyre = (cq.Workplane("XZ").circle(r).circle(r - 75).extrude(w / 2, both=True)
            .edges().fillet(28))
    # tread lugs
    for i in range(24):
        lug = box(0, 0, r - 4, 26, w * 0.86, 12).rotate((0, 0, 0), (0, 1, 0), i * 15)
        tyre = tyre.union(lug)
    rim = cq.Workplane("XZ").circle(r - 75).circle(r - 90).extrude(w * 0.42, both=True)
    hub = cq.Workplane("XZ").circle(r - 90).extrude(w * 0.30, both=True)
    for i in range(4):  # 4x100 bolt pattern studs
        a = math.radians(45 + 90 * i)
        hub = hub.union(cyl_y(50 * math.cos(a), w * 0.30, 50 * math.sin(a), 6, 14))
    shaft = cyl_y(0, -w * 0.30 - 45, 0, 15, 90)  # inboard fixed shaft
    return tyre, rim.union(hub), shaft


def base_frame():
    """Deck frame, legs, braces, axle plates. Returns dict of named solids (mm, robot frame)."""
    L, W = BASE["deck_length"] * mm, BASE["deck_width"] * mm
    zt = BASE["deck_top_z"] * mm
    zc = zt - E / 2                      # profile centreline
    yo = W / 2 - E / 2                   # outer rail centre
    yi = BASE["inner_rail_y"] * mm
    xl = BASE["leg_x"] * mm
    parts = []
    # outer + inner longitudinal rails
    for y in (yo, -yo, yi, -yi):
        parts.append(bar((-L / 2, y, zc), (L / 2, y, zc)))
    # cross members (between outer rails)
    for x in (-L / 2 + E / 2, -xl, -0.15 * mm, 0.15 * mm, xl, L / 2 - E / 2):
        for (ya, yb) in ((-yo + E / 2, -yi - E / 2), (-yi + E / 2, yi - E / 2), (yi + E / 2, yo - E / 2)):
            parts.append(bar((x, ya, zc), (x, yb, zc)))
    frame = parts[0]
    for p in parts[1:]:
        frame = frame.union(p)
    # legs: vertical 1515 at (+/-leg_x, +/-inner_rail_y) from deck underside to 200 mm
    legs = None
    leg_bot = 0.20 * mm
    for sx in (1, -1):
        for sy in (1, -1):
            leg = bar((sx * xl + sx * E, sy * yi, leg_bot), (sx * xl + sx * E, sy * yi, zt - E))
            # diagonal gusset plate (10 mm 6061) leg -> outer rail
            g = (cq.Workplane("YZ").polyline([(0, 0), (yo - yi, 0), (0, -160)]).close().extrude(10)
                 .translate((sx * xl + sx * E - 5, 0, zt - E)))
            if sy < 0:
                g = g.mirror("XZ")
            g = g.translate((0, sy * yi, 0))
            # axle plate: 10 mm plate carrying the hub-motor shaft clamp
            plate = box(sx * xl, sy * (yi + E / 2 + 5), 0.235 * mm, 160, 10, 150)
            clamp = cyl_y(sx * xl, sy * (yi + E / 2 + 22), WHEEL["radius"] * mm, 32, 34)
            unit = leg.union(g).union(plate).union(clamp)
            legs = unit if legs is None else legs.union(unit)
    # leg-to-plate tie: horizontal stub from leg to axle plate
    return frame, legs


def deck_plate():
    """3 mm 5052 aluminium deck plate, laser cut. Cut-outs for mast posts, cable pass-throughs, hatch."""
    L, W = BASE["deck_length"] * mm, BASE["deck_width"] * mm
    pl = cq.Workplane("XY").rect(L, W).extrude(3)
    for x in MAST["post_x"]:
        pl = pl.cut(cq.Workplane("XY").rect(78, 40).extrude(3).translate((x * mm, 0, 0)))
    pl = pl.cut(cq.Workplane("XY").rect(300, 200).extrude(3))                 # service hatch over enclosure
    for x in (-600, 600):
        pl = pl.cut(cq.Workplane("XY").circle(25).extrude(3).translate((x, 0, 0)))  # cable glands
    # perimeter bolt holes into T-slot (M8, 150 mm pitch)
    pts = [(x, s * (W / 2 - E / 2)) for x in range(-675, 676, 150) for s in (1, -1)]
    pl = pl.cut(cq.Workplane("XY").pushPoints(pts).circle(4.3).extrude(3))
    return pl


def axle_plate_2d():
    pl = cq.Workplane("XY").rect(160, 150).extrude(10)
    pl = pl.cut(cq.Workplane("XY").circle(15.5).extrude(10).translate((0, 19, 0)))         # shaft bore
    pl = pl.cut(cq.Workplane("XY").rect(31, 4).extrude(10).translate((0, 19 + 17, 0)))     # clamp slot
    pts = [(-60, -55), (60, -55), (-60, 55), (60, 55), (-19, -55), (19, -55)]
    return pl.cut(cq.Workplane("XY").pushPoints(pts).circle(4.3).extrude(10))


def keel_pack():
    k = BASE["keel"]
    l, w, h = k["length"] * mm, k["width"] * mm, k["height"] * mm
    body = box(0, 0, k["z_bottom"] * mm + h / 2, l, w, h).edges("|X").fillet(12)
    lid = box(0, 0, k["z_bottom"] * mm + h + 4, l - 20, w - 20, 8)
    # 4 hanger straps up to the inner rails
    zt = BASE["deck_top_z"] * mm - E
    hangers = None
    for x in (-l / 2 + 60, l / 2 - 60):
        for s in (1, -1):
            hng = box(x, s * (w / 2 + 3), (k["z_bottom"] * mm + h + zt) / 2 + 40, 50, 6, zt - k["z_bottom"] * mm - h + 80)
            hangers = hng if hangers is None else hangers.union(hng)
    conn = box(l / 2 + 15, 0, k["z_bottom"] * mm + h - 50, 30, 120, 60)       # Amphenol SurLok + CAN
    return body.union(lid), hangers, conn


def electronics_box():
    e = BASE["enclosure"]
    l, w, h = (v * mm for v in e["size"])
    zc = e["z_top"] * mm - h / 2
    body = box(0, 0, zc, l, w, h).edges("|Z").fillet(8)
    fins = None
    for i in range(14):
        f = box(-l / 2 + 40 + i * 37, 0, zc - h / 2 - 15, 4, w - 40, 30)
        fins = f if fins is None else fins.union(f)
    return body.union(fins)


def bumpers_and_safety():
    """Front/rear rubber safety-edge bumpers, 4 E-stop buttons, rear dock contacts, light tower base."""
    L, W = BASE["deck_length"] * mm, BASE["deck_width"] * mm
    zt = BASE["deck_top_z"] * mm
    bump = None
    for s in (1, -1):
        b = box(s * (L / 2 + 30), 0, zt - 120, 60, W - 40, 90).edges("|Y").fillet(25)
        bump = b if bump is None else bump.union(b)
        brk = box(s * (L / 2 + 5), 0, zt - 60, 20, W - 140, 60)
        bump = bump.union(brk)
    estops = None
    for sx in (1, -1):
        for sy in (1, -1):
            base_ = box(sx * (L / 2 - 60), sy * (W / 2 - 50), zt + 25, 70, 70, 50)
            btn = cyl_z(sx * (L / 2 - 60), sy * (W / 2 - 50), zt + 62, 22, 25)
            estops = (estops.union(base_) if estops is not None else base_)
            estops = estops.union(btn.translate((0, 0, 0)))
    contacts = None
    for y in (-110, 110):
        c = box(-L / 2 - 65, y, zt - 230, 14, 70, 120)
        contacts = c if contacts is None else contacts.union(c)
    return bump, estops, contacts


# ---------------------------------------------------------------------------------- HM-1 harvester
def mast():
    zt = BASE["deck_top_z"] * mm
    H = MAST["height"] * mm
    posts = None
    for x in MAST["post_x"]:
        for y in (-E / 2, E / 2):   # 1530 = two 1515 side by side
            p = bar((x * mm, y, zt), (x * mm, y, H - 60))
            posts = p if posts is None else posts.union(p)
    zarm = ARM["mount_z"] * mm
    yb = ARM["mount_y"] * mm
    # arm crossbeam: 2x 1515 along y at arm height, plus top sensor bar
    xs = [x * mm for x in MAST["post_x"]]
    beam = None
    for x in xs:
        for z in (zarm - 70, zarm + 70):
            b = bar((x + (E if x < 0 else -E), -yb + 15, z), (x + (E if x < 0 else -E), yb - 15, z))
            beam = b if beam is None else beam.union(b)
    zs = MAST["sensor_bar_z"] * mm
    for y in (-E / 2, E / 2):
        beam = beam.union(bar((xs[0] - 20, y, zs), (xs[1] + 20, y, zs)))
    beam = beam.union(bar((0, -330, zs + E), (0, 330, zs + E)))                    # antenna / camera bar
    # arm mounting plates (20 mm 6061, vertical, normal +/-y)
    plates = None
    for s in (1, -1):
        p = box(0, s * (yb - 10), zarm, 380, 20, 260)
        p = p.cut(cyl_y(0, s * (yb - 10), zarm, 45, 30))                             # cable bore
        plates = p if plates is None else plates.union(p)
    # lidar pedestal + top cap
    ped = cyl_z(0, 0, H - 40, 35, 80).union(box(0, 0, H - 80, 140, 100, 10))
    return posts, beam, plates, ped


def sensors():
    """ZED X stereo pair per side, Livox Mid-360 on top, 2 GNSS antennas, light tower, 4 LED floods."""
    zs = MAST["sensor_bar_z"] * mm
    H = MAST["height"] * mm
    out = {}
    cams = None
    for s in (1, -1):
        c = box(0, 0, 0, 40, 32, 46).union(box(0, 0, 0, 175, 30, 33).edges("|Y").fillet(14))  # ZED X 175x30x33
        c = c.rotate((0, 0, 0), (1, 0, 0), s * -20).translate((0, s * 300, zs - 45))
        cams = c if cams is None else cams.union(c)
    out["zedx"] = cams
    out["lidar"] = cyl_z(0, 0, H + 32, 32.5, 65)                                     # Mid-360: 65 dia x 65
    ants = None
    for y in (-300, 300):
        a = cyl_z(0, y, zs + E + 30, 75, 22).union(cyl_z(0, y, zs + E + 10, 12, 25))
        ants = a if ants is None else ants.union(a)
    out["gnss"] = ants
    tower = cyl_z(-100, 0, zs + 120, 25, 180)
    out["beacon"] = tower
    lights = None
    for x in (-140, 140):
        for s in (1, -1):
            l_ = box(x, s * 280, zs - 95, 90, 40, 70).rotate((x, s * 280, zs - 95), (x + 1, s * 280, zs - 95), s * -35)
            lights = l_ if lights is None else lights.union(l_)
    out["floods"] = lights
    brk = None
    for y in (-300, 300):
        b_ = box(0, y, zs + E / 2 - 30, 30, 30, 80)                                   # camera drop bracket
        b_ = b_.union(box(0, y * 0.9, zs - 60, 300, 20, 20))                        # flood light bar (behind the camera face)
        b_ = b_.union(box(0, y * 0.9, zs - 20, 20, 20, 90))
        brk = b_ if brk is None else brk.union(b_)
    out["brackets"] = brk
    # arm controllers (Fairino DC MINI, 245x180x45) on the posts
    ctl = None
    for x in MAST["post_x"]:
        c = box(x * mm + (60 if x > 0 else -60), 0, 820, 45, 180, 245)
        ctl = c if ctl is None else ctl.union(c)
    out["arm_ctrl"] = ctl
    return out


def totes():
    zt = BASE["deck_top_z"] * mm + 3
    lx, ly, h = (v * mm for v in TOTES["size"])
    out = None
    for x in TOTES["x"]:
        t = box(x * mm, 0, zt + h / 2, lx, ly, h).faces(">Z").shell(-4)
        # foam liner floor
        t = t.union(box(x * mm, 0, zt + 25, lx - 20, ly - 20, 40))
        out = t if out is None else out.union(t)
    return out


# ---------------------------------------------------------------------------------- arm (FR5-class) visuals per link
def arm_links():
    """Simplified FR5 link solids, each in its own URDF link frame (UR-style kinematics, metres -> mm)."""
    d1, a2, a3, d4, d5, d6 = (ARM[k] * mm for k in ("d1", "a2", "a3", "d4", "d5", "d6"))
    links = {}
    links["arm_base"] = cyl_z(0, 0, 45, 75, 90)
    links["shoulder"] = cyl_z(0, 0, 0, 62, 140).union(cyl_y(0, -20, 0, 62, 130))
    ua = (cq.Workplane("YZ").circle(46).extrude(-a2 * -1).translate((a2, 0, 135)))   # tube along -x
    ua = ua.union(cyl_z(0, 0, 70, 62, 140)).union(cyl_z(a2, 0, 70, 55, 140))
    links["upper_arm"] = ua
    fa = cq.Workplane("YZ").circle(38).extrude(-a3 * -1).translate((a3, 0, 20))
    fa = fa.union(cyl_z(0, 0, 50, 52, 100)).union(cyl_z(a3, 0, 30, 45, 90))
    links["forearm"] = fa
    links["wrist_1"] = cyl_z(0, 0, 0, 45, 90).union(cyl_y(0, -d5 / 2, 0, 42, d5))
    links["wrist_2"] = cyl_z(0, 0, 0, 45, 90).union(cyl_y(0, d6 / 2, 0, 42, d6))
    links["wrist_3"] = cyl_z(0, 0, -20, 42, 40)
    return links


# ---------------------------------------------------------------------------------- EE-1 end-effector
def ee_parts():
    """Peduncle-snap gripper. Built along +z from the tool flange (z = 0). Returns named solids (mm)."""
    R = EE["body_d"] * mm / 2
    Lb = EE["body_len"] * mm
    p = {}
    # ISO 9409-1-50-4-M6 adapter: dia 63 x 12, pilot 31.5 h7, 4x M6 on PCD 50, 2x dowel 6 mm
    ad = cq.Workplane("XY").circle(31.5).extrude(12)
    ad = ad.cut(cq.Workplane("XY").polarArray(25, 45, 360, 4).circle(3.3).extrude(12))
    ad = ad.cut(cq.Workplane("XY").circle(15.75).extrude(4))
    ad = ad.union(cq.Workplane("XY").circle(R).extrude(6).translate((0, 0, 12)))
    ad = ad.cut(cq.Workplane("XY").polarArray(38, 0, 360, 6).circle(2.2).extrude(6).translate((0, 0, 12)))
    p["flange_adapter"] = ad
    # sealed housing (MJF PA12, IP65 with O-ring grooves): holds Dynamixel XM430 + lead-screw ring
    hz = 18
    hs = cq.Workplane("XY").circle(R).extrude(Lb).translate((0, 0, hz))
    hs = hs.cut(cq.Workplane("XY").circle(R - 3).extrude(Lb - 6).translate((0, 0, hz + 3)))
    hs = hs.union(cq.Workplane("XY").rect(16, 40).extrude(30).translate((R + 4, 0, hz + 20)))   # cable gland boss
    hs = hs.edges(">Z or <Z").fillet(2)
    p["housing"] = hs
    p["servo_xm430"] = box(0, 0, hz + 3 + 23, 28.5, 46.5, 34)
    # front plate with 3 finger clevises
    fz = hz + Lb
    fp = cq.Workplane("XY").circle(R + 4).extrude(8).translate((0, 0, fz))
    fp = fp.cut(cq.Workplane("XY").circle(EE["cup_d"] * mm / 2 + 4).extrude(8).translate((0, 0, fz)))
    rc = 0.038 * mm
    for i in range(3):
        a = 90 + i * 120
        cl = box(rc, 0, fz + 14, 14, 30, 14).rotate((0, 0, 0), (0, 0, 1), a)
        fp = fp.union(cl)
    p["front_plate"] = fp
    # Fin-Ray fingers (TPU 95A): triangle truss, tip leaning to centre, 5 internal ribs
    fl, fw, ft = EE["finger_len"] * mm, EE["finger_w"] * mm, 20.0
    tri = cq.Workplane("XZ").polyline([(-ft / 2 - 6, 0), (ft / 2 + 6, 0), (0, fl)]).close().extrude(fw / 2, both=True)
    inner = (cq.Workplane("XZ").polyline([(-ft / 2 + 1, 5), (ft / 2 - 3, 5), (-1, fl - 14)]).close()
             .extrude(fw / 2 + 1, both=True))
    fin = tri.cut(inner)
    for k in range(1, 6):
        z = 5 + k * (fl - 19) / 6
        wfrac = 1 - z / fl
        fin = fin.union(box(0, 0, z, (ft + 12) * wfrac, fw, 2.2))
    fin = fin.union(box(0, 0, -3, 16, fw * 0.6, 8))                                   # pivot tab
    fingers = None
    for i in range(3):
        a = 90 + i * 120
        f = (fin.rotate((0, 0, 0), (0, 1, 0), -8)                                     # pre-closed 8 deg
             .translate((rc, 0, fz + 22)).rotate((0, 0, 0), (0, 0, 1), a))
        fingers = f if fingers is None else fingers.union(f)
    p["fingers"] = fingers
    p["finger_single"] = fin
    # suction: bellows cup (Piab BX40-class) on a 30 mm stroke plunger
    rod = EE["finger_len"] * mm + 22 - 15 - 21          # cup lip ~6 mm past the fingertips at rest
    cup = cq.Workplane("XY").circle(6).extrude(rod).translate((0, 0, fz))
    cup = cup.union(cq.Workplane("XY").circle(11).extrude(30).translate((0, 0, fz - 30)))   # actuator rod guide
    for k in range(3):
        cup = cup.union(cq.Workplane("XY").circle(EE["cup_d"] * mm / 2 - 4 * (2 - k)).extrude(7)
                        .edges().fillet(2.5).translate((0, 0, fz + rod + k * 7)))
    p["suction_cup"] = cup
    # D405 (42x42x23) on an angled bracket, looking at the grasp centre
    cam = box(0, 0, 0, 42, 23, 42).edges("|Y").fillet(4)
    cx, cz = EE["cam_x"] * mm, EE["cam_z"] * mm
    tilt = math.degrees(math.atan2(cx, EE["tcp_z"] * mm - cz))
    cam = cam.rotate((0, 0, 0), (0, 1, 0), -tilt).translate((cx, 0, cz))
    brk = box((R + cx) / 2 - 8, 0, cz - 10, cx - R + 10, 30, 12).union(box(R + 2, 0, cz - 25, 6, 30, 40))
    p["d405"] = cam
    p["cam_bracket"] = brk
    # LED ring light
    p["ring_light"] = (cq.Workplane("XY").circle(R + 2).circle(R - 10).extrude(5).translate((0, 0, fz + 8)))
    return p


# ---------------------------------------------------------------------------------- assembly
POSES = {  # render/demo pose: (tcp target in robot frame m, approach axis)
    "left": ((0.15, 0.70, 0.98), (0, 1, 0)),
    "right": ((-0.20, -0.68, 0.62), (0, -1, -0.35)),
}


def arm_chain_world(side, q=None):
    """Arm link solids placed by kin.fk (same chain as the URDF). Default q = IK solution for POSES[side]."""
    import numpy as np
    import kin
    if q is None:
        q, pe, ae = kin.ik(side, *POSES[side])
    frames = kin.fk(side, q)
    placed = []
    for name, M in zip(kin.LINKS, frames):
        M = M.copy(); M[:3, 3] *= mm
        placed.append((name, M))
    return arm_links(), placed


def to_loc(M):
    import numpy as np
    from OCP.gp import gp_Trsf
    t = gp_Trsf()
    t.SetValues(*M[0, :4], *M[1, :4], *M[2, :4])
    return cq.Location(t)


def build_harvester():
    assy = cq.Assembly(name="agrobo_HM1_harvester")
    frame, legs = base_frame()
    assy.add(frame, name="deck_frame", color=C["alu"])
    assy.add(legs, name="legs_and_axle_plates", color=C["alu"])
    assy.add(deck_plate().translate((0, 0, BASE["deck_top_z"] * mm)), name="deck_plate", color=C["green"])
    tyre, rimhub, shaft = wheel_assembly()
    for sx, nx in ((1, "f"), (-1, "r")):
        for sy, ny in ((1, "l"), (-1, "r")):
            loc = cq.Location(cq.Vector(sx * BASE["wheelbase"] / 2 * mm, sy * BASE["track"] / 2 * mm, WHEEL["radius"] * mm),
                              cq.Vector(0, 0, 1), 0 if sy > 0 else 180)
            assy.add(tyre, name=f"tyre_{nx}{ny}", loc=loc, color=C["tyre"])
            assy.add(rimhub, name=f"hub_motor_{nx}{ny}", loc=loc, color=C["rim"])
            assy.add(shaft, name=f"shaft_{nx}{ny}", loc=loc, color=C["dark"])
    body, hangers, conn = keel_pack()
    assy.add(body, name="battery_keel", color=C["dark"])
    assy.add(hangers, name="keel_hangers", color=C["alu"])
    assy.add(conn, name="battery_connector", color=C["orange"])
    assy.add(electronics_box(), name="electronics_enclosure", color=C["white"])
    bump, estops, contacts = bumpers_and_safety()
    assy.add(bump, name="bumpers", color=C["dark"])
    assy.add(estops, name="estops", color=C["red"])
    assy.add(contacts, name="dock_contacts", color=C["orange"])
    posts, beam, plates, ped = mast()
    assy.add(posts, name="mast_posts", color=C["alu"])
    assy.add(beam, name="mast_beams", color=C["alu"])
    assy.add(plates, name="arm_mount_plates", color=C["alu"])
    assy.add(ped, name="lidar_pedestal", color=C["alu"])
    for k, v in sensors().items():
        assy.add(v, name=k, color=dict(zedx=C["dark"], lidar=C["dark"], gnss=C["white"], beacon=C["yellow"],
                                       floods=C["dark"], arm_ctrl=C["dark"], brackets=C["alu"])[k])
    assy.add(totes(), name="totes", color=C["tote"])
    ee = ee_parts()
    for side in ("left", "right"):
        links, placed = arm_chain_world(side)
        for name, M in placed:
            col = C["white"] if name in ("upper_arm", "forearm") else C["dark"]
            assy.add(links[name], name=f"{side}_{name}", loc=to_loc(M), color=col)
        Mt = placed[-1][1]
        for k, v in ee.items():
            if k == "finger_single":
                continue
            col = dict(fingers=C["tpu"], suction_cup=C["orange"], d405=C["dark"], servo_xm430=C["dark"],
                       ring_light=C["white"]).get(k, C["alu"] if k != "housing" else C["green"])
            assy.add(v, name=f"{side}_ee_{k}", loc=to_loc(Mt), color=col)
    return assy


def build_hauler():
    """HL-1: same AB-1 base, no arms; 2-high rack carrying 8 totes on powered roller zones."""
    assy = cq.Assembly(name="agrobo_HL1_hauler")
    frame, legs = base_frame()
    assy.add(frame, name="deck_frame", color=C["alu"])
    assy.add(legs, name="legs_and_axle_plates", color=C["alu"])
    assy.add(deck_plate().translate((0, 0, BASE["deck_top_z"] * mm)), name="deck_plate", color=C["green"])
    tyre, rimhub, shaft = wheel_assembly()
    for sx in (1, -1):
        for sy in (1, -1):
            loc = cq.Location(cq.Vector(sx * BASE["wheelbase"] / 2 * mm, sy * BASE["track"] / 2 * mm, WHEEL["radius"] * mm),
                              cq.Vector(0, 0, 1), 0 if sy > 0 else 180)
            assy.add(tyre, name=f"tyre_{sx}_{sy}", loc=loc, color=C["tyre"])
            assy.add(rimhub, name=f"hub_{sx}_{sy}", loc=loc, color=C["rim"])
    body, hangers, conn = keel_pack()
    assy.add(body, name="battery_keel", color=C["dark"])
    assy.add(electronics_box(), name="electronics_enclosure", color=C["white"])
    bump, estops, contacts = bumpers_and_safety()
    assy.add(bump, name="bumpers", color=C["dark"]); assy.add(estops, name="estops", color=C["red"])
    zt = BASE["deck_top_z"] * mm
    lx, ly, h = (v * mm for v in TOTES["size"])
    rack = None
    for x in (-0.72, -0.24, 0.24, 0.72):
        for y in (-0.36, 0.36):
            p = bar((x * mm, y * mm, zt), (x * mm, y * mm, zt + 2 * h + 140))
            rack = p if rack is None else rack.union(p)
    for z in (zt + 30, zt + h + 100):
        for y in (-0.36, 0.36):
            rack = rack.union(bar((-0.74 * mm, y * mm, z), (0.74 * mm, y * mm, z)))
        for k in range(14):   # rollers along y (totes roll sideways)
            rack = rack.union(cyl_y((-0.70 + k * 0.108) * mm, 0, z + 25, 25, 0.68 * mm))
    assy.add(rack, name="tote_rack_rollers", color=C["alu"])
    for i, x in enumerate((-0.48, 0.0, 0.48)):
        for j, z in enumerate((zt + 55, zt + h + 125)):
            t = box(x * mm, 0, z + h / 2, lx * 0.92, ly, h).faces(">Z").shell(-4)
            assy.add(t, name=f"tote_{i}_{j}", color=C["tote"])
    posts = bar((0.70 * mm, 0, zt), (0.70 * mm, 0, zt + 2 * h + 300))
    assy.add(posts, name="sensor_post", color=C["alu"])
    for k, v in sensors().items():
        if k in ("lidar", "beacon"):
            assy.add(v.translate((0.70 * mm, 0, (zt + 2 * h + 300) - MAST["height"] * mm + 40)), name=k,
                     color=C["dark"] if k == "lidar" else C["yellow"])
    return assy


def export_stl(shape, path, tol=0.4):
    cq.exporters.export(shape, path, tolerance=tol, angularTolerance=0.2)


def write_cut_list():
    global CUT_TAG
    import collections, csv
    CUTS.clear()
    CUT_TAG = "AB-1 base frame + legs"; base_frame()
    CUT_TAG = "HM-1 mast (1530 = 2x 1515)"; mast()
    CUT_TAG = None
    cnt = collections.Counter(CUTS)
    with open(os.path.join(ROOT, "cut_list_1515.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["assembly", "length_mm", "qty", "ends", "note"])
        for (tag, L), q in sorted(cnt.items()):
            w.writerow([tag, L, q, "tap 5/16-18 both ends" if L < 800 else "anchor holes per drawing", "80/20 1515, clear anodised"])
        total = sum(L * q for (tag, L), q in cnt.items())
        w.writerow(["TOTAL", total, sum(cnt.values()), "", f"{total/1000:.1f} m of profile"])
    print("cut list:", total / 1000, "m")


def main():
    import numpy as np
    write_cut_list()
    # --- fabricated parts
    frame, legs = base_frame()
    dp = deck_plate()
    ap = axle_plate_2d()
    cq.exporters.export(dp, os.path.join(OUT_STEP, "AB1-201_deck_plate.step"))
    cq.exporters.export(dp.section(1.5), os.path.join(OUT_DXF, "AB1-201_deck_plate_3mm_5052.dxf"))
    cq.exporters.export(ap, os.path.join(OUT_STEP, "AB1-202_axle_plate.step"))
    cq.exporters.export(ap.section(5), os.path.join(OUT_DXF, "AB1-202_axle_plate_10mm_6061_x4.dxf"))
    amp = cq.Workplane("XZ").rect(380, 260).extrude(20)
    amp = amp.cut(cq.Workplane("XZ").circle(45).extrude(20))
    amp = amp.cut(cq.Workplane("XZ").polarArray(70, 0, 360, 4).circle(5.5).extrude(20))        # FR5 base: 4x M10? verify
    amp = amp.cut(cq.Workplane("XZ").pushPoints([(x, z) for x in (-170, 170) for z in (-110, -40, 40, 110)]).circle(4.3).extrude(20))
    cq.exporters.export(amp, os.path.join(OUT_STEP, "HM1-101_arm_mount_plate.step"))
    cq.exporters.export(amp.rotate((0, 0, 0), (1, 0, 0), 90).section(-10), os.path.join(OUT_DXF, "HM1-101_arm_mount_plate_20mm_6061_x2.dxf"))
    ee = ee_parts()
    for k, part_no in (("flange_adapter", "EE1-001"), ("housing", "EE1-002"), ("front_plate", "EE1-003"),
                       ("finger_single", "EE1-004"), ("cam_bracket", "EE1-005")):
        cq.exporters.export(ee[k], os.path.join(OUT_STEP, f"{part_no}_{k}.step"))
        export_stl(ee[k], os.path.join(OUT_STL, f"{part_no}_{k}.stl"), tol=0.05)
    # --- full assembly
    assy = build_harvester()
    assy.save(os.path.join(OUT_STEP, "HM1_harvester_full_assembly.step"))
    assy.save(os.path.join(ROOT, "renders_src_harvester.glb"))
    hl = build_hauler()
    hl.save(os.path.join(OUT_STEP, "HL1_hauler_full_assembly.step"))
    hl.save(os.path.join(ROOT, "renders_src_hauler.glb"))
    ee_assy = cq.Assembly(name="EE1_end_effector")
    for k, v in ee.items():
        if k != "finger_single":
            ee_assy.add(v, name=k, color=dict(fingers=C["tpu"], suction_cup=C["orange"], d405=C["dark"], servo_xm430=C["dark"],
                                              housing=C["green"], ring_light=C["white"]).get(k, C["alu"]))
    ee_assy.save(os.path.join(OUT_STEP, "EE1_end_effector_assembly.step"))
    ee_assy.save(os.path.join(ROOT, "renders_src_ee.glb"))

    # --- URDF meshes (metres, link frames)
    def mesh(shape, name, tol=1.0):
        export_stl(shape.val().scale(0.001) if hasattr(shape, "val") else shape, os.path.join(MESH, name), tol=tol / 1000)
    chassis = frame.union(legs).union(dp.translate((0, 0, BASE["deck_top_z"] * mm)))
    body, hangers, conn = keel_pack()
    chassis = chassis.union(body).union(hangers).union(electronics_box())
    bump, estops, contacts = bumpers_and_safety()
    chassis = chassis.union(bump).union(estops).union(contacts)
    mesh(chassis, "base_chassis.stl", 1.0)
    posts, beam, plates, ped = mast()
    ms = posts.union(beam).union(plates).union(ped)
    for v in sensors().values():
        ms = ms.union(v)
    mesh(ms, "harvester_mast.stl", 1.0)
    mesh(totes(), "harvester_totes.stl", 1.0)
    tyre, rimhub, shaft = wheel_assembly()
    mesh(tyre.union(rimhub), "wheel.stl", 1.0)
    for name, solid in arm_links().items():
        mesh(solid, f"arm_{name}.stl", 0.8)
    eebody = ee["flange_adapter"]
    for k in ("housing", "front_plate", "suction_cup", "d405", "cam_bracket", "ring_light"):
        eebody = eebody.union(ee[k])
    mesh(eebody, "ee_body.stl", 0.3)
    # single finger in its own joint frame (pivot at origin, finger along +z)
    mesh(ee["finger_single"], "ee_finger.stl", 0.3)
    print("CAD export done")


if __name__ == "__main__":
    main()

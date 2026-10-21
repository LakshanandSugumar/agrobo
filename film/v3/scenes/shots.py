"""Photoreal shots. Usage: python shots.py <shot> <f0> <f1> <spp> [w h]  (frames at 12 fps unless a still)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, lib, field
from mathutils import Vector, Matrix, Euler
OUT = os.environ.get('OUT', '/mnt/project-files/agrobo-film/v3/frames')
FPS = 12

def cam_path(cam, keys):
    for f, loc in keys: cam.location = loc; cam.keyframe_insert('location', frame=f)
    for fc in cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, 'fcurves') else []:
        for k in fc.keyframe_points: k.interpolation = 'BEZIER'

def obj_key(o, f, loc=None, rot=None):
    if loc is not None: o.location = loc; o.keyframe_insert('location', frame=f)
    if rot is not None: o.rotation_euler = rot; o.keyframe_insert('rotation_euler', frame=f)

# ---------------------------------------------------------------- dawn (0-7 s)
def shot_dawn():
    sc = bpy.context.scene; n = 7 * FPS
    sky = lib.world_sky3(elev=1.2, rot=90, strength=.5, aerosol=3.5, clouds=.55, cloud_tint=(1, .82, .66))
    sky.keyframe_insert('sun_elevation', frame=1); sky.sun_elevation = math.radians(4.5); sky.keyframe_insert('sun_elevation', frame=n)
    field.build3(rows=16, length=90, growth=.8, seed=3, tree_gap=25)
    sc.view_settings.exposure = .1; sc.view_settings.keyframe_insert('exposure', frame=1); sc.view_settings.exposure = -1.5; sc.view_settings.keyframe_insert('exposure', frame=n)
    cam, tgt = lib.camera(lens=40, loc=(-6, 0, .5), target=(60, 0, 1.6), fstop=2.2)
    cam.data.dof.focus_distance = 9; cam.data.dof.focus_object = None
    obj_key(cam, 1, (-6, 0, .42)); obj_key(cam, n, (-2.2, 0, .62))
    lib.shake(cam, .008, 30); lib.shake(tgt, .12, 40)
    lib.post(haze=(.9, .72, .55), haze_amt=.4, mist_start=25, mist_depth=450, bloom=.6)
    return n

# ---------------------------------------------------------------- desk with phone + watch (still)
def phone(name, screen_mat, coll=None):
    root = lib.link(bpy.data.objects.new(name, None), coll)
    frame = lib.mat_basic(name + '_ti', (.62, .55, .44), rough=.28, metal=1)
    glass = lib.mat_basic(name + '_glass', (.005, .005, .006), rough=.03, coat=1)
    b = lib.add_prim('cube', name + '_body', frame, coll, size=1); b.scale = (.0715, .1475, .0082); lib.bevel(b, .008, 6); b.parent = root
    s = lib.add_prim('cube', name + '_front', glass, coll, size=1, location=(0, 0, .0042)); s.scale = (.0695, .1455, .0004); lib.bevel(s, .007, 6); s.parent = root
    scr = lib.add_prim('plane', name + '_screen', screen_mat, coll, size=1, location=(0, 0, .00445)); scr.scale = (.0655, .1415, 1); scr.parent = root
    cm = lib.add_prim('cube', name + '_cam', glass, coll, size=1, location=(.018, .05, -.0055)); cm.scale = (.03, .03, .003); lib.bevel(cm, .006); cm.parent = root
    return root, scr

def watch(name, coll=None):
    root = lib.link(bpy.data.objects.new(name, None), coll)
    steel = lib.mat_basic(name + '_steel', (.75, .75, .76), rough=.12, metal=1); gold = lib.mat_basic(name + '_gold', (.95, .74, .38), rough=.15, metal=1)
    dial = lib.mat_basic(name + '_dial', (.01, .06, .035), rough=.25, coat=.6, metal=.3); crystal = lib.mat_basic(name + '_crystal', (1, 1, 1), rough=0, trans=1)
    case = lib.add_prim('cylinder', name + '_case', steel, coll, radius=.02, depth=.012, vertices=64); lib.bevel(case, .002, 4); case.parent = root
    bez = lib.add_prim('torus', name + '_bezel', gold, coll, major_radius=.0195, minor_radius=.0022, location=(0, 0, .006)); bez.parent = root
    d = lib.add_prim('cylinder', name + '_dial', dial, coll, radius=.0172, depth=.001, location=(0, 0, .0062), vertices=64); d.parent = root
    for k in range(12):
        a = k / 12 * 2 * math.pi
        m = lib.add_prim('cube', name + '_idx', gold, coll, size=1, location=(math.cos(a) * .0145, math.sin(a) * .0145, .0068), rotation=(0, 0, a)); m.scale = (.003, .0008, .0005); m.parent = root
    for L, wdt, a in ((.011, .0012, 1.0), (.0145, .0009, 2.6)):
        h = lib.add_prim('cube', name + '_hand', gold, coll, size=1, location=(math.cos(a) * L / 2, math.sin(a) * L / 2, .0072), rotation=(0, 0, a)); h.scale = (L, wdt, .0003); h.parent = root
    c = lib.add_prim('cylinder', name + '_crystal', crystal, coll, radius=.0175, depth=.0015, location=(0, 0, .0078), vertices=64); c.parent = root
    for s in (-1, 1):  # bracelet links
        for k in range(9):
            l = lib.add_prim('cube', name + '_link', steel if k % 2 else gold, coll, size=1, location=(0, s * (.024 + k * .0085), -.001 - k * k * .00035)); l.scale = (.022, .008, .004); lib.bevel(l, .0012, 2); l.parent = root
    cr = lib.add_prim('cylinder', name + '_crown', gold, coll, radius=.003, depth=.004, location=(.0215, 0, 0), rotation=(0, math.pi / 2, 0)); cr.parent = root
    return root

def wood(name='walnut'):
    m, nt, b = lib._mat(name)
    tc = nt.nodes.new('ShaderNodeNewGeometry'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (.25, 6, 1)
    nt.links.new(tc.outputs['Position'], mp.inputs['Vector'])
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.inputs['Scale'].default_value = 3; wv.inputs['Distortion'].default_value = 2.2; wv.inputs['Detail'].default_value = 10; wv.inputs['Detail Scale'].default_value = 1.5
    nt.links.new(mp.outputs[0], wv.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = (.035, .016, .008, 1); r.color_ramp.elements[1].color = (.12, .055, .025, 1)
    nt.links.new(wv.outputs['Fac'], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .28; b.inputs['Coat Weight'].default_value = .4; b.inputs['Coat Roughness'].default_value = .15
    return m

def screen_mat(name, color=(.02, .05, .035), strength=1.0):
    return lib.emissive(name, color, strength)

def shot_desk():
    sc = bpy.context.scene; lib.world_color((.004, .004, .004), 1)
    sc.view_settings.exposure = 0
    t = lib.add_prim('plane', 'desk', wood(), None, size=3)
    ph, scr = phone('phone', screen_mat('scr', (.015, .04, .03), 1.5)); ph.location = (0, 0, .0082 / 2)
    w = watch('watch'); w.location = (.16, .03, .007); w.rotation_euler = (0, 0, -.5)
    nb = lib.add_prim('cube', 'notebook', lib.mat_basic('leather', (.02, .016, .012), rough=.55), None, size=1, location=(-.2, .06, .009)); nb.scale = (.15, .21, .018); lib.bevel(nb, .006, 3); nb.rotation_euler = (0, 0, .12)
    pen = lib.add_prim('cylinder', 'pen', lib.mat_basic('penm', (.9, .72, .38), rough=.2, metal=1), None, radius=.0055, depth=.14, location=(-.11, -.02, .02), rotation=(math.pi / 2, 0, .2))
    cup = lib.add_prim('cylinder', 'cup', lib.mat_basic('cer', (.85, .83, .8), rough=.2, coat=.6), None, radius=.042, depth=.09, location=(-.06, .24, .045), vertices=48)
    # soft key light + rim
    k = bpy.data.lights.new('key', 'AREA'); k.energy = 60; k.size = .8; k.color = (1, .9, .78); ko = lib.link(bpy.data.objects.new('key', k)); ko.location = (-.6, -.5, .9); ko.rotation_euler = (math.radians(45), 0, math.radians(-50))
    r = bpy.data.lights.new('rim', 'AREA'); r.energy = 25; r.size = .5; r.color = (.75, .85, 1); ro = lib.link(bpy.data.objects.new('rim', r)); ro.location = (.7, .7, .5); ro.rotation_euler = (math.radians(60), 0, math.radians(135))
    cam, tgt = lib.camera(lens=55, loc=(.05, -.42, .3), target=(.03, .01, 0), fstop=2.0)
    cam.data.dof.focus_object = tgt
    return 1, {'screen': scr}

# ---------------------------------------------------------------- aerial farmland (still, ortho top-down)
def shot_aerial():
    sc = bpy.context.scene; lib.world_sky(elev=38, rot=200, strength=.9, aerosol=1)
    sc.view_settings.exposure = -3.0
    rnd = random.Random(26)
    # patchwork: 2400x1400 map px -> 240 x 140 m world (0.1 m/px); parcels follow the same jittered grid as the overlay
    cols, rows, x0, y0, cw, chh = 8, 5, 330, 260, 222, 176
    soil = lib.mat_soil('aerial_soil')
    g = lib.add_prim('plane', 'base', None, None, size=1, location=(120, -70, -.05)); g.scale = (600, 600, 1)
    crops = []
    for k in range(7):
        m, nt, b = lib._mat(f'crop{k}')
        pos = nt.nodes.new('ShaderNodeNewGeometry'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rnd.choice([0, math.pi / 2, .3]))
        nt.links.new(pos.outputs['Position'], mp.inputs['Vector'])
        wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = rnd.uniform(.8, 1.6); wv.inputs['Distortion'].default_value = .2; nt.links.new(mp.outputs[0], wv.inputs['Vector'])
        base = [(.03, .08, .015), (.06, .1, .02), (.12, .09, .045), (.16, .12, .06), (.025, .06, .012), (.08, .1, .025), (.2, .15, .08)][k]
        r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = (*[c * .6 for c in base], 1); r.color_ramp.elements[1].color = (*base, 1)
        nn = nt.nodes.new('ShaderNodeTexNoise'); nn.inputs['Scale'].default_value = .08
        nt.links.new(pos.outputs['Position'], nn.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = .6
        nt.links.new(wv.outputs['Fac'], r.inputs[0]); nt.links.new(r.outputs[0], mx.inputs[6]); nt.links.new(nn.outputs['Color'], mx.inputs[7])
        nt.links.new(mx.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .4; nt.links.new(wv.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
        crops.append(m)
    g.data.materials.append(crops[4])
    R = random.Random(26); pts = []
    for j in range(rows + 1):
        pts.append([])
        for i in range(cols + 1):
            pts[j].append((x0 + i * cw + ((R.random() - .5) * 70 if 0 < i < cols else 0), y0 + j * chh + ((R.random() - .5) * 56 if 0 < j < rows else 0)))
    import bmesh
    W2 = lambda p: Vector((p[0] * .1, -p[1] * .1, 0))
    for j in range(rows):
        for i in range(cols):
            bm = bmesh.new(); vs = [bm.verts.new(W2(p)) for p in (pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i])]
            bm.faces.new(vs); bmesh.ops.inset_region(bm, faces=bm.faces[:], thickness=.9)
            # keep only inner face
            o = lib.mesh_obj(f'parcel{j}_{i}', bm, crops[R.randrange(len(crops))])
            o.location.z = .02
    # roads along parcel edges + river
    road = lib.mat_basic('road', (.12, .11, .1), rough=.9)
    for j in (0, 2, 5):
        for i in range(cols):
            a, b = W2(pts[j][i]), W2(pts[j][i + 1]); m_ = (a + b) / 2; d = b - a
            o = lib.add_prim('plane', 'road', road, None, size=1, location=(m_.x, m_.y, .03), rotation=(0, 0, math.atan2(d.y, d.x))); o.scale = (d.length + 1, 1.4, 1)
    tree = lib.mat_leaf('atree', (.02, .05, .015), (.04, .08, .02))
    tex = bpy.data.textures.new('tn', 'CLOUDS'); tex.noise_scale = .5
    for k in range(170):
        j = R.randrange(rows + 1); i = R.randrange(cols); a, b = W2(pts[j][i]), W2(pts[j][i + 1]); p = a.lerp(b, R.random())
        o = lib.add_prim('ico_sphere', 'tr', tree, None, radius=R.uniform(.8, 1.7), location=(p.x + R.uniform(-1.5, 1.5), p.y + R.uniform(-1.5, 1.5), 1.2), subdivisions=3)
        dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tex; dm.strength = .5; lib.smooth(o)
    for k in range(5):  # farm buildings
        p = W2((R.uniform(400, 2000), R.uniform(300, 1100)))
        o = lib.add_prim('cube', 'barn', lib.mat_basic('roof', (.45, .45, .47), rough=.4, metal=.6), None, size=1, location=(p.x, p.y, 2)); o.scale = (R.uniform(5, 8), R.uniform(3, 5), 3); o.rotation_euler.z = R.uniform(0, 1)
    cd = bpy.data.cameras.new('ortho'); cd.type = 'ORTHO'; cd.ortho_scale = 240; cd.clip_end = 1000
    c = lib.link(bpy.data.objects.new('cam', cd)); c.location = (120, -70, 300); sc.camera = c
    return 1, {}

# ---------------------------------------------------------------- tilling (25-34 s)
def ground_till(name, xvar_default=-20):
    """Wild grass ground that becomes tilled soil where (|y|<1.4 and x<X) or y<-1.4. X is node 'X' value."""
    m, nt, b = lib._mat(name)
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    X = nt.nodes.new('ShaderNodeValue'); X.name = 'X'; X.outputs[0].default_value = xvar_default
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; nt.links.new(sep.outputs[0], lt.inputs[0]); nt.links.new(X.outputs[0], lt.inputs[1])
    ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; nt.links.new(sep.outputs[1], ab.inputs[0])
    ins = nt.nodes.new('ShaderNodeMath'); ins.operation = 'LESS_THAN'; nt.links.new(ab.outputs[0], ins.inputs[0]); ins.inputs[1].default_value = 1.45
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(lt.outputs[0], m1.inputs[0]); nt.links.new(ins.outputs[0], m1.inputs[1])
    left0 = nt.nodes.new('ShaderNodeMath'); left0.operation = 'LESS_THAN'; nt.links.new(sep.outputs[1], left0.inputs[0]); left0.inputs[1].default_value = -1.45
    left1 = nt.nodes.new('ShaderNodeMath'); left1.operation = 'GREATER_THAN'; nt.links.new(sep.outputs[1], left1.inputs[0]); left1.inputs[1].default_value = -16
    left = nt.nodes.new('ShaderNodeMath'); left.operation = 'MULTIPLY'; nt.links.new(left0.outputs[0], left.inputs[0]); nt.links.new(left1.outputs[0], left.inputs[1])
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; nt.links.new(m1.outputs[0], mx.inputs[0]); nt.links.new(left.outputs[0], mx.inputs[1])
    # tilled colour + furrows (bands across y)
    soilc, n1 = lib.noise_color(nt, 1.2, (.045, .03, .02), (.11, .07, .045), coord=geo.outputs['Position'])
    grassc, n2 = lib.noise_color(nt, .7, (.025, .045, .012), (.09, .1, .035), coord=geo.outputs['Position'])
    col = nt.nodes.new('ShaderNodeMix'); col.data_type = 'RGBA'; nt.links.new(mx.outputs[0], col.inputs['Factor']); nt.links.new(grassc.outputs[0], col.inputs[6]); nt.links.new(soilc.outputs[0], col.inputs[7])
    nt.links.new(col.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .93
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.pi / 2); nt.links.new(geo.outputs['Position'], mp.inputs['Vector'])
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 3.3; wv.inputs['Distortion'].default_value = 1.5; wv.inputs['Detail'].default_value = 4; nt.links.new(mp.outputs[0], wv.inputs['Vector'])
    cl = nt.nodes.new('ShaderNodeTexNoise'); cl.inputs['Scale'].default_value = 22; cl.inputs['Detail'].default_value = 10; nt.links.new(geo.outputs['Position'], cl.inputs['Vector'])
    h = nt.nodes.new('ShaderNodeMath'); h.operation = 'ADD'; nt.links.new(wv.outputs['Fac'], h.inputs[0]); nt.links.new(cl.outputs['Fac'], h.inputs[1])
    hm = nt.nodes.new('ShaderNodeMath'); hm.operation = 'MULTIPLY'; nt.links.new(h.outputs[0], hm.inputs[0]); nt.links.new(mx.outputs[0], hm.inputs[1])
    g2 = nt.nodes.new('ShaderNodeMath'); g2.operation = 'MULTIPLY'; nt.links.new(n2.outputs['Fac'], g2.inputs[0]); g2.inputs[1].default_value = .3
    hh = nt.nodes.new('ShaderNodeMath'); hh.operation = 'ADD'; nt.links.new(hm.outputs[0], hh.inputs[0]); nt.links.new(g2.outputs[0], hh.inputs[1])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .9; bp.inputs['Distance'].default_value = .06; nt.links.new(hh.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m, X

def shot_till():
    sc = bpy.context.scene; n = 9 * FPS
    lib.world_sky3(elev=11, rot=150, strength=.5, aerosol=2.2, clouds=.5); sc.view_settings.exposure = -1.2
    gm, X = ground_till('till')
    g = lib.add_prim('plane', 'ground', gm, None, size=1); g.scale = (600, 600, 1)
    u = lib.ugv('ugv', tool='tiller')
    x_start, x_end = -9, 9
    for f in range(1, n + 1, 3):
        x = x_start + (x_end - x_start) * (f - 1) / (n - 1)
        u.location = (x, 0, .02); u.keyframe_insert('location', frame=f)
        X.outputs[0].default_value = x - 1.15; X.outputs[0].keyframe_insert('default_value', frame=f)
    # grass tufts and weeds on the wild ground; tufts in the working strip vanish as the tiller passes
    R = random.Random(9); grass = lib.mat_leaf('grass', (.04, .08, .015), (.1, .15, .04)); dry = lib.mat_leaf('dry', (.12, .11, .05), (.2, .17, .08))
    tuft_coll = bpy.data.collections.new('tuftlib'); sc.collection.children.link(tuft_coll); bpy.context.view_layer.layer_collection.children['tuftlib'].exclude = True
    import bmesh
    tufts = []
    for v in range(4):
        c = bpy.data.collections.new(f'tuft{v}'); tuft_coll.children.link(c); bm = bmesh.new()
        for k in range(45):
            a = R.uniform(0, 6.28); d = Vector((math.cos(a) * R.uniform(.15, .6), math.sin(a) * R.uniform(.15, .6), 1)).normalized()
            lib.leaflet(bm, Vector((math.cos(a) * .04, math.sin(a) * .04, 0)), d, R.uniform(.18, .5), .009, R.uniform(.03, .12), up=Vector((1, 0, 0)), segs=4)
        lib.mesh_obj(f'tuftm{v}', bm, grass if v % 2 else dry, c); tufts.append(c)
    fld = bpy.data.collections.new('tufts'); sc.collection.children.link(fld)
    for k in range(4200):
        x = R.uniform(-16, 26); y = R.uniform(-1.45, 14) if k < 3600 else R.uniform(-40, -16)
        inst = lib.instance_collection(tufts[R.randrange(4)], 'tf', (x, y, 0), R.uniform(0, 6.28), R.uniform(.6, 1.4), fld)
        if abs(y) < 1.45:
            tf = 1 + (x + 1.15 - x_start) / (x_end - x_start) * (n - 1)
            if tf <= 1: inst.hide_render = True
            elif tf < n:
                inst.hide_render = False; inst.keyframe_insert('hide_render', frame=int(tf)); inst.hide_render = True; inst.keyframe_insert('hide_render', frame=int(tf) + 1)
    # clods on tilled strips
    clod = lib.mat_soil('clod')
    for k in range(500):
        x = R.uniform(-14, 22); y = R.uniform(-9, 1.4)
        if y > -1.45 and x > x_end: continue
        o = lib.add_prim('ico_sphere', 'cl', clod, None, radius=R.uniform(.02, .06), location=(x, y, 0), subdivisions=1); o.scale = (1, 1, .6)
        if y > -1.45:
            tf = 1 + (x + 1.15 - x_start) / (x_end - x_start) * (n - 1)
            if tf > 1 and tf < n:
                o.hide_render = True; o.keyframe_insert('hide_render', frame=1); o.keyframe_insert('hide_render', frame=int(tf)); o.hide_render = False; o.keyframe_insert('hide_render', frame=int(tf) + 1)
            elif tf >= n: o.hide_render = True
    # distant hedgerows / copses (card trees)
    tl = bpy.data.collections.new('treeline'); sc.collection.children.link(tl)
    field.tree_lines(tl, R, near=70, far=150, count=140, swap=True)
    cam, tgt = lib.camera(lens=50, loc=(14, 5.5, 1.4), target=(0, 0, .5), fstop=3.2)
    tgt.parent = None
    for f in range(1, n + 1, 3):
        x = x_start + (x_end - x_start) * (f - 1) / (n - 1)
        tgt.location = (x + .4, 0, .55); tgt.keyframe_insert('location', frame=f)
        cam.location = (x + 9 - 3 * (f / n), 5.2 - 1.2 * (f / n), 1.25); cam.keyframe_insert('location', frame=f)
    lib.shake(cam, .01, 26); lib.shake(tgt, .02, 34)
    lib.post(haze=(.45, .5, .58), haze_amt=.3, mist_start=20, mist_depth=350, bloom=.4)
    return n

# ---------------------------------------------------------------- drone + laser weeding (34-46 s)
def shot_cultivate():
    sc = bpy.context.scene; n = 12 * FPS
    lib.world_sky3(elev=17, rot=300, strength=.55, aerosol=2.2, clouds=.5); sc.view_settings.exposure = -1.4
    field.build3(rows=16, length=70, growth=1.0, fruit=3, ripe=.2, seed=5)
    R = random.Random(4)
    u = lib.ugv('laser', tool='laser'); y_lane = 0.0
    weedm = lib.mat_leaf('weed', (.15, .2, .04), (.28, .3, .07)); burnt = lib.mat_basic('burnt', (.02, .015, .01), rough=.9)
    beam = lib.emissive('beam', (1, .12, .04), 400)
    import bmesh
    zaps = []
    for k in range(9):
        x = 6 + k * 2.6 + R.uniform(-.3, .3); y = y_lane + R.choice([-.42, .42]); bm = bmesh.new()
        for j in range(7):
            a = j / 7 * 6.28; lib.leaflet(bm, Vector((0, 0, 0)), Vector((math.cos(a), math.sin(a), .5)), .07, .03, .02, segs=3)
        w = lib.mesh_obj(f'weed{k}', bm, weedm); w.location = (x, y, .0)
        zaps.append((x, y, w))
    # UGV drives the furrow (path between beds at y=0) left to right
    x0, x1 = 2, 30
    def ux(f): return x0 + (x1 - x0) * (f - 1) / (n - 1)
    for f in range(1, n + 1, 3): u.location = (ux(f), 0, .0); u.keyframe_insert('location', frame=f)
    u.scale = (.62, .62, .62)
    for (x, y, w) in zaps:
        fz = int(1 + (x - .62 * .95 - x0) / (x1 - x0) * (n - 1))
        if fz < 2 or fz > n - 4: continue
        bo = lib.add_prim('cylinder', 'beam', beam, None, radius=.006, depth=1, vertices=8)
        hx, hy, hz = x - .2, 0, .2
        d = Vector((x, y, .03)) - Vector((hx, hy, hz)); bo.location = (Vector((hx, hy, hz)) + Vector((x, y, .03))) / 2; bo.scale = (1, 1, d.length)
        bo.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        bo.hide_render = True; bo.keyframe_insert('hide_render', frame=1); bo.keyframe_insert('hide_render', frame=fz - 1)
        bo.hide_render = False; bo.keyframe_insert('hide_render', frame=fz); bo.keyframe_insert('hide_render', frame=fz + 2); bo.hide_render = True; bo.keyframe_insert('hide_render', frame=fz + 3)
        L = bpy.data.lights.new('zap', 'POINT'); L.color = (1, .3, .1); L.shadow_soft_size = .02; lo = lib.link(bpy.data.objects.new('zap', L)); lo.location = (x, y, .08)
        L.energy = 0; L.keyframe_insert('energy', frame=fz - 1); L.energy = 60; L.keyframe_insert('energy', frame=fz); L.keyframe_insert('energy', frame=fz + 2); L.energy = 0; L.keyframe_insert('energy', frame=fz + 3)
        w.data.materials[0] = weedm; w.keyframe_insert('scale', frame=fz + 2); w.scale = (.6, .6, .3); w.keyframe_insert('scale', frame=fz + 6)
        b2 = w.copy(); b2.data = w.data.copy(); b2.data.materials[0] = burnt; lib.link(b2); b2.hide_render = True; b2.keyframe_insert('hide_render', frame=fz + 2); b2.hide_render = False; b2.keyframe_insert('hide_render', frame=fz + 3)
        w.hide_render = False; w.keyframe_insert('hide_render', frame=fz + 2); w.hide_render = True; w.keyframe_insert('hide_render', frame=fz + 3)
    dr = drone('drone')
    for f in range(1, n + 1, 3):
        t = (f - 1) / (n - 1); dr.location = (-2 + 34 * t, 3.2 - 1.5 * t, 4.2 + .15 * math.sin(t * 9)); dr.rotation_euler = (0, .12, -.05); dr.keyframe_insert('location', frame=f); dr.keyframe_insert('rotation_euler', frame=f)
    cam, tgt = lib.camera(lens=35, loc=(-6, 6, 7.5), target=(4, 0, 1), fstop=4)
    for f in range(1, n + 1, 3):
        t = lib.smoothstep((f - 1) / (n - 1))
        cam.location = (lerp(-7, ux(f) - 4.2, t), lerp(7, 2.4, t), lerp(8, 1.2, t)); cam.keyframe_insert('location', frame=f)
        dl = dr.location.copy() if False else Vector((-2 + 34 * (f - 1) / (n - 1), 3.2 - 1.5 * (f - 1) / (n - 1), 4.2))
        tgt.location = Vector((dl.x, dl.y, dl.z)).lerp(Vector((ux(f) + 1.0, 0, .3)), t); tgt.keyframe_insert('location', frame=f)
    lib.shake(cam, .03, 40); lib.shake(tgt, .03, 40)
    lib.post(haze=(.42, .47, .55), haze_amt=.28, mist_start=30, mist_depth=500, bloom=.4)
    return n

def drone(name): return lib.drone(name)
def lerp(a, b, t): return a + (b - a) * t

# ---------------------------------------------------------------- harvest macro (46-56 s)
def shot_harvest():
    sc = bpy.context.scene; n = 10 * FPS
    lib.world_sky3(elev=9, rot=95, strength=.6, aerosol=2.6, clouds=.5); sc.view_settings.exposure = -1.0
    field.build3(rows=10, length=30, growth=1.15, fruit=4, ripe=.9, seed=8, skip=lambda x, y: -1.3 < y < -.3 and 1.5 < x < 6.5)
    # move generated field away so the hero vine sits in a furrow with plants behind
    R = random.Random(2)
    stemm = lib.mat_stem3('hstem'); leafm = [lib.mat_leaf_tex(f'hleaf{k}', k) for k in range(3)]
    red = lib.mat_tomato3('hred', 1); green = lib.mat_tomato3('hgreen', 0); orange = lib.mat_tomato3('hor', .5)
    H = Vector((4.0, .0, .78))  # hero truss anchor (in the furrow between beds at y=0)
    # truss stem from above
    import bmesh
    bm = bmesh.new(); pts = [H + Vector((0, 0, .35)), H + Vector((.004, 0, .26)), H + Vector((.01, 0, .18)), H + Vector((.02, 0, .11)), H + Vector((.03, 0, .06)), H + Vector((.045, 0, .02)), H + Vector((.06, 0, 0))]
    lib.tube(bm, pts, .0055, .0042, 10)
    lib.mesh_obj('truss', bm, stemm)
    fruits = []
    spots = [(.0, 0, -.07, red, .036), (.08, .03, -.06, orange, .032), (.11, -.035, -.09, green, .03), (.05, .055, -.12, green, .028), (.14, .01, -.13, green, .026)]
    for i, (dx, dy, dz, m, r) in enumerate(spots):
        o = lib.tomato_obj(f'fruit{i}', r, m, stemm, H + Vector((dx, dy, dz)), seed=40 + i)
        fruits.append(o)
        if True:
            top = o.location + Vector((0, 0, r * .8)); src = H + Vector((.04, 0, 0)); d = top - src
            bmp = bmesh.new(); kn = src.lerp(top, .45) + Vector((0, 0, .012)); pts_ = [src, src.lerp(kn, .5) + Vector((0, 0, .004)), kn, kn.lerp(top, .5) + Vector((0, 0, .006)), top]
            lib.tube(bmp, pts_, .0026, .0019, 8); bmesh.ops.create_uvsphere(bmp, u_segments=8, v_segments=6, radius=.0034, matrix=Matrix.Translation(kn))
            pd = lib.mesh_obj(f'ped{i}', bmp, stemm)
            if i == 0: pd.hide_render = False; pd.keyframe_insert('hide_render', frame=63); pd.hide_render = True; pd.keyframe_insert('hide_render', frame=64)
    # surrounding leaves near camera for depth
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    for k in range(16):
        b0 = H + Vector((R.uniform(-.1, .5), R.uniform(.02, .3), R.uniform(-.15, .38)))
        ll = R.uniform(.09, .16)
        lib.leaflet_uv(bm, uvl, b0, Vector((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-.2, .4))), ll, ll * .62, ll * .2, cup=.25, twist=R.uniform(-.5, .5), mi=k % 3)
    hl = lib.mesh_obj('hleaves', bm, None)
    for m_ in leafm: hl.data.materials.append(m_)
    # cobot arm: white shells, graphite joints, gold rings, soft two-finger gripper
    white = lib.mat_paint3('arm_white', (.72, .72, .7), rough=.36, dust=.25, ao=False); graph = lib.mat_paint3('arm_graph', (.025, .027, .03), rough=.4, dust=.2, ao=False)
    gold = lib.mat_basic('arm_gold', (.9, .7, .36), rough=.2, metal=1); sil = lib.mat_basic('silicone', (.03, .03, .033), rough=.65)
    lens = lib.mat_basic('arm_lens', (.005, .005, .006), rough=.02, coat=1)
    B = H + Vector((-.62, -.22, -.62)); L1, L2 = .52, .46
    def capsule(name, r, L, mat):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=r, radius2=r * .88, depth=L, matrix=Matrix.Translation((0, 0, L / 2)))
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r, matrix=Matrix.Translation((0, 0, 0)))
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r * .88, matrix=Matrix.Translation((0, 0, L)))
        return lib.mesh_obj(name, bm, mat)
    def joint(name, r, w):
        root = lib.link(bpy.data.objects.new(name, None))
        c = lib.add_prim('cylinder', name + 'c', graph, None, radius=r, depth=w, vertices=48); lib.bevel(c, .006, 3); c.parent = root
        g = lib.add_prim('cylinder', name + 'g', gold, None, radius=r * 1.02, depth=w * .12, vertices=48); g.parent = root
        cap = lib.add_prim('cylinder', name + 'w', white, None, radius=r * .7, depth=w * 1.04, vertices=48); cap.parent = root
        return root
    base = lib.add_prim('cylinder', 'abase', white, None, radius=.08, depth=.14, location=B - Vector((0, 0, .09)), vertices=48); lib.bevel(base, .01, 3)
    bring = lib.add_prim('cylinder', 'abring', gold, None, radius=.082, depth=.012, location=B - Vector((0, 0, .03)), vertices=48)
    lk1, lk2 = capsule('lk1', .042, L1, white), capsule('lk2', .034, L2, white)
    jS, jE = joint('jS', .058, .12), joint('jE', .048, .1)
    wrist = lib.link(bpy.data.objects.new('wrist', None))
    wr = lib.add_prim('cylinder', 'wr', graph, None, radius=.036, depth=.07, location=(0, 0, .035), vertices=48); wr.parent = wrist
    wg = lib.add_prim('cylinder', 'wg', gold, None, radius=.037, depth=.008, location=(0, 0, .072), vertices=48); wg.parent = wrist
    pm = lib.add_prim('cylinder', 'palm', white, None, radius=.03, depth=.04, location=(0, 0, .095), vertices=48); pm.parent = wrist
    cbox = lib.add_prim('cube', 'wcam', graph, None, size=1, location=(0, -.04, .06)); cbox.scale = (.03, .02, .03); cbox.parent = wrist
    cl = lib.add_prim('cylinder', 'wlens', lens, None, radius=.007, depth=.006, location=(0, -.051, .068), rotation=(math.pi / 2, 0, 0)); cl.parent = wrist
    fingers = []
    for s_ in (-1, 1):
        fr = lib.link(bpy.data.objects.new(f'fing{s_}', None)); fr.parent = wrist
        a1 = capsule(f'fa{s_}', .008, .05, graph); a1.parent = fr; a1.rotation_euler = (s_ * -.5, 0, 0)
        a2 = capsule(f'fb{s_}', .007, .055, sil); a2.parent = fr; a2.location = (0, s_ * .024, .044); a2.rotation_euler = (s_ * .35, 0, 0)
        fingers.append((fr, s_))
    def ik(P):
        d = P - B; dist = min(d.length, L1 + L2 - .001); dirn = d.normalized()
        a_ = math.acos(max(-1, min(1, (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist))))
        axis = dirn.cross(Vector((0, 0, 1))).normalized()
        return B + (Matrix.Rotation(-a_, 3, axis) @ dirn) * L1, axis
    def aim(o, a_, b_):
        o.location = a_; o.rotation_euler = (b_ - a_).to_track_quat('Z', 'Y').to_euler()
    tgt_fruit = fruits[0]; T0 = tgt_fruit.location.copy(); crate_p = H + Vector((-.32, -.28, -.6))
    APP = T0 + Vector((-.13, 0, 0)); REST = H + Vector((-.45, -.12, -.1)); PULL = APP + Vector((-.07, 0, -.015))
    def grip(t):
        if t < 2.4: return REST + Vector((0, 0, .012 * math.sin(t * 2))), 0
        if t < 4.4: return REST.lerp(APP, lib.smoothstep((t - 2.4) / 2)), 0
        if t < 4.9: return APP, 0
        if t < 5.5: return APP.lerp(PULL, lib.smoothstep((t - 4.9) / .6)), .6 * math.sin(math.pi * (t - 4.9) / .6)
        return PULL.lerp(crate_p + Vector((0, 0, .22)), lib.smoothstep((t - 5.5) / 2)), 0
    def spread(t):
        if t < 4.4: return 1.0
        if t < 4.9: return lerp(1.0, .55, (t - 4.4) / .5)
        if t < 7.6: return .55
        return lerp(.55, 1.0, min(1, (t - 7.6) / .4))
    crate = lib.add_prim('cube', 'crate', lib.mat_basic('crate', (.03, .03, .03), rough=.5), None, size=1, location=crate_p); crate.scale = (.4, .3, .14); lib.bevel(crate, .01)
    for k in range(10):
        lib.tomato_obj(f'cr{k}', .034, red, stemm, crate_p + Vector(((k % 5) * .07 - .14, (k // 5) * .08 - .04, .09)), seed=70 + k)
    for f in range(1, n + 1):
        t = (f - 1) / FPS; P, roll = grip(t)
        dirw = Vector((1, 0, 0)) if t < 5.5 else Vector((1, 0, 0)).lerp(Vector((0, 0, -1)), lib.smoothstep((t - 5.5) / 2)).normalized()
        W = P - dirw * .1; E, axis = ik(W)
        aim(lk1, B, E); aim(lk2, E, W)
        for j, p_ in ((jS, B), (jE, E)): j.location = p_; j.rotation_euler = axis.to_track_quat('Z', 'Y').to_euler()
        wrist.location = W; q = dirw.to_track_quat('Z', 'Y'); wrist.rotation_euler = (q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, 'Z')).to_euler()
        sp = spread(t)
        for fr, s_ in fingers: fr.location = (0, s_ * .012 * sp, .11); fr.rotation_euler = (s_ * -.35 * (sp - .55), 0, 0)
        for o in (lk1, lk2, jS, jE, wrist): o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)
        for fr, s_ in fingers: fr.keyframe_insert('location', frame=f); fr.keyframe_insert('rotation_euler', frame=f)
        if 4.9 <= t < 7.7: tgt_fruit.location = P + dirw * .035
        elif t >= 7.7: tgt_fruit.location = crate_p + Vector((0, .02, .1 + max(0, .12 - (t - 7.7) * .8)))
        else: tgt_fruit.location = T0
        tgt_fruit.keyframe_insert('location', frame=f)
    cam, tgt = lib.camera(lens=85, loc=(H.x + .2, H.y - 1.25, H.z + .12), target=H + Vector((-.05, 0, -.1)), fstop=2.0)
    cam.data.dof.focus_object = tgt
    for f in (1, n): cam.location = (H.x + .2 - .08 * (f / n), H.y - 1.25 + .12 * (f / n), H.z + .12); cam.keyframe_insert('location', frame=f)
    lib.shake(cam, .004, 24)
    lib.post(haze=(.66, .7, .76), haze_amt=.3, mist_start=10, mist_depth=200, bloom=.5)
    return n

# ---------------------------------------------------------------- packhouse conveyor (56-66 s)
def shot_pack():
    sc = bpy.context.scene; n = 10 * FPS; lib.world_hdri('warehouse', .35); sc.view_settings.exposure = -.3
    R = random.Random(6)
    floor = lib.add_prim('plane', 'floor', lib.mat_basic('concrete', (.12, .12, .12), rough=.6), None, size=40)
    frame_m = lib.mat_paint3('ss', (.62, .62, .64), rough=.28, dust=.15, metal=1, ao=False); frame_m.node_tree.nodes['Principled BSDF'].inputs['Anisotropic'].default_value = .7
    belt = lib.mat_paint3('belt', (.02, .02, .022), rough=.6, dust=.35, ao=False)
    for y in (-.35, .35):
        r = lib.add_prim('cube', 'rail', frame_m, None, size=1, location=(0, y, .85)); r.scale = (14, .04, .1)
    b = lib.add_prim('cube', 'belt', belt, None, size=1, location=(0, 0, .86)); b.scale = (14, .66, .02)
    for x in range(-7, 8):
        lg = lib.add_prim('cube', 'leg', frame_m, None, size=1, location=(x, -.33, .42)); lg.scale = (.04, .04, .85)
        lg = lib.add_prim('cube', 'leg', frame_m, None, size=1, location=(x, .33, .42)); lg.scale = (.04, .04, .85)
    # scanner arch
    arch = lib.mat_basic('arch', (.03, .03, .035), rough=.3, coat=.6)
    for y in (-.45, .45):
        p = lib.add_prim('cube', 'post', arch, None, size=1, location=(1.1, y, 1.2)); p.scale = (.1, .05, .8); lib.bevel(p, .01)
    top = lib.add_prim('cube', 'top', arch, None, size=1, location=(1.1, 0, 1.62)); top.scale = (.14, 1.0, .1); lib.bevel(top, .01)
    # back wall with warm windows + pendant lamps for bokeh, second line behind
    wall = lib.add_prim('plane', 'wall', lib.mat_basic('wallm', (.18, .18, .19), rough=.7), None, size=1, location=(0, 5, 2), rotation=(math.pi / 2, 0, 0)); wall.scale = (30, 6, 1)
    win = lib.emissive('win', (1, .85, .65), 6)
    for x in range(-6, 7, 2):
        w_ = lib.add_prim('plane', 'win', win, None, size=1, location=(x, 4.98, 2.3), rotation=(math.pi / 2, 0, 0)); w_.scale = (1.2, 1.4, 1)
    lamp = lib.emissive('lamp', (1, .9, .75), 30)
    for x in range(-5, 6, 2):
        for yy in (1.5, 3.2):
            lib.add_prim('cylinder', 'pend', lamp, None, radius=.18, depth=.02, location=(x, yy, 2.8), vertices=32)
    b2 = lib.add_prim('cube', 'belt2', belt, None, size=1, location=(0, 2.4, .86)); b2.scale = (14, .66, .05)
    led = lib.emissive('led', (.85, .9, 1), 40)
    s = lib.add_prim('cube', 'scanbar', led, None, size=1, location=(1.1, 0, 1.565)); s.scale = (.03, .8, .01)
    gold = lib.mat_basic('ggold', (.9, .7, .36), rough=.2, metal=1); gs = lib.add_prim('cube', 'gstripe', gold, None, size=1, location=(1.1 - .071, 0, 1.62)); gs.scale = (.002, .9, .02)
    spec = []
    for k, c in enumerate([(.5, .1, 1), (.1, .3, 1), (.1, .9, .8), (.2, 1, .2), (1, .9, .1), (1, .4, .05), (1, .05, .05)]):
        o = lib.add_prim('cube', 'spec', lib.emissive(f'sp{k}', c, 12), None, size=1, location=(1.1 - .075, -.3 + k * .1, 1.585)); o.scale = (.004, .09, .006)
    # overhead lights
    for x in (-3, 0, 3):
        L = bpy.data.lights.new('ov', 'AREA'); L.energy = 120; L.size = 1.2; L.color = (1, .95, .88); lo = lib.link(bpy.data.objects.new('ov', L)); lo.location = (x, 0, 3.2)
    rim = bpy.data.lights.new('rim', 'AREA'); rim.energy = 80; rim.size = 2; rim.color = (.7, .8, 1); ro = lib.link(bpy.data.objects.new('rim', rim)); ro.location = (2, 3, 2); ro.rotation_euler = (math.radians(-60), 0, 0)
    reds = [lib.mat_tomato3(f'pr{k}', c) for k, c in enumerate([1, .97, .93, .6])]
    calm = lib.mat_stem3('pcal')
    tmpl = [lib.tomato_obj(f'ptmpl{k}', 1.0, reds[0], calm, (0, 0, -50), seed=90 + k) for k in range(6)]
    speed = .35  # m/s
    for k in range(170):
        tp = tmpl[R.randrange(len(tmpl))]; o = lib.link(bpy.data.objects.new('pt', tp.data)); o.material_slots[0].link = 'OBJECT'
        o.material_slots[0].material = reds[3 if R.random() > .92 else R.randrange(3)]
        cal_ = lib.link(bpy.data.objects.new('ptc', tp.children[0].data)); cal_.parent = o
        rr_ = R.uniform(.03, .037); o.scale = (rr_, rr_, rr_)
        y = (k % 3 - 1) * .17 + R.uniform(-.02, .02); x0 = -6 + (k // 3) * .16 + R.uniform(-.03, .03)
        o.location = (x0, y, .905); o.keyframe_insert('location', frame=1)
        o.location = (x0 + speed * (n - 1) / FPS, y, .905); o.keyframe_insert('location', frame=n)
        o.rotation_euler = (0, 0, R.uniform(0, 6)); o.keyframe_insert('rotation_euler', frame=1); o.rotation_euler.y = speed * (n - 1) / FPS / .033; o.keyframe_insert('rotation_euler', frame=n)
        try:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        except Exception:
            pass
    # boxes at the end
    card = lib.mat_basic('card', (.45, .33, .2), rough=.8)
    for k in range(6):
        bx = lib.add_prim('cube', 'box', card, None, size=1, location=(3.4 + (k % 3) * .52, .9 + (k // 3) * .02, .15 + (k // 3) * .3)); bx.scale = (.5, .36, .28)
    cam, tgt = lib.camera(lens=45, loc=(-1.2, -1.15, 1.3), target=(.15, 0, .92), fstop=2.0)
    cam.data.dof.focus_object = tgt
    for f in (1, n): cam.location = (-1.2 + .35 * (f / n), -1.15 + .1 * (f / n), 1.3); cam.keyframe_insert('location', frame=f)
    lib.shake(cam, .004, 24)
    lib.post(haze=(0, 0, 0), haze_amt=0, bloom=.6)
    return n

# ---------------------------------------------------------------- dinner table (still)
def shot_dinner():
    sc = bpy.context.scene; lib.world_color((.002, .0015, .001), 1); sc.view_settings.exposure = .6
    R = random.Random(12)
    t = lib.add_prim('plane', 'table', wood('oak'), None, size=1); t.scale = (3, 1.6, 1); t.location = (0, .3, 0)
    cloth = lib.add_prim('plane', 'runner', lib.mat_basic('linen', (.03, .06, .045), rough=.85), None, size=1, location=(0, .3, .001)); cloth.scale = (3, .4, 1)
    ph, scr = phone('phone', screen_mat('scr', (.01, .015, .012), 1.0)); ph.location = (0, -.05, .0045); ph.rotation_euler = (0, 0, -.12)
    plate = lib.mat_basic('porc', (.85, .84, .8), rough=.15, coat=.7)
    for x in (-.45, .45):
        p = lib.add_prim('cylinder', 'plate', plate, None, radius=.14, depth=.015, location=(x, .2, .008), vertices=64); lib.bevel(p, .006, 3)
    glass = lib.mat_basic('wglass', (1, 1, 1), rough=0, trans=1); wine = lib.mat_basic('wine', (.35, .01, .02), rough=0, trans=1)
    for x in (-.25, .3):
        st = lib.add_prim('cylinder', 'stem', glass, None, radius=.004, depth=.1, location=(x, .38, .05)); bw = lib.add_prim('uv_sphere', 'bowl', glass, None, radius=.045, location=(x, .38, .14)); bw.scale = (1, 1, 1.25); lib.smooth(bw)
        wn = lib.add_prim('uv_sphere', 'wine', wine, None, radius=.04, location=(x, .38, .125)); wn.scale = (1, 1, .7); lib.smooth(wn)
    flame = lib.emissive('flame', (1, .55, .2), 120); wax = lib.mat_basic('wax', (.9, .85, .75), rough=.4, sss=.6)
    for k, (x, y) in enumerate([(-.16, .32), (.12, .4), (.42, .3), (-.45, .42), (.7, .5), (-.75, .55)]):
        hgt = .14 + (k % 3) * .04
        c = lib.add_prim('cylinder', 'candle', wax, None, radius=.016, depth=hgt, location=(x, y, hgt / 2))
        fl = lib.add_prim('uv_sphere', 'flame', flame, None, radius=.009, location=(x, y, hgt + .018)); fl.scale = (1, 1, 2.2)
        L = bpy.data.lights.new('cl', 'POINT'); L.energy = 4; L.color = (1, .6, .3); L.shadow_soft_size = .02; lo = lib.link(bpy.data.objects.new('cl', L)); lo.location = (x, y, hgt + .04)
    # far warm bokeh lights (string lights)
    bulb = lib.emissive('bulb', (1, .65, .3), 80)
    for k in range(40):
        lib.add_prim('uv_sphere', 'b', bulb, None, radius=.015, location=(R.uniform(-1.6, 1.6), R.uniform(1.2, 2.6), R.uniform(.25, .9)))
    cam, tgt = lib.camera(lens=45, loc=(.06, -.46, .15), target=(0, -.04, .0), fstop=1.6)
    cam.data.dof.focus_object = tgt
    return 1, {'screen': scr}

SHOTS = {'dawn': shot_dawn, 'desk': shot_desk, 'aerial': shot_aerial, 'till': shot_till, 'cultivate': shot_cultivate, 'harvest': shot_harvest, 'pack': shot_pack, 'dinner': shot_dinner}

if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    name, f0, f1, spp = a[0], int(a[1]), int(a[2]), int(a[3])
    res = (int(a[4]), int(a[5])) if len(a) > 5 else (1280, 720)
    sc = lib.reset(res, fps=FPS, samples=spp); lib.realism(sc)
    r = SHOTS[name](); extra = {}
    if isinstance(r, tuple): r, extra = r
    if 'screen' in extra:  # write projected screen corners for the 2D UI composite
        from bpy_extras.object_utils import world_to_camera_view
        bpy.context.view_layer.update(); scr = extra['screen']; cam = sc.camera
        pts = []
        for c in [(-.5, .5), (.5, .5), (-.5, -.5), (.5, -.5)]:
            v = scr.matrix_world @ Vector((c[0], c[1], 0)); p = world_to_camera_view(sc, cam, v); pts.append([p.x, 1 - p.y])
        os.makedirs(f'{OUT}/{name}', exist_ok=True); open(f'{OUT}/{name}/screen.json', 'w').write(str(pts))
    if os.environ.get('NORENDER'): sys.exit(0)
    os.makedirs(f'{OUT}/{name}', exist_ok=True)
    if name == 'harvest':  # per-frame screen position of the target fruit for the 2D precision ring
        from bpy_extras.object_utils import world_to_camera_view
        fr = bpy.data.objects['fruit0']; track = []
        for f in range(1, r + 1):
            sc.frame_set(f); p = world_to_camera_view(sc, sc.camera, fr.matrix_world.translation); track.append([round(p.x, 4), round(1 - p.y, 4)])
        open(f'{OUT}/harvest/track.json', 'w').write(str(track)); sc.frame_set(1)
    sc.render.filepath = f'{OUT}/{name}/f_'
    sc.render.use_overwrite = False  # resume after interruptions
    sc.frame_start, sc.frame_end = f0, min(f1, r)
    if len(a) > 6: sc.frame_step = int(a[6])
    bpy.ops.render.render(animation=True)

"""Shared Blender helpers for the photoreal Agrobo film (Cycles, procedural assets only)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

def reset(res=(1280, 720), fps=24, samples=24, frames=(1, 1)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = .04
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 2; c.transmission_bounces = 4; c.transparent_max_bounces = 8; c.volume_bounces = 0
    c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 1.0
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.fps = fps; sc.frame_start, sc.frame_end = frames
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    try:
        sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception as e: print('cm', e)
    sc.render.film_transparent = False
    return sc

def world_sky(elev=8, rot=0, strength=1.0, sun_size=1.2, air=1.0, aerosol=1.6):
    sc = bpy.context.scene; w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; s = nt.nodes.new('ShaderNodeTexSky'); s.sky_type = 'MULTIPLE_SCATTERING'
    s.sun_elevation = math.radians(elev); s.sun_rotation = math.radians(rot); s.sun_size = math.radians(sun_size)
    s.air_density = air; s.aerosol_density = aerosol; s.sun_intensity = 1.0
    bg = nt.nodes['Background']; bg.inputs[1].default_value = strength
    nt.links.new(s.outputs[0], bg.inputs[0]); return s

def world_color(rgb=(0.02, 0.02, 0.02), strength=1.0):
    sc = bpy.context.scene; w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (*rgb, 1); bg.inputs[1].default_value = strength

# ---------- materials ----------
def _mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes['Principled BSDF']

def mat_basic(name, col, rough=.5, metal=0, emit=None, es=0, coat=0, sss=0, trans=0, alpha=1):
    m, nt, b = _mat(name)
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Transmission Weight'].default_value = trans
    b.inputs['Alpha'].default_value = alpha
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    return m

def emissive(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type == 'BSDF_PRINCIPLED': nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0]); return m

def noise_color(nt, scale, c1, c2, detail=8, coord=None, lo=.35, hi=.65):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    if coord is not None: nt.links.new(coord, n.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].position = lo; r.color_ramp.elements[1].position = hi
    r.color_ramp.elements[0].color = (*c1, 1); r.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(n.outputs['Fac'], r.inputs[0]); return r, n

def mat_soil(name='soil', wet=0.0, furrow_scale=0.0, furrow_axis='Y'):
    """Dry loam with clods; optional furrow banding (period in metres = 1/furrow_scale)."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeNewGeometry')
    pos = tc.outputs['Position']
    r, n = noise_color(nt, .8, (.055, .036, .024), (.15, .1, .064), coord=pos)
    r2, n2 = noise_color(nt, 9.0, (.55, .55, .55), (1.15, 1.12, 1.1), coord=pos)
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    nt.links.new(r.outputs[0], mul.inputs[6]); nt.links.new(r2.outputs[0], mul.inputs[7]); nt.links.new(mul.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .92 - .4 * wet; b.inputs['Specular IOR Level'].default_value = .2
    # bump: fine clods + voronoi pebbles (+ furrows)
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .55; bump.inputs['Distance'].default_value = .02
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 35; nt.links.new(pos, vor.inputs['Vector'])
    nf = nt.nodes.new('ShaderNodeTexNoise'); nf.inputs['Scale'].default_value = 14; nf.inputs['Detail'].default_value = 12; nt.links.new(pos, nf.inputs['Vector'])
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'; nt.links.new(vor.outputs['Distance'], add.inputs[0]); nt.links.new(nf.outputs['Fac'], add.inputs[1])
    nt.links.new(add.outputs[0], bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
    return m

def mat_leaf(name='leaf', base=(.05, .16, .03), var=(.09, .24, .05)):
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    r, n = noise_color(nt, 6, base, var, coord=tc.outputs['Object'])
    # veins
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 9; wv.inputs['Distortion'].default_value = 3; nt.links.new(tc.outputs['UV'], wv.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'LIGHTEN'; mx.inputs['Factor'].default_value = .18
    nt.links.new(r.outputs[0], mx.inputs[6]); nt.links.new(wv.outputs['Color'], mx.inputs[7])
    nt.links.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .55; b.inputs['Subsurface Weight'].default_value = .0
    b.inputs['Specular IOR Level'].default_value = .3
    # translucency for backlight
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); tr.inputs[0].default_value = (.22, .45, .05, 1)
    mix = nt.nodes.new('ShaderNodeMixShader'); mix.inputs[0].default_value = .28
    out = nt.nodes['Material Output']; nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .15; nt.links.new(wv.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
    m.use_backface_culling = False
    return m

def mat_tomato(name, col):
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    r, n = noise_color(nt, 7, tuple(c * .82 for c in col), col, coord=tc.outputs['Object'], lo=.2, hi=.8)
    nt.links.new(r.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .3; b.inputs['Subsurface Weight'].default_value = .15
    b.inputs['Subsurface Radius'].default_value = (1, .2, .08); b.inputs['Subsurface Scale'].default_value = .004
    b.inputs['Coat Weight'].default_value = .35; b.inputs['Coat Roughness'].default_value = .12
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .05; nt.links.new(n.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
    return m

# ---------- geometry ----------
def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj); return obj

def mesh_obj(name, bm, mat=None, coll=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    if mat: me.materials.append(mat)
    return link(o, coll)

def add_prim(kind, name, mat=None, coll=None, **kw):
    getattr(bpy.ops.mesh, 'primitive_' + kind + '_add')(**kw); o = bpy.context.object; o.name = name
    if mat: o.data.materials.append(mat)
    if coll:
        for c in o.users_collection: c.objects.unlink(o)
        coll.objects.link(o)
    return o

def bevel(o, w=.02, seg=3):
    m = o.modifiers.new('bev', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'; return o

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True
    return o

def leaflet(bm, base, direction, length, width, droop, up=Vector((0, 0, 1)), segs=6):
    """Curved, slightly cupped leaf blade as a strip of quads."""
    d = direction.normalized(); side = d.cross(up).normalized(); prev = None
    for i in range(segs + 1):
        t = i / segs; wdt = width * math.sin(math.pi * min(.98, t * .9 + .06)) * (1 - .15 * t)
        c = base + d * (length * t) + Vector((0, 0, -droop * t * t))
        l = bm.verts.new(c + side * wdt * .5 + Vector((0, 0, wdt * .12))); m_ = bm.verts.new(c); r_ = bm.verts.new(c - side * wdt * .5 + Vector((0, 0, wdt * .12)))
        if prev:
            bm.faces.new((prev[0], prev[1], m_, l)); bm.faces.new((prev[1], prev[2], r_, m_))
        prev = (l, m_, r_)

def tomato_plant(name, seed, height=.9, leaves=13, mat_leaf_=None, mat_stem=None, coll=None, fruit_mats=None, fruit=0):
    rnd = random.Random(seed); bm = bmesh.new(); bm_s = bmesh.new()
    pts = [Vector((rnd.uniform(-.02, .02) * i, rnd.uniform(-.02, .02) * i, height * i / 6)) for i in range(7)]
    for a, b in zip(pts, pts[1:]):
        bmesh.ops.create_cone(bm_s, cap_ends=False, segments=6, radius1=.012, radius2=.01, depth=(b - a).length,
                              matrix=Matrix.Translation((a + b) / 2) @ (b - a).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    for k in range(leaves):
        h = height * (.18 + .8 * k / leaves); ang = k * 2.4 + rnd.uniform(-.3, .3)
        d = Vector((math.cos(ang), math.sin(ang), rnd.uniform(.05, .45))); L = .5 * (1.15 - .5 * k / leaves) * rnd.uniform(.8, 1.1)
        base = Vector((0, 0, h))
        # rachis
        tip = base + d * L * .9 + Vector((0, 0, -.08))
        bmesh.ops.create_cone(bm_s, cap_ends=False, segments=4, radius1=.005, radius2=.003, depth=(tip - base).length,
                              matrix=Matrix.Translation((base + tip) / 2) @ (tip - base).to_track_quat('Z', 'Y').to_matrix().to_4x4())
        for j in range(4):
            t = .2 + j * .2; p = base.lerp(tip, t); side = d.cross(Vector((0, 0, 1))).normalized()
            for s in (-1, 1):
                ld = (side * s + d * .45 + Vector((0, 0, rnd.uniform(-.2, .15)))).normalized()
                leaflet(bm, p, ld, L * .42 * rnd.uniform(.8, 1.15), L * .22, .06 * rnd.uniform(.5, 1.5))
                if j < 3: leaflet(bm, p.lerp(tip, .08), (ld + d).normalized(), L * .18, L * .1, .02)
        leaflet(bm, tip, d, L * .4, L * .22, .05)
    leaf_o = mesh_obj(name + '_leaves', bm, mat_leaf_, coll); stem_o = mesh_obj(name + '_stem', bm_s, mat_stem, coll)
    stem_o.parent = leaf_o
    if fruit and fruit_mats:
        for f in range(fruit):
            ang = rnd.uniform(0, 6.28); r = rnd.uniform(.06, .14); h = height * rnd.uniform(.3, .65)
            fo = add_prim('uv_sphere', f'{name}_fr{f}', fruit_mats[rnd.randrange(len(fruit_mats))], coll, radius=rnd.uniform(.03, .042), location=(math.cos(ang) * r, math.sin(ang) * r, h), segments=24, ring_count=16)
            fo.scale = (1, 1, .86); smooth(fo); fo.parent = leaf_o
    return leaf_o

def instance_collection(coll, name, loc, rot=0, scale=1, parent_coll=None):
    o = bpy.data.objects.new(name, None); o.instance_type = 'COLLECTION'; o.instance_collection = coll
    o.location = loc; o.rotation_euler = (0, 0, rot); o.scale = (scale,) * 3
    return link(o, parent_coll)

def camera(name='cam', lens=35, loc=(0, 0, 2), target=None, fstop=None, focus=None, sensor=36):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor; cd.clip_end = 3000
    o = link(bpy.data.objects.new(name, cd)); o.location = loc; bpy.context.scene.camera = o
    if fstop: cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    if focus is not None: cd.dof.focus_distance = focus
    if target is not None:
        e = link(bpy.data.objects.new(name + '_tgt', None)); e.location = target
        c = o.constraints.new('TRACK_TO'); c.target = e; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
        if fstop: cd.dof.focus_object = e
        return o, e
    return o, None

def key(o, path, frame, value):
    setattr(o, path, value) if not isinstance(value, tuple) else setattr(o, path, value)
    o.keyframe_insert(path, frame=frame)

def smoothstep(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)

# ---------- robots ----------
def ugv(name, coll=None, tool='tiller', accent=(.83, .66, .34)):
    """Agrobo modular UGV: low chassis, 4 lugged wheels, sensor mast, light bar."""
    root = link(bpy.data.objects.new(name, None), coll)
    body = mat_paint3(name + '_paint', (.045, .048, .052), rough=.4, dust=1.0)
    gold = mat_paint3(name + '_gold', accent, rough=.32, dust=.6, metal=1)
    tyre = mat_paint3(name + '_tyre', (.016, .015, .014), rough=.88, dust=1.8)
    alu = mat_paint3(name + '_alu', (.2, .2, .21), rough=.35, dust=.9, metal=1)
    glass = mat_basic(name + '_glass', (.02, .02, .02), rough=.05, coat=1)
    light = emissive(name + '_light', (1, .93, .8), 25)
    def part(o): o.parent = root; return o
    c = part(bevel(add_prim('cube', name + '_chassis', body, coll, size=1, location=(0, 0, .55)), .05)); c.scale = (1.6, .9, .38)
    t = part(bevel(add_prim('cube', name + '_top', body, coll, size=1, location=(-.1, 0, .8)), .04)); t.scale = (1.1, .78, .14)
    s = part(add_prim('cube', name + '_stripe', gold, coll, size=1, location=(0, 0, .56))); s.scale = (1.62, .92, .035)
    for x in (-.62, .62):
        for y in (-.55, .55):
            w = part(add_prim('cylinder', name + '_w', tyre, coll, radius=.33, depth=.22, location=(x, y, .33), rotation=(math.pi / 2, 0, 0), vertices=32)); bevel(w, .04)
            h = part(add_prim('cylinder', name + '_hub', alu, coll, radius=.16, depth=.235, location=(x, y, .33), rotation=(math.pi / 2, 0, 0), vertices=24))
            for k in range(14):  # lugs
                a = k / 14 * 2 * math.pi
                l = part(add_prim('cube', name + '_lug', tyre, coll, size=1, location=(x + math.cos(a) * .335, y, .33 + math.sin(a) * .335), rotation=(0, -a, 0))); l.scale = (.03, .2, .05)
    m = part(add_prim('cylinder', name + '_mast', alu, coll, radius=.025, depth=.55, location=(.45, 0, 1.05)))
    lid = part(add_prim('cylinder', name + '_lidar', glass, coll, radius=.075, depth=.09, location=(.45, 0, 1.36), vertices=32)); bevel(lid, .02)
    cam_ = part(bevel(add_prim('cube', name + '_stereo', glass, coll, size=1, location=(.8, 0, .72)), .01)); cam_.scale = (.06, .32, .06)
    lb = part(add_prim('cube', name + '_lightbar', light, coll, size=1, location=(.805, 0, .62))); lb.scale = (.01, .6, .025)
    pv = part(add_prim('cube', name + '_solar', mat_basic(name + '_pv', (.02, .03, .06), rough=.15, coat=1), coll, size=1, location=(-.15, 0, .885))); pv.scale = (1.0, .72, .01)
    if tool == 'tiller':
        tb = part(bevel(add_prim('cube', name + '_tiller', body, coll, size=1, location=(-1.05, 0, .32)), .03)); tb.scale = (.35, 1.3, .3)
        for y in [i * .16 - .56 for i in range(8)]:
            tn = part(add_prim('cube', name + '_tine', alu, coll, size=1, location=(-1.1, y, .1), rotation=(0, .4, 0))); tn.scale = (.03, .03, .22)
    if tool == 'laser':
        lh = part(bevel(add_prim('cube', name + '_laserhead', body, coll, size=1, location=(.95, 0, .3)), .02)); lh.scale = (.2, .25, .12)
        ln = part(add_prim('cylinder', name + '_laserlens', glass, coll, radius=.035, depth=.02, location=(.95, 0, .235), vertices=24))
    # ---- v3 detail: panel seams, hub bolts, fenders, logo, beacon, antenna, cable, decals
    seam = mat_basic(name + '_seam', (.004, .004, .004), rough=.7)
    for x in (-.4, .05, .5):
        for y in (-.452, .452):
            sm = part(add_prim('cube', name + '_seam', seam, coll, size=1, location=(x, y, .55))); sm.scale = (.006, .004, .3)
    sm = part(add_prim('cube', name + '_seamt', seam, coll, size=1, location=(-.1, 0, .874))); sm.scale = (1.0, .004, .004)
    for x in (-.62, .62):
        for y in (-.55, .55):
            sy = 1 if y > 0 else -1
            for k in range(6):
                a = k / 6 * 2 * math.pi
                bt = part(add_prim('cylinder', name + '_bolt', alu, coll, radius=.012, depth=.02, location=(x + math.cos(a) * .1, y + sy * .12, .33 + math.sin(a) * .1), rotation=(math.pi / 2, 0, 0), vertices=6))
            cap = part(add_prim('cylinder', name + '_cap', body, coll, radius=.05, depth=.03, location=(x, y + sy * .125, .33), rotation=(math.pi / 2, 0, 0), vertices=24))
            fd = part(bevel(add_prim('cube', name + '_fender', body, coll, size=1, location=(x, y, .7)), .02)); fd.scale = (.72, .26, .03)
    try:
        cu = bpy.data.curves.new(name + '_logo', 'FONT'); cu.body = 'AGROBO'; cu.size = .085; cu.extrude = .002; cu.align_x = 'CENTER'
        for sy in (-1, 1):
            lo = link(bpy.data.objects.new(name + '_logo', cu), coll); lo.data.materials.append(gold); lo.parent = root
            lo.location = (-.15, sy * .4535, .64); lo.rotation_euler = (math.pi / 2, 0, 0 if sy < 0 else math.pi)
        cu2 = bpy.data.curves.new(name + '_id', 'FONT'); cu2.body = 'UGV-07  |  48V'; cu2.size = .03; cu2.align_x = 'CENTER'
        for sy in (-1, 1):
            lo = link(bpy.data.objects.new(name + '_id', cu2), coll); lo.data.materials.append(mat_basic(name + '_wht', (.6, .6, .58), rough=.5)); lo.parent = root
            lo.location = (.45, sy * .4535, .45); lo.rotation_euler = (math.pi / 2, 0, 0 if sy < 0 else math.pi)
    except Exception as e: print('logo', e)
    amber = emissive(name + '_amber', (1, .45, .05), 8)
    bc = part(add_prim('cylinder', name + '_beacon', amber, coll, radius=.03, depth=.05, location=(-.55, .3, .92), vertices=16))
    an = part(add_prim('cylinder', name + '_ant', seam, coll, radius=.004, depth=.35, location=(-.6, -.3, 1.05), vertices=6))
    gn = part(add_prim('cylinder', name + '_gnss', mat_basic(name + '_gw', (.75, .75, .72), rough=.5), coll, radius=.06, depth=.025, location=(-.3, -.25, .9), vertices=24))
    wl = part(add_prim('cube', name + '_warn', mat_basic(name + '_yel', (.7, .5, .02), rough=.5), coll, size=1, location=(.8, .3, .45))); wl.scale = (.003, .06, .04)
    return root

def drone(name, coll=None):
    root = link(bpy.data.objects.new(name, None), coll)
    body = mat_paint3(name + '_body', (.05, .055, .06), rough=.38, dust=.3); carbon = mat_paint3(name + '_cf', (.015, .015, .015), rough=.4, dust=.2)
    prop = mat_basic(name + '_prop', (.02, .02, .02), rough=.4, alpha=.25); gold = mat_basic(name + '_gold', (.83, .66, .34), rough=.25, metal=1)
    prop.blend_method = 'BLEND' if hasattr(prop, 'blend_method') else None
    def part(o): o.parent = root; return o
    b = part(bevel(add_prim('cube', name + '_b', body, coll, size=1), .05)); b.scale = (.42, .26, .14)
    g = part(add_prim('cube', name + '_g', gold, coll, size=1, location=(0, 0, .072))); g.scale = (.3, .02, .005)
    cm = part(add_prim('uv_sphere', name + '_cam', mat_basic(name + '_lens', (.01, .01, .01), rough=.05, coat=1), coll, radius=.07, location=(.18, 0, -.1))); smooth(cm)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; x, y = math.cos(a) * .55, math.sin(a) * .55
        arm = part(add_prim('cylinder', name + '_arm', carbon, coll, radius=.025, depth=.6, location=(x / 2, y / 2, 0), rotation=(0, math.pi / 2, a)))
        mo = part(add_prim('cylinder', name + '_mot', carbon, coll, radius=.045, depth=.08, location=(x, y, .04)))
        d = part(add_prim('cylinder', name + '_disc', prop, coll, radius=.33, depth=.004, location=(x, y, .09), vertices=48))
    return root


# =====================================================================================
# v3 realism layer: textured leaves, lobed fruit with calyx, card trees, grime, clouds,
# atmospheric haze, lens character, camera shake. Everything is procedural or generated
# by textures.py, so the film stays self-contained.
# =====================================================================================
import os
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex')
_imgs = {}

def image(name, non_color=False):
    if name not in _imgs:
        im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
        if non_color: im.colorspace_settings.name = 'Non-Color'
        im.alpha_mode = 'STRAIGHT'; _imgs[name] = im
    return _imgs[name]

def fcurves(o):
    """All F-curves of an object's action (Blender 5 layered actions or legacy)."""
    ad = o.animation_data
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])): return list(act.fcurves)
    out = []
    for layer in getattr(act, 'layers', []):
        for st in layer.strips:
            for cb in st.channelbags: out += list(cb.fcurves)
    return out

def shake(o, amp=.01, scale=28, paths=('location',)):
    """Handheld / gimbal drift: smooth noise on top of the keyed motion."""
    if not o.animation_data or not o.animation_data.action:
        for p in paths: o.keyframe_insert(p, frame=1)
    for fc in fcurves(o):
        if fc.data_path in paths:
            m = fc.modifiers.new('NOISE'); m.scale = scale; m.strength = amp * 2; m.phase = random.uniform(0, 100); m.depth = 1

def hsv_var(nt, col_socket, amount_h=.03, amount_v=.3, amount_s=.2):
    """Per-object colour variation (works per instance)."""
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    hs = nt.nodes.new('ShaderNodeHueSaturation'); nt.links.new(col_socket, hs.inputs['Color'])
    for inp, a, c in (('Hue', amount_h, .5), ('Value', amount_v, 1.0), ('Saturation', amount_s, 1.0)):
        mp = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(oi.outputs['Random'], mp.inputs[0])
        mp.inputs[3].default_value = c - a; mp.inputs[4].default_value = c + a; nt.links.new(mp.outputs[0], hs.inputs[inp])
    return hs.outputs['Color']

def mat_leaf_tex(name, k=0, old=False, sheen=.12):
    """Tomato leaflet: image cut-out (lobed, serrated, veined), translucency, fine hairs (sheen)."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = image(f'leaflet{k % 3}.png'); nt.links.new(tc.outputs['UV'], ti.inputs[0])
    th = nt.nodes.new('ShaderNodeTexImage'); th.image = image(f'leaflet{k % 3}_h.png', True); nt.links.new(tc.outputs['UV'], th.inputs[0])
    col = hsv_var(nt, ti.outputs['Color'], .025, .22, .15)
    if old:
        tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MIX'; tint.inputs['Factor'].default_value = .35
        nt.links.new(col, tint.inputs[6]); tint.inputs[7].default_value = (.32, .3, .06, 1); col = tint.outputs[2]
    nt.links.new(col, b.inputs['Base Color']); nt.links.new(ti.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = .55; b.inputs['Specular IOR Level'].default_value = .22
    b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = .35; b.inputs['Sheen Tint'].default_value = (.7, .8, .6, 1)
    b.inputs['Transmission Weight'].default_value = 0
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .35; bump.inputs['Distance'].default_value = .002
    nt.links.new(th.outputs['Color'], bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
    # back-light translucency through the blade, cut by the same alpha
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    br = nt.nodes.new('ShaderNodeMix'); br.data_type = 'RGBA'; br.blend_type = 'MULTIPLY'; br.inputs['Factor'].default_value = 1
    nt.links.new(col, br.inputs[6]); br.inputs[7].default_value = (2.2, 2.6, 1.2, 1); nt.links.new(br.outputs[2], tr.inputs[0])
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = .32
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    tp = nt.nodes.new('ShaderNodeBsdfTransparent'); cut = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(ti.outputs['Alpha'], cut.inputs[0]); nt.links.new(tp.outputs[0], cut.inputs[1]); nt.links.new(mx.outputs[0], cut.inputs[2])
    nt.links.new(cut.outputs[0], nt.nodes['Material Output'].inputs[0])
    m.use_backface_culling = False
    return m

def mat_card(name, img_name, rough=.6, trans=.25):
    """Alpha card (tree twigs, hedges)."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord'); ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = image(img_name); nt.links.new(tc.outputs['UV'], ti.inputs[0])
    col = hsv_var(nt, ti.outputs['Color'], .02, .25, .15)
    nt.links.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); nt.links.new(col, tr.inputs[0])
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = trans; nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    tp = nt.nodes.new('ShaderNodeBsdfTransparent'); cut = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(ti.outputs['Alpha'], cut.inputs[0]); nt.links.new(tp.outputs[0], cut.inputs[1]); nt.links.new(mx.outputs[0], cut.inputs[2])
    nt.links.new(cut.outputs[0], nt.nodes['Material Output'].inputs[0]); m.use_backface_culling = False
    return m

def mat_stem3(name='stem3'):
    """Hairy green stem: sheen fuzz, mottled colour, slight translucency."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    r, n = noise_color(nt, 40, (.05, .11, .025), (.1, .19, .05), coord=tc.outputs['Object'])
    nt.links.new(hsv_var(nt, r.outputs[0], .02, .2), b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .55; b.inputs['Sheen Weight'].default_value = .4; b.inputs['Sheen Roughness'].default_value = .3
    b.inputs['Sheen Tint'].default_value = (.85, .9, .8, 1); b.inputs['Subsurface Weight'].default_value = 0
    b.inputs['Subsurface Radius'].default_value = (.4, 1, .3); b.inputs['Subsurface Scale'].default_value = .003
    return m

def mat_tomato3(name, ripeness, sss=True):
    """ripeness 0 green .. 1 red. Glossy waxy cuticle with broken highlights, shoulder tint, sub-surface flesh."""
    m, nt, b = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    lerp3 = lambda a, c, t: tuple(x + (y - x) * t for x, y in zip(a, c))
    body = lerp3((.13, .2, .05), (.42, .018, .008), ripeness) if ripeness <= 1 else (.42, .018, .008)
    if .2 < ripeness < .9: body = lerp3((.55, .2, .02), (.48, .07, .015), (ripeness - .2) / .7)
    shoulder = lerp3((.22, .28, .1), (.44, .05, .014), min(1, ripeness * 1.15))
    # shoulder gradient (object Z is up, radius ~1 after scaling)
    mr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sep.outputs['Z'], mr.inputs[0]); mr.inputs[1].default_value = .2; mr.inputs[2].default_value = 1.0
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.5; nz.inputs['Detail'].default_value = 6; nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; nt.links.new(nz.outputs['Fac'], ad.inputs[0]); ad.inputs[1].default_value = .5; nt.links.new(mr.outputs[0], ad.inputs[2])
    cr = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(ad.outputs[0], cr.inputs[0])
    cr.color_ramp.elements[0].position = .75; cr.color_ramp.elements[0].color = (*body, 1)
    cr.color_ramp.elements[1].position = 1.35; cr.color_ramp.elements[1].color = (*shoulder, 1)
    # faint lighter dots (lenticels) + streaks on green fruit
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 60; nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    dots = nt.nodes.new('ShaderNodeMath'); dots.operation = 'LESS_THAN'; nt.links.new(vo.outputs['Distance'], dots.inputs[0]); dots.inputs[1].default_value = .07
    dm = nt.nodes.new('ShaderNodeMix'); dm.data_type = 'RGBA'; dm.blend_type = 'SCREEN'; nt.links.new(dots.outputs[0], dm.inputs['Factor'])
    nt.links.new(cr.outputs[0], dm.inputs[6]); dm.inputs[7].default_value = (.12, .1, .05, 1)
    nt.links.new(hsv_var(nt, dm.outputs[2], .012, .12, .08), b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .24; b.inputs['Specular IOR Level'].default_value = .55
    b.inputs['Coat Weight'].default_value = .2; b.inputs['Coat Roughness'].default_value = .16
    b.inputs['Subsurface Weight'].default_value = .45 if sss else 0; b.inputs['Subsurface Scale'].default_value = .008
    b.inputs['Subsurface Radius'].default_value = (1, .25, .12) if ripeness > .4 else (.5, 1, .3)
    # micro surface: broken, slightly orange-peel highlight + roughness variation
    mic = nt.nodes.new('ShaderNodeTexNoise'); mic.inputs['Scale'].default_value = 180; mic.inputs['Detail'].default_value = 4; nt.links.new(tc.outputs['Object'], mic.inputs['Vector'])
    rr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(nz.outputs['Fac'], rr.inputs[0]); rr.inputs[3].default_value = .16 + .14 * (1 - ripeness); rr.inputs[4].default_value = .38 + .12 * (1 - ripeness)
    nt.links.new(rr.outputs[0], b.inputs['Roughness'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .08; bp.inputs['Distance'].default_value = .0005
    nt.links.new(mic.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def tomato_bm(bm, r, center=Vector((0, 0, 0)), lobes=5, seed=0, segs=36, rings=20):
    """Slightly lobed, flattened tomato with a stem dimple, added to bm. Returns top point."""
    rnd = random.Random(seed); ph = rnd.uniform(0, 6.28); lb = rnd.uniform(.025, .06); sq = rnd.uniform(.8, .9)
    ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1)
    for v in ret['verts']:
        p = v.co.copy(); th = math.atan2(p.y, p.x); z = p.z
        k = 1 + lb * math.cos(lobes * th + ph) * (1 - abs(z)) ** .5 + .02 * math.sin(3 * th + ph * 2)
        p.x *= k; p.y *= k; p.z *= sq
        if z > .8: p.z -= (z - .8) * .55  # dimple where the calyx sits
        if z < -.85: p.z += (-.85 - z) * .3
        v.co = center + p * r
    return center + Vector((0, 0, r * sq * .9))

def calyx_bm(bm, top, r, seed=0, n=None):
    """Star calyx: 5-7 narrow sepals curling down over the shoulder + a short knuckled pedicel."""
    rnd = random.Random(seed); n = n or rnd.choice((5, 6, 6, 7))
    for k in range(n):
        a = k / n * 2 * math.pi + rnd.uniform(-.2, .2); d = Vector((math.cos(a), math.sin(a), rnd.uniform(-.1, .35)))
        leaflet(bm, top + Vector((0, 0, r * .03)), d, r * rnd.uniform(.75, 1.05), r * .22, r * rnd.uniform(.15, .55), segs=5)
    p0 = top; p1 = top + Vector((rnd.uniform(-.2, .2) * r, rnd.uniform(-.2, .2) * r, r * .55))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r * .1, radius2=r * .075, depth=(p1 - p0).length,
                          matrix=Matrix.Translation((p0 + p1) / 2) @ (p1 - p0).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r * .12, matrix=Matrix.Translation(p1))
    return p1

def tomato_obj(name, r, mat, calyx_mat, loc, seed=0, coll=None):
    bm = bmesh.new(); top = tomato_bm(bm, r, seed=seed); o = mesh_obj(name, bm, mat, coll); o.location = loc
    bm2 = bmesh.new(); calyx_bm(bm2, top, r, seed=seed); c = mesh_obj(name + '_calyx', bm2, calyx_mat, coll); c.parent = o
    return o

def leaflet_uv(bm, uvl, base, direction, length, width, droop, up=Vector((0, 0, 1)), segs=5, cup=.18, twist=0.0, mi=0):
    """Textured leaflet quad strip (u along blade, v across), cupped and drooping. Uses the alpha cut-out for the outline."""
    d = direction.normalized(); side = d.cross(up)
    if side.length < 1e-4: side = d.cross(Vector((1, 0, 0)))
    side.normalize(); nrm = side.cross(d).normalized(); rows = []
    for i in range(segs + 1):
        t = i / segs; c = base + d * (length * t) + Vector((0, 0, -droop * t * t))
        sd = (Matrix.Rotation(twist * t, 3, d) @ side)
        w = width * .5
        rows.append([bm.verts.new(c + sd * w * s + nrm * (w * cup * abs(s))) for s in (-1, 0, 1)])
    for i in range(segs):
        for j in range(2):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])); f.material_index = mi
            for loop, (uu, vv) in zip(f.loops, ((i / segs, j / 2), (i / segs, (j + 1) / 2), ((i + 1) / segs, (j + 1) / 2), ((i + 1) / segs, j / 2))):
                loop[uvl].uv = (uu, vv)

def tube(bm, pts, r0, r1, segs=8):
    """Continuous tapered tube through pts (no visible joints)."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        q = d.to_track_quat('Z', 'Y').to_matrix(); r = r0 + (r1 - r0) * i / (len(pts) - 1)
        rings.append([bm.verts.new(p + q @ Vector((math.cos(a) * r, math.sin(a) * r, 0))) for a in [k / segs * 2 * math.pi for k in range(segs)]])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))

def tomato_plant3(name, seed, height=.9, leaves=16, leaf_mats=None, stem_mat=None, coll=None, fruit=0, fruit_mats=None, calyx_mat=None):
    """Tomato plant v3: tapered zig-zag main stem, compound leaves (rachis + 3-4 leaflet pairs + terminal +
    small interstitial leaflets) with textured blades; optional lobed fruit with calyx on trusses."""
    rnd = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); bm_s = bmesh.new()
    nodes = [Vector((0, 0, 0))]
    for i in range(1, 9):
        nodes.append(nodes[-1] + Vector((rnd.uniform(-.035, .035), rnd.uniform(-.035, .035), height / 8)))
    tube(bm_s, nodes, .015, .006, 10)
    for k in range(leaves):
        f_ = k / leaves; h = height * (.12 + .82 * f_); base = nodes[0].lerp(nodes[-1], .12 + .82 * f_)
        ang = k * 2.39996 + rnd.uniform(-.35, .35)
        d = Vector((math.cos(ang), math.sin(ang), rnd.uniform(.15, .6) - .25 * (1 - f_))).normalized()
        L = .5 * (1.2 - .5 * f_) * rnd.uniform(.85, 1.15)
        old = f_ < .15 and rnd.random() < .35
        tip = base + d * L * .92 + Vector((0, 0, -.1 * L - .05 * (1 - f_)))
        mid = base.lerp(tip, .5) + Vector((0, 0, .04 * L))
        tube(bm_s, [base, base.lerp(mid, .5) + Vector((0, 0, .01)), mid, mid.lerp(tip, .5), tip], .0055, .0028, 6)
        side = d.cross(Vector((0, 0, 1))).normalized()
        pairs = rnd.choice((3, 4, 4))
        for j in range(pairs):
            t = .22 + j * (.7 / pairs); p = base.lerp(mid, t * 2) if t < .5 else mid.lerp(tip, (t - .5) * 2)
            for s in (-1, 1):
                ld = (side * s + d * rnd.uniform(.25, .6) + Vector((0, 0, rnd.uniform(-.25, .2)))).normalized()
                mi = 3 if old else rnd.randrange(3)
                ll = L * rnd.uniform(.4, .52) * (1.05 - .2 * j / pairs)
                leaflet_uv(bm, uvl, p, ld, ll, ll * .62, ll * rnd.uniform(.08, .3), cup=rnd.uniform(.1, .3), twist=rnd.uniform(-.5, .5), mi=mi)
                if rnd.random() < .6:  # interstitial mini leaflets
                    q = p.lerp(tip, .07); ld2 = (ld + d).normalized(); l2 = ll * .35
                    leaflet_uv(bm, uvl, q, ld2, l2, l2 * .6, l2 * .1, mi=mi)
        lt = L * rnd.uniform(.36, .46)
        leaflet_uv(bm, uvl, tip, (d + Vector((0, 0, -.25))).normalized(), lt, lt * .62, lt * .2, cup=.2, mi=3 if old else rnd.randrange(3))
    leaf_o = mesh_obj(name + '_leaves', bm, None, coll); stem_o = mesh_obj(name + '_stem', bm_s, stem_mat, coll); stem_o.parent = leaf_o
    for m in leaf_mats: leaf_o.data.materials.append(m)
    if fruit and fruit_mats:
        for f in range(fruit):
            ang = rnd.uniform(0, 6.28); rr = rnd.uniform(.07, .15); hz = height * rnd.uniform(.28, .62)
            fo = tomato_obj(f'{name}_fr{f}', rnd.uniform(.028, .04), fruit_mats[rnd.randrange(len(fruit_mats))], calyx_mat or stem_mat,
                            (math.cos(ang) * rr, math.sin(ang) * rr, hz), seed=seed * 31 + f, coll=coll)
            fo.parent = leaf_o
    return leaf_o

def tree3(name, seed, height=12, crown=5, card_mats=None, bark=None, coll=None, cards=1300):
    """Broadleaf tree: tapered trunk + recursive branches (bmesh) carrying alpha twig cards."""
    rnd = random.Random(seed); bm = bmesh.new(); bmc = bmesh.new(); uvl = bmc.loops.layers.uv.new('UVMap')
    tips = []
    def branch(p, d, L, r, depth):
        q = p + d * L
        bmesh.ops.create_cone(bm, cap_ends=False, segments=max(5, 10 - depth * 2), radius1=r, radius2=r * .7, depth=L,
                              matrix=Matrix.Translation((p + q) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        if depth >= 4 or r < .02: tips.append(q); return
        for k in range(rnd.choice((2, 3, 3))):
            nd = (d + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-.1, .7))) * .75).normalized()
            branch(q, nd, L * rnd.uniform(.55, .78), r * .62, depth + 1)
        if depth >= 2: tips.append(q)
    trunk_h = height * rnd.uniform(.16, .26)
    branch(Vector((0, 0, 0)), Vector((rnd.uniform(-.05, .05), rnd.uniform(-.05, .05), 1)).normalized(), trunk_h, height * .028, 0)
    o = mesh_obj(name + '_wood', bm, bark, coll)
    top = Vector((0, 0, height - crown * .95))
    lobes_ = [top + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-.6, .8))) * crown * .55 for _ in range(6)]
    for k in range(cards):
        # leaf mass = union of a few lumpy sub-crowns, denser toward the surface, plus some at branch tips
        if rnd.random() < .25: c = tips[rnd.randrange(len(tips))] + Vector((rnd.gauss(0, .4), rnd.gauss(0, .4), rnd.gauss(0, .4)))
        else:
            ctr = lobes_[rnd.randrange(len(lobes_))]; dirv = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            c = ctr + dirv * crown * .55 * rnd.random() ** .35
        s = rnd.uniform(1.0, 1.8); a = Euler((rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28))).to_matrix()
        vs = [bmc.verts.new(c + a @ Vector((x * s, 0, y * s))) for x, y in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))]
        f = bmc.faces.new(vs); f.material_index = rnd.randrange(len(card_mats))
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uvl].uv = uv
    co = mesh_obj(name + '_cards', bmc, None, coll, smooth=False)
    for m in card_mats: co.data.materials.append(m)
    co.parent = o
    return o

def mat_bark(name='bark'):
    m, nt, b = _mat(name); tc = nt.nodes.new('ShaderNodeTexCoord')
    r, n = noise_color(nt, 6, (.03, .025, .02), (.09, .08, .065), coord=tc.outputs['Object'])
    nt.links.new(r.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
    w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = 'Z'; w.inputs['Scale'].default_value = 2; w.inputs['Distortion'].default_value = 12
    nt.links.new(tc.outputs['Object'], w.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .7; nt.links.new(w.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def mat_grassland(name='grassland', dry=.5):
    """Mixed pasture / stubble for everything beyond the beds: multi-scale colour patches + fine bump."""
    m, nt, b = _mat(name); geo = nt.nodes.new('ShaderNodeNewGeometry'); pos = geo.outputs['Position']
    g1, _ = noise_color(nt, .04, (.035, .055, .015), (.12, .12, .045), coord=pos, lo=.3, hi=.7)
    g2, _ = noise_color(nt, .5, (.6, .6, .6), (1.25, 1.2, 1.1), coord=pos)
    g3, n3 = noise_color(nt, 9, (.7, .7, .7), (1.2, 1.15, 1.1), coord=pos)
    a = nt.nodes.new('ShaderNodeMix'); a.data_type = 'RGBA'; a.blend_type = 'MULTIPLY'; a.inputs['Factor'].default_value = 1
    nt.links.new(g1.outputs[0], a.inputs[6]); nt.links.new(g2.outputs[0], a.inputs[7])
    c = nt.nodes.new('ShaderNodeMix'); c.data_type = 'RGBA'; c.blend_type = 'MULTIPLY'; c.inputs['Factor'].default_value = 1
    nt.links.new(a.outputs[2], c.inputs[6]); nt.links.new(g3.outputs[0], c.inputs[7])
    straw = nt.nodes.new('ShaderNodeMix'); straw.data_type = 'RGBA'; straw.inputs['Factor'].default_value = dry * .5
    nt.links.new(c.outputs[2], straw.inputs[6]); straw.inputs[7].default_value = (.2, .16, .07, 1)
    nt.links.new(straw.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .95; b.inputs['Specular IOR Level'].default_value = .08
    fn = nt.nodes.new('ShaderNodeTexNoise'); fn.inputs['Scale'].default_value = 120; fn.inputs['Detail'].default_value = 3; nt.links.new(pos, fn.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .6; nt.links.new(fn.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def grime(nt, b, base_col_socket, dust=(.2, .16, .11), height=.55, amount=1.0, ao=True):
    """Dust that builds up toward the ground and in crevices (AO), plus roughness break-up."""
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    hz = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sep.outputs['Z'], hz.inputs[0]); hz.inputs[1].default_value = height; hz.inputs[2].default_value = 0
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 7; nz.inputs['Detail'].default_value = 10; nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(hz.outputs[0], m1.inputs[0]); nt.links.new(nz.outputs['Fac'], m1.inputs[1])
    tot = m1
    if ao:
        a = nt.nodes.new('ShaderNodeAmbientOcclusion'); a.samples = 4; a.inputs['Distance'].default_value = .08
        inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; nt.links.new(a.outputs['AO'], inv.inputs[1])
        ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.use_clamp = True; nt.links.new(m1.outputs[0], ad.inputs[0]); nt.links.new(inv.outputs[0], ad.inputs[1]); tot = ad
    sc_ = nt.nodes.new('ShaderNodeMath'); sc_.operation = 'MULTIPLY'; sc_.use_clamp = True; nt.links.new(tot.outputs[0], sc_.inputs[0]); sc_.inputs[1].default_value = 1.6 * amount
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; nt.links.new(sc_.outputs[0], mx.inputs['Factor'])
    nt.links.new(base_col_socket, mx.inputs[6]); mx.inputs[7].default_value = (*dust, 1); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sc_.outputs[0], rr.inputs[0]); rr.inputs[3].default_value = b.inputs['Roughness'].default_value; rr.inputs[4].default_value = .95
    nt.links.new(rr.outputs[0], b.inputs['Roughness'])
    return sc_

def mat_paint3(name, col, rough=.42, dust=1.0, metal=0.0, ao=True):
    """Powder-coated / painted metal with orange-peel bump, rough variation and dust."""
    m, nt, b = _mat(name); tc = nt.nodes.new('ShaderNodeTexCoord')
    rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    grime(nt, b, rgb.outputs[0], amount=dust, ao=ao)
    op = nt.nodes.new('ShaderNodeTexNoise'); op.inputs['Scale'].default_value = 260; nt.links.new(tc.outputs['Object'], op.inputs['Vector'])
    sc = nt.nodes.new('ShaderNodeTexNoise'); sc.inputs['Scale'].default_value = 4; sc.inputs['Detail'].default_value = 15; sc.inputs['Roughness'].default_value = .75
    nt.links.new(tc.outputs['Object'], sc.inputs['Vector'])
    scr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sc.outputs['Fac'], scr.inputs[0]); scr.inputs[1].default_value = .62; scr.inputs[2].default_value = .66
    hgt = nt.nodes.new('ShaderNodeMath'); hgt.operation = 'MULTIPLY_ADD'; nt.links.new(op.outputs['Fac'], hgt.inputs[0]); hgt.inputs[1].default_value = .2; nt.links.new(scr.outputs[0], hgt.inputs[2])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .12; bp.inputs['Distance'].default_value = .001
    nt.links.new(hgt.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    return m

def world_sky3(elev=8, rot=0, strength=1.0, sun_size=1.0, air=1.0, aerosol=1.6, clouds=.45, cloud_scale=.9, cloud_tint=(1, .97, .92)):
    """Physical sky + a high cirrus/cumulus layer projected onto the sky dome (cheap, lights the scene too)."""
    s = world_sky(elev, rot, strength, sun_size, air, aerosol)
    if clouds <= 0: return s
    nt = bpy.context.scene.world.node_tree; bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mz = nt.nodes.new('ShaderNodeMath'); mz.operation = 'MAXIMUM'; nt.links.new(sep.outputs['Z'], mz.inputs[0]); mz.inputs[1].default_value = .03
    px = nt.nodes.new('ShaderNodeMath'); px.operation = 'DIVIDE'; nt.links.new(sep.outputs['X'], px.inputs[0]); nt.links.new(mz.outputs[0], px.inputs[1])
    py = nt.nodes.new('ShaderNodeMath'); py.operation = 'DIVIDE'; nt.links.new(sep.outputs['Y'], py.inputs[0]); nt.links.new(mz.outputs[0], py.inputs[1])
    cmb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(px.outputs[0], cmb.inputs[0]); nt.links.new(py.outputs[0], cmb.inputs[1])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.noise_dimensions = '2D'; nz.inputs['Scale'].default_value = cloud_scale; nz.inputs['Detail'].default_value = 12; nz.inputs['Roughness'].default_value = .62
    nz.inputs['Distortion'].default_value = .4; nt.links.new(cmb.outputs[0], nz.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(nz.outputs['Fac'], cr.inputs[0]); cr.inputs[1].default_value = .58 - .12 * clouds; cr.inputs[2].default_value = .78
    hf = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(sep.outputs['Z'], hf.inputs[0]); hf.inputs[1].default_value = .02; hf.inputs[2].default_value = .25
    msk = nt.nodes.new('ShaderNodeMath'); msk.operation = 'MULTIPLY'; nt.links.new(cr.outputs[0], msk.inputs[0]); nt.links.new(hf.outputs[0], msk.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.use_clamp = True; nt.links.new(msk.outputs[0], m2.inputs[0]); m2.inputs[1].default_value = .9
    # cloud colour = sky radiance brightened and tinted (so dawn clouds glow warm)
    br = nt.nodes.new('ShaderNodeMix'); br.data_type = 'RGBA'; br.blend_type = 'MULTIPLY'; br.inputs['Factor'].default_value = 1
    nt.links.new(s.outputs[0], br.inputs[6]); br.inputs[7].default_value = (*[c * 1.9 for c in cloud_tint], 1)
    ad = nt.nodes.new('ShaderNodeMix'); ad.data_type = 'RGBA'; ad.blend_type = 'ADD'; ad.inputs['Factor'].default_value = 1
    nt.links.new(br.outputs[2], ad.inputs[6]); ad.inputs[7].default_value = (.02, .02, .022, 1)
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; nt.links.new(m2.outputs[0], mx.inputs['Factor'])
    nt.links.new(s.outputs[0], mx.inputs[6]); nt.links.new(ad.outputs[2], mx.inputs[7]); nt.links.new(mx.outputs[2], bg.inputs[0])
    return s

def post(haze=(.6, .66, .75), haze_amt=.55, mist_start=15, mist_depth=350, bloom=.6, ca=.006, vignette=.35):
    """Compositor: aerial perspective from the mist pass, bloom, lateral chromatic aberration, vignette."""
    sc = bpy.context.scene; vl = bpy.context.view_layer; vl.use_pass_mist = True
    w = sc.world; w.mist_settings.start = mist_start; w.mist_settings.depth = mist_depth; w.mist_settings.falloff = 'QUADRATIC'
    t = bpy.data.node_groups.new('post', 'CompositorNodeTree'); sc.compositing_node_group = t
    t.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = t.nodes.new('CompositorNodeRLayers'); out = t.nodes.new('NodeGroupOutput')
    cur = rl.outputs['Image']
    if haze_amt > 0:
        mm = t.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.use_clamp = True; t.links.new(rl.outputs['Mist'], mm.inputs[0]); mm.inputs[1].default_value = haze_amt
        mx = t.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; t.links.new(mm.outputs[0], mx.inputs['Factor'])
        t.links.new(cur, mx.inputs[6]); mx.inputs[7].default_value = (*haze, 1); cur = mx.outputs[2]
    if bloom > 0:
        g = t.nodes.new('CompositorNodeGlare'); t.links.new(cur, g.inputs[0])
        try:
            g.inputs['Type'].default_value = 'Bloom'; g.inputs['Quality'].default_value = 'Medium'
            g.inputs['Threshold'].default_value = 2.0; g.inputs['Strength'].default_value = bloom * .12; g.inputs['Size'].default_value = .6
        except Exception as e:
            print('glare api', e)
        cur = g.outputs[0]
    if ca > 0:
        ld = t.nodes.new('CompositorNodeLensdist'); t.links.new(cur, ld.inputs[0])
        try: ld.inputs['Dispersion'].default_value = ca; ld.inputs['Distortion'].default_value = -.008
        except Exception as e: print('lensdist api', e)
        cur = ld.outputs[0]
    if vignette > 0:
        em = t.nodes.new('CompositorNodeEllipseMask')
        try: em.inputs['Size'].default_value = (1.25, 1.25)
        except Exception: em.width = 1.25; em.height = 1.25
        bl = t.nodes.new('CompositorNodeBlur')
        try: bl.inputs['Size'].default_value = (400, 400)
        except Exception: bl.size_x = bl.size_y = 400
        t.links.new(em.outputs[0], bl.inputs[0])
        mv = t.nodes.new('ShaderNodeMapRange'); t.links.new(bl.outputs[0], mv.inputs[0]); mv.inputs[3].default_value = 1 - vignette; mv.inputs[4].default_value = 1
        mu = t.nodes.new('ShaderNodeMix'); mu.data_type = 'RGBA'; mu.blend_type = 'MULTIPLY'; mu.inputs['Factor'].default_value = 1
        t.links.new(cur, mu.inputs[6]); cmb = t.nodes.new('CompositorNodeCombineColor')
        for i in range(3): t.links.new(mv.outputs[0], cmb.inputs[i])
        t.links.new(cmb.outputs[0], mu.inputs[7]); cur = mu.outputs[2]
    t.links.new(cur, out.inputs[0])
    return t

def realism(sc, shutter=.3):
    """Render settings shared by v3 shots: motion blur, light tree, more transparent bounces for leaf cut-outs."""
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = shutter
    c = sc.cycles; c.transparent_max_bounces = 16; c.use_light_tree = True; c.adaptive_threshold = .04
    c.diffuse_bounces = 2; c.transmission_bounces = 4; c.glossy_bounces = 2; c.max_bounces = 6

def world_hdri(name, strength=1.0, rot=0.0):
    sc = bpy.context.scene; w = bpy.data.worlds.new('hdri'); sc.world = w; w.use_nodes = True; nt = w.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, rot)
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(os.path.join(TEX, 'hdri', name + '.exr'))
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], env.inputs['Vector'])
    bg = nt.nodes['Background']; bg.inputs[1].default_value = strength; nt.links.new(env.outputs[0], bg.inputs[0])
    return w

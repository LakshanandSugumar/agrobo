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
    r, n = noise_color(nt, .8, (.10, .068, .045), (.26, .18, .115), coord=pos)
    r2, n2 = noise_color(nt, 9.0, (.55, .55, .55), (1.15, 1.12, 1.1), coord=pos)
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
    nt.links.new(r.outputs[0], mul.inputs[6]); nt.links.new(r2.outputs[0], mul.inputs[7]); nt.links.new(mul.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .92 - .4 * wet
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
    body = mat_basic(name + '_paint', (.035, .04, .042), rough=.32, coat=.6)
    gold = mat_basic(name + '_gold', accent, rough=.25, metal=1)
    tyre = mat_basic(name + '_tyre', (.012, .012, .012), rough=.85)
    alu = mat_basic(name + '_alu', (.7, .7, .72), rough=.3, metal=1)
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
    return root

def drone(name, coll=None):
    root = link(bpy.data.objects.new(name, None), coll)
    body = mat_basic(name + '_body', (.05, .055, .06), rough=.3, coat=.5); carbon = mat_basic(name + '_cf', (.015, .015, .015), rough=.35)
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

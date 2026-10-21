"""Reusable tomato field: raised beds, drip tape, instanced plants, horizon trees."""
import bpy, math, random
from mathutils import Vector
import lib

def build(rows=16, length=70, spacing=.5, row_gap=1.6, growth=1.0, fruit=0, variants=5, plants=True, tilled=True, ripe=0.0, seed=1, skip=None, tree_gap=0):
    rnd = random.Random(seed)
    lib_coll = bpy.data.collections.new('plant_lib'); bpy.context.scene.collection.children.link(lib_coll)
    bpy.context.view_layer.layer_collection.children['plant_lib'].exclude = True
    leaf = lib.mat_leaf(); stem = lib.mat_basic('stem', (.09, .16, .05), rough=.6)
    fm = [lib.mat_tomato('tom_g', (.18, .32, .05)), lib.mat_tomato('tom_o', (.55, .18, .02)), lib.mat_tomato('tom_r', (.45, .03, .015))]
    fruit_mats = fm[:1] if ripe < .3 else (fm if ripe < .8 else fm[1:])
    var = []
    for v in range(variants):
        c = bpy.data.collections.new(f'pv{v}'); lib_coll.children.link(c)
        lib.tomato_plant(f'p{v}', seed * 100 + v, height=.85, leaves=9 + v % 3, mat_leaf_=leaf, mat_stem=stem, coll=c, fruit_mats=fruit_mats, fruit=fruit)
        var.append(c)
    field = bpy.data.collections.new('field'); bpy.context.scene.collection.children.link(field)
    soil = lib.mat_soil('soil'); bed = lib.mat_soil('bed')
    g = lib.add_prim('plane', 'ground', soil, field, size=1, location=(0, 0, 0)); g.scale = (900, 900, 1)
    tape = lib.mat_basic('tape', (.01, .01, .01), rough=.35)
    for r in range(rows):
        y = (r - (rows - 1) / 2) * row_gap
        b = lib.bevel(lib.add_prim('cube', f'bed{r}', bed, field, size=1, location=(length / 2 - 5, y, .06)), .08, 3); b.scale = (length + 10, .8, .16)
        sub = b.modifiers.new('s', 'SUBSURF'); sub.levels = sub.render_levels = 0
        rm = b.modifiers.new('rm', 'REMESH') if False else None
        t = lib.add_prim('cylinder', f'tape{r}', tape, field, radius=.012, depth=length + 10, location=(length / 2 - 5, y + .12, .145), rotation=(0, math.pi / 2, 0), vertices=8)
        if plants:
            for i in range(int(length / spacing)):
                x = i * spacing + rnd.uniform(-.05, .05)
                if skip and skip(x, y): continue
                s = growth * rnd.uniform(.85, 1.12)
                lib.instance_collection(var[rnd.randrange(variants)], f'pl{r}_{i}', (x, y + rnd.uniform(-.04, .04), .13), rnd.uniform(0, 6.28), s, field)
    # horizon tree lines and far hills
    treem = lib.mat_leaf('tree', (.025, .05, .015), (.05, .09, .03))
    tex = bpy.data.textures.new('treenoise', 'CLOUDS'); tex.noise_scale = .6
    for k in range(140):
        x = rnd.uniform(160, 320); y = rnd.uniform(-420, 420); r_ = rnd.uniform(3, 8)
        if abs(y) < tree_gap: continue
        o = lib.add_prim('ico_sphere', f'tree{k}', treem, field, radius=r_, location=(x, y, r_ * .9), subdivisions=5); o.scale = (1, 1, rnd.uniform(.7, 1.2))
        dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tex; dm.strength = r_ * .45; lib.smooth(o)
    return field

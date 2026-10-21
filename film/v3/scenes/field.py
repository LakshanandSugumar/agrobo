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


# ============================== v3 field ==============================
def bed_mesh(name, length, mat, coll, x0=-5, y=0, seed=0):
    """Mounded soil bed: rounded trapezoid cross-section, slumped shoulders, displaced crumbly surface."""
    import bmesh
    from mathutils import Vector
    rnd = random.Random(seed); bm = bmesh.new()
    prof = [(-.62, 0), (-.5, .05), (-.42, .12), (-.36, .155), (-.2, .165), (0, .17), (.2, .165), (.36, .155), (.42, .12), (.5, .05), (.62, 0)]
    nx = int(length / .2); rows = []
    for i in range(nx + 1):
        x = x0 + i * .2; wob = .03 * math.sin(x * .7 + seed) + rnd.uniform(-.01, .01)
        rows.append([bm.verts.new((x, y + py * (1 + rnd.uniform(-.03, .03)) + wob, pz * rnd.uniform(.92, 1.06))) for py, pz in prof])
    for a, b in zip(rows, rows[1:]):
        for k in range(len(prof) - 1): bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
    o = lib.mesh_obj(name, bm, mat, coll)
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = sub.render_levels = 1
    tex = bpy.data.textures.get('clods') or bpy.data.textures.new('clods', 'CLOUDS')
    tex.noise_scale = .05; tex.noise_depth = 3
    d = o.modifiers.new('clods', 'DISPLACE'); d.texture = tex; d.strength = .025; d.texture_coords = 'GLOBAL'
    return o

def tree_lines(coll, R, near=150, far=320, count=200, gap=0, cards=1100, xdir=1, swap=False):
    """Instanced card trees in irregular hedgerows / copses along the horizon."""
    cardm = [lib.mat_card(f'twig{k}', f'twig{k}.png') for k in range(4)]; bark = lib.mat_bark()
    lib_c = bpy.data.collections.new('tree_lib'); bpy.context.scene.collection.children.link(lib_c)
    bpy.context.view_layer.layer_collection.children['tree_lib'].exclude = True
    var = []; bush = []
    for k in range(5):
        c = bpy.data.collections.new(f'tree{k}'); lib_c.children.link(c)
        lib.tree3(f'tree{k}', 50 + k, height=R.uniform(10, 16), crown=R.uniform(5, 7.5), card_mats=cardm, bark=bark, coll=c, cards=int(cards * 1.6))
        var.append(c)
    for k in range(3):
        c = bpy.data.collections.new(f'bush{k}'); lib_c.children.link(c)
        lib.tree3(f'bush{k}', 80 + k, height=R.uniform(3.5, 5.5), crown=R.uniform(2.2, 3.2), card_mats=cardm, bark=bark, coll=c, cards=int(cards * .5))
        bush.append(c)
    hedges = [(R.uniform(near, far), R.uniform(-.25, .25)) for _ in range(5)]
    for k in range(count):
        hx, ang = hedges[k % len(hedges)]
        y = R.uniform(-380, 380)
        if abs(y) < gap: continue
        x = (hx + y * math.tan(ang) + R.uniform(-6, 6)) * xdir
        if swap: x, y = y, -x
        lib.instance_collection(var[R.randrange(len(var))], 'tree', (x, y, 0), R.uniform(0, 6.28), R.uniform(.75, 1.25), coll)
        for _ in range(2):  # understorey shrubs fill the hedgerow
            bx, by = x + R.uniform(-6, 6), y + R.uniform(-9, 9)
            lib.instance_collection(bush[R.randrange(len(bush))], 'bush', (bx, by, 0), R.uniform(0, 6.28), R.uniform(.8, 1.3), coll)

def build3(rows=16, length=70, spacing=.5, row_gap=1.6, growth=1.0, fruit=0, variants=6, plants=True, ripe=0.0, seed=1, skip=None,
           tree_gap=0, trees=True, x0=-5, dry=.45):
    rnd = random.Random(seed)
    lib_coll = bpy.data.collections.new('plant_lib'); bpy.context.scene.collection.children.link(lib_coll)
    bpy.context.view_layer.layer_collection.children['plant_lib'].exclude = True
    leafm = [lib.mat_leaf_tex(f'leaf{k}', k) for k in range(3)] + [lib.mat_leaf_tex('leaf_old', 1, old=True)]
    stem = lib.mat_stem3()
    fm = [lib.mat_tomato3('tom_g', 0, sss=False), lib.mat_tomato3('tom_t', .5, sss=False), lib.mat_tomato3('tom_r', 1, sss=False)]
    fruit_mats = fm[:1] if ripe < .3 else (fm if ripe < .8 else fm[1:])
    var = []
    for v in range(variants):
        c = bpy.data.collections.new(f'pv{v}'); lib_coll.children.link(c)
        lib.tomato_plant3(f'p{v}', seed * 100 + v, height=.9 * rnd.uniform(.85, 1.1), leaves=14 + v % 4, leaf_mats=leafm, stem_mat=stem, coll=c,
                          fruit=fruit, fruit_mats=fruit_mats, calyx_mat=stem)
        var.append(c)
    fld = bpy.data.collections.new('field'); bpy.context.scene.collection.children.link(fld)
    g = lib.add_prim('plane', 'ground', lib.mat_grassland('grassland', dry), fld, size=1, location=(0, 0, -.01)); g.scale = (1200, 1200, 1)
    soil = lib.mat_soil('soil'); bedm = lib.mat_soil('bed')
    # tilled strip under the whole field (between the beds)
    w = rows * row_gap + 2
    st = lib.add_prim('plane', 'strip', soil, fld, size=1, location=(x0 + (length + 10) / 2, 0, 0)); st.scale = (length + 10, w, 1)
    tape = lib.mat_basic('tape', (.008, .008, .008), rough=.35, coat=.3)
    for r in range(rows):
        y = (r - (rows - 1) / 2) * row_gap
        bed_mesh(f'bed{r}', length + 10, bedm, fld, x0=x0, y=y, seed=r)
        lib.add_prim('cylinder', f'tape{r}', tape, fld, radius=.009, depth=length + 10, location=(x0 + (length + 10) / 2, y + .12, .175), rotation=(0, math.pi / 2, 0), vertices=8)
        if plants:
            for i in range(int(length / spacing)):
                x = i * spacing + rnd.uniform(-.05, .05)
                if skip and skip(x, y): continue
                if rnd.random() < .025: continue  # the odd missing plant
                s = growth * rnd.uniform(.82, 1.15)
                o = lib.instance_collection(var[rnd.randrange(variants)], f'pl{r}_{i}', (x, y + rnd.uniform(-.04, .04), .15), rnd.uniform(0, 6.28), s, fld)
                o.rotation_euler.x = rnd.uniform(-.07, .07); o.rotation_euler.y = rnd.uniform(-.07, .07)
    if trees: tree_lines(fld, rnd, gap=tree_gap)
    return fld

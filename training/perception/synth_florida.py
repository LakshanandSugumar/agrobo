"""Photoreal synthetic data for the Agrobo harvester's perception, tuned to SW Florida fresh-market tomatoes.

What is Florida-specific (vs agrobo-world/synth/generate_dataset.py):
  - raised beds on 1.83 m centres under plastic mulch (black, white or silver), sandy row middles;
  - staked plants (wooden stakes every 2 plants, twine weave), fruit band ~0.45-1.4 m above ground;
  - fruit grows in trusses with a peduncle, pedicels and a calyx; ripeness runs proximal (ripest) to distal;
  - four ripeness classes, because Florida rounds are mostly picked MATURE-GREEN and ethylene-ripened:
        1 tomato_immature_green  (leave on the vine)
        2 tomato_mature_green    (main pick target)
        3 tomato_breaker_turning (pick, separate stream)
        4 tomato_ripe            (pick for vine-ripe / local market)
        5 weed
  - three camera rigs matching the harvester (hardware thread): mast stereo (~1.8 m, looking down the row),
    arm-height side view (~0.95 m, facing the row) and the eye-in-hand D405 (15-50 cm from a truss).

Output layout is the same as agrobo-world's generator, so masks_to_yolo.py reads either:
  images/NNNNNN.png, masks/NNNNNN.png (R + 256*G = instance, B = class id), annotations.json (COCO).

Run (Blender as a Python module, `pip install bpy`):
  python synth_florida.py --n 2000 --out data/synth_fl --res 960 720 --spp 32 --seed 0 [--device GPU]
"""
import sys, os, math, random, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.environ.get('AGROBO_WORLD', os.path.join(HERE, '..', '..', 'agrobo-world'))
sys.path.insert(0, os.path.join(WORLD, 'scenes'))
import bpy, bmesh, lib
from mathutils import Vector, Matrix
import numpy as np

CATS = [{'id': 1, 'name': 'tomato_immature_green'}, {'id': 2, 'name': 'tomato_mature_green'},
        {'id': 3, 'name': 'tomato_breaker_turning'}, {'id': 4, 'name': 'tomato_ripe'}, {'id': 5, 'name': 'weed'}]
BED_PITCH = 1.83

def set_device(kind):
    """Use the RTX card through OptiX/CUDA when asked; fall back to CPU silently."""
    sc = bpy.context.scene
    if kind == 'CPU': sc.cycles.device = 'CPU'; return 'CPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for backend in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
        try:
            prefs.compute_device_type = backend; prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == backend]
            if devs:
                for d in prefs.devices: d.use = d.type == backend
                sc.cycles.device = 'GPU'; return backend
        except TypeError:
            continue
    sc.cycles.device = 'CPU'; return 'CPU'

def mat_mulch(R):
    kind = R.choices(['black', 'white', 'silver'], [.5, .3, .2])[0]
    col = {'black': (.012, .012, .014), 'white': (.75, .75, .72), 'silver': (.55, .56, .58)}[kind]
    return lib.mat_basic('mulch_' + kind, col, rough=R.uniform(.25, .5), metal=.6 if kind == 'silver' else 0, coat=.3)

def fruit_mats(R):
    # base colours in linear RGB; each sample jitters them so the boundary between classes is learnt, not memorised
    j = lambda c, s=.12: tuple(max(0, x * R.uniform(1 - s, 1 + s)) for x in c)
    return {1: lib.mat_tomato('imm', j((.05, .13, .025))),
            2: lib.mat_tomato('mg', j((.20, .32, .10))),       # lighter, whitish, glossy
            3: lib.mat_tomato('brk', j((.48, .26, .045))),
            4: lib.mat_tomato('ripe', j((.42, .025, .012)))}

def calyx(bm, top, R):
    for k in range(5):
        a = k / 5 * 6.28 + R.uniform(-.2, .2)
        lib.leaflet(bm, top, Vector((math.cos(a), math.sin(a), -.35)), R.uniform(.018, .03), .007, .004, segs=3)

def truss(name, base, out, stage, R, mats, stem_bm, cal_bm, labels):
    """A peduncle hanging off the main stem with 3-6 fruit; proximal fruit are the most mature."""
    n = R.randint(3, 6); L = R.uniform(.12, .22)
    tip = base + out * L + Vector((0, 0, -R.uniform(.05, .12)))
    bmesh.ops.create_cone(stem_bm, cap_ends=False, segments=5, radius1=.004, radius2=.003, depth=(tip - base).length,
                          matrix=Matrix.Translation((base + tip) / 2) @ (tip - base).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    for f in range(n):
        cls = max(1, min(4, stage - (f // 2) + R.choice([0, 0, 0, -1])))
        r = {1: R.uniform(.014, .028), 2: R.uniform(.03, .040), 3: R.uniform(.031, .041), 4: R.uniform(.032, .042)}[cls]
        p = base.lerp(tip, (f + .5) / n)
        side = out.cross(Vector((0, 0, 1))).normalized() * R.uniform(-.05, .05)
        c = p + side + Vector((0, 0, -R.uniform(.03, .06) - r))
        bmesh.ops.create_cone(stem_bm, cap_ends=False, segments=4, radius1=.002, radius2=.0015, depth=max(.005, (p - c).length - r),
                              matrix=Matrix.Translation((p + c + Vector((0, 0, r))) / 2) @ (p - c).to_track_quat('Z', 'Y').to_matrix().to_4x4())
        o = lib.add_prim('uv_sphere', f'{name}_f{f}', mats[cls], None, radius=r, segments=32, ring_count=16, location=c)
        o.scale = (R.uniform(1, 1.08), R.uniform(1, 1.08), R.uniform(.78, .9)); o.rotation_euler.z = R.uniform(0, 6.28); lib.smooth(o)
        calyx(cal_bm, c + Vector((0, 0, r * .85)), R)
        labels.append((o, cls))

def build(R, args):
    lib.reset((args.res[0], args.res[1]), samples=args.spp)
    sc = bpy.context.scene
    lib.world_sky(elev=R.uniform(8, 75), rot=R.uniform(0, 360), strength=R.uniform(.35, .8), aerosol=R.uniform(.8, 4))
    sc.view_settings.exposure = R.uniform(-1.6, -.3)
    sand = lib.mat_soil('sand'); sand.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.32, .27, .19, 1) if R.random() < .5 else (.18, .15, .11, 1)
    g = lib.add_prim('plane', 'ground', sand, None, size=1); g.scale = (60, 60, 1)
    mulch = mat_mulch(R)
    if not mulch.name.startswith('mulch_black'): sc.view_settings.exposure -= .8   # white / silver mulch: keep it off the clip
    leaf = lib.mat_leaf('leaf', (R.uniform(.03, .07), R.uniform(.11, .2), .03), (R.uniform(.07, .11), R.uniform(.19, .28), .05))
    stem = lib.mat_basic('stem', (.09, .16, .05), rough=.6)
    stake_m = lib.mat_basic('stake', (R.uniform(.18, .3), R.uniform(.12, .18), .07), rough=.9)
    twine = lib.mat_basic('twine', (.6, .55, .4) if R.random() < .5 else (.05, .05, .05), rough=.8)
    mats = fruit_mats(R)
    labels = []; stem_bm = bmesh.new(); cal_bm = bmesh.new(); stake_bm = bmesh.new(); twine_bm = bmesh.new()
    rows = (-1, 0, 1); spacing = R.uniform(.45, .6); nplants = 12
    for ri in rows:
        y = ri * BED_PITCH
        bed = lib.add_prim('cube', 'bed', mulch, None, size=1, location=(3, y, .1)); bed.scale = (14, R.uniform(.76, .9), .2)
        for i in range(nplants):
            x = i * spacing + R.uniform(-.04, .04)
            h = R.uniform(1.05, 1.5)
            # lib's plant has film-scale leaflets (~20 cm); build it tall and shrink it so leaflets are a real 8-12 cm
            k = R.uniform(.55, .65)
            p = lib.tomato_plant(f'p{ri}_{i}', R.randrange(10 ** 6), height=h / k, leaves=R.randint(14, 20), mat_leaf_=leaf, mat_stem=stem)
            p.location = (x, y, .2); p.rotation_euler.z = R.uniform(0, 6.28)
            p.scale = (k * R.uniform(.9, 1.1), k * R.uniform(.9, 1.1), k)
            stage = R.choices([1, 2, 3, 4], [.25, .45, .18, .12])[0]
            for t in range(R.randint(2, 5)):
                bh = .2 + R.uniform(.25, 1.2)   # truss height above ground: fruit band ~0.45-1.4 m
                a = R.uniform(0, 6.28); out = Vector((math.cos(a), math.sin(a), 0))
                truss(f't{ri}_{i}_{t}', Vector((x, y, bh)), out, stage, R, mats, stem_bm, cal_bm, labels)
            if i % 2 == 0:   # stake between every second plant
                sx = x + spacing / 2
                bmesh.ops.create_cube(stake_bm, size=1, matrix=Matrix.Translation((sx, y + R.uniform(-.03, .03), .2 + .65)) @ Matrix.Diagonal((.025, .025, 1.3, 1)))
        for zh in (.45, .7, .95, 1.2):   # twine weave, both sides of the plants
            for s in (-1, 1):
                a = Vector((-.2, y + s * .05, zh)); b = Vector((nplants * spacing, y + s * .05, zh))
                bmesh.ops.create_cone(twine_bm, cap_ends=False, segments=4, radius1=.0015, radius2=.0015, depth=(b - a).length,
                                      matrix=Matrix.Translation((a + b) / 2) @ (b - a).to_track_quat('Z', 'Y').to_matrix().to_4x4())
    lib.mesh_obj('peduncles', stem_bm, stem); lib.mesh_obj('calyxes', cal_bm, leaf); lib.mesh_obj('stakes', stake_bm, stake_m, smooth=False)
    lib.mesh_obj('twine', twine_bm, twine)
    wm = lib.mat_leaf('weed', (R.uniform(.1, .2), .2, .04), (.28, .32, .07))
    for k in range(R.randint(3, 25)):   # weeds live in the sandy row middles and in planting holes
        bm = bmesh.new()
        for j in range(R.randint(5, 12)):
            a = j / 8 * 6.28; lib.leaflet(bm, Vector((0, 0, 0)), Vector((math.cos(a), math.sin(a), R.uniform(.2, .9))), R.uniform(.04, .14), .03, .02, segs=3)
        w = lib.mesh_obj(f'weed{k}', bm, wm)
        mid = R.choice([-.5, .5]) * BED_PITCH
        w.location = (R.uniform(-.5, nplants * spacing), mid + R.uniform(-.45, .45), 0); w.scale = (R.uniform(.6, 1.6),) * 3
        labels.append((w, 5))
    # camera rigs: the harvester drives the row middle at y = +-BED_PITCH/2
    rig = R.choices(['mast', 'arm', 'hand', 'drone'], [.25, .35, .3, .1])[0]
    cy = R.choice([-.5, .5]) * BED_PITCH; face = -1 if cy > 0 else 1; x0 = R.uniform(1, nplants * spacing - 1.5)
    if rig == 'mast':
        lib.camera(lens=R.uniform(18, 28), loc=(x0, cy, R.uniform(1.6, 2.0)), target=(x0 + R.uniform(1.5, 3), cy + face * R.uniform(.5, .9), .7))
    elif rig == 'arm':
        lib.camera(lens=R.uniform(20, 30), loc=(x0, cy + face * R.uniform(0, .25), R.uniform(.75, 1.15)), target=(x0 + R.uniform(-.3, .3), cy + face * BED_PITCH / 2, R.uniform(.5, 1.2)))
    elif rig == 'hand':
        fruit = [o for o, c in labels if c <= 4 and abs(o.location.y - (cy + face * BED_PITCH / 2)) < .5]
        tgt = R.choice(fruit).location if fruit else Vector((x0, cy + face * BED_PITCH / 2, .8))
        d = R.uniform(.15, .5); a = R.uniform(-.6, .6); e = R.uniform(-.4, .5)
        loc = Vector((tgt.x + d * math.sin(a), tgt.y - face * d * math.cos(a) * math.cos(e), tgt.z + d * math.sin(e)))
        lib.camera(lens=R.uniform(14, 20), loc=tuple(loc), target=tuple(tgt))   # D405-like wide FOV, short range
    else:
        lib.camera(lens=28, loc=(x0, cy + R.uniform(-.5, .5), R.uniform(2.5, 4)), target=(x0, cy + R.uniform(-.5, .5), 0))
    return sc, labels, rig

def render_mask(sc, labels, path):
    """Second pass: flat unique emission colour per labelled instance, black elsewhere (same scheme as agrobo-world)."""
    lin = lambda c: (c / 255 / 12.92) if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4
    black = lib.emissive('m_black', (0, 0, 0), 0)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(black)
    for idx, (o, cid) in enumerate(labels, start=1):
        m = lib.emissive(f'm{idx}', (lin(idx % 256), lin(idx // 256), lin(cid)), 1); o.data.materials.clear(); o.data.materials.append(m)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0
    sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.cycles.filter_width = .01; sc.render.dither_intensity = 0
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0; sc.view_settings.gamma = 1
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=10); ap.add_argument('--out', default='data/synth_fl')
    ap.add_argument('--res', type=int, nargs=2, default=[960, 720]); ap.add_argument('--spp', type=int, default=32)
    ap.add_argument('--seed', type=int, default=0); ap.add_argument('--device', default='GPU', choices=['GPU', 'CPU'])
    args = ap.parse_args(argv)
    from PIL import Image
    os.makedirs(f'{args.out}/images', exist_ok=True); os.makedirs(f'{args.out}/masks', exist_ok=True)
    jp = f'{args.out}/annotations.json'
    coco = json.load(open(jp)) if os.path.exists(jp) else {'images': [], 'annotations': [], 'categories': CATS}
    done = {im['file_name'] for im in coco['images']}
    for s in range(args.seed, args.seed + args.n):
        name = f'{s:06d}.png'
        if f'images/{name}' in done: continue
        R = random.Random(s); sc, labels, rig = build(R, args)
        dev = set_device(args.device)
        sc.render.filepath = f'{args.out}/images/{name}'; bpy.ops.render.render(write_still=True)
        render_mask(sc, labels, f'{args.out}/masks/{name}')
        m = np.array(Image.open(f'{args.out}/masks/{name}').convert('RGB')).astype(int)
        ids = m[..., 0] + 256 * m[..., 1]
        img_id = max([im['id'] for im in coco['images']], default=0) + 1
        coco['images'].append({'id': img_id, 'file_name': f'images/{name}', 'mask_file': f'masks/{name}', 'width': args.res[0],
                               'height': args.res[1], 'seed': s, 'rig': rig})
        n = 0
        for idx, (o, cid) in enumerate(labels, start=1):
            ys, xs = np.nonzero(ids == idx)
            if len(xs) < 12: continue  # fully occluded or off-screen
            coco['annotations'].append({'id': len(coco['annotations']) + 1, 'image_id': img_id, 'category_id': cid, 'instance_value': idx,
                                        'bbox': [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
                                        'area': int(len(xs)), 'iscrowd': 0})
            n += 1
        tmp = jp + '.tmp'; json.dump(coco, open(tmp, 'w')); os.replace(tmp, jp)
        print(f'sample {s} [{rig}, {dev}]: {n} labelled objects', flush=True)

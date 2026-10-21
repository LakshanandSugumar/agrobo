"""Photoreal synthetic training data for Agrobo perception (ripeness detection + weed detection).
Each sample: randomised field patch, sun, camera pose, ripeness and weeds -> RGB image, instance mask, COCO labels.
Run: <blender-python> generate_dataset.py --n 200 --out ./dataset [--res 960 720] [--spp 16] [--seed 0]"""
import sys, os, math, random, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scenes'))
import bpy, bmesh, lib
from mathutils import Vector
import numpy as np

CATS = [{'id': 1, 'name': 'tomato_ripe'}, {'id': 2, 'name': 'tomato_turning'}, {'id': 3, 'name': 'tomato_unripe'}, {'id': 4, 'name': 'weed'}]

def build(R):
    lib.reset((args.res[0], args.res[1]), samples=args.spp)
    sc = bpy.context.scene
    lib.world_sky(elev=R.uniform(6, 60), rot=R.uniform(0, 360), strength=R.uniform(.35, .7), aerosol=R.uniform(.8, 3.5))
    sc.view_settings.exposure = R.uniform(-1.4, -.4)
    soil = lib.mat_soil('soil'); g = lib.add_prim('plane', 'ground', soil, None, size=1); g.scale = (60, 60, 1)
    leaf = lib.mat_leaf('leaf', (R.uniform(.03, .07), R.uniform(.12, .2), .03), (R.uniform(.07, .11), R.uniform(.2, .28), .05))
    stem = lib.mat_basic('stem', (.09, .16, .05), rough=.6)
    fm = {1: lib.mat_tomato('ripe', (R.uniform(.38, .55), .025, .012)), 2: lib.mat_tomato('turning', (.55, R.uniform(.15, .3), .02)), 3: lib.mat_tomato('unripe', (.18, R.uniform(.28, .36), .05))}
    ripe_p = R.uniform(.1, .7)
    labels = []   # (object, category_id)
    for r in range(3):
        y = (r - 1) * 1.6
        bed = lib.add_prim('cube', 'bed', lib.mat_soil('bed'), None, size=1, location=(4, y, .06)); bed.scale = (12, .8, .16)
        for i in range(10):
            p = lib.tomato_plant(f'p{r}_{i}', R.randrange(10 ** 6), height=R.uniform(.75, 1.0), leaves=R.randint(10, 14), mat_leaf_=leaf, mat_stem=stem)
            p.location = (i * .5 + R.uniform(-.05, .05), y, .13); p.rotation_euler.z = R.uniform(0, 6.28)
            for f in range(R.randint(3, 7)):
                cid = 1 if R.random() < ripe_p else R.choice([2, 3, 3])
                a = R.uniform(0, 6.28); rr = R.uniform(.08, .2); h = R.uniform(.25, .65)
                o = lib.add_prim('uv_sphere', f'fruit_{r}_{i}_{f}', fm[cid], None, radius=R.uniform(.028, .042), segments=32, ring_count=16,
                                 location=(p.location.x + math.cos(a) * rr, y + math.sin(a) * rr, .13 + h)); o.scale = (1, 1, .87); lib.smooth(o)
                labels.append((o, cid))
    wm = lib.mat_leaf('weed', (.15, .2, .04), (.28, .3, .07))
    for k in range(R.randint(4, 20)):
        bm = bmesh.new()
        for j in range(R.randint(5, 10)):
            a = j / 8 * 6.28; lib.leaflet(bm, Vector((0, 0, 0)), Vector((math.cos(a), math.sin(a), .5)), R.uniform(.05, .11), .03, .02, segs=3)
        w = lib.mesh_obj(f'weed{k}', bm, wm); w.location = (R.uniform(-.5, 5), R.choice([-.8, .8]) + R.uniform(-.3, .3), 0)
        labels.append((w, 4))
    # robot-eye camera in a furrow looking at a bed, or overhead scout view
    if R.random() < .7:
        cy = R.choice([-.8, .8]); tgt = (R.uniform(.5, 4), cy + (-1 if cy > 0 else 1) * R.uniform(.6, .9), R.uniform(.3, .7))
        lib.camera(lens=R.uniform(24, 40), loc=(tgt[0] + R.uniform(-.8, .8), cy, R.uniform(.35, 1.1)), target=tgt)
    else:
        lib.camera(lens=28, loc=(R.uniform(1, 3.5), R.uniform(-1, 1), R.uniform(1.8, 3)), target=(R.uniform(1, 3.5), R.uniform(-1, 1), 0))
    return sc, labels

def render_mask(sc, labels, path):
    """Second pass: flat unique emission colour per labelled instance, black elsewhere."""
    lin = lambda c: (c / 255 / 12.92) if c / 255 <= .04045 else ((c / 255 + .055) / 1.055) ** 2.4
    black = lib.emissive('m_black', (0, 0, 0), 0)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for i in range(len(o.data.materials)): o.data.materials[i] = black
    for idx, (o, cid) in enumerate(labels, start=1):
        # pre-linearise so the sRGB view writes the exact integer codes (R,G = instance index, B = class id)
        m = lib.emissive(f'm{idx}', (lin(idx % 256), lin(idx // 256), lin(cid)), 1); o.data.materials.clear(); o.data.materials.append(m)
    sc.world.node_tree.nodes['Background'].inputs[1].default_value = 0
    sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.cycles.filter_width = .01; sc.render.dither_intensity = 0
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0; sc.view_settings.gamma = 1
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=10); ap.add_argument('--out', default='dataset')
    ap.add_argument('--res', type=int, nargs=2, default=[960, 720]); ap.add_argument('--spp', type=int, default=16); ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args(argv)
    from PIL import Image
    os.makedirs(f'{args.out}/images', exist_ok=True); os.makedirs(f'{args.out}/masks', exist_ok=True)
    jp = f'{args.out}/annotations.json'
    coco = json.load(open(jp)) if os.path.exists(jp) else {'images': [], 'annotations': [], 'categories': CATS}
    done = {im['file_name'] for im in coco['images']}
    for s in range(args.seed, args.seed + args.n):
        name = f'{s:06d}.png'
        if f'images/{name}' in done: continue
        R = random.Random(s); sc, labels = build(R)
        sc.render.filepath = f'{args.out}/images/{name}'; bpy.ops.render.render(write_still=True)
        render_mask(sc, labels, f'{args.out}/masks/{name}')
        m = np.array(Image.open(f'{args.out}/masks/{name}').convert('RGB')).astype(int)
        ids = m[..., 0] + 256 * m[..., 1]
        img_id = len(coco['images']) + 1
        coco['images'].append({'id': img_id, 'file_name': f'images/{name}', 'mask_file': f'masks/{name}', 'width': args.res[0], 'height': args.res[1], 'seed': s})
        for idx, (o, cid) in enumerate(labels, start=1):
            ys, xs = np.nonzero(ids == idx)
            if len(xs) < 12: continue  # fully occluded or off-screen
            coco['annotations'].append({'id': len(coco['annotations']) + 1, 'image_id': img_id, 'category_id': cid, 'instance_value': idx,
                                        'bbox': [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)], 'area': int(len(xs)), 'iscrowd': 0})
        json.dump(coco, open(jp, 'w'))
        print(f'sample {s}: {sum(1 for a in coco["annotations"] if a["image_id"] == img_id)} labelled objects')

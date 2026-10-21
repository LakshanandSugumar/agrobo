"""Convert one or more synthetic datasets (COCO + exact instance masks) into an Ultralytics YOLO segmentation dataset.

Works on synth_florida.py output (5 classes) and on agrobo-world/synth output (old 4-class scheme, remapped).
Polygons come from the pixel-exact masks, so occluded fruit split into several pieces stay one instance.

  python masks_to_yolo.py data/synth_fl [more dirs...] --out data/yolo_fl --val 0.1
"""
import os, json, argparse, random, shutil
import numpy as np, cv2
from PIL import Image

NAMES = ['tomato_immature_green', 'tomato_mature_green', 'tomato_breaker_turning', 'tomato_ripe', 'weed']
# category name in a source COCO -> YOLO class index above
REMAP = {'tomato_immature_green': 0, 'tomato_mature_green': 1, 'tomato_breaker_turning': 2, 'tomato_ripe': 3, 'weed': 4,
         'tomato_unripe': 1, 'tomato_turning': 2}   # agrobo-world: its "unripe" fruit are full-size, so they count as mature-green

def polygon(mask):
    """Largest outer contour; extra pieces are bridged in with zero-width seams so the instance stays one polygon."""
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cs = sorted([c.reshape(-1, 2) for c in cs if len(c) >= 3], key=lambda c: -cv2.contourArea(c))
    if not cs: return None
    out = cs[0]
    for c in cs[1:]:
        if cv2.contourArea(c) < 6: continue
        d = ((out[:, None, :] - c[None, :, :]) ** 2).sum(-1); i, j = np.unravel_index(d.argmin(), d.shape)
        c = np.roll(c, -j, axis=0)
        out = np.concatenate([out[:i + 1], c, c[:1], out[i:]])
    return out

def convert(src, dst, split_of, stats):
    coco = json.load(open(os.path.join(src, 'annotations.json')))
    cats = {c['id']: c['name'] for c in coco['categories']}
    by_img = {}
    for a in coco['annotations']: by_img.setdefault(a['image_id'], []).append(a)
    tag = os.path.basename(os.path.normpath(src))
    for im in coco['images']:
        split = split_of(f"{tag}/{im['file_name']}")
        stem = f"{tag}_{os.path.splitext(os.path.basename(im['file_name']))[0]}"
        m = np.array(Image.open(os.path.join(src, im['mask_file'])).convert('RGB')).astype(np.int32)
        ids = m[..., 0] + 256 * m[..., 1]; W, H = im['width'], im['height']
        lines = []
        for a in by_img.get(im['id'], []):
            cls = REMAP.get(cats[a['category_id']])
            if cls is None: continue
            poly = polygon(ids == a['instance_value'])
            if poly is None or len(poly) < 3: continue
            xy = (poly / [W, H]).clip(0, 1).reshape(-1)
            lines.append(f"{cls} " + ' '.join(f'{v:.5f}' for v in xy))
            stats[split][cls] += 1
        os.makedirs(f'{dst}/images/{split}', exist_ok=True); os.makedirs(f'{dst}/labels/{split}', exist_ok=True)
        shutil.copyfile(os.path.join(src, im['file_name']), f'{dst}/images/{split}/{stem}.png')
        open(f'{dst}/labels/{split}/{stem}.txt', 'w').write('\n'.join(lines) + ('\n' if lines else ''))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('src', nargs='+'); ap.add_argument('--out', default='data/yolo_fl')
    ap.add_argument('--val', type=float, default=.1); ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    # deterministic per-file split, so re-running after generating more samples never moves an image between splits
    split_of = lambda key: 'val' if random.Random(f'{a.seed}:{key}').random() < a.val else 'train'
    stats = {'train': [0] * len(NAMES), 'val': [0] * len(NAMES)}
    for s in a.src: convert(s, a.out, split_of, stats)
    out = os.path.abspath(a.out)
    with open(f'{a.out}/data.yaml', 'w') as f:
        f.write(f'path: {out}\ntrain: images/train\nval: images/val\nnames:\n' + ''.join(f'  {i}: {n}\n' for i, n in enumerate(NAMES)))
    for sp in stats:
        print(sp, ', '.join(f'{n}={c}' for n, c in zip(NAMES, stats[sp])))
    print('wrote', f'{a.out}/data.yaml')

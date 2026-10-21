"""Score the segmenter the way the harvester uses it: not just mAP, but the PICK decision.

For each ground-truth fruit in the val split, the robot must decide pick / leave:
  pick  = mature-green, breaker/turning, ripe   (Florida harvests from mature-green up)
  leave = immature green
Reports pick recall (ripe-enough fruit found), wrong-pick rate (immature fruit picked: lost yield) and the
ripeness confusion matrix, plus box/mask mAP. Works on any YOLO-format dataset with the same 5 classes,
including a real-photo set labelled later.
  python evaluate.py --weights runs/seg/fl_ripeness/weights/best.pt --data data/yolo_fl/data.yaml
"""
import argparse, glob, json, os
import numpy as np
from ultralytics import YOLO

NAMES = ['tomato_immature_green', 'tomato_mature_green', 'tomato_breaker_turning', 'tomato_ripe', 'weed']
PICK = {1, 2, 3}

def load_labels(p, W, H):
    out = []
    if os.path.exists(p):
        for line in open(p):
            v = line.split()
            if len(v) < 7: continue
            c = int(v[0]); xy = np.array(v[1:], float).reshape(-1, 2) * [W, H]
            out.append((c, [*xy.min(0), *xy.max(0)]))
    return out

def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy; u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--weights', required=True); ap.add_argument('--data', required=True)
    ap.add_argument('--conf', type=float, default=.35); ap.add_argument('--imgsz', type=int, default=640); a = ap.parse_args()
    model = YOLO(a.weights)
    val = model.val(data=a.data, imgsz=a.imgsz, split='val', plots=False, verbose=False)
    root = os.path.dirname(os.path.abspath(a.data))
    imgs = sorted(glob.glob(os.path.join(root, 'images', 'val', '*')))
    conf = np.zeros((5, 6), int)     # rows: truth class; cols: predicted class, last col = missed
    for r in model.predict(imgs, imgsz=a.imgsz, conf=a.conf, stream=True, verbose=False):
        H, W = r.orig_shape
        lab = os.path.join(root, 'labels', 'val', os.path.splitext(os.path.basename(r.path))[0] + '.txt')
        gts = load_labels(lab, W, H)
        preds = [(int(c), b.tolist()) for c, b in zip(r.boxes.cls.cpu().numpy(), r.boxes.xyxy.cpu().numpy())]
        used = set()
        for gc, gb in gts:
            best, bj = 0, None
            for j, (pc, pb) in enumerate(preds):
                if j in used: continue
                v = iou(gb, pb)
                if v > best: best, bj = v, j
            if bj is not None and best >= .5: used.add(bj); conf[gc, preds[bj][0]] += 1
            else: conf[gc, 5] += 1
    fruit = conf[:4]
    should_pick = fruit[1:4].sum(); picked_ok = fruit[1:4][:, 1:4].sum()
    imm = fruit[0].sum(); imm_picked = fruit[0, 1:4].sum()
    rep = dict(box_map50=float(val.box.map50), mask_map50=float(val.seg.map50), mask_map50_95=float(val.seg.map),
               pick_recall=float(picked_ok / max(1, should_pick)), wrong_pick_rate=float(imm_picked / max(1, imm)),
               weed_recall=float(conf[4, 4] / max(1, conf[4].sum())),
               confusion={NAMES[i]: dict(zip(NAMES + ['missed'], map(int, conf[i]))) for i in range(5)})
    out = os.path.join(os.path.dirname(os.path.dirname(a.weights)), 'pick_eval.json')
    json.dump(rep, open(out, 'w'), indent=2); print(json.dumps(rep, indent=2)); print('wrote', out)

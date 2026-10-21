"""Train the harvester's fruit-ripeness + weed segmenter (Ultralytics YOLO11-seg).

Sized for an 8 GB card (RTX 5060): yolo11s-seg at 640 px with AMP and auto batch fills ~70% of VRAM.
  python train.py --data data/yolo_fl/data.yaml                        # default: yolo11s-seg, 150 epochs
  python train.py --data data/yolo_fl/data.yaml --model yolo11m-seg.pt --imgsz 960 --batch 6   # bigger, still fits 8 GB
  python train.py --data data/yolo_fl/data.yaml --smoke                # 1 epoch on CPU, proves the pipeline
Fine-tune on real field photos later with --model runs/seg/<name>/weights/best.pt --data real.yaml --lr0 0.002.
"""
import argparse, json, os
from ultralytics import YOLO
import torch

ap = argparse.ArgumentParser()
ap.add_argument('--data', required=True); ap.add_argument('--model', default='yolo11s-seg.pt')
ap.add_argument('--epochs', type=int, default=150); ap.add_argument('--imgsz', type=int, default=640)
ap.add_argument('--batch', type=float, default=None, help='images per batch, or a 0-1 fraction of VRAM (default 0.7 on GPU)')
ap.add_argument('--name', default='fl_ripeness'); ap.add_argument('--lr0', type=float, default=0.01)
ap.add_argument('--workers', type=int, default=None); ap.add_argument('--smoke', action='store_true')
a = ap.parse_args()

gpu = torch.cuda.is_available()
if gpu:
    p = torch.cuda.get_device_properties(0)
    print(f'GPU: {p.name}, {p.total_memory / 2**30:.1f} GB, sm_{p.major}{p.minor}')
else:
    print('No CUDA GPU found: training on CPU (fine for --smoke only)')
batch = a.batch if a.batch is not None else (0.7 if gpu else 4)
batch = int(batch) if batch >= 1 else batch

model = YOLO(a.model)
res = model.train(
    data=a.data, epochs=1 if a.smoke else a.epochs, imgsz=320 if a.smoke else a.imgsz, batch=batch,
    device=0 if gpu else 'cpu', workers=a.workers if a.workers is not None else (min(8, os.cpu_count()) if gpu else 2),
    name=a.name + ('_smoke' if a.smoke else ''), project=os.path.abspath('runs/seg'), exist_ok=True, amp=gpu, cache=False,
    lr0=a.lr0, cos_lr=True, patience=40, close_mosaic=15, fraction=1.0,
    # sim-to-real: colour and lighting are where synthetic data lies most, so push those augmentations hard.
    # hsv_h stays small: hue IS the ripeness signal, a big hue shift would turn mature-green into breaker.
    hsv_h=0.008, hsv_s=0.6, hsv_v=0.5, degrees=8, translate=0.1, scale=0.5, shear=2, perspective=0.0005,
    fliplr=0.5, flipud=0.0, mosaic=1.0, mixup=0.1, copy_paste=0.2, erasing=0.3, plots=True,
)
best = os.path.join(res.save_dir, 'weights', 'best.pt') if res is not None else None
m = YOLO(best).val(data=a.data, imgsz=320 if a.smoke else a.imgsz, device=0 if gpu else 'cpu', plots=True, split='val')
names = m.names
summary = {
    'weights': best, 'gpu': torch.cuda.get_device_name(0) if gpu else 'cpu',
    'box_map50': float(m.box.map50), 'box_map50_95': float(m.box.map), 'mask_map50': float(m.seg.map50), 'mask_map50_95': float(m.seg.map),
    'per_class_mask_map50_95': {names[int(c)]: float(v) for c, v in zip(m.seg.ap_class_index, m.seg.maps[m.seg.ap_class_index])},
}
json.dump(summary, open(os.path.join(res.save_dir, 'summary.json'), 'w'), indent=2)
print(json.dumps(summary, indent=2))

"""Export the trained segmenter for the robot.
  python export.py runs/seg/fl_ripeness/weights/best.pt              # ONNX (portable, any PC)
  python export.py <best.pt> --engine                                 # TensorRT FP16 engine; run this ON the Jetson Orin
The harvester's compute (hardware thread BOM) is a Jetson; TensorRT engines are tied to the GPU they are built on,
so build the .engine on the robot itself, from the .onnx or the .pt.
"""
import argparse
from ultralytics import YOLO
ap = argparse.ArgumentParser(); ap.add_argument('weights'); ap.add_argument('--imgsz', type=int, default=640)
ap.add_argument('--engine', action='store_true'); a = ap.parse_args()
m = YOLO(a.weights)
print(m.export(format='onnx', imgsz=a.imgsz, simplify=True, dynamic=False, opset=17))
if a.engine:
    print(m.export(format='engine', imgsz=a.imgsz, half=True, device=0))

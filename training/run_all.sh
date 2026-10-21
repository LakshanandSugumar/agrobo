#!/usr/bin/env bash
# Agrobo: full training run on one Linux GPU box (own PC or rented).  bash run_all.sh [images] [pick_steps] [envs]
set -euo pipefail
cd "$(dirname "$0")"
IMAGES=${1:-2000}; PICK_STEPS=${2:-20000000}; ENVS=${3:-$(( $(nproc) > 3 ? $(nproc) - 2 : 2 ))}
export AGROBO_WORLD=$(realpath ../agrobo-world) AGROBO_ROBOTS=$(realpath ../agrobo-robots) MUJOCO_GL=egl
PY=.venv/bin/python
echo "1/5 photoreal Florida dataset ($IMAGES images)"; $PY perception/synth_florida.py --n $IMAGES --out data/synth_fl --res 960 720 --spp 32 --device GPU
echo "2/5 convert to YOLO";                          $PY perception/masks_to_yolo.py data/synth_fl ../agrobo-world/synth/sample_dataset --out data/yolo_fl
echo "3/5 train segmenter";                          $PY perception/train.py --data data/yolo_fl/data.yaml --epochs 150
$PY perception/evaluate.py --weights runs/seg/fl_ripeness/weights/best.pt --data data/yolo_fl/data.yaml
$PY perception/export.py runs/seg/fl_ripeness/weights/best.pt
echo "4/5 train picking policy ($PICK_STEPS steps, $ENVS sims)"; (cd picking && ../$PY train_ppo.py --steps $PICK_STEPS --envs $ENVS)
echo "5/5 evaluate + film";                          (cd picking && ../$PY evaluate.py --run runs/pick/ppo_fr5 --episodes 200 --video 4)

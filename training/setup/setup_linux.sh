#!/usr/bin/env bash
# Agrobo training setup for Linux (Ubuntu 22.04/24.04) + NVIDIA RTX 50-series, or a rented cloud GPU.
#   bash setup/setup_linux.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3.13}
command -v $PY >/dev/null || { echo "Need Python 3.13 (bpy 5.x). e.g. sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.13 python3.13-venv"; exit 1; }
command -v nvidia-smi >/dev/null && nvidia-smi || echo "WARNING: no nvidia-smi; CPU only"
# headless MuJoCo rendering + Blender runtime libs
sudo apt-get install -y libegl1 libgl1 libosmesa6 libxi6 libxkbcommon0 libsm6 libxrender1 libxfixes3 >/dev/null 2>&1 || true
[ -d .venv ] || $PY -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install -r requirements.txt
.venv/bin/python setup/check_env.py

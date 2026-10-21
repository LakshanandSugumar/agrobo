# Agrobo training setup for Windows + NVIDIA RTX 50-series (tested target: RTX 5060 8 GB).
# Run from the agrobo-train folder in PowerShell:   powershell -ExecutionPolicy Bypass -File setup\setup_windows.ps1
$ErrorActionPreference = "Stop"
Write-Host "== Agrobo training setup =="
# 1. Python 3.13 (bpy 5.x wheels target 3.13). Install from python.org or: winget install Python.Python.3.13
$py = "py -3.13"
try { & py -3.13 --version } catch { Write-Error "Python 3.13 not found. Install it (winget install Python.Python.3.13) and re-run."; exit 1 }
# 2. NVIDIA driver must support CUDA 12.8+ (driver 570 or newer for RTX 50-series)
try { nvidia-smi } catch { Write-Warning "nvidia-smi not found: install the latest NVIDIA Game Ready / Studio driver first." }
# 3. venv
if (-not (Test-Path .venv)) { & py -3.13 -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip wheel
# 4. PyTorch built for CUDA 12.8 (Blackwell sm_120 needs cu128 or newer)
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
# 5. everything else
.\.venv\Scripts\pip install -r requirements.txt
# 6. check
.\.venv\Scripts\python setup\check_env.py

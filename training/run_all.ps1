# Agrobo: full overnight training run on one PC (Windows, RTX 5060).  powershell -ExecutionPolicy Bypass -File run_all.ps1
# Each stage skips work already done, so re-running after a crash resumes.
param([int]$Images = 2000, [int]$PickSteps = 20000000, [int]$Envs = 0)
$ErrorActionPreference = "Stop"
$env:AGROBO_WORLD  = (Resolve-Path ..\agrobo-world).Path
$env:AGROBO_ROBOTS = (Resolve-Path ..\agrobo-robots).Path
$py = ".\.venv\Scripts\python"
if ($Envs -eq 0) { $Envs = [Math]::Max(2, [Environment]::ProcessorCount - 2) }
Write-Host "1/5 photoreal Florida dataset ($Images images, Blender Cycles on the GPU)"
& $py perception\synth_florida.py --n $Images --out data\synth_fl --res 960 720 --spp 32 --device GPU
Write-Host "2/5 convert to YOLO (Florida set + the original agrobo-world sample set)"
& $py perception\masks_to_yolo.py data\synth_fl ..\agrobo-world\synth\sample_dataset --out data\yolo_fl
Write-Host "3/5 train the ripeness + weed segmenter"
& $py perception\train.py --data data\yolo_fl\data.yaml --epochs 150
& $py perception\evaluate.py --weights runs\seg\fl_ripeness\weights\best.pt --data data\yolo_fl\data.yaml
& $py perception\export.py runs\seg\fl_ripeness\weights\best.pt
Write-Host "4/5 train the picking policy ($PickSteps steps, $Envs parallel sims)"
Push-Location picking
& ..\$py train_ppo.py --steps $PickSteps --envs $Envs
Write-Host "5/5 score it against the scripted picker and film it"
& ..\$py evaluate.py --run runs\pick\ppo_fr5 --episodes 200 --video 4
Pop-Location
Write-Host "Done. Results: runs\seg\fl_ripeness\  and  picking\runs\pick\ppo_fr5\"

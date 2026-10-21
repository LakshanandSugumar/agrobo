# Agrobo robot training

This folder trains the two learnt skills on the Agrobo harvester (hardware package `../agrobo-robots`, rev A.1):

1. **Perception.** A ripeness and weed segmenter for SW Florida fresh-market tomatoes, trained on photoreal synthetic images.
2. **Picking.** A grasp-detach-extract policy for one FR5 arm with the EE-1 gripper (3 Fin-Ray fingers plus a suction cup), trained in MuJoCo.

Both are built to run overnight on one RTX 5060 (8 GB) PC. Everything here was smoke-tested on CPU in the cloud. The real runs have not happened yet.

## Quick start (Windows, RTX 5060)

Copy `agrobo-train`, `agrobo-world` and `agrobo-robots` into the same parent folder, then:

```powershell
cd agrobo-train
powershell -ExecutionPolicy Bypass -File setup\setup_windows.ps1   # Python 3.13 venv, PyTorch cu128, checks the GPU
powershell -ExecutionPolicy Bypass -File run_all.ps1               # dataset -> segmenter -> picking policy -> scores
```

On Linux or a rented GPU, run `bash setup/setup_linux.sh` and then `bash run_all.sh`. Each stage resumes where it stopped.

Rough wall-clock times on an RTX 5060 with an 8-12 thread CPU. These are estimates, not measured yet:

| stage | time |
|---|---|
| 2,000 photoreal images (Cycles + OptiX, 960x720, 32 spp) | 2-3 h |
| YOLO11s-seg, 150 epochs at 640 px | 1.5-2 h |
| picking PPO, 20 M steps, about 10 parallel sims | 5-7 h (CPU-bound) |

Picking physics runs on the CPU (MuJoCo), so more CPU cores speed it up and the GPU does not. A rented GPU is only worth it for bigger perception models (YOLO11m/l at 960 px or more), which outgrow 8 GB.

## 1. Perception (`perception/`)

| file | what it does |
|---|---|
| `synth_florida.py` | Blender Cycles generator. It renders raised beds on 1.83 m centres under black, white or silver plastic mulch, with sandy row middles, wooden stakes every second plant and twine weave. Fruit hang in trusses with a peduncle, pedicels and calyxes, and are ripest at the proximal end. Images come from 3 camera rigs that match the harvester: mast stereo (~1.8 m), arm-height side view (~0.95 m) and the eye-in-hand D405 (15-50 cm). Each image comes with a pixel-exact instance mask and COCO labels. |
| `masks_to_yolo.py` | Converts the masks to YOLO segmentation polygons. It merges occluded fragments into one instance, uses a deterministic train/val split, and also reads `agrobo-world`'s older dataset. |
| `train.py` | Trains YOLO11-seg with auto-batch at 70% of VRAM and AMP. Hue augmentation is kept small on purpose, because hue is the ripeness signal. |
| `evaluate.py` | Scores the pick decision as well as mAP: **pick recall** (mature-green or riper fruit found), **wrong-pick rate** (immature fruit picked, which is lost yield) and the ripeness confusion matrix. |
| `export.py` | Exports ONNX. `--engine` builds a TensorRT FP16 engine; run it on the robot's Jetson. |

Classes: 0 immature green (leave), 1 **mature green** (the main Florida pick target: picked green and ethylene-ripened), 2 breaker/turning, 3 ripe, 4 weed.

## 2. Picking (`picking/`)

`env.py` (`AgroboTomatoPick-v0`) builds the arm from `agrobo-robots/cad/src/params.py`, so a hardware change flows straight into training. Its kinematics match the hardware `kin.fk` to 0.1 mm.

- **Robot.** A side-mounted FR5 at z 0.95 m with the datasheet joint limits (J2/J4 -265..+85 deg, J3 +-160). The EE-1 gripper has 3 coupled Fin-Ray fingers and a 40 mm bellows cup on a 65 mm plunger, which retracts by itself once the cup seals, like the vacuum switch on the real gripper. A wrist force/torque sensor is included.
- **Plant.** Each fruit hangs on its knuckle (abscission zone). The pedicel stretches under tension (800 N/m) and buckles under compression. The knuckle breaks on a pull above 18-32 N, a bend past 65-100 deg (about 7-11 N at the fruit) or a twist past 115-230 deg. Each truss has 2-4 neighbour fruit on the same kind of knuckle. The main stem and stake are rigid. The twine is flexible, but snagging it is penalised.
- **Perception error.** The policy gets fruit, neighbour and stem positions with a per-episode bias (6-10 mm) plus per-step jitter, as a detector plus depth camera would give.
- **Action** (20 Hz): TCP move and rotation, finger close and vacuum. A bounded IK servo turns these into FR5 joint targets, respecting the joint stops and giving up gripper roll first.
- **Success**: the fruit is detached, held and pulled 15 cm clear. Episodes report bruising (low-pass finger force above 20-45 N depending on ripeness), neighbour knock-offs, drops and cycle time.

| file | what it does |
|---|---|
| `expert.py` | The scripted picker. It plans an approach around the neighbours (reachability plus clearance), advances with the cup extended, draws the fruit in, closes the fingers, lifts the fruit about its knuckle as a hand picker does, then pulls it clear. It serves as the baseline and as the source of warm-start demos. |
| `train_ppo.py` | Behaviour-clones the expert's successful episodes, then runs PPO (SB3) on parallel sims with VecNormalize. It evaluates on held-out plants every 250 k steps and keeps the best model by clean picks minus knock-offs. |
| `evaluate.py` | Runs the learnt policy and the scripted picker on the same 200 held-out plants, writes `pick_kpis.json` and films `picks.mp4`. |

### Results so far (cloud CPU, 4 sims, 1.3 M steps each)

Scored on the same 200 held-out plants:

| | success | clean (no bruise) | knocked neighbour | dropped | cycle |
|---|---|---|---|---|---|
| scripted picker | 37% | 16.5% | 19.5% | n/a | 4.2 s |
| run 4: BC + PPO, frozen obs normalisation (best at 750 k) | 29% | **22%** | 25.5% | 23% | 4.1 s |
| run 5: same + BC loss kept during PPO (best at 900 k) | 27% | 17.5% | 22.5% | 22% | 4.1 s |

What we learnt:
- Runs 1-3 collapsed to 0% because VecNormalize kept re-estimating the observation scaling during PPO, so the behaviour-cloned actor saw shifted inputs. `train_ppo.py` now freezes the scaling at the demo statistics. With that fix the policy holds its starting skill through the critic warm-up.
- The learnt policy already beats the scripted picker on clean picks (22% vs 16.5%), because it bruises less. It does not yet beat it on total picks. 1.3 M steps is about 6% of the 20 M-step real run.
- Keeping a BC loss during PPO (`--bc-reg 1`) did not help at this length, so it is off by default.
- Evals on 40 plants are noisy (about ±8 points). Trust the 200-plant `evaluate.py` scores.

Results, logs and videos are in `results/cloud_cpu_run*`. The sim runs at about 210 steps/s per CPU thread.

## Honest limits

- All of this is simulation. Knuckle strengths, bruise limits and pedicel stiffness are from literature ranges, not from measuring Florida fruit. Measuring 30 fruit with a force gauge would calibrate them.
- The policy sees fruit positions as numbers (perception output), not pixels. Linking it to the camera model is the next step, either through the eye-in-hand images from `synth_florida.py` or by moving to Isaac Lab with the hardware URDF (`agrobo_harvester.relative.urdf`).
- The synthetic images still need a real-photo check. Label 200-300 field photos (CVAT or Label Studio, same 5 classes) and run `evaluate.py` on them before trusting any number.
- The FR5 joint zero convention relative to the vendor's is still to be checked on hardware (see the hardware package).

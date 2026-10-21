"""Prints what the training stack can see: GPU, CUDA, and every library the pipelines import."""
import importlib, platform, sys
print('python', sys.version.split()[0], platform.platform())
try:
    import torch
    print('torch', torch.__version__, 'cuda', torch.version.cuda, 'gpu available', torch.cuda.is_available())
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        print(f'  {p.name}: {p.total_memory / 2**30:.1f} GB, compute capability {p.major}.{p.minor}')
        x = torch.randn(2048, 2048, device='cuda'); (x @ x).sum().item(); print('  CUDA matmul OK')
except Exception as e:
    print('torch problem:', e)
for m in ('ultralytics', 'mujoco', 'gymnasium', 'stable_baselines3', 'scipy', 'cv2', 'imageio', 'bpy'):
    try:
        mod = importlib.import_module(m); print(f'{m:18s} OK', getattr(mod, '__version__', ''))
    except Exception as e:
        print(f'{m:18s} MISSING ({e})')
try:
    import bpy
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for backend in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = backend; prefs.get_devices()
            devs = [d.name for d in prefs.devices if d.type == backend]
            if devs: print(f'Blender Cycles {backend}:', devs); break
        except TypeError: pass
except Exception as e:
    print('bpy GPU check skipped:', e)

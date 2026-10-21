"""Score a trained picking policy against the scripted baseline on the same held-out plants, and film a few picks.
  python evaluate.py --run runs/pick/ppo_fr5 --episodes 200 --video 4
Writes <run>/pick_kpis.json and <run>/picks.mp4.
"""
import argparse, json, os, sys
import numpy as np
os.environ.setdefault('MUJOCO_GL', 'egl' if sys.platform.startswith('linux') else 'glfw')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env as E
from expert import Expert
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv

def run(policy, n, seed, video_eps, frames):
    e = E.TomatoPickEnv(); S = []
    for k in range(n):
        o, _ = e.reset(seed=seed + k); policy.reset() if hasattr(policy, 'reset') else None
        while True:
            o, r, te, tr, info = e.step(policy(o))
            if k < video_eps: frames.append(e.render())
            if te or tr: break
        S.append(info)
    m = lambda f: float(np.mean([s[f] for s in S]))
    ok = [s for s in S if s['success']]
    return dict(episodes=n, success=m('success'), clean_success=float(np.mean([s['success'] and not s['bruised'] for s in S])),
                knocked_neighbour=m('knocked'), dropped=m('dropped'), bruised=m('bruised'),
                mean_cycle_s=float(np.mean([s['t'] for s in ok])) if ok else None,
                detach_modes={md: sum(1 for s in S if s['detach_mode'] == md) for md in ('pull', 'bend', 'twist')})

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--run', required=True); ap.add_argument('--episodes', type=int, default=200)
    ap.add_argument('--seed', type=int, default=90_000); ap.add_argument('--video', type=int, default=4); a = ap.parse_args()
    model = PPO.load(os.path.join(a.run, 'best_model.zip'), device='cpu')
    stats = VecNormalize.load(os.path.join(a.run, 'vecnormalize.pkl'), DummyVecEnv([lambda: E.TomatoPickEnv()])).obs_rms
    learnt = lambda o: model.predict(np.clip((o - stats.mean) / np.sqrt(stats.var + 1e-8), -10, 10), deterministic=True)[0]
    frames = []
    rep = {'learnt_policy': run(learnt, a.episodes, a.seed, a.video, frames)}
    e2 = E.TomatoPickEnv(); ex = Expert(e2, grip=-.3); S = []   # the expert plans with the env it acts in
    for k in range(a.episodes):
        o, _ = e2.reset(seed=a.seed + k); ex.reset()
        while True:
            o, r, te, tr, info = e2.step(ex(o))
            if te or tr: break
        S.append(info)
    rep['scripted_baseline'] = dict(success=float(np.mean([s['success'] for s in S])),
                                    clean_success=float(np.mean([s['success'] and not s['bruised'] for s in S])),
                                    knocked_neighbour=float(np.mean([s['knocked'] for s in S])),
                                    mean_cycle_s=float(np.mean([s['t'] for s in S if s['success']] or [np.nan])))
    json.dump(rep, open(os.path.join(a.run, 'pick_kpis.json'), 'w'), indent=2); print(json.dumps(rep, indent=2))
    if frames:
        import imageio.v2 as iio
        iio.mimsave(os.path.join(a.run, 'picks.mp4'), frames, fps=20); print('wrote', os.path.join(a.run, 'picks.mp4'))

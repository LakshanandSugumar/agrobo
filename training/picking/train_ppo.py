"""Train the picking policy on TomatoPick-v0 with PPO (Stable-Baselines3), warm-started by behaviour cloning the
scripted picker so PPO starts from ~40% success instead of 0%.

  python train_ppo.py --steps 20_000_000 --envs 12                 # real run (RTX 5060 PC: one env per CPU thread)
  python train_ppo.py --steps 200_000 --envs 4 --bc-episodes 60    # smoke test
Outputs runs/pick/<name>/: best_model.zip, vecnormalize.pkl, eval_log.csv, tensorboard/ .
The physics runs on the CPU (MuJoCo); the GPU barely matters for a 256x256 MLP, so --device defaults to cpu.
"""
import argparse, csv, json, os, sys, time
import numpy as np
import torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env as E
from expert import Expert
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import BaseCallback

def make(rank, seed, min_clearance):
    def f():
        e = E.TomatoPickEnv(min_clearance=min_clearance)
        e.reset(seed=seed + 1000 * rank)
        return e
    return f

def collect_demos(n, seed, min_clearance, grip=-.3):
    """Run the scripted picker; keep only its successful episodes."""
    e = E.TomatoPickEnv(min_clearance=min_clearance); ex = Expert(e, grip=grip)
    O, A, kept = [], [], 0
    for k in range(n):
        o, _ = e.reset(seed=seed + k); ex.reset(); eo, ea = [], []
        while True:
            a = ex(o); eo.append(o); ea.append(a)
            o, r, te, tr, info = e.step(a)
            if te or tr: break
        if info['success']:
            O += eo; A += ea; kept += 1
    print(f'BC demos: {kept}/{n} successful expert episodes, {len(O)} steps', flush=True)
    return np.array(O, np.float32), np.clip(np.array(A, np.float32), -1, 1)

def behaviour_clone(model, venv, O, A, epochs=40, lr=1e-3):
    # seed the observation normaliser with the demo statistics so BC and PPO see the same inputs
    # and freeze it there: a huge count makes VecNormalize's running updates negligible. Letting the stats drift
    # during PPO shifted every input the cloned actor sees and took it from 28% to 0% picks (cloud runs 1-3).
    venv.obs_rms.mean = O.mean(0); venv.obs_rms.var = O.var(0) + 1e-6; venv.obs_rms.count = 1e12
    On = torch.as_tensor(np.clip((O - venv.obs_rms.mean) / np.sqrt(venv.obs_rms.var + 1e-8), -10, 10), device=model.device)
    At = torch.as_tensor(A, device=model.device)
    pol = model.policy; opt = torch.optim.Adam(pol.parameters(), lr=lr)
    for ep in range(epochs):
        perm = torch.randperm(len(On)); tot = 0
        for i in range(0, len(On), 256):
            idx = perm[i:i + 256]
            dist = pol.get_distribution(On[idx])
            loss = ((dist.distribution.mean - At[idx]) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(idx)
        if ep % 10 == 0 or ep == epochs - 1: print(f'  BC epoch {ep}: mse {tot / len(On):.4f}', flush=True)
    with torch.no_grad(): pol.log_std.fill_(-1.5)     # explore close to the cloned behaviour (wider noise made PPO drift into 'do nothing')

def evaluate(model, vn_stats, n, seed, min_clearance):
    e = E.TomatoPickEnv(min_clearance=min_clearance); S = []
    for k in range(n):
        o, _ = e.reset(seed=seed + k)
        while True:
            on = np.clip((o - vn_stats.mean) / np.sqrt(vn_stats.var + 1e-8), -10, 10)
            a, _ = model.predict(on, deterministic=True)
            o, r, te, tr, info = e.step(a)
            if te or tr: break
        S.append(info)
    m = lambda f: float(np.mean([s[f] for s in S]))
    clean = float(np.mean([s['success'] and not s['bruised'] for s in S]))
    return dict(success=m('success'), clean_success=clean, knocked=m('knocked'), dropped=m('dropped'), bruised=m('bruised'),
                cycle_s=float(np.mean([s['t'] for s in S if s['success']])) if m('success') else None)

class EvalCB(BaseCallback):
    def __init__(self, out, every, n_eval, min_clearance):
        super().__init__(); self.out, self.every, self.n_eval, self.mc = out, every, n_eval, min_clearance
        self.best = -1; self.next = 0; self.t0 = time.time()
        self.f = open(os.path.join(out, 'eval_log.csv'), 'a', newline=''); self.w = csv.writer(self.f)
    def _on_step(self):
        if self.num_timesteps >= self.next:
            self.next += self.every
            vn = self.model.get_env()
            r = evaluate(self.model, vn.obs_rms, self.n_eval, 50_000, self.mc)
            self.w.writerow([self.num_timesteps, round(time.time() - self.t0)] + [r[k] for k in ('success', 'clean_success', 'knocked', 'dropped', 'bruised', 'cycle_s')]); self.f.flush()
            print(f'[{self.num_timesteps:>9} steps, {time.time() - self.t0:6.0f}s] ' + ' '.join(f'{k}={v:.2f}' if isinstance(v, float) else f'{k}={v}' for k, v in r.items()), flush=True)
            score = r['clean_success'] - .5 * r['knocked']
            if score > self.best:
                self.best = score; self.model.save(os.path.join(self.out, 'best_model')); vn.save(os.path.join(self.out, 'vecnormalize.pkl'))
                json.dump(dict(r, steps=self.num_timesteps), open(os.path.join(self.out, 'best_eval.json'), 'w'), indent=2)
        return True

class BCRegCB(BaseCallback):
    """Keeps PPO near the demos (DAPG-style): after each rollout, a few behaviour-cloning steps on the actor with a
    weight that decays from w0 to w0/10 over the run. Without it PPO drifted from 30% to 17% picks in 300k steps (run 4)."""
    def __init__(self, O, A, total, w0=1., steps=4):
        super().__init__(); self.O, self.A, self.total, self.w0, self.k = O, A, total, w0, steps
    def _on_step(self): return True
    def _on_rollout_end(self):
        pol = self.model.policy; vn = self.model.get_env()
        if not hasattr(self, 'opt'):
            self.On = torch.as_tensor(np.clip((self.O - vn.obs_rms.mean) / np.sqrt(vn.obs_rms.var + 1e-8), -10, 10), device=pol.device, dtype=torch.float32)
            self.At = torch.as_tensor(self.A, device=pol.device, dtype=torch.float32)
            self.opt = torch.optim.Adam(list(pol.mlp_extractor.policy_net.parameters()) + list(pol.action_net.parameters()), lr=1e-4)
        w = self.w0 * max(.1, 1 - self.num_timesteps / self.total)
        for _ in range(self.k):
            idx = torch.randint(len(self.On), (256,))
            loss = w * ((pol.get_distribution(self.On[idx]).distribution.mean - self.At[idx]) ** 2).mean()
            self.opt.zero_grad(); loss.backward(); self.opt.step()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--steps', type=int, default=20_000_000); ap.add_argument('--envs', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument('--name', default='ppo_fr5'); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--bc-episodes', type=int, default=400, help='scripted-picker episodes for the warm start (0 = none)')
    ap.add_argument('--min-clearance', type=float, default=0., help='lower = more cluttered trusses (try -0.01 after a first run)')
    ap.add_argument('--eval-every', type=int, default=250_000); ap.add_argument('--eval-episodes', type=int, default=50)
    ap.add_argument('--critic-warmup', type=int, default=300_000, help='steps that fit only the value function after BC')
    ap.add_argument('--bc-reg', type=float, default=1., help='weight of the BC loss kept during PPO (0 = off)')
    ap.add_argument('--device', default='cpu'); ap.add_argument('--resume')
    a = ap.parse_args()
    out = os.path.join('runs', 'pick', a.name); os.makedirs(out, exist_ok=True)
    json.dump(vars(a), open(os.path.join(out, 'args.json'), 'w'), indent=2)
    fns = [make(i, a.seed, a.min_clearance) for i in range(a.envs)]
    venv = SubprocVecEnv(fns, start_method='spawn') if a.envs > 1 else DummyVecEnv(fns)
    venv = VecNormalize(venv, norm_obs=True, norm_reward=True, clip_obs=10., gamma=.99)
    if a.resume:
        model = PPO.load(a.resume, env=venv, device=a.device)
        venv.obs_rms = VecNormalize.load(os.path.join(os.path.dirname(a.resume), 'vecnormalize.pkl'), venv).obs_rms
    else:
        model = PPO('MlpPolicy', venv, n_steps=max(64, 4096 // a.envs), batch_size=1024, n_epochs=8, learning_rate=1e-4,
                    gamma=.99, gae_lambda=.95, clip_range=.1, ent_coef=.0, vf_coef=.5, max_grad_norm=.5, target_kl=.03,
                    policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256]), log_std_init=-.5),
                    tensorboard_log=os.path.join(out, 'tensorboard'), device=a.device, seed=a.seed, verbose=0)
        if a.bc_episodes:
            O, A = collect_demos(a.bc_episodes, 20_000, a.min_clearance)
            if len(O): behaviour_clone(model, venv, O, A)
            else: a.bc_reg = 0
    if a.bc_episodes and not a.resume and a.critic_warmup:
        # Critic warm-up: with the cloned actor frozen, PPO only fits the value function first. Fine-tuning straight
        # away let an untrained critic's noisy advantages wipe out the cloned behaviour within 200k steps.
        actor = list(model.policy.mlp_extractor.policy_net.parameters()) + list(model.policy.action_net.parameters()) + [model.policy.log_std]
        for p_ in actor: p_.requires_grad_(False)
        print(f'critic warm-up: {a.critic_warmup} steps with the actor frozen', flush=True)
        model.learn(total_timesteps=a.critic_warmup, reset_num_timesteps=True)
        for p_ in actor: p_.requires_grad_(True)
    cb = EvalCB(out, a.eval_every, a.eval_episodes, a.min_clearance)
    cb.model = model; cb._on_step()          # eval the starting point (BC policy) before PPO touches it
    cbs = [cb] + ([BCRegCB(O, A, a.steps, a.bc_reg)] if a.bc_episodes and not a.resume and a.bc_reg else [])
    model.learn(total_timesteps=a.steps, callback=cbs, reset_num_timesteps=False)
    model.save(os.path.join(out, 'final_model')); venv.save(os.path.join(out, 'vecnormalize_final.pkl'))
    print('done ->', out)

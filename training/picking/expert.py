"""Scripted picker for TomatoPick-v0. It only reads the observation (the same noisy perception the policy gets),
so it doubles as (a) proof that the task is solvable, (b) a baseline the learnt policy has to beat, and
(c) a demo source for behaviour-cloning warm starts (train_ppo.py --bc-demos).

Sequence: line up 10 cm in front of the fruit -> advance until the cup touches -> vacuum on (plunger pulls the
fruit into the fingers) -> close fingers -> roll the wrist (bends the knuckle, the hand-picker's snap) while
easing back -> pull it clear of the plant.
  python expert.py --episodes 100           # success rate, cycle time, failure modes
  python expert.py --episodes 3 --video out/expert.mp4
"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env as E

def unpack(o):
    return dict(R0=o[15:18], R2=o[18:21], fq=o[21], fruit=o[24:27], radius=o[30], fruit0=o[34:37], stem=o[37:40],
                fingers=o[46] * 3, cup=o[47] > .5, detached=o[48] > .5)

def rot_to(Rc, Rd):
    """Tool-frame rotation vector that takes Rc to Rd."""
    M = Rc.T @ Rd; c = np.clip((np.trace(M) - 1) / 2, -1, 1); th = math.acos(c)
    if th < 1e-6: return np.zeros(3)
    v = np.array([M[2, 1] - M[1, 2], M[0, 2] - M[2, 0], M[1, 0] - M[0, 1]]) / (2 * math.sin(th))
    return v * th

class Expert:
    def __init__(self, env, grip=-.3):
        self.env, self.grip = env, grip   # grip: finger command in [-1, 1]
        self.grasp_back = env.g['grasp_off']   # tcp -> grasp centre along tool z
        self.reset()

    def reset(self):
        self.phase, self.t, self.ap, self.roll = 'align', 0, None, 0

    def __call__(self, o):
        s = unpack(o); a = np.zeros(8)
        x = s['R0']; z = s['R2']; y = np.cross(z, x); Rc = np.stack([x, y, z], 1)
        grasp_to_fruit = s['fruit'] + self.grasp_back * z           # fruit relative to the grasp centre
        if self.ap is None:   # plan once: the reachable approach with the most room around the neighbour fruit
            tcp_w = o[12:15] + self.env.base_pos; fruit_w = tcp_w + s['fruit']
            neigh = [(tcp_w + nb[:3], nb[3]) for nb in o[50:].reshape(-1, 4) if nb[3] > 0]
            cands = sorted(self.env.approach_candidates(fruit_w), key=lambda ap: -self.env.clearance(fruit_w, ap, neigh))
            self.ap = next((ap for ap in cands[:8] if self.env.reachable(fruit_w, self.env.q_home, standoff=.16, ap=ap)
                            and self.env.reachable(fruit_w, self.env.q_home, ap=ap)), cands[0])
            self.Rd = E.TomatoPickEnv._approach_R(self.ap)
        self.t += 1
        def move(vec, gain=1.):
            a[:3] = np.clip(vec / .012 * gain, -1, 1)
        if self.phase == 'align':
            move(grasp_to_fruit - self.ap * .16)
            a[6] = -1
            if np.linalg.norm(grasp_to_fruit - self.ap * .16) < .015 or self.t > 80: self.phase, self.t = 'advance', 0
        elif self.phase == 'advance':   # cup rides extended with vacuum on; stop as soon as it seals
            move(grasp_to_fruit + self.ap * .005, .4); a[6] = -1; a[7] = 1
            if s['cup'] or np.linalg.norm(grasp_to_fruit) < .01 or self.t > 50: self.phase, self.t = 'draw', 0
        elif self.phase == 'draw':      # plunger draws the fruit in while the hand slides forward around it
            move(grasp_to_fruit, .4); a[6] = -1; a[7] = 1
            if np.linalg.norm(grasp_to_fruit) < .012 or self.t > 15: self.phase, self.t = 'close', 0
        elif self.phase == 'close':
            a[6] = self.grip; a[7] = 1
            if self.t > 8: self.phase, self.t = 'snap', 0
        elif self.phase == 'snap':      # hand-picker's lift: swing the fruit up and out about its knuckle
            a[6] = self.grip; a[7] = 1
            move(np.array([0, 0, .005]) - self.ap * .002)
            if s['detached'] or self.t > 50: self.phase, self.t = 'carry', 0
        elif self.phase == 'carry':     # pull the fruit straight back out of the canopy
            a[6] = self.grip; a[7] = 1
            move(-self.ap * .012 + np.array([0, -.004, 0]))
        if True:
            zd = self.Rd[:, 2]; xd = x - (x @ zd) * zd; xd /= np.linalg.norm(xd) + 1e-9
            Rd = np.stack([xd, np.cross(zd, xd), zd], 1)    # same approach axis, current roll
            a[3:6] = np.clip(rot_to(Rc, Rd) / .08, -1, 1)
        return a

def run(n, seed=0, video=None, verbose=True):
    env = E.TomatoPickEnv(); ex = Expert(env); stats = []; frames = []
    for ep in range(n):
        o, _ = env.reset(seed=seed + ep); ex.reset(); R = 0
        while True:
            o, r, te, tr, info = env.step(ex(o)); R += r
            if video and ep < 3: frames.append(env.render())
            if te or tr: break
        info['return'] = R; stats.append(info)
        if verbose: print(ep, 'OK ' if info['success'] else 'FAIL', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})
    sr = np.mean([s['success'] for s in stats])
    summary = dict(episodes=n, success_rate=float(sr),
                   mean_cycle_s=float(np.mean([s['t'] for s in stats if s['success']])) if sr else None,
                   bruise_rate=float(np.mean([s['bruised'] for s in stats])),
                   knocked_neighbour_rate=float(np.mean([s['knocked'] for s in stats])),
                   drop_rate=float(np.mean([s['dropped'] for s in stats])),
                   detach_modes={m: sum(1 for s in stats if s['detach_mode'] == m) for m in ('pull', 'bend', 'twist')})
    if video and frames:
        import imageio.v2 as iio
        os.makedirs(os.path.dirname(video) or '.', exist_ok=True); iio.mimsave(video, frames, fps=20)
    return summary

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--episodes', type=int, default=50); ap.add_argument('--seed', type=int, default=10_000)
    ap.add_argument('--video'); a = ap.parse_args()
    print(json.dumps(run(a.episodes, a.seed, a.video), indent=2))

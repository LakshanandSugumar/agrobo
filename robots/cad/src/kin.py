"""Forward/inverse kinematics of the side-mounted FR5-class arms, in the robot frame (metres).
Same joint chain as the URDF (UR-style), so CAD poses, URDF and IK agree."""
import math
import numpy as np
from scipy.optimize import least_squares
from params import ARM, EE


def T(xyz=(0, 0, 0), rpy=(0, 0, 0)):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    M = np.eye(4)
    M[:3, :3] = [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                 [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                 [-sp, cp * sr, cp * cr]]
    M[:3, 3] = xyz
    return M


def Rz(q):
    return T(rpy=(0, 0, q))


JOINTS = ["shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"]
LINKS = ["arm_base", "shoulder", "upper_arm", "forearm", "wrist_1", "wrist_2", "wrist_3"]


def chain():
    d1, a2, a3, d4, d5, d6 = (ARM[k] for k in ("d1", "a2", "a3", "d4", "d5", "d6"))
    return [((0, 0, d1), (0, 0, 0)), ((0, 0, 0), (math.pi / 2, 0, 0)), ((a2, 0, 0), (0, 0, 0)),
            ((a3, 0, d4), (0, 0, 0)), ((0, -d5, 0), (math.pi / 2, 0, 0)), ((0, d6, 0), (math.pi / 2, math.pi, math.pi))]


def mount(side):
    s = 1 if side == "left" else -1
    return T((ARM["mount_x"], s * ARM["mount_y"], ARM["mount_z"]), (-s * math.pi / 2, 0, 0))


def fk(side, q, tcp=False):
    """Returns list of 4x4 link frames [arm_base, shoulder, ..., wrist_3] (+ tcp if asked)."""
    M = mount(side)
    frames = [M.copy()]
    for (xyz, rpy), qi in zip(chain(), q):
        M = M @ T(xyz, rpy) @ Rz(qi)
        frames.append(M.copy())
    if tcp:
        frames.append(M @ T((0, 0, EE["tcp_z"])))
    return frames


def ik(side, target, approach, q0=None):
    """Position + approach-axis IK (tool z along `approach`). Returns (q, pos_err_m, ang_err_deg)."""
    target, approach = np.asarray(target, float), np.asarray(approach, float) / np.linalg.norm(approach)
    lo = np.radians([l[0] for l in ARM["limits_deg"]])
    hi = np.radians([l[1] for l in ARM["limits_deg"]])

    def res(q):
        F = fk(side, q, tcp=True)[-1]
        return np.r_[(F[:3, 3] - target) * 10, (F[:3, 2] - approach)]
    best = None
    seeds = [np.clip(q0, lo, hi)] if q0 is not None else []
    rng = np.random.default_rng(1)
    seeds += [rng.uniform(lo, hi) for _ in range(24)]   # seeds inside the joint limits
    for s0 in seeds:
        r = least_squares(res, s0, bounds=(lo, hi))
        if best is None or r.cost < best.cost:
            best = r
        if r.cost < 1e-10:
            break
    F = fk(side, best.x, tcp=True)[-1]
    pe = np.linalg.norm(F[:3, 3] - target)
    ae = math.degrees(math.acos(np.clip(F[:3, 2] @ approach, -1, 1)))
    return best.x, pe, ae


if __name__ == "__main__":
    F = fk("left", np.zeros(6), tcp=True)
    for n, M in zip(LINKS + ["tcp"], F):
        print(n, np.round(M[:3, 3], 3), "z-axis", np.round(M[:3, 2], 2))
    for tgt, ap in (((0.2, 0.75, 1.0), (0, 1, 0)), ((0.45, 0.0, 1.15), (0, 0, -1)), ((-0.3, 0.8, 0.5), (0, 1, -0.4))):
        q, pe, ae = ik("left", tgt, ap)
        print(tgt, "->", np.round(np.degrees(q), 1), f"err {pe*1000:.2f} mm {ae:.2f} deg")

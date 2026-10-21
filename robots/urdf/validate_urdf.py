"""Checks the generated URDF: loads it, compares TCP forward kinematics with cad/src/kin.py, checks mesh bounds."""
import os, sys, numpy as np, trimesh, yourdfpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "src"))
import kin
pkg = os.path.join(HERE, "agrobo_description")
r = yourdfpy.URDF.load(os.path.join(pkg, "agrobo_harvester.relative.urdf"), mesh_dir=pkg)
print("links", len(r.link_map), "joints", len(r.joint_map), "actuated", len(r.actuated_joint_names))
rng = np.random.default_rng(0)
worst = 0
for side in ("left", "right"):
    for _ in range(200):
        q = rng.uniform(-3, 3, 6)
        cfg = {f"{side}_arm_{j}_joint": v for j, v in zip(kin.JOINTS, q)}
        r.update_cfg(cfg)
        A = r.get_transform(f"{side}_ee_tcp", "base_link")
        Bm = kin.fk(side, q, tcp=True)[-1]
        worst = max(worst, np.abs(A - Bm).max())
print(f"URDF vs kin.py TCP FK max abs diff over 400 random poses: {worst:.2e}")
for f in sorted(os.listdir(os.path.join(pkg, "meshes"))):
    m = trimesh.load(os.path.join(pkg, "meshes", f))
    print(f"{f:28s} faces {len(m.faces):7d}  bounds_min {np.round(m.bounds[0],3)} max {np.round(m.bounds[1],3)}")

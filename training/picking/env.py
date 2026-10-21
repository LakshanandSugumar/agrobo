"""TomatoPick-v0: one harvester arm picking one fruit from a staked Florida tomato truss (MuJoCo + Gymnasium).

Robot geometry is the hardware package's (agrobo-robots/cad/src/params.py): FR5 UR-style chain side-mounted at
z 0.95 m / y 0.22 m, EE-1 end-effector with 3 Fin-Ray fingers, a 40 mm bellows suction cup on a 30 mm plunger
and a 205 mm TCP. If that file is missing the same numbers are used from FALLBACK below.

Plant model (what makes this a picking problem and not a reaching problem):
  * each fruit hangs from its pedicel knuckle (abscission zone) through a slide joint (pull) and a ball joint
    (bend + twist), both spring-loaded. A weld holds the fruit to the knuckle until the knuckle breaks:
    pull force > F_pull, or bend angle > bend_max, or twist angle > twist_max (randomised per episode).
    Bending and twisting break it at far lower forces than a straight pull, which is what good hand pickers do.
  * 2-4 neighbour fruit on the same truss hang on the same kind of knuckle. Knocking one off ends the episode.
  * the main stem and the stake are rigid obstacles. The twine weave is strong but flexible (it deflects several cm),
    so it does not block the arm; the gripper passing within its own radius of a string is penalised as a snag.
  * finger normal force above the fruit's bruise limit is penalised (per soft Fin-Ray finger: ~45 N mature-green
    down to ~20 N red ripe).
Perception is not simulated pixel by pixel here: the policy gets the fruit / stem position the vision stack
would give it, with a per-episode bias plus per-step jitter, which is the error a real detector + depth has.

Success: fruit detached at the knuckle, held, and pulled 15 cm clear of the plant without knocking off a neighbour.
Action (8, all in [-1, 1]):  dx dy dz (TCP, robot frame, x 0.012 m/step) | rx ry rz (tool frame, x 0.08 rad/step)
                             | finger close (absolute) | vacuum on (> 0; the plunger retracts by itself once the cup seals)
Control at 20 Hz, physics at 500 Hz. An episode is at most 12 s (240 steps).
"""
import os, math, importlib.util
import numpy as np
import mujoco
import gymnasium as gym
from gymnasium import spaces

HERE = os.path.dirname(os.path.abspath(__file__))
FALLBACK = dict(
    ARM=dict(d1=0.152, a2=-0.425, a3=-0.395, d4=0.102, d5=0.102, d6=0.100, mount_z=0.95, mount_y=0.22, mount_x=0.0, mass=22.0),
    EE=dict(body_d=0.090, body_len=0.110, finger_len=0.095, finger_w=0.028, grip_open_d=0.120, grip_closed_d=0.045,
            cup_d=0.040, cup_stroke=0.065, mass=1.10, tcp_z=0.205),
    FIELD=dict(bed_centres=1.83, canopy_half_width=0.35, fruit_z=(0.45, 1.40), plant_spacing=0.51),
)

def load_params():
    p = os.environ.get('AGROBO_ROBOTS', os.path.join(HERE, '..', '..', 'agrobo-robots'))
    f = os.path.join(p, 'cad', 'src', 'params.py')
    if os.path.exists(f):
        spec = importlib.util.spec_from_file_location('agrobo_params', f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return dict(ARM=m.ARM, EE=m.EE, FIELD=m.FIELD), f
    return FALLBACK, None

N_NEIGH = 4                    # neighbour slots (unused ones are parked far away)
EXTRACT = .15   # success = fruit detached, still in the hand, and pulled 15 cm clear (8 cm of it back toward the aisle).
                # Dropping it into the catch chute is a fixed scripted move on the real robot, so it is not learnt.
CTRL_DT, SUBSTEPS = 0.05, 25
# FR5 datasheet joint ranges (J2 and J4 are asymmetric, -265..+85 deg). Assumes the hardware URDF keeps the vendor's
# zero positions (agrobo-robots says its chain comes from the vendor frcobot_ros2 URDF).
JOINT_LO = np.radians([-175, -265, -160, -265, -175, -175])
JOINT_HI = np.radians([175, 85, 160, 85, 175, 175])
if 'limits_deg' in load_params()[0]['ARM']:   # rev A.1+ of the hardware package carries the limits itself
    JOINT_LO, JOINT_HI = (np.radians([l[i] for l in load_params()[0]['ARM']['limits_deg']]) for i in (0, 1))
GRASP_FRAC = .75   # grasp centre (where a drawn-in fruit sits) as a fraction of finger length from the front plate
K_BEND = .22   # Nm/rad at the knuckle: a 65-100 deg bend breaks it at ~0.25-0.4 Nm, i.e. 7-11 N at the fruit (lit.: 6-12 N)
K_BUCKLE = 40.  # N/m: the same pedicel pushed back toward its knuckle
K_PULL = 800.   # N/m: pedicel + peduncle + truss compliance lumped into the pull spring (a 25 N pull stretches ~3 cm)
MAX_STEPS = 240

def build_xml(P):
    A, E = P['ARM'], P['EE']
    d1, a2, a3, d4, d5, d6 = (A[k] for k in ('d1', 'a2', 'a3', 'd4', 'd5', 'd6'))
    pi = math.pi
    # (pos, rpy) per joint frame, identical to agrobo-robots kin.chain(); joint axis is local z
    chain = [((0, 0, d1), (0, 0, 0)), ((0, 0, 0), (pi / 2, 0, 0)), ((a2, 0, 0), (0, 0, 0)),
             ((a3, 0, d4), (0, 0, 0)), ((0, -d5, 0), (pi / 2, 0, 0)), ((0, d6, 0), (pi / 2, pi, pi))]
    masses = [3.7, 8.4, 2.3, 1.2, 1.2, 0.25]
    torques = [150, 150, 150, 28, 28, 28]
    names = ['shoulder_pan', 'shoulder_lift', 'elbow', 'wrist_1', 'wrist_2', 'wrist_3']
    # visual/collision geometry per body (approximate FR5 envelope). Body i is the frame AFTER joint i, so the upper
    # arm lives in shoulder_lift_link (0 -> a2) and the forearm in elbow_link (0 -> a3).
    link_geom = ['<geom type="cylinder" size=".065 .07" pos="0 0 -.02"/>',
                 f'<geom type="capsule" fromto="0 0 0 {a2} 0 0" size=".05"/>',
                 f'<geom type="capsule" fromto="0 0 0 {a3} 0 0" size=".04"/>',
                 '<geom type="cylinder" size=".04 .05"/>',
                 '<geom type="cylinder" size=".04 .05"/>',
                 '<geom type="cylinder" size=".04 .02" pos="0 0 -.02"/>']
    com = ['0 0 0', f'{a2 / 2} 0 0', f'{a3 / 2} 0 0', '0 0 0', '0 0 0', '0 0 0']
    body = ''
    close = ''
    for i, ((x, y, z), (r, p, yw)) in enumerate(chain):
        body += (f'<body name="{names[i]}_link" pos="{x} {y} {z}" euler="{r} {p} {yw}" gravcomp="1">'
                 f'<inertial pos="{com[i]}" mass="{masses[i]}" diaginertia="{masses[i]*.004} {masses[i]*.004} {masses[i]*.003}"/>'
                 f'<joint name="{names[i]}" axis="0 0 1" range="{JOINT_LO[i]:.4f} {JOINT_HI[i]:.4f}" damping="2" armature=".1"/>'
                 f'<geom class="arm" {link_geom[i][6:]}\n')
        close += '</body>'
    # end-effector on wrist_3 (tool axis = +z)
    L, R = E['body_len'], E['body_d'] / 2
    fl = E['finger_len']; hinge_r = R + .005
    tip_open, tip_closed = E['grip_open_d'] / 2, E['grip_closed_d'] / 2
    f_open = -math.asin((tip_open - hinge_r) / fl); f_closed = math.asin((hinge_r - tip_closed) / fl)
    fingers = ''
    for k in range(3):
        a = 2 * pi * k / 3; c, s = math.cos(a), math.sin(a)
        fingers += (f'<body name="finger{k}" pos="{hinge_r*c:.4f} {hinge_r*s:.4f} {L}" euler="0 0 {a:.4f}" gravcomp="1">'
                    f'<inertial pos="0 0 .04" mass=".03" diaginertia="2e-5 2e-5 5e-6"/>'
                    f'<joint name="finger{k}" axis="0 -1 0" range="{f_open - .05:.3f} {f_closed + .25:.3f}" damping=".05" armature=".001"/>'
                    f'<geom class="finger" name="finger{k}_pad" type="box" size=".006 {E["finger_w"]/2} {fl/2}" pos="-.004 0 {fl/2}"/>'
                    f'</body>')
    # Plunger stroke: the drawn-in fruit must sit between the fingers (centre at the grasp site), ~65 mm for EE-1
    # (rev A.1 of the hardware package adopted 65 mm; an older params.py with less is overridden to what the geometry needs).
    grasp_z = L + GRASP_FRAC * fl; lip_out = E['tcp_z'] + .005
    stroke = max(E['cup_stroke'], lip_out - (grasp_z - .035))
    ee = (f'<body name="ee" pos="0 0 0" gravcomp="1"><inertial pos="0 0 .06" mass="{E["mass"] - .2}" diaginertia=".003 .003 .002"/>'
          f'<geom class="arm" name="ee_housing" type="cylinder" size="{R} {L/2}" pos="0 0 {L/2}"/>'
          f'<geom class="arm" name="d405" type="box" size=".021 .0125 .021" pos="0 {-R - .02} {L*.6}"/>'
          f'<site name="ft" pos="0 0 0"/><site name="tcp" pos="0 0 {E["tcp_z"]}"/><site name="grasp" pos="0 0 {grasp_z:.4f}"/>'
          f'{fingers}'
          f'<body name="cup" pos="0 0 {lip_out - .012:.4f}" gravcomp="1"><inertial pos="0 0 0" mass=".05" diaginertia="1e-5 1e-5 1e-5"/>'
          f'<joint name="plunger" type="slide" axis="0 0 1" range="{-stroke} .001" stiffness="0" damping="4"/>'
          f'<geom class="finger" name="cup_rod" type="cylinder" size=".006 .05" pos="0 0 -.05" contype="0" conaffinity="0"/>'
          f'<geom class="cupg" name="cup_lip" type="cylinder" size="{E["cup_d"]/2} .006" pos="0 0 .006"/>'
          f'</body></body>')
    fruits = ''
    for i in range(N_NEIGH + 1):
        nm = 'target' if i == 0 else f'n{i}'
        fruits += (f'<body name="{nm}_stalk" pos="0 0 3">'
                   f'<body name="{nm}_knuckle"><inertial pos="0 0 0" mass=".004" diaginertia="1e-7 1e-7 1e-7"/>'
                   f'<joint name="{nm}_pull" type="slide" axis="0 0 -1" range="-.05 .07" stiffness="0" damping="6" armature=".05"/>'
                   f'<joint name="{nm}_bend" type="ball" stiffness="{K_BEND}" damping=".02" armature="3e-4"/>'
                   f'</body></body>'
                   f'<body name="{nm}" pos="0 0 3"><freejoint name="{nm}_free"/>'
                   f'<geom class="fruit" name="{nm}_geom" type="ellipsoid" size=".035 .035 .03" mass=".18"/></body>')
    eqs = ''.join(f'<weld name="{nm}_attach" body1="{nm}_knuckle" body2="{nm}" relpose="0 0 -.05 1 0 0 0" solref=".004 1"/>'
                  for nm in ['target'] + [f'n{i}' for i in range(1, N_NEIGH + 1)])
    twine = ''.join(f'<geom name="twine{j}" type="capsule" size=".002" fromto="-1 0 {z} 1 0 {z}" contype="0" conaffinity="0" rgba=".6 .55 .4 1"/>'
                    for j, z in enumerate((.45, .70, .95, 1.20)))
    xml = f"""<mujoco model="agrobo_tomato_pick">
  <compiler angle="radian" eulerseq="XYZ" autolimits="true"/>
  <option timestep="{CTRL_DT / SUBSTEPS}" integrator="implicit" cone="elliptic" impratio="5"/>
  <size memory="20M"/>
  <visual><headlight ambient=".35 .35 .35" diffuse=".55 .55 .55"/><quality shadowsize="4096"/></visual>
  <default>
    <geom contype="1" conaffinity="2" friction="1 .02 .001" solref=".01 1"/>
    <default class="arm"><geom rgba=".85 .86 .88 1"/></default>
    <default class="finger"><geom rgba=".95 .55 .2 1" friction="1.1 .03 .001" solref=".015 1" solimp=".85 .95 .004" condim="4"/></default>
    <default class="cupg"><geom rgba=".95 .45 .1 1" friction="1.2 .03 .001" solref=".02 1" solimp=".8 .95 .005" condim="4"/></default>
    <default class="fruit"><geom contype="2" conaffinity="3" rgba=".25 .45 .12 1" friction=".8 .02 .001" condim="4" solref=".008 1"/></default>
    <default class="obst"><geom contype="2" conaffinity="1" rgba=".35 .3 .15 1"/></default>
  </default>
  <worldbody>
    <light pos="0 0 3" dir="0 .3 -1" diffuse=".8 .8 .8"/>
    <geom name="ground" type="plane" size="3 3 .1" rgba=".3 .27 .2 1" contype="2" conaffinity="1"/>
    <geom name="deck" type="box" size=".75 .38 .02" pos="0 0 .58" rgba=".2 .2 .22 1" contype="2" conaffinity="1"/>
    <geom class="obst" name="stem" type="capsule" size=".012" fromto="0 0 .2 0 0 1.5"/>
    <geom class="obst" name="stake" type="box" size=".0125 .0125 .65" pos="0 0 .85"/>
    {twine}
    <body name="arm_base" pos="{A['mount_x']} {A['mount_y']} {A['mount_z']}" euler="{-pi/2} 0 0">
      <geom class="arm" type="cylinder" size=".07 .02" pos="0 0 -.02"/>
      {body}{ee}{close}
    </body>
    {fruits}
  </worldbody>
  <equality>{eqs}
    <joint joint1="finger1" joint2="finger0"/><joint joint1="finger2" joint2="finger0"/>
  </equality>
  <contact><exclude body1="ee" body2="cup"/><exclude body1="wrist_3_link" body2="cup"/></contact>
  <actuator>
    {''.join(f'<position name="{n}" joint="{n}" kp="{3000 if i < 3 else 600}" kv="{120 if i < 3 else 25}" forcerange="{-t} {t}"/>' for i, (n, t) in enumerate(zip(names, torques)))}
    <position name="grip" joint="finger0" kp="15" kv=".1" forcerange="-5 5" ctrlrange="{f_open:.3f} {f_closed + .25:.3f}"/>
     <position name="plunger" joint="plunger" kp="350" kv="6" ctrlrange="{-stroke} 0"/>
    <adhesion name="suction" body="cup" ctrlrange="0 1" gain="19"/>
  </actuator>
  <sensor><force name="ft_force" site="ft"/><torque name="ft_torque" site="ft"/></sensor>
</mujoco>"""
    return xml, dict(f_open=f_open, f_closed=f_closed, stroke=stroke, grasp_off=E['tcp_z'] - grasp_z)

def quat_angle_axis_z(q):
    """Ball-joint quaternion -> (bend angle of local z, twist about local z)."""
    w, x, y, z = q
    bend = math.acos(min(1., max(-1., 1 - 2 * (x * x + y * y))))
    twist = 2 * math.atan2(z, w)   # swing-twist decomposition about z
    twist = (twist + math.pi) % (2 * math.pi) - math.pi
    return bend, abs(twist)

def so3_exp(w):
    th = np.linalg.norm(w)
    if th < 1e-9: return np.eye(3)
    k = w / th; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K

def so3_log(M):
    c = np.clip((np.trace(M) - 1) / 2, -1, 1); th = math.acos(c)
    if th < 1e-6: return np.zeros(3)
    if th > math.pi - 1e-4:    # 180 deg: axis from the diagonal
        k = np.sqrt(np.clip((np.diag(M) + 1) / 2, 0, 1)); return k * th
    return np.array([M[2, 1] - M[1, 2], M[0, 2] - M[2, 0], M[1, 0] - M[0, 1]]) * th / (2 * math.sin(th))

class TomatoPickEnv(gym.Env):
    metadata = {'render_modes': ['rgb_array'], 'render_fps': 20}

    def __init__(self, render_mode=None, seed=None, randomize=True, obs_noise=True, min_clearance=0.):
        self.P, self.params_file = load_params()
        xml, self.g = build_xml(self.P)
        self.model = mujoco.MjModel.from_xml_string(xml); self.data = mujoco.MjData(self.model)
        m = self.model
        self.arm_j = [m.joint(n).id for n in ('shoulder_pan', 'shoulder_lift', 'elbow', 'wrist_1', 'wrist_2', 'wrist_3')]
        self.arm_q = np.array([m.jnt_qposadr[j] for j in self.arm_j]); self.arm_v = np.array([m.jnt_dofadr[j] for j in self.arm_j])
        self.tcp = m.site('tcp').id; self.grasp = m.site('grasp').id; self.ft = m.site('ft').id
        self.fruit_names = ['target'] + [f'n{i}' for i in range(1, N_NEIGH + 1)]
        self.fb = [m.body(n).id for n in self.fruit_names]; self.fg = [m.geom(n + '_geom').id for n in self.fruit_names]
        self.stalk = [m.body(n + '_stalk').id for n in self.fruit_names]
        self.attach_eq = [m.equality(n + '_attach').id for n in self.fruit_names]
        self.pull_q = [m.jnt_qposadr[m.joint(n + '_pull').id] for n in self.fruit_names]
        self.pull_qa = np.array(self.pull_q); self.pull_va = np.array([m.jnt_dofadr[m.joint(n + '_pull').id] for n in self.fruit_names])
        self.bend_q = [m.jnt_qposadr[m.joint(n + '_bend').id] for n in self.fruit_names]
        self.free_q = [m.jnt_qposadr[m.joint(n + '_free').id] for n in self.fruit_names]
        self.free_v = [m.jnt_dofadr[m.joint(n + '_free').id] for n in self.fruit_names]
        self.finger_geoms = {m.geom(f'finger{k}_pad').id: k for k in range(3)}
        self.cup_geom = m.geom('cup_lip').id
        self.obst = {m.geom(n).id for n in ['stem', 'stake']}
        self.twine_z = np.array([.45, .70, .95, 1.20])
        self.arm_geoms = {g for g in range(m.ngeom) if m.geom_contype[g] == 1}
        self.stem_g, self.stake_g = m.geom('stem').id, m.geom('stake').id
        self.twine_g = [m.geom(f'twine{j}').id for j in range(4)]
        self.base_pos = np.array([self.P['ARM']['mount_x'], self.P['ARM']['mount_y'], self.P['ARM']['mount_z']])
        self.randomize, self.obs_noise = randomize, obs_noise
        self.min_clearance = min_clearance   # curriculum knob: lower (negative) = more cluttered, harder trusses
        self.action_space = spaces.Box(-1, 1, (8,), np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, (50 + 4 * N_NEIGH,), np.float32)
        self.render_mode = render_mode; self._renderer = None
        self.q_home = self._find_home()
        self._seed0 = seed

    # ------------------------------------------------------------------ kinematics
    def _tcp_pose(self):
        return self.data.site_xpos[self.tcp].copy(), self.data.site_xmat[self.tcp].reshape(3, 3).copy()

    def _ik_step(self, p_t, R_t, damping=.05, rot_w=.3, roll_w=.1, limit_gain=.03):
        """One damped-least-squares step toward (p_t, R_t), with joint-limit avoidance.
        Roll about the tool axis is weighted low: the 3-finger gripper is nearly symmetric, so when a joint nears its
        stop the controller gives up roll before it gives up position or approach angle."""
        m, d = self.model, self.data
        p, Rm = self._tcp_pose()
        e_p = p_t - p
        e_r = Rm.T @ (.5 * sum(np.cross(Rm[:, i], R_t[:, i]) for i in range(3)))      # tool frame
        jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv)); mujoco.mj_jacSite(m, d, jp, jr, self.tcp)
        w = np.array([rot_w, rot_w, roll_w])
        J = np.vstack([jp[:, self.arm_v], w[:, None] * (Rm.T @ jr[:, self.arm_v])]); e = np.r_[e_p, w * e_r]
        q = d.qpos[self.arm_q]; mid = (JOINT_LO + JOINT_HI) / 2; half = (JOINT_HI - JOINT_LO) / 2
        g = limit_gain * ((mid - q) / half) ** 3                                          # push away from the stops
        Jpinv = J.T @ np.linalg.inv(J @ J.T + damping ** 2 * np.eye(6))
        dq = Jpinv @ e + (np.eye(6) - Jpinv @ J) @ g     # limit avoidance only in what the task leaves free (mostly roll)
        return dq, np.linalg.norm(e_p), np.linalg.norm(e_r)

    def _ik_servo(self, p_t, R_t, roll_w=.15):
        """Per-step servo: bounded Levenberg-Marquardt IK warm-started at the current joints (a few iterations), so
        it respects the FR5 joint stops and degrades gracefully near singularities. Roll about the tool axis is
        weighted low (the 3-finger gripper is nearly symmetric). Physics state is left untouched."""
        from scipy.optimize import least_squares
        d = self.data; q_now = d.qpos[self.arm_q].copy()
        m = self.model; jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv))
        sk = lambda v: np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        def res(q):
            d.qpos[self.arm_q] = q; mujoco.mj_kinematics(m, d)
            p, Rm = self._tcp_pose()
            return np.r_[(p - p_t) * 10, Rm[:, 2] - R_t[:, 2], roll_w * (Rm[:, 0] - R_t[:, 0])]
        def jac(q):   # analytic: d(axis)/dq = -[axis]x J_rot  (saves the finite-difference evaluations)
            d.qpos[self.arm_q] = q; mujoco.mj_kinematics(m, d); mujoco.mj_comPos(m, d)
            mujoco.mj_jacSite(m, d, jp, jr, self.tcp); Rm = d.site_xmat[self.tcp].reshape(3, 3)
            Jr = jr[:, self.arm_v]
            return np.vstack([10 * jp[:, self.arm_v], -sk(Rm[:, 2]) @ Jr, -roll_w * sk(Rm[:, 0]) @ Jr])
        lo, hi = JOINT_LO + .02, JOINT_HI - .02
        sol = least_squares(res, np.clip(q_now, lo + 1e-3, hi - 1e-3), jac=jac, bounds=(lo, hi), max_nfev=8, x_scale=.3)
        d.qpos[self.arm_q] = q_now; mujoco.mj_kinematics(self.model, d)
        return sol.x - q_now

    def _solve_kinematic(self, p_t, R_t, q0, iters=60):
        """Full position + orientation IK (Levenberg-Marquardt) from seed q0; leaves data at the solution."""
        from scipy.optimize import least_squares
        d = self.data
        def res(q):
            d.qpos[self.arm_q] = q; mujoco.mj_kinematics(self.model, d)
            p, Rm = self._tcp_pose()
            return np.r_[(p - p_t) * 10, (Rm - R_t)[:, [0, 2]].reshape(-1, order='F')]
        lo, hi = JOINT_LO + .02, JOINT_HI - .02
        sol = least_squares(res, np.clip(q0, lo + .01, hi - .01), bounds=(lo, hi), max_nfev=iters * 10)
        q = sol.x; res(q); mujoco.mj_comPos(self.model, d)
        p, Rm = self._tcp_pose()
        er = .5 * np.linalg.norm(sum(np.cross(Rm[:, i], R_t[:, i]) for i in range(3)))
        return q.copy(), np.linalg.norm(p - p_t), er

    def approach_dir(self, fruit):
        """Default approach axis for a fruit (robot frame): along the line from the arm base, level for fruit at
        or above shoulder height and tilted down for low fruit (keeps the wrist above the deck)."""
        ap = fruit - self.base_pos; ap[2] = 0; ap /= np.linalg.norm(ap) + 1e-9
        ap[2] = np.clip(2.0 * (fruit[2] - (self.base_pos[2] + .05)), -.7, .2)
        return ap / np.linalg.norm(ap)

    def approach_candidates(self, fruit):
        """The default axis plus yaw / pitch variants, so a planner can come in around an occluding neighbour."""
        ap0 = self.approach_dir(fruit); out = []
        for dyaw in (0, .35, -.35, .7, -.7, 1.0, -1.0):
            for dz in (0, .35, -.35, .7, -.7):
                c, s_ = math.cos(dyaw), math.sin(dyaw)
                ap = np.array([c * ap0[0] - s_ * ap0[1], s_ * ap0[0] + c * ap0[1], ap0[2] + dz])
                out.append(ap / np.linalg.norm(ap))
        return out

    @staticmethod
    def clearance(fruit, ap, neighbours, finger_r=.065, length=.25):
        """Free space (m) between the open gripper's swept volume and the neighbour fruit when coming in along ap."""
        a, b = fruit - ap * length, fruit - ap * .01
        best = 1.
        for c, r in neighbours:
            t = np.clip((c - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
            best = min(best, np.linalg.norm(c - (a + t * (b - a))) - r - finger_r)
        return best

    def reachable(self, fruit, q0, standoff=0., ap=None):
        """Kinematic check only: the physics state is restored afterwards, so it is safe to call mid-episode."""
        q_save = self.data.qpos[self.arm_q].copy()
        try:
            return self._reachable(fruit, q0, standoff, ap)
        finally:
            self.data.qpos[self.arm_q] = q_save; mujoco.mj_forward(self.model, self.data)

    def _reachable(self, fruit, q0, standoff, ap):
        ap = self.approach_dir(fruit) if ap is None else ap; R = self._approach_R(ap)
        grasp_off = self.g['grasp_off']
        q, ep, er = self._solve_kinematic(fruit - ap * standoff + R[:, 2] * grasp_off, R, q0, iters=25)
        if ep > 3e-3 or er > 3e-2: return False
        zs = [self.data.xpos[self.model.body(n).id][2] for n in ('elbow_link', 'wrist_1_link', 'wrist_2_link', 'wrist_3_link')]
        elbow_y = self.data.xpos[self.model.body('elbow_link').id][1]
        canopy_edge = self.P['FIELD']['bed_centres'] / 2 - self.P['FIELD']['canopy_half_width']
        # wrist and elbow above the deck, elbow out of the canopy (the forearm must not sweep through the plants)
        # and every arm link stays behind the flange along the approach, so only the gripper enters the plant
        x = lambda n: self.data.xpos[self.model.body(n).id]
        behind = all((x(n) - x('wrist_3_link')) @ ap < -.01 for n in ('elbow_link', 'wrist_1_link'))
        return min(zs) > .65 and elbow_y < canopy_edge - .1 and behind

    def _find_home(self):
        """Start pose: TCP 0.4 m in front of the base and 0.3 m above its axis, tool into the row (+y). Among the IK
        branches, keep the one that reaches most of the fruit band without leaving its branch."""
        R_t = self._approach_R(np.array([0, 1., 0]))
        p_t = self.base_pos + np.array([0, .40, .30])
        rng = np.random.default_rng(0); homes = []
        for k in range(40):
            q, ep, er = self._solve_kinematic(p_t, R_t, rng.uniform(JOINT_LO, JOINT_HI))
            if ep < 1e-3 and er < 1e-2 and not any(np.allclose(q, h, atol=.05) for h in homes): homes.append(q)
        assert homes, 'no IK solution for the home pose'
        bed = self.P['FIELD']['bed_centres'] / 2
        grid = [np.array([x, bed + dy, z]) for x in (-.3, .3) for dy in (-.3, -.1) for z in (.55, .8, 1.05, 1.3)]
        cover = [sum(self.reachable(g, h) for g in grid) for h in homes]
        return homes[int(np.argmax(cover))]

    @staticmethod
    def _approach_R(z, up=np.array([0, 0, 1.])):
        z = z / np.linalg.norm(z); x = np.cross(up, z)
        if np.linalg.norm(x) < 1e-6: x = np.array([1., 0, 0])
        x /= np.linalg.norm(x); y = np.cross(z, x)
        return np.stack([x, y, z], 1)

    # ------------------------------------------------------------------ scene sampling
    def _sample_scene(self):
        r = self.np_random; m = self.model
        F = self.P['FIELD']; bed_y = F['bed_centres'] / 2
        # truss: peduncle leaves the stem toward the aisle and droops; fruit hang along it, spaced so they touch at most
        for attempt in range(1000):
            # the base parks so the plant is 0.15-0.4 m ahead of or behind the shoulder axis: straight-in approaches
            # with the wrist ON the side-mounted base axis (z = mount height) are the arm's shoulder singularity
            sx, sy = r.choice([-1, 1]) * r.uniform(.15, .40), bed_y + r.uniform(-.04, .04)
            twine_y = sy - r.uniform(.06, .11)
            zt = r.uniform(max(.6, F['fruit_z'][0] + .15), min(1.42, F['fruit_z'][1] + .05))
            yaw = r.uniform(-1.0, 1.0); droop = r.uniform(.1, .5)
            out = np.array([math.sin(yaw), -math.cos(yaw), -droop]); out /= np.linalg.norm(out)
            n = int(r.integers(3, N_NEIGH + 2))
            ti = int(r.integers(0, n))          # which fruit on the truss is ready to pick
            fr, knuck, ped = [], [], []
            along = r.uniform(.03, .06); prev_r = 0.
            for k in range(n):
                rad = r.uniform(.029, .042) if k == ti else r.uniform(.015, .04)
                along += prev_r + rad + r.uniform(.004, .015) if k else 0
                side = np.cross(out, [0, 0, 1.]); side /= np.linalg.norm(side)
                kp = np.array([sx, sy, zt]) + out * along + side * r.uniform(-.015, .015)
                tilt = r.normal(0, .15, 2); pdir = np.array([tilt[0], tilt[1], -1.]); pdir /= np.linalg.norm(pdir)
                off = r.uniform(.015, .03) + rad * .9
                knuck.append(kp); ped.append(pdir); fr.append((kp + pdir * off, rad, off)); prev_r = rad
            c = [f[0] for f in fr]; rads = [f[1] for f in fr]
            ok = all(np.linalg.norm(c[i] - c[j]) > rads[i] + rads[j] + .003 for i in range(n) for j in range(i))
            ok = ok and all(np.linalg.norm(c[i][:2] - [sx, sy]) > rads[i] + .016 for i in range(n))
            ok = ok and c[ti][1] < twine_y - rads[ti] - .004        # target hangs on the aisle side of the twine
            ok = ok and all(abs(c[i][1] - twine_y) > rads[i] + .004 for i in range(n))
            ok = ok and all(abs(c[i][2] - z) > rads[i] + .004 for i in range(n) for z in (.45, .70, .95, 1.20))
            ok = ok and .30 < np.linalg.norm(c[ti] - (self.base_pos + [0, .15, 0])) < .80 and abs(c[ti][0] - self.base_pos[0]) > .12
            if ok:   # the fruit must be pickable: some approach is reachable and not blocked by a neighbour
                neigh = [(c[k], rads[k]) for k in range(n) if k != ti]
                cands = sorted(self.approach_candidates(c[ti]), key=lambda ap: -self.clearance(c[ti], ap, neigh))
                ok = False
                for ap in cands[:4]:
                    if self.clearance(c[ti], ap, neigh) < self.min_clearance: break
                    if self.reachable(c[ti], self.q_home, ap=ap) and self.reachable(c[ti], self.q_home, standoff=.12, ap=ap):
                        ok = True; break
            if ok: break
        m.geom_pos[self.stem_g][:2] = [sx, sy]
        m.geom_pos[self.stake_g] = [sx + r.choice([-1, 1]) * r.uniform(.2, .26), sy + r.uniform(-.02, .02), .85]
        for g in self.twine_g: m.geom_pos[g][:2] = [sx, twine_y]
        order = [ti] + [k for k in range(n) if k != ti]
        self.n_fruit = n
        self.ripeness = r.uniform(0, 1)       # 0 mature-green (firm) .. 1 red ripe (soft)
        for slot in range(N_NEIGH + 1):
            if slot < n:
                k = order[slot]; c_, rad, off = fr[k]; kp = knuck[k]; pdir = ped[k]
            else:
                kp = np.array([3. + slot, 3., 3.]); pdir = np.array([0, 0, -1.]); rad, off = .03, .05; c_ = kp + pdir * off
            Rk = self._approach_R(-pdir, up=np.array([1., 0, 0]))   # local -z along the pedicel
            qk = np.zeros(4); mujoco.mju_mat2Quat(qk, Rk.reshape(-1))
            m.body_pos[self.stalk[slot]] = kp; m.body_quat[self.stalk[slot]] = qk
            g = self.fg[slot]; m.geom_size[g] = [rad, rad, rad * r.uniform(.8, .9)]
            mass = 1000 * 4 / 3 * math.pi * rad ** 3 * .95; b = self.fb[slot]
            m.body_mass[b] = mass; m.body_inertia[b] = .4 * mass * rad ** 2
            m.geom_friction[g, 0] = r.uniform(.55, 1.0) if self.randomize else .8
            m.eq_data[self.attach_eq[slot], 3:6] = [0, 0, -off]
            m.eq_data[self.attach_eq[slot], 6:10] = [1, 0, 0, 0]
            self.data.qpos[self.free_q[slot]:self.free_q[slot] + 3] = c_
            self.data.qpos[self.free_q[slot] + 3:self.free_q[slot] + 7] = qk
            self.data.eq_active[self.attach_eq[slot]] = 1
            m.geom_rgba[g] = [.2 + .6 * self.ripeness, .45 - .35 * self.ripeness, .1, 1] if slot == 0 else [.15, .4, .1, 1]
        # knuckle strength (per episode): straight pull is strong, bend and twist break it far earlier
        self.F_pull = r.uniform(18, 32); self.bend_max = r.uniform(1.1, 1.7); self.twist_max = r.uniform(2.0, 4.0)
        self.F_bruise = 45 - 25 * self.ripeness   # per Fin-Ray finger (spread contact): firm mature-green ~45 N, red ~20 N
        self.target_radius = fr[ti][1]
        # perception error: bias per episode (detector + depth) plus per-step jitter
        s = self.obs_noise
        self.fruit_bias = r.normal(0, .006, 3) * s; self.rad_bias = r.normal(0, .003) * s
        self.neigh_bias = r.normal(0, .008, (N_NEIGH, 3)) * s; self.neigh_r = [fr[k][1] for k in order[1:]]
        self.ped_dir = ped[ti]; self.ped_bias = r.normal(0, .2, 3) * s
        self.stem_xy = np.array([sx, sy]); self.stem_bias = r.normal(0, .01, 2) * s

    # ------------------------------------------------------------------ gym API
    def reset(self, seed=None, options=None):
        super().reset(seed=seed if seed is not None else self._seed0); self._seed0 = None
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        self._sample_scene()
        # start pose: home, jittered
        R0 = self._approach_R(np.array([self.np_random.uniform(-.3, .3), 1, self.np_random.uniform(-.3, .2)]))
        tgt = d.qpos[self.free_q[0]:self.free_q[0] + 3].copy()
        for _ in range(20):
            p0 = self.base_pos + np.array([np.sign(tgt[0]) * self.np_random.uniform(.05, .3), self.np_random.uniform(.32, .45), self.np_random.uniform(.15, .35)])
            if np.linalg.norm(p0 - tgt) > .22: break
        q, ep, er = self._solve_kinematic(p0, R0, self.q_home, iters=30)
        if ep > 5e-3: q = self.q_home
        d.qpos[self.arm_q] = q; d.qvel[:] = 0
        d.ctrl[:6] = q; d.ctrl[6] = self.g['f_open']; d.ctrl[7] = 0; d.ctrl[8] = 0
        mujoco.mj_forward(m, d)
        for _ in range(150): self._physics_step()     # let the fruit settle on their knuckles (0.3 s)
        d.qvel[:] = 0
        # knuckle strain is measured from this settled rest state, so gravity sag never counts toward a break
        self.rest_pull = np.array([d.qpos[a] for a in self.pull_q])
        self.fruit0 = d.xpos[self.fb[0]].copy()
        self.rest_quat = [d.qpos[a:a + 4].copy() for a in self.bend_q]
        self.rest_conj = [np.array([q[0], -q[1], -q[2], -q[3]]) for q in self.rest_quat]; self._rel = np.zeros(4)
        self.p_t, self.R_t = self._tcp_pose()
        self.steps = 0; self.detached = np.zeros(N_NEIGH + 1, bool); self.prev = None
        self.sealed = False; self.cup_contact = False; self.f_filt = np.zeros(3)
        self.info_acc = dict(max_finger_force=0., max_stem_force=0., bruised=False, detach_mode=None, twine_contact=0)
        return self._obs(), {}

    def _contacts(self):
        m, d = self.model, self.data
        fingers = set(); cup = False; fsum = np.zeros(3); stem_f = 0.; twine = False; neigh_hit = 0.
        f6 = np.zeros(6)
        tg = self.fg[0]
        for i in range(d.ncon):
            c = d.contact[i]; g1, g2 = c.geom1, c.geom2
            pair = {g1, g2}
            if tg in pair:
                o = g2 if g1 == tg else g1
                if o in self.finger_geoms or o == self.cup_geom:
                    mujoco.mj_contactForce(m, d, i, f6)
                    if o == self.cup_geom: cup = True
                    else: fingers.add(self.finger_geoms[o]); fsum[self.finger_geoms[o]] += abs(f6[0])
            if pair & self.arm_geoms:
                o = (pair - self.arm_geoms)
                o = next(iter(o)) if o else None
                if o in (self.stem_g, self.stake_g):
                    mujoco.mj_contactForce(m, d, i, f6); stem_f = max(stem_f, abs(f6[0]))
                elif o in self.twine_g: twine = True
                elif o in self.fg[1:]:
                    mujoco.mj_contactForce(m, d, i, f6); neigh_hit = max(neigh_hit, abs(f6[0]))
        return fingers, cup, fsum, stem_f, twine, neigh_hit

    def _extracted(self, fruit):
        """0..1 progress of pulling the picked fruit clear of the plant."""
        moved = np.linalg.norm(fruit - self.fruit0); back = self.fruit0[1] - fruit[1]
        return min(moved / EXTRACT, back / .08)

    def _physics_step(self):
        """mj_step plus the pedicel spring, which is tension-only: pulling stretches it (K_PULL) but pushing the fruit
        toward its knuckle just buckles the pedicel (K_BUCKLE), as a real one does."""
        x = self.data.qpos[self.pull_qa]
        self.data.qfrc_applied[self.pull_va] = -np.where(x > 0, K_PULL, K_BUCKLE) * x
        mujoco.mj_step(self.model, self.data)

    def _twine_snag(self):
        """Gripper (housing to fingertips) within its radius of a twine line, measured in the y-z plane."""
        ty = self.model.geom_pos[self.twine_g[0]][1]; R = self.P['EE']['body_d'] / 2 + .01
        for site_pos in (self.data.site_xpos[self.grasp], self.data.site_xpos[self.ft]):
            if np.min(np.hypot(site_pos[1] - ty, site_pos[2] - self.twine_z)) < R: return True
        return False

    def _knuckle(self, slot):
        d = self.data
        pull = (d.qpos[self.pull_q[slot]] - self.rest_pull[slot]) * K_PULL
        rel = self._rel; mujoco.mju_mulQuat(rel, self.rest_conj[slot], d.qpos[self.bend_q[slot]:self.bend_q[slot] + 4])
        bend, twist = quat_angle_axis_z(rel)
        return pull, bend, twist

    def step(self, action):
        a = np.clip(np.asarray(action, np.float64), -1, 1)
        m, d = self.model, self.data
        # 1. update TCP target and solve one IK step toward it
        p, Rm = self._tcp_pose()
        self.p_t = self.p_t + .012 * a[:3]
        lo = self.base_pos + np.array([-.6, .05, -.55]); hi = self.base_pos + np.array([.6, .95, .55])
        self.p_t = np.clip(self.p_t, lo, hi)
        self.p_t = p + np.clip(self.p_t - p, -.04, .04)     # never let the target run away from the real TCP
        self.R_t = self.R_t @ so3_exp(.08 * a[3:6])
        w_err = so3_log(Rm.T @ self.R_t)                    # keep the orientation target within 0.35 rad of reality
        if np.linalg.norm(w_err) > .35: self.R_t = Rm @ so3_exp(w_err * .35 / np.linalg.norm(w_err))
        dq = self._ik_servo(self.p_t, self.R_t)
        d.ctrl[:6] = np.clip(d.qpos[self.arm_q] + np.clip(dq, -.15, .15), JOINT_LO, JOINT_HI)
        d.ctrl[6] = self.g['f_open'] + (a[6] + 1) / 2 * (self.g['f_closed'] + .25 - self.g['f_open'])
        suction = a[7] > 0
        # EE firmware behaviour: the cup rides extended; once the vacuum switch sees a seal (cup contact with vacuum on)
        # the plunger retracts and draws the fruit into the fingers. Vacuum off -> plunger extends again.
        if not suction: self.sealed = False
        elif self.cup_contact: self.sealed = True
        d.ctrl[8] = 1. if suction else 0.; d.ctrl[7] = -self.g['stroke'] if self.sealed else 0.
        # 2. physics, checking knuckle breaks every substep
        newly = []
        for k in range(SUBSTEPS):
            self._physics_step()
            if k % 5 != 4: continue                     # knuckle check at 100 Hz
            for s in np.flatnonzero(~self.detached[:self.n_fruit]):
                pull, bend, twist = self._knuckle(s)
                mode = 'pull' if pull > self.F_pull else 'bend' if bend > self.bend_max else 'twist' if twist > self.twist_max else None
                if mode:
                    d.eq_active[self.attach_eq[s]] = 0; self.detached[s] = True; newly.append((s, mode))
        self.steps += 1
        fingers, cup, fsum, stem_f, _, neigh_hit = self._contacts()
        self.cup_contact = cup
        twine = self._twine_snag()
        fruit = d.xpos[self.fb[0]].copy(); tcp = d.site_xpos[self.grasp].copy()
        held = len(fingers) >= 2 or (cup and suction)
        dist = np.linalg.norm(tcp - fruit)
        # 3. reward
        r = -.02 - .002 * float(a @ a)
        if not self.detached[0]:
            r += .6 * (1 - math.tanh(6 * dist)) + .3 * (cup and suction) + .15 * len(fingers)
        else:
            r += 1. + (2. * min(1., self._extracted(fruit)) if held else 0)
        for s, mode in newly:
            if s == 0:
                r += 8. if held else 2.
                self.info_acc['detach_mode'] = mode
        # bruising follows sustained squeeze, not millisecond contact spikes: low-pass the per-finger force (~0.1 s)
        self.f_filt = .6 * self.f_filt + .4 * fsum
        fmax = float(self.f_filt.max())
        self.info_acc['max_finger_force'] = max(self.info_acc['max_finger_force'], fmax)
        self.info_acc['max_stem_force'] = max(self.info_acc['max_stem_force'], stem_f)
        if fmax > self.F_bruise:
            r -= .5 + .05 * (fmax - self.F_bruise); self.info_acc['bruised'] = True
        if stem_f > 5: r -= .02 * min(stem_f, 60)
        if neigh_hit > 3: r -= .1
        if twine: r -= .05; self.info_acc['twine_contact'] += 1
        # 4. termination
        success = bool(self.detached[0] and held and self._extracted(fruit) >= 1)
        dropped = bool(self.detached[0] and not held and np.linalg.norm(fruit - tcp) > .12)
        knocked = bool(self.detached[1:self.n_fruit].any())
        broke_plant = stem_f > 80
        terminated = success or dropped or knocked or broke_plant
        if success: r += 40.   # big enough that PPO never trades picking for safely doing nothing
        if dropped: r -= 5.
        if knocked: r -= 6.
        if broke_plant: r -= 6.
        truncated = self.steps >= MAX_STEPS and not terminated
        info = dict(self.info_acc, success=success, dropped=dropped, knocked=knocked, broke_plant=broke_plant,
                    detached=bool(self.detached[0]), held=held, t=self.steps * CTRL_DT)
        return self._obs(fingers, cup, suction), float(r), terminated, truncated, info

    def _obs(self, fingers=frozenset(), cup=False, suction=False):
        d = self.data; r = self.np_random
        tcp, Rm = self._tcp_pose()
        jit = r.normal(0, .002, 3) * self.obs_noise
        fruit_est = d.xpos[self.fb[0]] + self.fruit_bias + jit
        ped = self.ped_dir + self.ped_bias; ped /= np.linalg.norm(ped)
        stem = np.r_[self.stem_xy + self.stem_bias, tcp[2]]
        ft = np.r_[d.sensordata[0:3] / 20, d.sensordata[3:6] / 2]
        fq = (d.qpos[self.model.jnt_qposadr[self.model.joint('finger0').id]] - self.g['f_open']) / (self.g['f_closed'] - self.g['f_open'])
        o = np.r_[d.qpos[self.arm_q] / math.pi, np.clip(d.qvel[self.arm_v] / 3, -3, 3),
                  tcp - self.base_pos, Rm[:, 0], Rm[:, 2], fq, d.qpos[self.model.jnt_qposadr[self.model.joint('plunger').id]] / .03,
                  float(suction), fruit_est - tcp, Rm.T @ (fruit_est - tcp), self.target_radius + self.rad_bias, ped,
                  self.fruit0 + self.fruit_bias - tcp, stem - tcp, np.clip(ft, -5, 5), len(fingers) / 3, float(cup), float(self.detached[0]),
                  self.steps / MAX_STEPS]
        nb = np.zeros((N_NEIGH, 4))
        for k in range(1, self.n_fruit):   # neighbours the detector sees on the truss (zeros = empty slot / gone)
            if not self.detached[k]:
                nb[k - 1] = np.r_[d.xpos[self.fb[k]] + self.neigh_bias[k - 1] - tcp, self.neigh_r[k - 1]]
        o = np.r_[o, nb.reshape(-1)]
        return o.astype(np.float32)

    def render(self):
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, 480, 640)
            self._cam = mujoco.MjvCamera(); self._cam.lookat[:] = [0, .55, 1.0]; self._cam.distance = 1.6
            self._cam.azimuth = 200; self._cam.elevation = -18
        self._renderer.update_scene(self.data, self._cam)
        return self._renderer.render()

gym.register('AgroboTomatoPick-v0', entry_point=TomatoPickEnv, max_episode_steps=MAX_STEPS)

"""Modular field UGV (ugv_alpha, ugv_beta): one chassis, hot-swappable implements.

Implements (auto-coupler at the dock, ~6 min swap):
  laser_weeder  - 2 x 150 W CO2 galvo heads + close-range RGB-D verification
  micro_doser   - per-plant root-zone liquid N injection
  picker_arm    - 2 x 6-DoF arms, soft 3-finger grippers with tactile force control
                  (the /crop_picker_manipulator component lives here)

Actions (namespaced by robot id)
  /<id>/weed_zone       WeedZone
  /<id>/dose_nutrients  DoseNutrients
  /<id>/harvest_rows    HarvestRows
Topics
  /fleet/status   RobotStatus     /harvest/lots   HarvestLot (one per bin)
"""
import math

import numpy as np
from agrobo_interfaces.action import DoseNutrients, HarvestRows, WeedZone
from agrobo_interfaces.msg import HarvestLot
from agrobo_interfaces.srv import FieldInteract, GetFieldState, PlanCoverage
from rclpy.action import ActionServer

from agrobo_sim.robot_base import RobotNode
from agrobo_sim.ros_util import RELIABLE

FI = FieldInteract.Request
TOOL_SWAP_S = 360.0


class CropPickerManipulator:
    """Grasp/detach model for one arm. Cycle-time terms are from bench timing targets."""

    def __init__(self, rng, arms=2):
        self.rng, self.arms = rng, arms
        self.approach_s, self.grasp_s, self.detach_s, self.place_s = 1.6, 0.9, 0.8, 1.2
        self.full_scan_s = 7.0           # multi-view arm-camera sweep to find fruit (no prior)
        self.localise_s = 2.5            # per-fruit 6D pose refinement without prior
        self.verify_s = 1.2              # twin-guided: confirm predicted fruit pose & ripeness
        self.force_mean_n, self.force_sigma_n = 3.6, 0.55

    def cycle_s(self):
        return self.approach_s + self.grasp_s + self.detach_s + self.place_s

    def grip_force(self):
        return float(max(1.5, self.rng.normal(self.force_mean_n, self.force_sigma_n)))


class UGVPlatform(RobotNode):
    def __init__(self):
        super().__init__("ugv_platform", "ugv_modular", speed=0.7, drive_kw=1.1, battery_kwh=12.0)
        self.declare_parameter("dock_y", 0.0)
        self.declare_parameter("seed", 5)
        self.dock = (-2.0, self.get_parameter("dock_y").value)
        self.x, self.y = self.dock
        self.rng = np.random.default_rng(self.get_parameter("seed").value)
        self.implement = "none"
        self.tool_swaps = 0
        self.picker = CropPickerManipulator(self.rng)
        self.interact = self.client(FieldInteract, "/field/interact")
        self.get_state = self.client(GetFieldState, "/field/get_state")
        self.planner = self.client(PlanCoverage, "/fleet_path_planner/plan")
        self.lot_pub = self.create_publisher(HarvestLot, "/harvest/lots", RELIABLE)
        ns = f"/{self.robot_id}"
        ActionServer(self, WeedZone, f"{ns}/weed_zone", self.on_weed, callback_group=self.cbg)
        ActionServer(self, DoseNutrients, f"{ns}/dose_nutrients", self.on_dose, callback_group=self.cbg)
        ActionServer(self, HarvestRows, f"{ns}/harvest_rows", self.on_harvest, callback_group=self.cbg)
        self.lot_seq = 0

    # ------------------------------------------------------------------ implement state machine
    def ensure_implement(self, tool):
        if self.implement == tool:
            return 0.0
        h = self.go_home() + self.work(TOOL_SWAP_S, 0.3)
        self.emit("tool_change", robot_id=self.robot_id, frm=self.implement, to=tool)
        self.implement, self.tool_swaps = tool, self.tool_swaps + 1
        return h

    def tour(self, xs, ys):
        if not xs:
            return [], 0.0
        r = self.call(self.planner, PlanCoverage.Request(robot_id=self.robot_id, mode="tsp", xs=list(xs),
                                                         ys=list(ys), start_x=self.x, start_y=self.y))
        return list(r.order), r.length_m

    # ------------------------------------------------------------------ weeding
    def on_weed(self, gh):
        g = gh.request
        hours = self.ensure_implement("laser_weeder")
        self.task, self.speed = "weeding", 0.5
        truth = self.call(self.get_state, GetFieldState.Request(include_fruit=False)).state.weeds
        alive = {w.weed_id: w for w in truth}
        order, length = self.tour(g.xs, g.ys)
        d0 = self.odo
        hours += self.drive_to(g.xs[order[-1]], g.ys[order[-1]], length) if order else 0.0
        kill_ids, kill_e, misfire, cleared = [], [], [], ([], [])
        rejected = opp = 0
        work_s = 0.0
        for k, i in enumerate(order):
            tx, ty = g.xs[i], g.ys[i]
            near = [w for w in alive.values() if (w.x - tx) ** 2 + (w.y - ty) ** 2 < 0.08 ** 2]
            ring = [w for w in alive.values() if 0.08 ** 2 <= (w.x - tx) ** 2 + (w.y - ty) ** 2 < 0.3 ** 2]
            work_s += 0.6                                         # stop, re-detect, aim
            if near:
                for w in near:
                    if self.rng.random() < 0.985:                 # close-range verification recall
                        e = 4.0 + 1.4 * w.size_cm * self.rng.normal(1.0, 0.08)
                        kill_ids.append(w.weed_id); kill_e.append(e)
                        work_s += e / 150.0 + 0.15
                        alive.pop(w.weed_id)
            elif self.rng.random() < 0.97:
                rejected += 1                                     # false target, no shot
            else:
                misfire += [tx, ty]
                work_s += 0.3
            for w in ring:                                        # opportunistic kills in the camera FOV
                if self.rng.random() < 0.9:
                    e = 4.0 + 1.4 * w.size_cm
                    kill_ids.append(w.weed_id); kill_e.append(e)
                    work_s += e / 150.0 + 0.4
                    alive.pop(w.weed_id)
                    opp += 1
            cleared[0].append(tx); cleared[1].append(ty)
            if k % 50 == 0:
                gh.publish_feedback(WeedZone.Feedback(progress=k / max(1, len(order))))
        res_k = self.call(self.interact, FI(op=FI.OP_KILL_WEED, target_ids=kill_ids, values=kill_e))
        dmg = []
        if misfire:
            dmg = self.call(self.interact, FI(op=FI.OP_LASER_MISFIRE, values=misfire)).collateral_ids
        hours += self.work(work_s, 0.9)
        self.task = "idle"
        gh.succeed()
        killed = len(res_k.succeeded_ids)
        r = WeedZone.Result(killed=killed, missed=len(kill_ids) - killed, false_targets_rejected=rejected,
                            crop_damage=len(dmg), opportunistic_kills=opp, cleared_x=cleared[0],
                            cleared_y=cleared[1], herbicide_l=0.0, distance_m=self.odo - d0, duration_h=hours)
        self.emit_task("weeding", duration_h=hours, targets=len(order), killed=killed, missed=r.missed,
                       rejected=rejected, crop_damage=len(dmg), opportunistic=opp, herbicide_l=0.0)
        return r

    # ------------------------------------------------------------------ dosing
    def on_dose(self, gh):
        g = gh.request
        hours = self.ensure_implement("micro_doser")
        self.task, self.speed = "dosing", 0.6
        st = self.call(self.get_state, GetFieldState.Request(include_fruit=False)).state
        pos = {p.plant_id: (p.x, p.y) for p in st.plants}
        ids = [i for i in g.plant_ids if i in pos]
        order, length = self.tour([pos[i][0] for i in ids], [pos[i][1] for i in ids])
        hours += self.drive_to(*pos[ids[order[-1]]], length) if order else 0.0
        hours += self.work(3.0 * len(ids), 0.4)
        self.call(self.interact, FI(op=FI.OP_DOSE_NITROGEN, target_ids=list(g.plant_ids), values=list(g.dose_g_n)))
        self.task = "idle"
        gh.succeed()
        total = float(sum(g.dose_g_n))
        self.emit_task("dosing", duration_h=hours, plants=len(ids), n_g=total)
        return DoseNutrients.Result(dosed=len(ids), total_n_g=total, duration_h=hours)

    # ------------------------------------------------------------------ harvesting
    def on_harvest(self, gh):
        g = gh.request
        hours = self.ensure_implement("picker_arm")
        self.task, self.speed = "harvesting", 0.6
        res = self.call(self.get_state, GetFieldState.Request(include_fruit=True))
        pos = {p.plant_id: (p.x, p.y) for p in res.state.plants}
        on_plant = {}
        for f in res.fruit:
            on_plant.setdefault(f.plant_id, []).append(f)
        known = set(g.fruit_ids)
        visit = [p for p in g.plant_ids if p in pos]
        order, length = self.tour([pos[p][0] for p in visit], [pos[p][1] for p in visit])
        hours += self.drive_to(*pos[visit[order[-1]]], length) if order else 0.0
        pk = self.picker
        work_s, first_pick_s, attempts = 0.0, None, []
        travel_s_per_plant = (length / self.speed) / max(1, len(order))
        for k, i in enumerate(order):
            pid = visit[i]
            fruit = on_plant.get(pid, [])
            work_s += pk.verify_s if g.twin_guided else pk.full_scan_s
            for f in fruit:
                # onboard stereo + ripeness head, close range
                vis = 0.97 if f.fruit_id in known else (0.7 if f.occluded else 0.92)
                if self.rng.random() > vis:
                    continue
                r_est = f.ripeness + self.rng.normal(0, 0.03)
                if not ((g.min_ripeness or 0.75) <= r_est < 1.0):
                    continue
                if not (g.twin_guided and f.fruit_id in known):
                    work_s += pk.localise_s
                work_s += pk.cycle_s() / pk.arms
                attempts.append((f.fruit_id, pk.grip_force(), 1.0 if f.occluded else 0.0))
                if first_pick_s is None:
                    first_pick_s = work_s + k * travel_s_per_plant
            if k % 40 == 0:
                gh.publish_feedback(HarvestRows.Feedback(picked_so_far=len(attempts)))
        ids = [a[0] for a in attempts]
        vals = [v for a in attempts for v in a[1:]]
        out = self.call(self.interact, FI(op=FI.OP_PICK_FRUIT, target_ids=ids, values=vals)) if ids else None
        # failed grasps get one retry
        if out is not None:
            failed = [a for a in attempts if a[0] not in set(out.succeeded_ids)]
            if failed:
                work_s += len(failed) * pk.cycle_s() / pk.arms
                out2 = self.call(self.interact, FI(op=FI.OP_PICK_FRUIT, target_ids=[a[0] for a in failed],
                                                   values=[v for a in failed for v in a[1:]]))
                out.succeeded_ids = list(out.succeeded_ids) + list(out2.succeeded_ids)
                out.out_values = list(out.out_values) + list(out2.out_values)
        hours += self.work(work_s, 0.6)
        picked = list(out.succeeded_ids) if out else []
        ov = list(out.out_values) if out else []
        rip, mass, bru = ov[0::3], ov[1::3], [b > 0.5 for b in ov[2::3]]
        self.lot_seq += 1
        lot_id = f"{self.robot_id}-d{g.day:03d}-{self.lot_seq:03d}"
        lot = HarvestLot(lot_id=lot_id, picked_by=self.robot_id, day_harvested=g.day, fruit_count=len(picked),
                         mass_kg=sum(mass) / 1000.0, mean_ripeness=float(np.mean(rip)) if rip else 0.0,
                         bruise_rate=float(np.mean(bru)) if bru else 0.0,
                         first_pick_hour=g.start_hour + hours_before_first(first_pick_s),
                         ripeness=rip, mass_g=mass, bruised=bru)
        if picked:
            self.lot_pub.publish(lot)
        self.task = "idle"
        gh.succeed()
        n_att = len(attempts)
        cycle = (hours * 3600.0 / len(picked)) if picked else 0.0
        self.emit_task("harvesting", duration_h=hours, attempted=n_att, picked=len(picked), bruised=int(sum(bru)),
                       mass_kg=lot.mass_kg, twin_guided=g.twin_guided, plants_visited=len(order),
                       predicted=len(known), lot_id=lot_id, day=g.day)
        return HarvestRows.Result(attempted=n_att, picked=len(picked), bruised=int(sum(bru)), mass_kg=lot.mass_kg,
                                  mean_cycle_s=cycle, duration_h=hours, lot_id=lot_id if picked else "",
                                  picked_ids=picked)


def hours_before_first(s):
    return (s or 0.0) / 3600.0


def main(args=None):
    from agrobo_sim.ros_util import spin
    spin(UGVPlatform, args)

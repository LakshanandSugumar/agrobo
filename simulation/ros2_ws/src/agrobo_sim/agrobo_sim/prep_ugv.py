"""/prep_ugv: Phase 2 infrastructure & prep platform (heavy UGV, implement hitch).

Actions
  /prep_ugv/prep_field   PrepField   clear -> RTK grid layout -> till -> lay drip tape
  /prep_ugv/transplant   Transplant  precision transplanting of plug seedlings
"""
from agrobo_interfaces.action import PrepField, Transplant
from agrobo_interfaces.srv import FieldInteract, GetFieldState, PlanCoverage
from rclpy.action import ActionServer

from agrobo_sim.robot_base import RobotNode

FI = FieldInteract.Request
#            swath m, speed m/s, implement kW
STAGES = {"clear": (2.0, 1.2, 9.0), "till": (1.5, 0.9, 15.0)}


class PrepUGV(RobotNode):
    def __init__(self):
        super().__init__("prep_ugv", "ugv_prep", speed=1.2, drive_kw=3.0, battery_kwh=40.0, dock=(-3.0, -2.0))
        self.interact = self.client(FieldInteract, "/field/interact")
        self.get_state = self.client(GetFieldState, "/field/get_state")
        self.planner = self.client(PlanCoverage, "/fleet_path_planner/plan")
        ActionServer(self, PrepField, "/prep_ugv/prep_field", self.on_prep, callback_group=self.cbg)
        ActionServer(self, Transplant, "/prep_ugv/transplant", self.on_transplant, callback_group=self.cbg)

    def _op(self, op, ids=(), vals=()):
        return self.call(self.interact, FI(op=op, target_ids=list(ids), values=list(vals)))

    def on_prep(self, gh):
        g = gh.request
        L, W = g.plants_per_row * g.plant_spacing_m, g.rows * g.row_spacing_m
        hours, dist0, fb = 0.0, self.odo, PrepField.Feedback()
        for i, (stage, op) in enumerate([("clear", FI.OP_CLEAR), ("survey", None), ("till", FI.OP_TILL),
                                         ("irrigation", FI.OP_DEPLOY_IRRIGATION)]):
            self.task = f"prep:{stage}"
            if stage in STAGES:
                swath, v, kw = STAGES[stage]
                plan = self.call(self.planner, PlanCoverage.Request(robot_id=self.robot_id, mode="boustrophedon",
                                                                    xs=[L, swath], ys=[W], start_x=self.x, start_y=self.y))
                self.speed = v
                hours += self.drive_to(plan.path_x[-1], plan.path_y[-1], plan.length_m)
                hours += self.work(plan.length_m / v, kw)
                self._op(op)
            elif stage == "survey":
                # RTK-GNSS layout: drive each planting line, drop a geo-tagged marker per plant site
                self.speed = 0.8
                n = g.rows * g.plants_per_row
                hours += self.drive_to(L, W, g.rows * (L + 2.0))
                hours += self.work(n * 1.5, 0.5)
            else:
                # drip tape + header line: one pass per planting row, plus mainline along the headland
                self.speed = 0.6
                hours += self.drive_to(0.0, W, g.rows * (L + 2.0) + W)
                hours += self.work(g.rows * 600.0, 4.0)       # fittings/emitter checks per lateral
                self._op(op)
            fb.stage, fb.progress = stage, (i + 1) / 4.0
            gh.publish_feedback(fb)
        hours += self.go_home()
        self.task = "idle"
        gh.succeed()
        r = PrepField.Result(success=True, area_ha=L * W / 1e4, distance_m=self.odo - dist0,
                             energy_kwh=self.energy, duration_h=hours)
        self.emit_task("prep", duration_h=hours, area_ha=r.area_ha, distance_m=r.distance_m)
        return r

    def on_transplant(self, gh):
        ids = list(gh.request.plant_ids)
        st = self.call(self.get_state, GetFieldState.Request(include_fruit=False)).state
        pos = {p.plant_id: (p.x, p.y) for p in st.plants}
        self.task, self.speed, hours = "transplant", 0.5, 0.0
        # 2-row transplanter: visits row pairs, 3.5 s per plug (pick from tray, dibble, firm)
        rows = sorted({round(pos[i][1], 3) for i in ids})
        L = max(x for x, _ in pos.values()) + 0.25
        for k in range(0, len(rows), 2):
            hours += self.drive_to(L if (k // 2) % 2 == 0 else 0.0, rows[k], L + 3.0)
        hours += self.work(len(ids) * 3.5 / 2.0, 1.5)
        res = self.call(self.interact, FI(op=FI.OP_TRANSPLANT, target_ids=ids))
        hours += self.go_home()
        self.task = "idle"
        gh.succeed()
        self.emit_task("transplant", duration_h=hours, planted=len(res.succeeded_ids))
        return Transplant.Result(planted=len(res.succeeded_ids), duration_h=hours)


def main(args=None):
    from agrobo_sim.ros_util import spin
    spin(PrepUGV, args)

"""/mission_orchestrator: season-level behavior tree + Field Ledger (plant-level twin).

Runs on the edge hub. Ticks a py_trees tree that walks the five macro-phases:

agrobo_season (Sequence, memory)
 |- phase1_sourcing   ? [sourced] / call /strategy/evaluate_parcels
 |- phase2_prep       ? [prepped] / action /prep_ugv/prep_field
 |- phase3_establish  ? [planted] / action /prep_ugv/transplant
 '- season_loop (repeat until season_days)
     '- daily_cycle (Sequence, memory)
         |- start_day
         |- scouting      ? [not due] / (scout_field -> wait_for_perception)
         |- plan_work     Field Ledger -> work orders -> auction to modular UGVs
         |- field_ops     Parallel(SuccessOnAll): lane ugv_alpha || lane ugv_beta
         |                each lane = per-robot state machine:
         |                IDLE -> TOOL_SWAP -> HARVEST | WEED | DOSE -> ... -> IDLE
         |- logistics     ? [no lots] / (haul_to_hub -> process_lot x N)
         |- cloud_gate    ? (link_up -> publish yield forecast / forward contracts) / edge_only
         |- market        action /market/sell_inventory
         '- advance_day   call /field/advance_day -> ledger.on_day
"""
import json
import threading

import numpy as np
import py_trees
from agrobo_interfaces.action import (DoseNutrients, HarvestRows, HaulToHub, PrepField, ProcessLot, ScoutField,
                                      SellInventory, Transplant, WeedZone)
from agrobo_interfaces.msg import DetectionArray, FieldState
from agrobo_interfaces.srv import AdvanceDay, EvaluateParcels
from rclpy.action import ActionClient
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from std_msgs.msg import Bool, Float64MultiArray, String

from agrobo_sim.core.twin import FieldLedger
from agrobo_sim.ros_util import LATCHED, RELIABLE, AgroboNode, spin

S = py_trees.common.Status
UGVS = ("ugv_alpha", "ugv_beta")


# ============================================================================ behaviours
class Cond(py_trees.behaviour.Behaviour):
    def __init__(self, name, fn):
        super().__init__(name)
        self.fn = fn

    def update(self):
        return S.SUCCESS if self.fn() else S.FAILURE


class Do(py_trees.behaviour.Behaviour):
    def __init__(self, name, fn):
        super().__init__(name)
        self.fn = fn

    def update(self):
        r = self.fn()
        return S.FAILURE if r is False else S.SUCCESS


class WaitFor(py_trees.behaviour.Behaviour):
    def __init__(self, name, fn):
        super().__init__(name)
        self.fn = fn

    def update(self):
        return S.SUCCESS if self.fn() else S.RUNNING


class _Async:
    """Tracks one ROS action goal or service call from inside a tick-driven behaviour."""

    def __init__(self):
        self.done, self.result, self.ok = False, None, False

    def send_action(self, client, goal):
        def on_goal(f):
            gh = f.result()
            if not gh.accepted:
                self.done = True
                return
            gh.get_result_async().add_done_callback(on_result)

        def on_result(f):
            r = f.result()
            self.result, self.ok, self.done = r.result, r.status == 4, True   # STATUS_SUCCEEDED

        client.send_goal_async(goal).add_done_callback(on_goal)

    def send_srv(self, client, req):
        def cb(f):
            self.result, self.ok, self.done = f.result(), f.exception() is None, True
        client.call_async(req).add_done_callback(cb)


class ActionCall(py_trees.behaviour.Behaviour):
    """goal_fn() -> goal | None (None = nothing to do, SUCCESS). on_result(result) -> bool."""

    def __init__(self, name, client, goal_fn, on_result=None, service=False):
        super().__init__(name)
        self.client, self.goal_fn, self.on_result, self.service = client, goal_fn, on_result, service
        self.op = None
        self.skip = False

    def initialise(self):
        goal = self.goal_fn()
        self.skip, self.op = goal is None, None
        if not self.skip:
            self.op = _Async()
            (self.op.send_srv if self.service else self.op.send_action)(self.client, goal)

    def update(self):
        if self.skip:
            return S.SUCCESS
        if not self.op.done:
            return S.RUNNING
        if not self.op.ok:
            return S.FAILURE
        ok = self.on_result(self.op.result) if self.on_result else True
        return S.FAILURE if ok is False else S.SUCCESS


class QueueRunner(py_trees.behaviour.Behaviour):
    """Executes ctx.queues[key] items (client, goal_fn, on_result) one after another.

    For a UGV this is the per-robot task state machine; tool swaps happen inside the
    robot when consecutive orders need different implements.
    """

    def __init__(self, name, ctx, key):
        super().__init__(name)
        self.ctx, self.key, self.op, self.item = ctx, key, None, None

    def initialise(self):
        self.op, self.item = None, None

    def update(self):
        q = self.ctx.queues.setdefault(self.key, [])
        if self.op is not None:
            if not self.op.done:
                return S.RUNNING
            client, _, on_result = self.item
            if self.op.ok and on_result:
                on_result(self.op.result)
            elif not self.op.ok:
                self.ctx.node.get_logger().warn(f"{self.key}: task failed")
            self.op = None
        if not q:
            return S.SUCCESS
        self.item = q.pop(0)
        client, goal_fn, _ = self.item
        goal = goal_fn()
        if goal is None:
            self.item = None
            return S.RUNNING
        self.op = _Async()
        self.op.send_action(client, goal)
        return S.RUNNING


class SeasonLoop(py_trees.decorators.Decorator):
    """Re-runs the daily cycle until the season ends."""

    def __init__(self, name, child, done_fn):
        super().__init__(name=name, child=child)
        self.done_fn = done_fn

    def update(self):
        if self.done_fn():
            return S.SUCCESS
        if self.decorated.status == S.SUCCESS:
            self.decorated.stop(S.INVALID)
        elif self.decorated.status == S.FAILURE:
            return S.FAILURE
        return S.RUNNING


# ============================================================================ node
class Ctx:
    pass


class MissionOrchestrator(AgroboNode):
    def __init__(self):
        super().__init__("mission_orchestrator")
        for k, v in dict(season_days=125, twin_guided=True, scout_every=2, harvest_min_fruit=25,
                         weed_trigger=12, rows=10, plants_per_row=48, run_name="agrobo").items():
            self.declare_parameter(k, v)
        P = lambda n: self.get_parameter(n).value
        self.season_days, self.twin_guided = P("season_days"), P("twin_guided")
        self.ledger = FieldLedger()
        self.tick_group = MutuallyExclusiveCallbackGroup()
        c = self.ctx = Ctx()
        c.node, c.queues, c.lots_today, c.lane_end = self, {}, [], {}
        c.flags = dict(sourced=False, prepped=False, planted=False)
        c.day, c.eop, c.eop_needed, c.last_scout, c.last_harvest, c.last_dose = 0, 0, 0, -99, 0, 0
        c.link_up, c.plant_ids, c.state, c.gdd_hist = True, [], None, []
        c.season_done, c.parcel_id = False, None
        self.lock = threading.Lock()

        A = lambda t, n: ActionClient(self, t, n, callback_group=self.cbg)
        self.ac = dict(prep=A(PrepField, "/prep_ugv/prep_field"), transplant=A(Transplant, "/prep_ugv/transplant"),
                       scout=A(ScoutField, "/scout_uav/scout_field"), haul=A(HaulToHub, "/hauler_ugv/haul_to_hub"),
                       process=A(ProcessLot, "/hub/process_lot"), sell=A(SellInventory, "/market/sell_inventory"))
        for u in UGVS:
            self.ac[f"{u}/weed"] = A(WeedZone, f"/{u}/weed_zone")
            self.ac[f"{u}/dose"] = A(DoseNutrients, f"/{u}/dose_nutrients")
            self.ac[f"{u}/harvest"] = A(HarvestRows, f"/{u}/harvest_rows")
        self.srv_eval = self.create_client(EvaluateParcels, "/strategy/evaluate_parcels", callback_group=self.cbg)
        self.srv_adv = self.create_client(AdvanceDay, "/field/advance_day", callback_group=self.cbg)
        self.forecast_pub = self.create_publisher(Float64MultiArray, "/farm_twin/yield_forecast", RELIABLE)
        self.bt_pub = self.create_publisher(String, "/mission_orchestrator/bt_snapshot", 10)

        g = self.tick_group
        self.create_subscription(DetectionArray, "/perception/weeds", self.on_weeds, RELIABLE, callback_group=g)
        self.create_subscription(DetectionArray, "/perception/fruit", self.on_fruit, RELIABLE, callback_group=g)
        self.create_subscription(DetectionArray, "/perception/chlorosis", self.on_chl, RELIABLE, callback_group=g)
        self.create_subscription(FieldState, "/field/state", lambda m: setattr(c, "state", m), LATCHED, callback_group=g)
        self.create_subscription(Bool, "/cloud/link_up", lambda m: setattr(c, "link_up", m.data), LATCHED,
                                 callback_group=g)

        self.tree = py_trees.trees.BehaviourTree(self.build_tree())
        self.metrics = dict(scout_passes=0, harvest_runs=0, weed_runs=0, dose_runs=0, picked=0, predicted=0,
                            edge_only_days=0, work_orders=[])
        self._ready = False
        self.create_timer(0.01, self.tick, callback_group=g)
        self.create_timer(2.0, self.publish_snapshot, callback_group=g)

    # ---------------------------------------------------------------- perception -> ledger
    def _eop(self, m):
        if m.header.frame_id == "eop":
            self.ctx.eop += 1
            return True
        return False

    def on_weeds(self, m):
        if not self._eop(m):
            for d in m.detections:
                if d.confidence >= 0.4:
                    self.ledger.ingest_weed(d.x, d.y, d.value, d.confidence)

    def on_fruit(self, m):
        if not self._eop(m):
            for d in m.detections:
                self.ledger.ingest_fruit(d.target_id, int(d.class_name.split(":")[1]), d.value)

    def on_chl(self, m):
        if not self._eop(m):
            for d in m.detections:
                self.ledger.ingest_chlorosis(d.target_id, d.x, d.y, d.value)

    # ---------------------------------------------------------------- tree
    def build_tree(self):
        c, ac = self.ctx, self.ac
        Seq = lambda n, ch: py_trees.composites.Sequence(n, memory=True, children=ch)
        Sel = lambda n, ch: py_trees.composites.Selector(n, memory=False, children=ch)
        Inv = lambda b: py_trees.decorators.Inverter(name=f"not_{b.name}", child=b)

        phase1 = Sel("phase1_sourcing", [
            Cond("sourced?", lambda: c.flags["sourced"]),
            ActionCall("evaluate_parcels", self.srv_eval, lambda: EvaluateParcels.Request(n_candidates=40, seed=2026),
                       self.on_sourcing, service=True)])
        phase2 = Sel("phase2_prep", [
            Cond("prepped?", lambda: c.flags["prepped"]),
            Seq("prep_sequence", [
                WaitFor("parcel_applied", lambda: c.state is not None and c.state.header.frame_id == f"field:{c.parcel_id}"),
                ActionCall("prep_field", ac["prep"], self.goal_prep, self.on_prep)])])
        phase3 = Sel("phase3_establish", [
            Cond("planted?", lambda: c.flags["planted"]),
            ActionCall("transplant", ac["transplant"], lambda: Transplant.Goal(plant_ids=c.plant_ids),
                       self.on_transplant)])
        scouting = Sel("scouting", [
            Inv(Cond("scout_due?", lambda: c.day - c.last_scout >= self.get_parameter("scout_every").value)),
            Seq("scout_pass", [
                ActionCall("scout_field", ac["scout"], self.goal_scout, self.on_scout),
                WaitFor("perception_settled", lambda: c.eop >= c.eop_needed)])])
        field_ops = py_trees.composites.Parallel(
            "field_ops", policy=py_trees.common.ParallelPolicy.SuccessOnAll(),
            children=[QueueRunner(f"lane_{u}", c, u) for u in UGVS])
        logistics = Sel("logistics", [
            Inv(Cond("lots_today?", lambda: bool(c.lots_today))),
            Seq("field_to_market", [
                ActionCall("haul_to_hub", ac["haul"], self.goal_haul, self.on_haul),
                Do("queue_lots", self.queue_lots),
                QueueRunner("hub_process_lots", c, "hub")])])
        cloud_gate = Sel("cloud_gate", [
            Seq("cloud_online", [Cond("link_up?", lambda: c.link_up), Do("publish_yield_forecast", self.forecast)]),
            Do("edge_only_mode", self.edge_only)])
        daily = Seq("daily_cycle", [
            Do("start_day", self.start_day), scouting, Do("plan_work", self.plan_work), field_ops, logistics,
            cloud_gate,
            ActionCall("sell_inventory", ac["sell"], lambda: SellInventory.Goal(day=c.day), None),
            ActionCall("advance_day", self.srv_adv, lambda: AdvanceDay.Request(days=1), self.on_advance, service=True)])
        season = SeasonLoop("season_loop", daily, lambda: c.day >= self.season_days)
        return Seq("agrobo_season", [phase1, phase2, phase3, season, Do("season_complete", self.finish)])

    def tick(self):
        if not self._ready:
            names = [self.srv_eval, self.srv_adv] + list(self.ac.values())
            if not all((n.service_is_ready() if hasattr(n, "service_is_ready") else n.server_is_ready())
                       for n in names):
                return
            self._ready = True
            self.get_logger().info("all servers up; starting season")
        if self.ctx.season_done:
            return
        self.tree.tick()

    def publish_snapshot(self):
        self.bt_pub.publish(String(data=py_trees.display.unicode_tree(self.tree.root, show_status=True)))

    # ---------------------------------------------------------------- phase callbacks
    def on_sourcing(self, r):
        self.ctx.flags["sourced"] = True
        self.ctx.parcel_id = r.parcel_id
        self.emit("phase", phase="sourcing", parcel=r.parcel_id, crop=r.crop, suitability=r.suitability_score,
                  npv_usd=r.projected_npv_usd)
        self.get_logger().info(f"[phase1] parcel {r.parcel_id} crop={r.crop} suitability={r.suitability_score:.2f}")

    def goal_prep(self):
        P = lambda n: self.get_parameter(n).value
        return PrepField.Goal(rows=P("rows"), plants_per_row=P("plants_per_row"), row_spacing_m=1.5,
                              plant_spacing_m=0.5)

    def on_prep(self, r):
        self.ctx.flags["prepped"] = True
        self.ctx.plant_ids = [p.plant_id for p in self.ctx.state.plants]
        self.emit("phase", phase="prep", duration_h=r.duration_h, area_ha=r.area_ha, distance_m=r.distance_m)
        self.get_logger().info(f"[phase2] prep done: {r.area_ha:.3f} ha in {r.duration_h:.1f} h")

    def on_transplant(self, r):
        self.ctx.flags["planted"] = True
        self.emit("phase", phase="establish", planted=r.planted, duration_h=r.duration_h)
        self.get_logger().info(f"[phase3] transplanted {r.planted} plugs in {r.duration_h:.1f} h")

    # ---------------------------------------------------------------- daily callbacks
    def start_day(self):
        c = self.ctx
        c.queues = {u: [] for u in UGVS}
        c.queues["hub"] = []
        c.lots_today, c.lane_end = [], {u: 6.5 for u in UGVS}

    def goal_scout(self):
        c = self.ctx
        c.eop_needed = c.eop + 3
        return ScoutField.Goal(robot_id="scout_uav", altitude_m=8.0)

    def on_scout(self, r):
        self.ctx.last_scout = self.ctx.day
        self.metrics["scout_passes"] += 1

    def plan_work(self):
        """Field Ledger -> work orders -> allocation that minimises implement swaps."""
        c, L = self.ctx, self.ledger
        orders = []
        if c.state is None:
            return
        pos = {p.plant_id: (p.x, p.y) for p in c.state.plants}
        fruiting = [p.plant_id for p in c.state.plants if p.stage >= 4]
        if self.twin_guided:
            ripe = L.harvest_orders(lo=0.80)        # pick on the forecast day of market-optimal ripeness
            if len(ripe) >= self.get_parameter("harvest_min_fruit").value or (ripe and c.day - c.last_harvest >= 3):
                plants = sorted({t.pid for t in ripe})
                orders.append(("harvest", plants, [t.fid for t in ripe]))
        elif fruiting and c.day - c.last_harvest >= 3:
            orders.append(("harvest", fruiting, []))           # ablation: no prior, scan every plant
        weeds = L.weeds
        if weeds and (len(weeds) >= self.get_parameter("weed_trigger").value or
                      c.day - min(w.day for w in weeds) >= 4):
            orders.append(("weed", weeds, None))
        doses = L.dose_orders()
        if doses and (len(doses) >= 20 or c.day - c.last_dose >= 7):
            c.last_dose = c.day
            orders.append(("dose", doses, None))
        # split big harvests across both UGVs by row band (both carry picker arms)
        expanded = []
        for o in orders:
            if o[0] == "harvest" and len(o[1]) > 40:
                rows = sorted({round(pos[p][1], 2) for p in o[1]})
                half = set(rows[: len(rows) // 2])
                a = [p for p in o[1] if round(pos[p][1], 2) in half]
                b = [p for p in o[1] if round(pos[p][1], 2) not in half]
                fa = [f for f in o[2] if L.fruit[f].pid in set(a)]
                fb = [f for f in o[2] if L.fruit[f].pid in set(b)]
                expanded += [("harvest", a, fa), ("harvest", b, fb)]
            else:
                expanded.append(o)
        load = {u: 0 for u in UGVS}
        tool = {u: getattr(self, f"_tool_{u}", "none") for u in UGVS}
        need = {"harvest": "picker_arm", "weed": "laser_weeder", "dose": "micro_doser"}
        for kind, a, b in expanded:
            # auction: cost = queued tasks + swap penalty
            u = min(UGVS, key=lambda r: load[r] + (0 if tool[r] == need[kind] else 0.6))
            load[u] += 1
            tool[u] = need[kind]
            c.queues[u].append(self.make_task(u, kind, a, b))
        for u in UGVS:
            setattr(self, f"_tool_{u}", tool[u])
        self.metrics["work_orders"].append(dict(day=c.day, orders=[(k, len(a)) for k, a, _ in expanded]))
        self.emit("work_plan", day=c.day, orders=[dict(kind=k, n=len(a)) for k, a, _ in expanded],
                  weed_tracks=len(weeds), predicted_ripe=len(L.harvest_orders()))

    def make_task(self, u, kind, a, b):
        c, L = self.ctx, self.ledger
        if kind == "harvest":
            def goal():
                return HarvestRows.Goal(robot_id=u, fruit_ids=list(b), twin_guided=self.twin_guided, plant_ids=list(a),
                                        start_hour=c.lane_end[u], day=c.day,
                                        min_ripeness=0.80 if self.twin_guided else 0.75)

            def done(r):
                c.lane_end[u] += r.duration_h
                c.last_harvest = c.day
                L.mark_picked(r.picked_ids)
                self.metrics["harvest_runs"] += 1
                self.metrics["picked"] += r.picked
                self.metrics["predicted"] += len(b)
                if r.lot_id:
                    c.lots_today.append(r.lot_id)
            return (self.ac[f"{u}/harvest"], goal, done)
        if kind == "weed":
            def goal():
                return WeedZone.Goal(robot_id=u, xs=[w.x for w in a], ys=[w.y for w in a],
                                     sizes_cm=[w.size_cm for w in a], method="laser")

            def done(r):
                c.lane_end[u] += r.duration_h
                L.clear_weeds(list(zip(r.cleared_x, r.cleared_y)))
                self.metrics["weed_runs"] += 1
            return (self.ac[f"{u}/weed"], goal, done)

        def goal():
            return DoseNutrients.Goal(robot_id=u, plant_ids=[p for p, _ in a], dose_g_n=[g for _, g in a])

        def done(r):
            c.lane_end[u] += r.duration_h
            for p, _ in a:
                L.plants[p].last_dose_day = c.day
            self.metrics["dose_runs"] += 1
        return (self.ac[f"{u}/dose"], goal, done)

    def goal_haul(self):
        c = self.ctx
        return HaulToHub.Goal(robot_id="hauler_ugv", lot_ids=c.lots_today, start_hour=max(c.lane_end.values()))

    def on_haul(self, r):
        return True

    def queue_lots(self):
        c = self.ctx
        c.queues["hub"] = [(self.ac["process"], (lambda i=i: ProcessLot.Goal(lot_id=i)), None) for i in c.lots_today]

    def forecast(self):
        g = float(np.mean(self.ctx.gdd_hist[-7:])) if self.ctx.gdd_hist else 14.0
        f = self.ledger.yield_forecast_kg(3, g)
        kg_a = 0.7 * f[-1]                                    # P50 grade-A share from past lots
        if kg_a > 0:
            self.forecast_pub.publish(Float64MultiArray(data=[float(self.ctx.day + 3), kg_a]))

    def edge_only(self):
        self.metrics["edge_only_days"] += 1
        self.emit("edge_only", day=self.ctx.day, ledger_fruit=len(self.ledger.fruit), weed_tracks=len(self.ledger.weeds))

    def on_advance(self, r):
        self.ctx.day = r.day
        self.ctx.gdd_hist.append(r.gdd_today)
        self.ledger.on_day(r.day, r.gdd_today)
        if r.day % 10 == 0:
            self.get_logger().info(f"day {r.day}: ledger fruit={len(self.ledger.fruit)} weeds={len(self.ledger.weeds)} "
                                   f"picked={self.metrics['picked']}")

    def finish(self):
        self.ctx.season_done = True
        m = {k: v for k, v in self.metrics.items() if k != "work_orders"}
        self.emit("season_complete", day=self.ctx.day, twin_guided=self.twin_guided,
                  run_name=self.get_parameter("run_name").value, metrics=m,
                  bt=py_trees.display.unicode_tree(self.tree.root))
        self.get_logger().info(f"season complete: {json.dumps(m)}")


def main(args=None):
    spin(MissionOrchestrator, args, threads=6)

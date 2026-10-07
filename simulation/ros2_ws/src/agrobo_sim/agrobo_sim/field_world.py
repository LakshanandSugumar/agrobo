"""/field_world: ground-truth farm (crop growth, weeds, soil, weather) as a ROS 2 node.

Services
  /field/get_state    agrobo_interfaces/srv/GetFieldState
  /field/interact     agrobo_interfaces/srv/FieldInteract   (every physical robot effect)
  /field/advance_day  agrobo_interfaces/srv/AdvanceDay
Topics
  /field/state        agrobo_interfaces/msg/FieldState (latched, on change)
  /strategy/selected_parcel  std_msgs/String (in; JSON parcel -> soil parameters)
"""
import json
import threading

import numpy as np
from agrobo_interfaces.msg import FieldState, Fruit
from agrobo_interfaces.srv import AdvanceDay, FieldInteract, GetFieldState
from std_msgs.msg import String

from agrobo_sim.core.agronomy import Field, FieldConfig
from agrobo_sim.ros_util import LATCHED, AgroboNode, plant_to_msg, spin, weed_to_msg

FI = FieldInteract.Request


class FieldWorld(AgroboNode):
    def __init__(self):
        super().__init__("field_world")
        self.declare_parameter("rows", 10)
        self.declare_parameter("plants_per_row", 48)
        self.declare_parameter("seed", 7)
        self.declare_parameter("weed_seedbank", 1.0)
        self.lock = threading.RLock()
        self.field = Field(self._cfg())
        self.parcel_id = "default"
        self.pub = self.create_publisher(FieldState, "/field/state", LATCHED)
        self.create_service(GetFieldState, "/field/get_state", self.on_get, callback_group=self.cbg)
        self.create_service(FieldInteract, "/field/interact", self.on_interact, callback_group=self.cbg)
        self.create_service(AdvanceDay, "/field/advance_day", self.on_advance, callback_group=self.cbg)
        self.create_subscription(String, "/strategy/selected_parcel", self.on_parcel, LATCHED,
                                 callback_group=self.cbg)
        self.publish_state()
        self.get_logger().info(f"field ready: {len(self.field.plants)} plant sites, {self.field.area_ha:.3f} ha")

    def _cfg(self, **over):
        g = lambda n: self.get_parameter(n).value
        return FieldConfig(rows=g("rows"), plants_per_row=g("plants_per_row"), seed=g("seed"),
                           weed_seedbank=g("weed_seedbank"), **over)

    def on_parcel(self, msg):
        p = json.loads(msg.data)
        with self.lock:
            if self.field.day == 0 and not (self.field.tilled or self.field.cleared):
                self.field = Field(self._cfg(soil_n_ppm=p["n_ppm"], soil_om_pct=p["om_pct"]))
                self.parcel_id = p["parcel_id"]
                self.get_logger().info(f"field re-initialised for parcel {p['parcel_id']} (N={p['n_ppm']:.1f} ppm)")
        self.publish_state()

    def state_msg(self):
        f = self.field
        m = FieldState(day=f.day, air_temp_c=f.temp_c, soil_moisture=f.soil_moisture,
                       soil_nitrogen_ppm=float(np.mean([p.soil_n for p in f.plants])),
                       irrigation_deployed=f.irrigation, tilled=f.tilled)
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = f"field:{self.parcel_id}"
        m.plants = [plant_to_msg(p, f) for p in f.plants]
        m.weeds = [weed_to_msg(w) for w in f.live_weeds()]
        return m

    def publish_state(self):
        with self.lock:
            self.pub.publish(self.state_msg())

    def on_get(self, req, res):
        with self.lock:
            res.state = self.state_msg()
            if req.include_fruit:
                res.fruit = [Fruit(fruit_id=i, plant_id=p, ripeness=r, height_m=h, occluded=o)
                             for i, p, r, h, o in self.field.fruit_on_plants(0.3)]
        return res

    def on_interact(self, req, res):
        f = self.field
        with self.lock:
            op, ids, vals = req.op, list(req.target_ids), list(req.values)
            if op == FI.OP_CLEAR:
                f.clear(); res.message = "cleared"
            elif op == FI.OP_TILL:
                f.till(); res.message = "tilled"
            elif op == FI.OP_DEPLOY_IRRIGATION:
                f.deploy_irrigation(); res.message = "drip deployed"
            elif op == FI.OP_TRANSPLANT:
                res.succeeded_ids = f.transplant(ids)
            elif op == FI.OP_KILL_WEED:
                for i, wid in enumerate(ids):
                    if f.kill_weed(wid, vals[i] if i < len(vals) else 10.0):
                        res.succeeded_ids.append(wid)
            elif op == FI.OP_LASER_MISFIRE:
                for k in range(0, len(vals) - 1, 2):
                    pid = f.laser_misfire(vals[k], vals[k + 1])
                    if pid:
                        res.collateral_ids.append(pid)
            elif op == FI.OP_DOSE_NITROGEN:
                for i, pid in enumerate(ids):
                    f.dose_n(pid, vals[i])
                    res.succeeded_ids.append(pid)
            elif op == FI.OP_PICK_FRUIT:
                # values: [grip_force_N, occluded_view(0/1)] per fruit; out: [ripeness, mass_g, bruised] per success
                for i, fid in enumerate(ids):
                    ok, r, m, b = f.pick(fid, vals[2 * i], vals[2 * i + 1] > 0.5)
                    if ok:
                        res.succeeded_ids.append(fid)
                        res.out_values.extend([r, m, 1.0 if b else 0.0])
            else:
                res.message = f"unknown op {op}"
        if op in (FI.OP_CLEAR, FI.OP_TILL, FI.OP_DEPLOY_IRRIGATION, FI.OP_TRANSPLANT):
            self.publish_state()
        return res

    def on_advance(self, req, res):
        g = 0.0
        with self.lock:
            for _ in range(max(1, req.days)):
                g += self.field.step_day()
            f = self.field
            res.day, res.gdd_today = f.day, g
            planted = [p for p in f.plants if p.stage]
            self.emit("field_day", day=f.day, gdd=g, temp_c=f.temp_c, live_weeds=len(f.live_weeds()),
                      mean_weed_comp=float(np.mean([p.weed_comp for p in planted])) if planted else 0.0,
                      mean_n_stress=float(np.mean([p.n_stress for p in planted])) if planted else 0.0,
                      fruit_on_plants=int((f.f_state == 0).sum()),
                      ripe_on_plants=int(((f.f_state == 0) & (f.f_ripe >= 0.75) & (f.f_ripe < 1.0)).sum()),
                      overripe_on_plants=int(((f.f_state == 0) & (f.f_ripe >= 1.0)).sum()),
                      stats=f.stats, area_ha=f.area_ha, plants=len(planted),
                      total_set_kg=float(f.f_mass.sum() / 1000.0))
        self.publish_state()
        return res


def main(args=None):
    spin(FieldWorld, args)

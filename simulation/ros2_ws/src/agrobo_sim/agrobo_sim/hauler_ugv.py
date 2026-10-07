"""/hauler_ugv: field-to-hub logistics (150 kg payload, follows the headland track).

Action  /hauler_ugv/haul_to_hub  HaulToHub
Topics  /harvest/lots (in)  ->  /harvest/lot_delivered (out, delivered_hour stamped)
"""
import math

from agrobo_interfaces.action import HaulToHub
from agrobo_interfaces.msg import HarvestLot
from rclpy.action import ActionServer

from agrobo_sim.robot_base import RobotNode
from agrobo_sim.ros_util import RELIABLE


class HaulerUGV(RobotNode):
    def __init__(self):
        super().__init__("hauler_ugv", "ugv_hauler", speed=1.5, drive_kw=1.8, battery_kwh=15.0, dock=(-15.0, -10.0))
        self.declare_parameter("payload_kg", 150.0)
        self.declare_parameter("pickup_xy", [-1.0, 7.5])
        self.declare_parameter("hub_xy", [-15.0, -10.0])
        self.lots = {}
        self.create_subscription(HarvestLot, "/harvest/lots", lambda m: self.lots.__setitem__(m.lot_id, m), RELIABLE,
                                 callback_group=self.cbg)
        self.pub = self.create_publisher(HarvestLot, "/harvest/lot_delivered", RELIABLE)
        ActionServer(self, HaulToHub, "/hauler_ugv/haul_to_hub", self.on_haul, callback_group=self.cbg)

    def on_haul(self, gh):
        g = gh.request
        cap = self.get_parameter("payload_kg").value
        px, py = self.get_parameter("pickup_xy").value
        hx, hy = self.get_parameter("hub_xy").value
        leg = math.hypot(px - hx, py - hy) * 1.25          # farm-track tortuosity
        self.task, t, d0, trips = "hauling", 0.0, self.odo, 0
        t += self.drive_to(px, py, math.hypot(self.x - px, self.y - py) * 1.25)
        load, onboard = 0.0, []
        lots = [self.lots[i] for i in g.lot_ids if i in self.lots]
        # a lot that does not fit in the remaining payload starts a new trip (bins are not split)
        for k, lot in enumerate(lots + [None]):
            if lot is None or (onboard and load + lot.mass_kg > cap):
                if onboard:
                    t += self.work(90.0, 0.5)                   # bin load
                    t += self.drive_to(hx, hy, leg)
                    t += self.work(60.0, 0.5)                   # dock at cold-room door
                    trips += 1
                    for o in onboard:
                        o.delivered_hour = g.start_hour + t
                        o.pick_to_cool_h = max(0.0, o.delivered_hour - o.first_pick_hour)
                        self.pub.publish(o)
                    if lot is not None:
                        t += self.drive_to(px, py, leg)
                onboard, load = [], 0.0
            if lot is not None:
                onboard.append(lot)
                load += lot.mass_kg
            gh.publish_feedback(HaulToHub.Feedback(progress=(k + 1) / (len(lots) + 1)))
        self.task = "idle"
        gh.succeed()
        self.emit_task("hauling", duration_h=t, trips=trips, lots=len(lots), kg=sum(l.mass_kg for l in lots))
        return HaulToHub.Result(trips=trips, distance_m=self.odo - d0, duration_h=t)


def main(args=None):
    from agrobo_sim.ros_util import spin
    spin(HaulerUGV, args)

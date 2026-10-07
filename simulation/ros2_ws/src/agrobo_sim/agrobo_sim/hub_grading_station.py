"""/hub_grading_station: hyperspectral grading + autonomous cold-chain packing.

Action  /hub/process_lot  ProcessLot
Topics  /harvest/lot_delivered (in) -> /hub/inventory (out, graded & packed HarvestLot)
"""
import numpy as np
from agrobo_interfaces.action import ProcessLot
from agrobo_interfaces.msg import HarvestLot
from rclpy.action import ActionServer

from agrobo_sim.core.postharvest import ColdChainPacker, FruitItem, HyperspectralGrader, Lot
from agrobo_sim.ros_util import RELIABLE, AgroboNode, spin


class HubGradingStation(AgroboNode):
    def __init__(self):
        super().__init__("hub_grading_station")
        self.rng = np.random.default_rng(404)
        self.grader, self.packer = HyperspectralGrader(), ColdChainPacker()
        self.lots = {}
        self.create_subscription(HarvestLot, "/harvest/lot_delivered", lambda m: self.lots.__setitem__(m.lot_id, m),
                                 RELIABLE, callback_group=self.cbg)
        self.pub = self.create_publisher(HarvestLot, "/hub/inventory", RELIABLE)
        ActionServer(self, ProcessLot, "/hub/process_lot", self.on_process, callback_group=self.cbg)

    def on_process(self, gh):
        m = self.lots.get(gh.request.lot_id)
        if m is None:
            gh.abort()
            return ProcessLot.Result()
        lot = Lot(m.lot_id, m.day_harvested, [FruitItem(r, w, b) for r, w, b in zip(m.ripeness, m.mass_g, m.bruised)])
        gh.publish_feedback(ProcessLot.Feedback(stage="hyperspectral_grading"))
        t = self.grader.grade(self.rng, lot)
        gh.publish_feedback(ProcessLot.Feedback(stage="cold_chain_packing"))
        t += self.packer.pack(lot, m.pick_to_cool_h)
        m.grade = [i.grade for i in lot.items]
        m.kg_grade_a, m.kg_grade_b, m.kg_grade_c, m.kg_rejected = (lot.grade_kg(g) for g in ("A", "B", "C", "reject"))
        m.shelf_life_d, m.graded, m.packed = lot.shelf_life_d, True, True
        self.pub.publish(m)
        gh.succeed()
        self.emit("lot_processed", lot_id=m.lot_id, day=m.day_harvested, kg=m.mass_kg, a=m.kg_grade_a,
                  b=m.kg_grade_b, c=m.kg_grade_c, rej=m.kg_rejected, pick_to_cool_h=m.pick_to_cool_h,
                  shelf_life_d=m.shelf_life_d, bruise_rate=m.bruise_rate, mean_ripeness=m.mean_ripeness,
                  duration_h=t)
        return ProcessLot.Result(lot=m, duration_h=t)


def main(args=None):
    spin(HubGradingStation, args)

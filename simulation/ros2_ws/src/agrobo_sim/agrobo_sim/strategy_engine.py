"""/strategy_engine: Phase 1 GIS parcel screening, crop matrix and financial forecast.

Service  /strategy/evaluate_parcels  agrobo_interfaces/srv/EvaluateParcels
Topic    /strategy/selected_parcel   std_msgs/String (latched JSON; consumed by /field_world)
"""
import json

from agrobo_interfaces.srv import EvaluateParcels
from std_msgs.msg import String

from agrobo_sim.core import strategy
from agrobo_sim.ros_util import LATCHED, AgroboNode, spin


class StrategyEngine(AgroboNode):
    def __init__(self):
        super().__init__("strategy_engine")
        self.declare_parameter("crop_lock", "tomato")
        self.pub = self.create_publisher(String, "/strategy/selected_parcel", LATCHED)
        self.create_service(EvaluateParcels, "/strategy/evaluate_parcels", self.on_eval, callback_group=self.cbg)

    def on_eval(self, req, res):
        lock = self.get_parameter("crop_lock").value or None
        best, report = strategy.evaluate(req.n_candidates or 40, req.seed or 2026, lock)
        p = best["parcel"]
        res.parcel_id, res.crop, res.suitability_score = p["parcel_id"], best["crop"], best["score"]
        res.soil_ph, res.soil_om_pct, res.soil_n_ppm, res.slope_pct = p["ph"], p["om_pct"], p["n_ppm"], p["slope_pct"]
        res.projected_npv_usd = best["npv"]
        res.projected_yield_t_ha = strategy.CROPS[best["crop"]]["y"]
        res.report_json = report
        self.pub.publish(String(data=json.dumps(p)))
        self.emit("strategy", report=json.loads(report))
        self.get_logger().info(f"selected {p['parcel_id']} for {best['crop']} (suitability {best['score']:.2f}, "
                               f"NPV ${best['npv'] / 1e6:.1f}M)")
        return res


def main(args=None):
    spin(StrategyEngine, args)

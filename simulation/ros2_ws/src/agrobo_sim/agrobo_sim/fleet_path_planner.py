"""/fleet_path_planner: coverage and target-tour planning for the fleet.

Service /fleet_path_planner/plan  agrobo_interfaces/srv/PlanCoverage
  mode=boustrophedon : xs[0]=field length, ys[0]=field width, xs[1]=swath width
  mode=tsp           : lane-constrained tour over (xs, ys) targets
"""
from agrobo_interfaces.srv import PlanCoverage

from agrobo_sim.core.planning import LaneMetric, boustrophedon, tsp_tour
from agrobo_sim.ros_util import AgroboNode, spin


class FleetPathPlanner(AgroboNode):
    def __init__(self):
        super().__init__("fleet_path_planner")
        self.declare_parameter("row_spacing_m", 1.5)
        self.declare_parameter("field_length_m", 24.0)
        self.create_service(PlanCoverage, "/fleet_path_planner/plan", self.on_plan, callback_group=self.cbg)

    def on_plan(self, req, res):
        start = (req.start_x, req.start_y)
        if req.mode == "boustrophedon":
            xs, ys, length = boustrophedon(req.xs[0], req.ys[0], req.xs[1], start)
            res.path_x, res.path_y, res.length_m = xs, ys, length
            return res
        rs = self.get_parameter("row_spacing_m").value
        # targets snap to the nearest inter-row lane the tool reaches from
        pts = [(x, round(y / rs) * rs) for x, y in zip(req.xs, req.ys)]
        metric = LaneMetric(rs, self.get_parameter("field_length_m").value)
        order, length = tsp_tour(pts, (start[0], round(start[1] / rs) * rs), metric)
        res.order = order
        res.path_x = [req.xs[i] for i in order]
        res.path_y = [req.ys[i] for i in order]
        res.length_m = length
        return res


def main(args=None):
    spin(FleetPathPlanner, args)

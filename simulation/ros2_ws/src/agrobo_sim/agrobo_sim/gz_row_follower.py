"""/gz_row_follower: physics-in-the-loop check on Gazebo.

Drives the Gazebo UGV through a boustrophedon over the first N inter-row lanes with
pure pursuit on bridged odometry (/model/<robot>/odometry -> nav_msgs/Odometry,
/model/<robot>/cmd_vel <- geometry_msgs/Twist), logs cross-track error against the
lane centreline and RTK fixes, and writes a JSON summary. This validates that the
kinematic motion model used for season-scale runs (speed, lane-change cost) matches
wheel-terrain physics.
"""
import json
import math
import os

import rclpy
from geometry_msgs.msg import Pose, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, NavSatFix

from agrobo_sim.core.planning import boustrophedon


class GzRowFollower(Node):
    def __init__(self):
        super().__init__("gz_row_follower")
        for k, v in dict(robot="ugv_alpha", lanes=2, length_m=24.0, row_spacing_m=1.5, speed=0.7,
                         lookahead_m=0.8, start_x=-2.0, start_y=0.0, output="results/gazebo/row_follow.json",
                         timeout_s=600.0, localization="rtk_imu", lat0=35.9519, lon0=-119.8804).items():
            self.declare_parameter(k, v)
        P = lambda n: self.get_parameter(n).value
        self.robot = P("robot")
        L, rs, n = P("length_m"), P("row_spacing_m"), P("lanes")
        # lanes sit on row boundaries y = rs, 2rs, ...; start from the robot's dock lane
        xs, ys, _ = boustrophedon(L, n * rs, rs, (P("start_x"), P("start_y")))
        ys = [y + rs / 2 for y in ys]                       # boustrophedon centres strips; shift to row gaps
        self.wps = [(P("start_x"), P("start_y"))] + list(zip(xs, ys))
        self.seg = 0
        self.pose = None
        self.cte, self.track, self.fixes = [], [], 0
        self.t0 = self.get_clock().now()
        self.cmd = self.create_publisher(Twist, f"/model/{self.robot}/cmd_vel", 10)
        self.create_subscription(Odometry, f"/model/{self.robot}/odometry", self.on_odom, 20)
        self.create_subscription(NavSatFix, f"/{self.robot}/navsat", self.on_fix, 20)
        self.create_subscription(Pose, f"/model/{self.robot}/pose", self.on_truth, 20)
        self.create_subscription(Imu, f"/{self.robot}/imu", self.on_imu, 50)
        self.mode = P("localization")
        self.fix_xy, self.imu_yaw = None, None
        self.truth, self.cte_true, self.drift, self.truth_track = None, [], [], []
        self.create_timer(0.05, self.control)
        self.done = False

    def on_fix(self, m):
        """RTK fix -> local ENU (equirectangular about the world origin; < 1 mm error over 100 m)."""
        self.fixes += 1
        R = 6378137.0
        lat0, lon0 = math.radians(self.get_parameter("lat0").value), math.radians(self.get_parameter("lon0").value)
        self.fix_xy = (R * math.cos(lat0) * (math.radians(m.longitude) - lon0), R * (math.radians(m.latitude) - lat0))
        if self.mode == "rtk_imu" and self.imu_yaw is not None:
            self.pose = (self.fix_xy[0], self.fix_xy[1], self.imu_yaw)

    def on_imu(self, m):
        q = m.orientation
        self.imu_yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        if self.mode == "rtk_imu" and self.fix_xy is not None:
            self.pose = (self.fix_xy[0], self.fix_xy[1], self.imu_yaw)

    def on_truth(self, m):
        self.truth = (m.position.x, m.position.y)

    def on_odom(self, m):
        if self.mode != "odom":
            return
        p, q = m.pose.pose.position, m.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        # odometry starts at the spawn pose
        self.pose = (p.x + self.get_parameter("start_x").value, p.y + self.get_parameter("start_y").value, yaw)

    def control(self):
        if self.done:
            return
        elapsed = (self.get_clock().now() - self.t0).nanoseconds / 1e9
        if self.pose is None:
            if elapsed > 30:
                self.finish(False, "no odometry from Gazebo")
            return
        if elapsed > self.get_parameter("timeout_s").value:
            self.finish(False, "timeout")
            return
        x, y, yaw = self.pose
        a, b = self.wps[self.seg], self.wps[self.seg + 1]
        if int(elapsed) % 5 == 0 and int(elapsed) != getattr(self, "_last_log", -1):
            self._last_log = int(elapsed)
            self.get_logger().info(f"t={elapsed:.0f}s seg={self.seg} est=({x:.2f},{y:.2f},{yaw:.2f}) truth={self.truth}")
        dx, dy = b[0] - a[0], b[1] - a[1]
        seglen = math.hypot(dx, dy) or 1e-6
        t = ((x - a[0]) * dx + (y - a[1]) * dy) / seglen ** 2
        if t >= 1.0 or math.hypot(b[0] - x, b[1] - y) < 0.3:
            self.seg += 1
            if self.seg >= len(self.wps) - 1:
                self.finish(True, "completed")
            return
        cte = ((x - a[0]) * dy - (y - a[1]) * dx) / seglen
        if abs(dy) < 1e-6 and 0.05 < t < 0.95:          # only along-row segments count for row keeping
            self.cte.append(cte)
            if self.truth:
                tx, ty = self.truth
                self.cte_true.append(((tx - a[0]) * dy - (ty - a[1]) * dx) / seglen)
        if self.truth:
            self.drift.append(math.hypot(self.truth[0] - x, self.truth[1] - y))
        self.track.append((round(x, 3), round(y, 3)))
        if self.truth:
            self.truth_track.append((round(self.truth[0], 3), round(self.truth[1], 3)))
        la = self.get_parameter("lookahead_m").value
        tt = min(1.0, max(0.0, t) + la / seglen)
        gx, gy = a[0] + tt * dx, a[1] + tt * dy
        alpha = math.atan2(gy - y, gx - x) - yaw
        alpha = math.atan2(math.sin(alpha), math.cos(alpha))
        v = self.get_parameter("speed").value * (0.3 if abs(alpha) > 0.8 else 1.0)
        m = Twist()
        m.linear.x = v if abs(alpha) < 1.4 else 0.0
        m.angular.z = max(-1.2, min(1.2, 2.0 * v * math.sin(alpha) / la + (0.8 * alpha if abs(alpha) > 1.4 else 0)))
        self.cmd.publish(m)

    def finish(self, ok, why):
        self.done = True
        self.cmd.publish(Twist())
        rms = math.sqrt(sum(c * c for c in self.cte) / len(self.cte)) if self.cte else None
        dist = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.track, self.track[1:]))
        sim_s = (self.get_clock().now() - self.t0).nanoseconds / 1e9
        rms_t = math.sqrt(sum(c * c for c in self.cte_true) / len(self.cte_true)) if self.cte_true else None
        res = dict(ok=ok, reason=why, localization=self.mode, robot=self.robot, lanes=self.get_parameter("lanes").value,
                   cross_track_rms_true_m=rms_t,
                   cross_track_max_true_m=max((abs(c) for c in self.cte_true), default=None),
                   loc_error_final_m=self.drift[-1] if self.drift else None,
                   loc_error_max_m=max(self.drift, default=None),
                   cross_track_rms_m=rms, cross_track_max_m=max((abs(c) for c in self.cte), default=None),
                   distance_m=round(dist, 2), sim_time_s=round(sim_s, 1),
                   mean_speed_mps=round(dist / sim_s, 3) if sim_s else None, gnss_fixes=self.fixes,
                   waypoints=self.wps, track_sample=self.track[::20], truth_sample=self.truth_track[::20])
        out = self.get_parameter("output").value
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        self.get_logger().info(f"row follow {why}: RMS cross-track {rms} m over {dist:.1f} m -> {out}")
        raise SystemExit


def main(args=None):
    rclpy.init(args=args)
    n = GzRowFollower()
    try:
        rclpy.spin(n)
    except SystemExit:
        pass
    finally:
        n.destroy_node()
        rclpy.try_shutdown()

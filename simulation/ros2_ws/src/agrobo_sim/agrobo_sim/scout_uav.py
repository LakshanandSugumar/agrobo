"""/scout_uav: multispectral quadrotor survey (RGB + 5-band MS, RTK, 8 m AGL).

Action  /scout_uav/scout_field  ScoutField
Topic   /scout_uav/frames       SensorFrame (one per flight strip; ground truth in FOV)
"""
import math

from agrobo_interfaces.action import ScoutField
from agrobo_interfaces.msg import SensorFrame
from agrobo_interfaces.srv import GetFieldState
from rclpy.action import ActionServer

from agrobo_sim.robot_base import RobotNode
from agrobo_sim.ros_util import RELIABLE


class ScoutUAV(RobotNode):
    def __init__(self):
        super().__init__("scout_uav", "uav_scout", speed=4.0, drive_kw=0.65, battery_kwh=0.36, dock=(-2.0, -2.0))
        self.declare_parameter("hfov_deg", 70.0)
        self.get_state = self.client(GetFieldState, "/field/get_state")
        self.pub = self.create_publisher(SensorFrame, "/scout_uav/frames", RELIABLE)
        ActionServer(self, ScoutField, "/scout_uav/scout_field", self.on_scout, callback_group=self.cbg)

    def on_scout(self, gh):
        alt = gh.request.altitude_m or 8.0
        self.task = "scouting"
        res = self.call(self.get_state, GetFieldState.Request(include_fruit=True))
        st, fruit = res.state, res.fruit
        L = max(p.x for p in st.plants) + 0.25
        W = max(p.y for p in st.plants) + 0.75
        swath = 2 * alt * math.tan(math.radians(self.get_parameter("hfov_deg").value) / 2) * 0.7   # 30 % sidelap
        n_strips = max(1, math.ceil(W / swath))
        plant_y = {p.plant_id: p.y for p in st.plants}
        hours, d0, frames, wf, ff = 0.0, self.odo, 0, 0, 0
        hours += self.drive_to(0.0, 0.0)
        for s in range(n_strips):
            y0, y1 = s * swath, (s + 1) * swath
            m = SensorFrame(robot_id=self.robot_id, sensor="rgb_multispectral_uav", altitude_m=alt)
            m.header.stamp = self.get_clock().now().to_msg()
            m.header.frame_id = f"strip_{s}"
            m.plants = [p for p in st.plants if y0 <= p.y < y1]
            m.weeds = [w for w in st.weeds if y0 <= w.y < y1]
            m.fruit = [f for f in fruit if y0 <= plant_y[f.plant_id] < y1]
            self.pub.publish(m)
            frames, wf, ff = frames + 1, wf + len(m.weeds), ff + len(m.fruit)
            hours += self.drive_to(L if s % 2 == 0 else 0.0, min(W, (s + 0.5) * swath), L + swath)
            gh.publish_feedback(ScoutField.Feedback(progress=(s + 1) / n_strips))
        end = SensorFrame(robot_id=self.robot_id, sensor="rgb_multispectral_uav", end_of_pass=True)
        end.header.frame_id = "eop"
        self.pub.publish(end)
        hours += self.go_home()
        self.task = "idle"
        gh.succeed()
        self.emit_task("scouting", duration_h=hours, frames=frames, weeds_in_fov=wf, fruit_in_fov=ff)
        return ScoutField.Result(frames_published=frames, weeds_in_fov=wf, fruit_in_fov=ff,
                                 distance_m=self.odo - d0, duration_h=hours)


def main(args=None):
    from agrobo_sim.ros_util import spin
    spin(ScoutUAV, args)

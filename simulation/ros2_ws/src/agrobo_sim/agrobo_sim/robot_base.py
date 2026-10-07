"""Common robot model: kinematic motion, energy/battery, status telemetry, mesh-link state."""
import math

from agrobo_interfaces.msg import RobotStatus
from std_msgs.msg import Bool

from agrobo_sim.ros_util import LATCHED, AgroboNode


class RobotNode(AgroboNode):
    def __init__(self, name, robot_type, speed=0.8, drive_kw=1.2, battery_kwh=6.0, dock=(-2.0, 0.0)):
        super().__init__(name)
        self.declare_parameter("robot_id", name)
        self.robot_id = self.get_parameter("robot_id").value
        self.robot_type = robot_type
        self.speed, self.drive_kw, self.battery_kwh = speed, drive_kw, battery_kwh
        self.dock = dock
        self.x, self.y = dock
        self.soc, self.odo, self.energy, self.op_hours = 1.0, 0.0, 0.0, 0.0
        self.task = "idle"
        self.link_up = True
        self.swaps = 0
        self.status_pub = self.create_publisher(RobotStatus, "/fleet/status", 50)
        self.create_subscription(Bool, "/cloud/link_up", lambda m: setattr(self, "link_up", m.data), LATCHED)
        self.create_timer(1.0, self.publish_status)

    # -------------------------------------------------------------- physics-lite
    def _consume(self, kwh, hours):
        self.energy += kwh
        self.op_hours += hours
        self.soc -= kwh / self.battery_kwh
        extra = 0.0
        if self.soc < 0.15:                        # return to dock, hot-swap pack, come back
            d = 2 * math.hypot(self.x - self.dock[0], self.y - self.dock[1])
            extra = d / self.speed / 3600.0 + 0.15
            self.odo += d
            self.energy += self.drive_kw * d / self.speed / 3600.0
            self.soc = 1.0
            self.swaps += 1
        return extra

    def drive_to(self, x, y, dist=None):
        d = dist if dist is not None else math.hypot(x - self.x, y - self.y)
        self.x, self.y = x, y
        self.odo += d
        h = d / self.speed / 3600.0
        return h + self._consume(self.drive_kw * h, h)

    def work(self, seconds, kw):
        h = seconds / 3600.0
        return h + self._consume(kw * h, h)

    def go_home(self):
        return self.drive_to(*self.dock)

    def publish_status(self):
        m = RobotStatus(robot_id=self.robot_id, robot_type=self.robot_type, task=self.task, x=self.x, y=self.y,
                        battery_soc=self.soc, odometer_m=self.odo, energy_kwh=self.energy, link_up=self.link_up)
        m.header.stamp = self.get_clock().now().to_msg()
        self.status_pub.publish(m)

    def emit_task(self, task, **kw):
        self.emit("robot_task", robot_id=self.robot_id, robot_type=self.robot_type, task=task,
                  energy_kwh_total=self.energy, op_hours_total=self.op_hours, odometer_m=self.odo,
                  battery_swaps=self.swaps, **kw)

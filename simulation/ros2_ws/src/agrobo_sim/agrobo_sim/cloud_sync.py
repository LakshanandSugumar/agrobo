"""/cloud_sync: rural LTE uplink model + store-and-forward replication of the Field Ledger log.

The farm runs on the edge hub; the cloud SaaS (fleet telemetry, B2B exchange) is reached
over an intermittent link. Outages start with p_outage per sim-day and last 1-3 days.
Topics  /agrobo/events (in), /cloud/link_up (out, latched Bool)
"""
import json

import numpy as np
from std_msgs.msg import Bool, String

from agrobo_sim.ros_util import EVENTS, LATCHED, AgroboNode, spin


class CloudSync(AgroboNode):
    def __init__(self):
        super().__init__("cloud_sync")
        self.declare_parameter("p_outage", 0.12)
        self.declare_parameter("seed", 99)
        self.rng = np.random.default_rng(self.get_parameter("seed").value)
        self.link = True
        self.down_until = 0
        self.queue = 0
        self.stats = dict(outage_days=0, events_buffered=0, events_replicated=0, max_backlog=0)
        self.pub = self.create_publisher(Bool, "/cloud/link_up", LATCHED)
        self.pub.publish(Bool(data=True))
        self.create_subscription(String, "/agrobo/events", self.on_event, EVENTS, callback_group=self.cbg)

    def on_event(self, m):
        ev = json.loads(m.data)
        if ev.get("node") == self.get_name():
            return
        if self.link:
            self.stats["events_replicated"] += 1
        else:
            self.queue += 1
            self.stats["events_buffered"] += 1
            self.stats["max_backlog"] = max(self.stats["max_backlog"], self.queue)
        if ev["type"] == "field_day":
            day = ev["day"]
            if self.link and self.rng.random() < self.get_parameter("p_outage").value:
                self.link, self.down_until = False, day + int(self.rng.integers(1, 4))
                self.pub.publish(Bool(data=False))
                self.emit("link", day=day, up=False)
            elif not self.link and day >= self.down_until:
                self.link = True
                self.stats["events_replicated"] += self.queue
                self.queue = 0
                self.pub.publish(Bool(data=True))
                self.emit("link", day=day, up=True)
            if not self.link:
                self.stats["outage_days"] += 1
            self.emit("cloud_stats", day=day, link_up=self.link, **self.stats)


def main(args=None):
    spin(CloudSync, args)

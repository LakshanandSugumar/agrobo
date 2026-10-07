"""Shared ROS 2 helpers for Agrobo nodes."""
from __future__ import annotations

import json
import threading

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                     reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
RELIABLE = QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
EVENTS = QoSProfile(depth=5000, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST,
                    durability=DurabilityPolicy.TRANSIENT_LOCAL)


class AgroboNode(Node):
    """Node base: reentrant callback group, KPI event bus, blocking service calls."""

    def __init__(self, name: str, **kw):
        super().__init__(name, **kw)
        self.cbg = ReentrantCallbackGroup()
        self._events = self.create_publisher(String, "/agrobo/events", EVENTS)

    def emit(self, kind: str, **data):
        data["type"] = kind
        data["node"] = self.get_name()
        self._events.publish(String(data=json.dumps(data)))

    def client(self, srv_type, name):
        c = self.create_client(srv_type, name, callback_group=self.cbg)
        return c

    def call(self, client, request, timeout: float = 60.0):
        """Blocking call from inside a callback (needs a MultiThreadedExecutor)."""
        if not client.wait_for_service(timeout_sec=timeout):
            raise RuntimeError(f"service {client.srv_name} unavailable")
        done = threading.Event()
        fut = client.call_async(request)
        fut.add_done_callback(lambda _: done.set())
        if not done.wait(timeout):
            raise RuntimeError(f"service {client.srv_name} timed out")
        return fut.result()


def spin(node_cls, args=None, threads: int = 4):
    rclpy.init(args=args)
    node = node_cls()
    ex = rclpy.executors.MultiThreadedExecutor(num_threads=threads)
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.try_shutdown()


def plant_to_msg(p, field):
    from agrobo_interfaces.msg import PlantState
    g, r, o = field.fruit_counts(p.pid) if p.stage >= 3 else (0, 0, 0)
    return PlantState(plant_id=p.pid, row=p.row, col=p.col, x=p.x, y=p.y, stage=p.stage, gdd_accum=p.gdd,
                      biomass_g=p.biomass_g, nitrogen_stress=p.n_stress, water_stress=p.water_stress,
                      weed_competition=p.weed_comp, fruit_green=g, fruit_ripe=r, fruit_overripe=o, alive=p.alive)


def weed_to_msg(w):
    from agrobo_interfaces.msg import Weed
    return Weed(weed_id=w.wid, x=w.x, y=w.y, size_cm=w.size_cm, species=w.species)

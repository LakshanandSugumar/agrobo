"""/market_engine: B2B algorithmic selling (contracts, spot, wholesale, processor).

Action  /market/sell_inventory   SellInventory
Topics  /hub/inventory (in), /farm_twin/yield_forecast (in, Float64MultiArray [day, kg_A]),
        /cloud/link_up (in), /market/trades (out)
"""
from agrobo_interfaces.action import SellInventory
from agrobo_interfaces.msg import HarvestLot, MarketTrade
from rclpy.action import ActionServer
from std_msgs.msg import Bool, Float64MultiArray

from agrobo_sim.core.market import MarketEngine
from agrobo_sim.ros_util import LATCHED, RELIABLE, AgroboNode, spin


class _LotView:
    def __init__(self, m):
        self.lot_id, self.shelf_life_d = m.lot_id, m.shelf_life_d
        self.kg = {"A": m.kg_grade_a, "B": m.kg_grade_b, "C": m.kg_grade_c}

    def grade_kg(self, g):
        return self.kg.get(g, 0.0)


class MarketNode(AgroboNode):
    def __init__(self):
        super().__init__("market_engine")
        self.engine = MarketEngine()
        self.online = True
        self.pending = []
        self.create_subscription(HarvestLot, "/hub/inventory", lambda m: self.pending.append(m), RELIABLE,
                                 callback_group=self.cbg)
        self.create_subscription(Float64MultiArray, "/farm_twin/yield_forecast", self.on_forecast, RELIABLE,
                                 callback_group=self.cbg)
        self.create_subscription(Bool, "/cloud/link_up", lambda m: setattr(self, "online", m.data), LATCHED,
                                 callback_group=self.cbg)
        self.trades = self.create_publisher(MarketTrade, "/market/trades", RELIABLE)
        ActionServer(self, SellInventory, "/market/sell_inventory", self.on_sell, callback_group=self.cbg)

    def on_forecast(self, m):
        day, kg = int(m.data[0]), float(m.data[1])
        if self.online:                      # contracts need the cloud B2B exchange
            self.engine.commit_forward(day, kg)
            self.emit("forward_commit", day=day, kg=kg * self.engine.cfg.contract_hedge)

    def on_sell(self, gh):
        day = gh.request.day
        for m in self.pending:
            self.engine.add_lot(_LotView(m), m.day_harvested)
        self.pending = []
        n0, sp0 = len(self.engine.trades), self.engine.spoiled_kg
        rev = self.engine.clear_day(day, online=self.online)
        new = self.engine.trades[n0:]
        msgs = [MarketTrade(day=t["day"], buyer=t["buyer"], grade=t["grade"], kg=t["kg"],
                            price_per_kg=t["price_per_kg"], lot_id=t["lot_id"]) for t in new]
        for t in msgs:
            self.trades.publish(t)
        gh.succeed()
        self.emit("market_day", day=day, revenue=rev, spot=self.engine.spot_price(day), online=self.online,
                  sold_kg=sum(t["kg"] for t in new), spoiled_kg=self.engine.spoiled_kg - sp0,
                  inventory_kg=sum(i.kg for i in self.engine.inv), penalties_total=self.engine.penalties,
                  by_buyer={b: sum(t["kg"] for t in new if t["buyer"] == b) for b in {t["buyer"] for t in new}})
        return SellInventory.Result(trades=msgs, revenue_usd=rev, spoiled_kg=self.engine.spoiled_kg - sp0)


def main(args=None):
    spin(MarketNode, args)

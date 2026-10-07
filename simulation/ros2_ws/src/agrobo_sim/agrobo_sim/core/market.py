"""B2B algorithmic selling engine.

Channels (USD/kg, fresh-market tomato, modelled):
- retail_contract : Grade A only, forward-contracted volume at a premium. Volume is
                    committed D+3 from the Field Ledger yield forecast (P50 x hedge).
                    Shortfall pays a penalty.
- foodservice_spot: Grade A/B, stochastic daily price, daily volume cap.
- wholesale       : Grade A/B, unlimited, terminal-market price (discounted).
- processor       : Grade C, unlimited, low price.
Policy: FEFO (first-expiring-first-out), contracts first, then best spot bid,
hold B-grade when today's price is >1 sigma below mean and shelf-life allows.
Baseline policy: no grading, no contracts, sell everything at wholesale on the day.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MarketConfig:
    contract_price: float = 1.95
    contract_penalty: float = 0.50
    contract_hedge: float = 0.80
    spot_mean: float = 1.60
    spot_sigma: float = 0.22
    spot_glut_drop: float = 0.35    # mid-season regional glut
    foodservice_cap_kg: float = 45.0
    wholesale_discount: float = 0.82
    processor_price: float = 0.22
    ungraded_discount: float = 0.88  # field-run (ungraded) price vs graded wholesale


@dataclass
class Inventory:
    lot_id: str
    grade: str
    kg: float
    expiry_day: float


class MarketEngine:
    def __init__(self, cfg: MarketConfig | None = None, seed: int = 11):
        self.cfg = cfg or MarketConfig()
        self.rng = np.random.default_rng(seed)
        self.inv: list[Inventory] = []
        self.commitments: dict[int, float] = {}      # day -> kg Grade A committed
        self.trades: list[dict] = []
        self.spoiled_kg = 0.0
        self.penalties = 0.0
        self._price_cache: dict[int, float] = {}

    def spot_price(self, day: int) -> float:
        if day not in self._price_cache:
            c = self.cfg
            glut = c.spot_glut_drop * np.exp(-((day - 95) / 15.0) ** 2)
            self._price_cache[day] = float(max(0.6, c.spot_mean - glut + self.rng.normal(0, c.spot_sigma)))
        return self._price_cache[day]

    def add_lot(self, lot, day: int):
        for g in ("A", "B", "C"):
            kg = lot.grade_kg(g)
            if kg > 0:
                self.inv.append(Inventory(lot.lot_id, g, kg, day + lot.shelf_life_d))

    def commit_forward(self, day: int, forecast_kg_a: float):
        if forecast_kg_a > 0:
            self.commitments[day] = self.commitments.get(day, 0.0) + self.cfg.contract_hedge * forecast_kg_a

    def _sell(self, day, inv, kg, buyer, price):
        inv.kg -= kg
        self.trades.append(dict(day=day, buyer=buyer, grade=inv.grade, kg=kg, price_per_kg=price, lot_id=inv.lot_id))
        return kg * price

    def clear_day(self, day: int, online: bool = True):
        """Run the day's allocation. Offline: only contract deliveries (pre-agreed) execute."""
        c, rev = self.cfg, 0.0
        for i in self.inv:
            if i.expiry_day <= day and i.kg > 1e-9:
                self.spoiled_kg += i.kg
                i.kg = 0.0
        self.inv = [i for i in self.inv if i.kg > 1e-9]
        self.inv.sort(key=lambda i: i.expiry_day)
        # 1) contracts
        need = self.commitments.pop(day, 0.0)
        for i in self.inv:
            if need <= 1e-9:
                break
            if i.grade == "A":
                q = min(i.kg, need)
                rev += self._sell(day, i, q, "retail_contract", c.contract_price)
                need -= q
        if need > 1e-9:
            self.penalties += need * c.contract_penalty
            rev -= need * c.contract_penalty
        if not online:
            self.inv = [i for i in self.inv if i.kg > 1e-9]
            return rev
        spot = self.spot_price(day)
        fs_left = c.foodservice_cap_kg
        for i in self.inv:
            if i.kg <= 1e-9:
                continue
            if i.grade == "C":
                rev += self._sell(day, i, i.kg, "processor", c.processor_price)
                continue
            shelf_left = i.expiry_day - day
            cheap = spot < c.spot_mean - c.spot_sigma
            if i.grade == "A" and shelf_left > 3 and any(d > day for d in self.commitments):
                continue                                   # hold for upcoming contracts
            if cheap and shelf_left > 4:
                continue                                   # wait out a price dip
            if fs_left > 0:
                q = min(i.kg, fs_left)
                rev += self._sell(day, i, q, "foodservice_spot", spot * (1.05 if i.grade == "A" else 0.95))
                fs_left -= q
            if i.kg > 1e-9:
                rev += self._sell(day, i, i.kg, "wholesale", spot * c.wholesale_discount)
        self.inv = [i for i in self.inv if i.kg > 1e-9]
        return rev

    def baseline_revenue(self, harvest_by_day: dict[int, float]):
        """Conventional: sell ungraded field-run at wholesale the same day; ~6 % culls in transit."""
        c = self.cfg
        return sum(kg * 0.94 * self.spot_price(d) * c.wholesale_discount * c.ungraded_discount
                   for d, kg in harvest_by_day.items())

    @property
    def revenue(self):
        return sum(t["kg"] * t["price_per_kg"] for t in self.trades) - self.penalties

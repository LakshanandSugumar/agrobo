"""Hub: hyperspectral grading (400-1000 nm line-scan) and robotic cold-chain packing."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class FruitItem:
    ripeness: float
    mass_g: float
    bruised: bool
    grade: str = ""


@dataclass
class Lot:
    lot_id: str
    day: int
    items: list = field(default_factory=list)
    first_pick_h: float = 0.0        # hour-of-day of first pick
    cooled_h: float = 0.0            # hour-of-day the lot entered the cold room
    graded: bool = False
    packed: bool = False
    shelf_life_d: float = 0.0
    sold_kg: dict = field(default_factory=dict)

    @property
    def mass_kg(self):
        return sum(i.mass_g for i in self.items) / 1000.0

    def grade_kg(self, g):
        return sum(i.mass_g for i in self.items if i.grade == g) / 1000.0


@dataclass
class HyperspectralGrader:
    ripeness_sigma: float = 0.02      # PLS-regressed lycopene/chlorophyll index
    bruise_recall: float = 0.95       # sub-surface bruise detection (NIR 970 nm water band)
    bruise_fpr: float = 0.02
    throughput_fps: float = 8.0       # fruit per second on the singulating conveyor

    def grade(self, rng, lot: Lot):
        for it in lot.items:
            r = it.ripeness + rng.normal(0, self.ripeness_sigma)
            bruise_seen = (rng.random() < self.bruise_recall) if it.bruised else (rng.random() < self.bruise_fpr)
            if r >= 1.05 or (bruise_seen and r > 0.95):
                it.grade = "reject"
            elif bruise_seen:
                it.grade = "C"
            elif 0.72 <= r < 0.97 and it.mass_g >= 110:   # market-ripe window, grader tolerance
                it.grade = "A"
            else:
                it.grade = "B"
        lot.graded = True
        return len(lot.items) / self.throughput_fps / 3600.0


@dataclass
class ColdChainPacker:
    pack_rate_fpm: float = 40.0       # delta-arm pick-and-place into 5 kg flats
    base_shelf_life_d: float = 14.0   # at 10-12 C, cooled within 2 h
    heat_penalty_d_per_h: float = 0.6 # lost shelf-life per hour of field heat beyond 2 h

    def pack(self, lot: Lot, pick_to_cool_h: float):
        lot.shelf_life_d = max(2.0, self.base_shelf_life_d - self.heat_penalty_d_per_h * max(0.0, pick_to_cool_h - 2.0))
        lot.packed = True
        return len(lot.items) / self.pack_rate_fpm / 60.0

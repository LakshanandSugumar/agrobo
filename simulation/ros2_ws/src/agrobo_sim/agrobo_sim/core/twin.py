"""Field Ledger: the plant-level digital twin that is Agrobo's core moat.

Every plant, fruit and weed track gets a persistent record fused from UAV and
UGV observations. Ripeness is forecast forward in thermal time (GDD), so the
fleet acts on *predicted* state:
- harvest orders list the exact fruit expected to be ripe on the pick day,
  with their plant anchor and height (picker skips the search phase),
- the market engine pre-sells forecast volume before it is picked,
- weeding and dosing orders are per-target, not per-zone.

Runs on the edge hub, so it keeps working through cloud outages; the cloud copy
is a replicated, append-only log (see cloud_sync node).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

PRIOR_RATE = 1.0 / 840.0        # ripeness per GDD
RIPE_MIN, RIPE_MAX = 0.75, 0.97


@dataclass
class FruitTrack:
    fid: int
    pid: int
    r_obs: float
    gdd_obs: float
    rate: float = PRIOR_RATE
    n_obs: int = 1
    picked: bool = False


@dataclass
class WeedTrack:
    x: float
    y: float
    size_cm: float
    conf: float
    day: int
    hits: int = 1


@dataclass
class PlantTrack:
    pid: int
    x: float
    y: float
    n_stress_est: float = 0.0
    last_dose_day: int = -99


class FieldLedger:
    def __init__(self):
        self.gdd_cum = 0.0
        self.day = 0
        self.fruit: dict[int, FruitTrack] = {}
        self.weeds: list[WeedTrack] = []
        self.plants: dict[int, PlantTrack] = {}
        self.history: list[dict] = []

    # ---------------------------------------------------------------- ingest
    def on_day(self, day: int, gdd: float):
        self.day = day
        self.gdd_cum += gdd

    def ingest_fruit(self, fid, pid, r_est):
        t = self.fruit.get(fid)
        if t is None:
            self.fruit[fid] = FruitTrack(fid, pid, r_est, self.gdd_cum)
            return
        dg = self.gdd_cum - t.gdd_obs
        if dg > 20:
            inst = (r_est - t.r_obs) / dg
            w = 0.5 if t.n_obs == 1 else 0.3
            t.rate = float(np.clip((1 - w) * t.rate + w * inst, 0.4 * PRIOR_RATE, 2.0 * PRIOR_RATE))
        # Kalman-style blend of forecast and new measurement
        pred = t.r_obs + t.rate * dg
        t.r_obs = 0.4 * pred + 0.6 * r_est if dg < 200 else r_est
        t.gdd_obs, t.n_obs = self.gdd_cum, t.n_obs + 1

    def ingest_weed(self, x, y, size, conf, assoc_radius=0.06):
        for w in self.weeds:
            if (w.x - x) ** 2 + (w.y - y) ** 2 < assoc_radius ** 2:
                w.x, w.y = 0.5 * (w.x + x), 0.5 * (w.y + y)
                w.size_cm, w.conf, w.day, w.hits = size, max(w.conf, conf), self.day, w.hits + 1
                return
        self.weeds.append(WeedTrack(x, y, size, conf, self.day))

    def ingest_chlorosis(self, pid, x, y, est):
        t = self.plants.setdefault(pid, PlantTrack(pid, x, y))
        t.n_stress_est = est

    def clear_weeds(self, killed_xy, radius=0.08):
        keep = []
        for w in self.weeds:
            if not any((w.x - x) ** 2 + (w.y - y) ** 2 < radius ** 2 for x, y in killed_xy):
                keep.append(w)
        self.weeds = keep

    def mark_picked(self, fids):
        for f in fids:
            if f in self.fruit:
                self.fruit[f].picked = True

    # ---------------------------------------------------------------- forecast
    def forecast(self, t: FruitTrack, gdd_ahead: float = 0.0):
        return t.r_obs + t.rate * (self.gdd_cum + gdd_ahead - t.gdd_obs)

    def harvest_orders(self, gdd_ahead: float = 0.0, lo=RIPE_MIN, hi=1.05):
        return [t for t in self.fruit.values() if not t.picked and lo <= self.forecast(t, gdd_ahead) < hi]

    def yield_forecast_kg(self, days: int, gdd_per_day: float, mean_mass_g: float = 125.0):
        """Fruit predicted to cross RIPE_MIN within the horizon (per day)."""
        out = []
        for d in range(1, days + 1):
            n = sum(1 for t in self.fruit.values() if not t.picked
                    and self.forecast(t, (d - 1) * gdd_per_day) < RIPE_MIN <= self.forecast(t, d * gdd_per_day))
            out.append(n * mean_mass_g / 1000.0)
        return out

    def weed_pressure(self):
        return len(self.weeds)

    def dose_orders(self, threshold=0.22, g_per_stress=1.6, min_interval=10):
        return [(t.pid, round(g_per_stress * t.n_stress_est, 2)) for t in self.plants.values()
                if t.n_stress_est >= threshold and self.day - t.last_dose_day >= min_interval]

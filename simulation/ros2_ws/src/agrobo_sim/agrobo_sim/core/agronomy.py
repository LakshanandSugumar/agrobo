"""Ground-truth agronomic model of an open-field fresh-market tomato block.

Pure Python (numpy only) so it can be unit-tested and reused outside ROS. The
ROS node `field_world` wraps it. Units: metres, days, grams, ppm, degrees C.

Model summary
- Weather: daily mean temperature with seasonal drift + noise -> growing degree
  days (GDD, base 10 C, cap 30 C).
- Plants: development driven by stress-scaled GDD. Stages: seedling,
  vegetative, flowering, fruiting, senescent.
- Stress: nitrogen (local soil N, spatially variable), water (drip-controlled
  soil moisture) and weed competition, each 0..1, combined multiplicatively.
- Fruit: set during flowering/fruiting at a stress-scaled rate; each fruit
  ripens with GDD; >=0.75 harvestable, >=1.0 overripe, >=1.25 drops (loss).
- Weeds: Poisson emergence that falls as canopy closes; grow with GDD; compete
  with crop plants within 0.5 m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

STAGE_EMPTY, STAGE_SEEDLING, STAGE_VEGETATIVE, STAGE_FLOWERING, STAGE_FRUITING, STAGE_SENESCENT = range(6)
STAGE_GDD = [(STAGE_SEEDLING, 0.0), (STAGE_VEGETATIVE, 150.0), (STAGE_FLOWERING, 450.0),
             (STAGE_FRUITING, 620.0), (STAGE_SENESCENT, 1750.0)]

RIPE_MIN, OVERRIPE, DROP = 0.75, 1.0, 1.25
WEED_SPECIES = ("amaranthus_palmeri", "chenopodium_album", "cyperus_esculentus", "solanum_nigrum")


@dataclass
class FieldConfig:
    rows: int = 10
    plants_per_row: int = 48
    row_spacing_m: float = 1.5
    plant_spacing_m: float = 0.5
    soil_n_ppm: float = 32.0
    soil_n_cv: float = 0.30           # spatial coefficient of variation of soil N
    soil_om_pct: float = 2.8
    t_mean_c: float = 23.0
    weed_seedbank: float = 1.0        # multiplier on emergence rate
    seed: int = 7


@dataclass
class Plant:
    pid: int
    row: int
    col: int
    x: float
    y: float
    stage: int = STAGE_EMPTY
    gdd: float = 0.0
    biomass_g: float = 0.0
    soil_n: float = 30.0
    n_stress: float = 0.0
    water_stress: float = 0.0
    weed_comp: float = 0.0
    alive: bool = True
    damage: float = 0.0               # accumulated mechanical/laser damage 0..1


@dataclass
class Weed:
    wid: int
    x: float
    y: float
    size_cm: float
    species: str
    alive: bool = True


class Field:
    """Ground truth. Every robot effect goes through `interact_*` methods."""

    def __init__(self, cfg: FieldConfig | None = None):
        self.cfg = cfg or FieldConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.day = 0
        self.temp_c = self.cfg.t_mean_c
        self.tilled = False
        self.cleared = False
        self.irrigation = False
        self.soil_moisture = 0.16
        self.plants: list[Plant] = []
        self.weeds: dict[int, Weed] = {}
        self._next_weed = 1
        # Fruit arrays (structure-of-arrays for speed); index == fruit_id - 1
        self.f_plant = np.zeros(0, dtype=np.int32)
        self.f_ripe = np.zeros(0)
        self.f_rate = np.zeros(0)
        self.f_mass = np.zeros(0)
        self.f_h = np.zeros(0)
        self.f_occ = np.zeros(0, dtype=bool)
        self.f_state = np.zeros(0, dtype=np.int8)   # 0 on plant, 1 picked, 2 dropped
        self.stats = dict(dropped_fruit=0, dropped_kg=0.0, weeds_seeded=0, gdd_total=0.0,
                          n_applied_g=0.0, crop_damage_events=0)
        self._layout()

    # ------------------------------------------------------------------ layout
    def _layout(self):
        c = self.cfg
        # Smooth spatial N field: sum of a few random Gaussian blobs.
        L, W = c.plants_per_row * c.plant_spacing_m, c.rows * c.row_spacing_m
        blobs = [(self.rng.uniform(0, L), self.rng.uniform(0, W), self.rng.normal(0, 1), self.rng.uniform(3, 8))
                 for _ in range(6)]
        pid = 1
        for r in range(c.rows):
            for k in range(c.plants_per_row):
                x, y = (k + 0.5) * c.plant_spacing_m, (r + 0.5) * c.row_spacing_m
                z = sum(a * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / (2 * s * s)) for bx, by, a, s in blobs)
                n = max(5.0, c.soil_n_ppm * (1 + c.soil_n_cv * z / 1.2))
                self.plants.append(Plant(pid, r, k, x, y, soil_n=n))
                pid += 1

    @property
    def extent(self):
        c = self.cfg
        return c.plants_per_row * c.plant_spacing_m, c.rows * c.row_spacing_m

    @property
    def area_ha(self):
        L, W = self.extent
        return L * W / 1e4

    def plant(self, pid: int) -> Plant:
        return self.plants[pid - 1]

    # ------------------------------------------------------------------ dynamics
    def step_day(self) -> float:
        c = self.cfg
        self.day += 1
        self.temp_c = c.t_mean_c + 3.0 * math.sin(2 * math.pi * self.day / 160.0) + self.rng.normal(0, 2.0)
        gdd = float(np.clip(min(self.temp_c, 30.0) - 10.0, 0.0, 20.0))
        self.stats["gdd_total"] += gdd
        rain = self.rng.random() < 0.12
        if self.irrigation:
            self.soil_moisture = 0.27 + self.rng.normal(0, 0.01)
        else:
            self.soil_moisture = float(np.clip(self.soil_moisture - 0.015 + (0.08 if rain else 0.0), 0.08, 0.35))
        w_stress = float(np.clip((0.19 - self.soil_moisture) / 0.08, 0, 1))

        self._grow_weeds(gdd)
        planted = [p for p in self.plants if p.stage != STAGE_EMPTY and p.alive]
        for p in planted:
            p.water_stress = w_stress
            p.n_stress = float(np.clip((24.0 - p.soil_n) / 16.0, 0, 1))
            f = self.vigor(p)
            p.gdd += gdd * (0.55 + 0.45 * f)
            p.biomass_g += gdd * 1.6 * f
            uptake = 0.0 if p.stage <= STAGE_SEEDLING else 0.11 * (1.0 if p.stage < STAGE_FRUITING else 1.5)
            p.soil_n = max(2.0, p.soil_n - uptake * (0.5 + 0.5 * f) + 0.02 * c.soil_om_pct)  # mineralisation
            for st, th in STAGE_GDD:
                if p.gdd >= th:
                    p.stage = st
            if p.stage in (STAGE_FLOWERING, STAGE_FRUITING) and p.gdd < 1600:
                n_new = self.rng.poisson(0.8 * f)
                if n_new:
                    self._set_fruit(p, n_new, f)
        # Ripening
        on = self.f_state == 0
        if on.any():
            self.f_ripe[on] += gdd * self.f_rate[on]
            drop = on & (self.f_ripe >= DROP)
            if drop.any():
                self.f_state[drop] = 2
                self.stats["dropped_fruit"] += int(drop.sum())
                self.stats["dropped_kg"] += float(self.f_mass[drop].sum() / 1000.0)
        return gdd

    def vigor(self, p: Plant) -> float:
        return (1 - 0.65 * p.n_stress) * (1 - 0.5 * p.water_stress) * (1 - 0.55 * p.weed_comp) * (1 - p.damage)

    def _set_fruit(self, p: Plant, n: int, f: float):
        self.f_plant = np.concatenate([self.f_plant, np.full(n, p.pid, dtype=np.int32)])
        self.f_ripe = np.concatenate([self.f_ripe, np.zeros(n)])
        # ~45 days set->ripe at 14 GDD/day: rate ~ 0.75 / (45*14)
        self.f_rate = np.concatenate([self.f_rate, self.rng.normal(1.0 / 840.0, 0.00012, n).clip(0.0008)])
        self.f_mass = np.concatenate([self.f_mass, self.rng.normal(85 + 55 * f, 18, n).clip(40)])
        self.f_h = np.concatenate([self.f_h, self.rng.uniform(0.25, 1.2, n)])
        self.f_occ = np.concatenate([self.f_occ, self.rng.random(n) < 0.35])
        self.f_state = np.concatenate([self.f_state, np.zeros(n, dtype=np.int8)])

    def _grow_weeds(self, gdd: float):
        c = self.cfg
        canopy = np.mean([min(1.0, p.biomass_g / 900.0) for p in self.plants if p.stage]) if any(
            p.stage for p in self.plants) else 0.0
        rate = c.weed_seedbank * (0.9 if self.tilled else 2.5) * (1 - 0.85 * canopy) * len(self.plants) * 0.03
        L, W = self.extent
        for _ in range(self.rng.poisson(max(rate, 0.0))):
            p = self.plants[self.rng.integers(len(self.plants))]
            x = float(np.clip(p.x + self.rng.normal(0, 0.25), 0, L))
            y = float(np.clip(p.y + self.rng.normal(0, 0.35), 0, W))
            sp = WEED_SPECIES[self.rng.integers(len(WEED_SPECIES))]
            self.weeds[self._next_weed] = Weed(self._next_weed, x, y, 0.3, sp)
            self._next_weed += 1
        for w in self.weeds.values():
            if w.alive:
                w.size_cm += gdd * 0.075 * (1.4 if w.species == "amaranthus_palmeri" else 1.0)
                if w.size_cm > 30 and self.rng.random() < 0.05:
                    self.stats["weeds_seeded"] += 1
        # competition: weeds within 0.5 m of each plant
        live = [w for w in self.weeds.values() if w.alive]
        if live and any(p.stage for p in self.plants):
            wx = np.array([w.x for w in live]); wy = np.array([w.y for w in live])
            ws = np.array([w.size_cm for w in live])
            for p in self.plants:
                d2 = (wx - p.x) ** 2 + (wy - p.y) ** 2
                p.weed_comp = float(np.clip((ws[d2 < 0.25] / 40.0).sum(), 0, 1))
        else:
            for p in self.plants:
                p.weed_comp = 0.0

    # ------------------------------------------------------------------ robot effects
    def clear(self):
        self.cleared = True
        self.weeds.clear()

    def till(self):
        self.tilled = True
        for w in self.weeds.values():
            w.alive = False

    def deploy_irrigation(self):
        self.irrigation = True

    def transplant(self, pids):
        done = []
        for pid in pids:
            p = self.plant(pid)
            if p.stage == STAGE_EMPTY:
                p.stage, p.gdd, p.biomass_g = STAGE_SEEDLING, 0.0, 12.0
                done.append(pid)
        return done

    def kill_weed(self, wid: int, energy_j: float) -> bool:
        w = self.weeds.get(wid)
        if not w or not w.alive:
            return False
        need = 4.0 + 1.2 * w.size_cm          # J needed to kill the meristem
        p_kill = 0.985 if energy_j >= need else 0.985 * energy_j / need
        if self.rng.random() < p_kill:
            w.alive = False
            return True
        w.size_cm *= 0.8
        return False

    def laser_misfire(self, x: float, y: float) -> int:
        """A shot aimed at a false-positive target. Returns damaged plant id or 0."""
        p = min(self.plants, key=lambda q: (q.x - x) ** 2 + (q.y - y) ** 2)
        if (p.x - x) ** 2 + (p.y - y) ** 2 < 0.15 ** 2 and p.stage:
            p.damage = min(0.6, p.damage + 0.08)
            self.stats["crop_damage_events"] += 1
            return p.pid
        return 0

    def dose_n(self, pid: int, grams_n: float):
        p = self.plant(pid)
        p.soil_n += grams_n * 9.0      # ~9 ppm root-zone rise per g N for a 0.11 m3 zone
        self.stats["n_applied_g"] += grams_n

    def pick(self, fid: int, grip_force_n: float, occluded_view: bool):
        """Returns (success, ripeness, mass_g, bruised)."""
        i = fid - 1
        if i < 0 or i >= len(self.f_state) or self.f_state[i] != 0:
            return False, 0.0, 0.0, False
        p_ok = 0.95 if not (self.f_occ[i] or occluded_view) else 0.80
        if self.rng.random() > p_ok:
            return False, float(self.f_ripe[i]), 0.0, False
        self.f_state[i] = 1
        r = float(self.f_ripe[i])
        softness = max(0.0, r - 0.85) * 3.0
        p_bruise = 0.01 + 0.25 * max(0.0, grip_force_n - 5.0) + 0.1 * softness
        bruised = self.rng.random() < min(p_bruise, 0.9)
        return True, r, float(self.f_mass[i]), bool(bruised)

    # ------------------------------------------------------------------ queries
    def fruit_counts(self, pid: int):
        m = (self.f_plant == pid) & (self.f_state == 0)
        r = self.f_ripe[m]
        return int((r < RIPE_MIN).sum()), int(((r >= RIPE_MIN) & (r < OVERRIPE)).sum()), int((r >= OVERRIPE).sum())

    def fruit_on_plants(self, min_ripeness: float = 0.0):
        idx = np.nonzero((self.f_state == 0) & (self.f_ripe >= min_ripeness))[0]
        return [(int(i + 1), int(self.f_plant[i]), float(self.f_ripe[i]), float(self.f_h[i]), bool(self.f_occ[i]))
                for i in idx]

    def live_weeds(self):
        return [w for w in self.weeds.values() if w.alive]

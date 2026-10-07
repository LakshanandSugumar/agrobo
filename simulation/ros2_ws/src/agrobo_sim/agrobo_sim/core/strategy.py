"""Phase 1 - Sourcing & Strategy.

GIS parcel screening (FAO-style fuzzy land suitability), crop-selection matrix
(market demand x margin x automation fit), and a 5-year robotic-farm NPV.
In production the parcel layers come from SSURGO/SoilGrids, USGS 3DEP slope,
NOAA frost-free days and county parcel/price data; here they are synthesised
with realistic distributions so the decision logic is exercised end to end.
"""
from __future__ import annotations

import json
import math

import numpy as np

CROPS = {
    #           yield t/ha, farm-gate $/kg, inputs $/ha/yr, demand idx, labour h/ha, automation fit, pH lo-hi, frost-free d
    "tomato":     dict(y=55.0, p=1.35, inputs=28000, demand=0.90, labour=1450, auto=0.85, ph=(6.0, 6.8), ffd=150),
    "strawberry": dict(y=40.0, p=3.2, inputs=46000, demand=0.85, labour=2300, auto=0.60, ph=(5.5, 6.5), ffd=140),
    "bell_pepper": dict(y=35.0, p=1.5, inputs=22000, demand=0.70, labour=1250, auto=0.70, ph=(6.0, 7.0), ffd=160),
    "lettuce":    dict(y=30.0, p=0.95, inputs=9000, demand=0.80, labour=600, auto=0.90, ph=(6.0, 7.0), ffd=70),
}


def tri(x, lo, opt_lo, opt_hi, hi):
    if x <= lo or x >= hi:
        return 0.0
    if opt_lo <= x <= opt_hi:
        return 1.0
    return (x - lo) / (opt_lo - lo) if x < opt_lo else (hi - x) / (hi - opt_hi)


def synth_parcels(n: int, seed: int):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append(dict(
            parcel_id=f"P-{seed % 1000:03d}-{i:03d}",
            lat=36.0 + rng.normal(0, 0.6), lon=-120.0 + rng.normal(0, 0.6),
            area_ha=float(rng.uniform(8, 120)),
            ph=float(rng.normal(6.6, 0.6)), om_pct=float(rng.gamma(4, 0.7)), n_ppm=float(rng.normal(28, 8)),
            slope_pct=float(abs(rng.normal(2.5, 2.5))), drainage=float(rng.uniform(0.3, 1.0)),
            well_m3_h=float(rng.gamma(3, 15)), ffd=float(rng.normal(205, 25)),
            km_to_dc=float(rng.gamma(3, 25)), land_usd_ha=float(rng.normal(32000, 9000)),
            lte_coverage=float(rng.uniform(0.2, 1.0)),
        ))
    return out


def suitability(parcel, crop):
    c = CROPS[crop]
    lo, hi = c["ph"]
    s = {
        "ph": tri(parcel["ph"], lo - 0.8, lo, hi, hi + 0.8),
        "om": tri(parcel["om_pct"], 0.5, 2.0, 6.0, 12.0),
        "slope": tri(parcel["slope_pct"], -1, 0, 3.0, 8.0),       # robots: >8 % is a no-go
        "drainage": parcel["drainage"],
        "water": min(1.0, parcel["well_m3_h"] / 40.0),
        "season": min(1.0, parcel["ffd"] / (c["ffd"] + 30)),
        "logistics": math.exp(-parcel["km_to_dc"] / 120.0),
        "connectivity": 0.6 + 0.4 * parcel["lte_coverage"],        # edge autonomy keeps this soft
    }
    w = dict(ph=1.0, om=0.6, slope=1.2, drainage=0.8, water=1.2, season=1.0, logistics=0.7, connectivity=0.3)
    # weighted geometric mean: one zero kills the parcel
    score = math.exp(sum(w[k] * math.log(max(v, 1e-6)) for k, v in s.items()) / sum(w.values()))
    return score, s


def npv(parcel, crop, ha=None, years=5, rate=0.12, robot_capex_usd_ha=38000.0):
    c = CROPS[crop]
    ha = ha or parcel["area_ha"]
    capex = ha * (robot_capex_usd_ha + 3200.0)               # robots + drip/hub infrastructure
    cash = [-capex]
    for t in range(1, years + 1):
        ramp = min(1.0, 0.7 + 0.15 * t)
        rev = ha * c["y"] * 1000 * c["p"] * ramp * 0.92
        opex = ha * (c["inputs"] + c["labour"] * 0.12 * 22.0 + 4200.0 + 0.08 * robot_capex_usd_ha + 1800.0)  # 88 % labour automated; land lease 1800
        cash.append(rev - opex)
    return sum(v / (1 + rate) ** i for i, v in enumerate(cash)), cash


def evaluate(n_candidates=40, seed=2026, crop_lock: str | None = "tomato"):
    parcels = synth_parcels(n_candidates, seed)
    ranked = []
    for p in parcels:
        for crop, c in CROPS.items():
            s, parts = suitability(p, crop)
            if s < 0.35:
                continue
            value, cash = npv(p, crop)
            margin_idx = c["demand"] * c["auto"] * s
            ranked.append(dict(parcel=p, crop=crop, score=s, parts=parts, npv=value, cash=cash,
                               rank_key=margin_idx * max(value, 0) / p["area_ha"]))
    ranked.sort(key=lambda r: r["rank_key"], reverse=True)
    pool = [r for r in ranked if r["crop"] == crop_lock] if crop_lock else ranked
    best = pool[0]
    report = dict(
        method="weighted-geometric FAO suitability x (demand x automation-fit) x NPV/ha",
        candidates=n_candidates, viable_combinations=len(ranked),
        crop_lock=crop_lock,
        top5=[dict(parcel=r["parcel"]["parcel_id"], crop=r["crop"], suitability=round(r["score"], 3),
                   npv_usd=round(r["npv"]), npv_per_ha=round(r["npv"] / r["parcel"]["area_ha"]))
              for r in ranked[:5]],
        chosen=dict(parcel=best["parcel"], crop=best["crop"], factors={k: round(v, 3) for k, v in best["parts"].items()},
                    cashflow_usd=[round(v) for v in best["cash"]]),
    )
    return best, json.dumps(report)

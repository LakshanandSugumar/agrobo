#!/usr/bin/env python3
"""Pick-success sensitivity of Agrobo OpEx per kg.

The season sim (core/agronomy.py, FieldModel.pick) assumes a 95% pick success
rate (80% when the fruit is occluded). The learnt picker in training/ reaches
29% (22% clean) after ~6% of its planned training, and the scripted baseline 42%.

This re-scales each twin-guided run's harvest robot-hours, maintenance and UGV
fleet by 0.95 / p, holding energy, supervision and inputs fixed. It ignores fruit
dropped or bruised by failed picks, so it flatters Agrobo. It is a
back-of-envelope estimate on existing run outputs, not a new simulation run.

    python3 tools/pick_sensitivity.py results            # writes results/pick_sensitivity.json
"""
import json
import sys
from pathlib import Path

SIM_P = 0.95
POINTS = [("Assumed in the season sim", 0.95), ("Scripted picker today", 0.42),
          ("Learnt picker today (run 4)", 0.29)]


def run_opex(k):
    e = k["kpi_3_unit_economics"]
    kg = k["kpi_2_harvest_capture_and_quality"]["harvested_kg"]
    lines, fleet = e["agrobo_opex"]["lines"], e["fleet_sizing"]
    ugv, other = fleet["parts"]["ugv"], fleet["total_usd_ha"] - fleet["parts"]["ugv"]
    fixed = (lines["energy"] + lines["supervision"] + lines["nitrogen"] + lines["herbicide"]) / kg
    maint = lines["maintenance"] / kg

    def opex(p):
        s = SIM_P / p
        return fixed + maint * s + (ugv * s + other) * k["area_ha"] / 10 / kg  # 10-season amortisation
    return opex, e["conventional_opex"]["usd_per_kg"]


def solve(f, target):
    lo, hi = 0.05, SIM_P
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) > target else (lo, m)
    return hi


def main(results_dir):
    runs = sorted(Path(results_dir, "runs").glob("twin_s*/kpis.json"))
    models = [run_opex(json.loads(p.read_text())) for p in runs]
    mean = lambda xs: sum(xs) / len(xs)
    conv = mean([c for _, c in models])
    out = dict(
        method=__doc__.split("\n\n")[2].replace("\n", " "),
        seeds=[p.parent.name for p in runs],
        conventional_usd_per_kg=round(conv, 3),
        points=[dict(label=l, pick_success=p, agrobo_usd_per_kg=round(mean([f(p) for f, _ in models]), 3)) for l, p in POINTS],
        break_even_pick_success=round(mean([solve(f, c) for f, c in models]), 2),
        pick_success_for_usd_0_30=round(mean([solve(f, 0.30) for f, _ in models]), 2),
    )
    Path(results_dir, "pick_sensitivity.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results")

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
    python3 tools/pick_sensitivity.py harvester results  # harvester alone vs hand crew: results/harvester_break_even.json
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


def solve(f, target, lo=0.05, hi=SIM_P):
    """Smallest pick success in [lo, hi] at which cost f(p) falls to target (f falls as p rises).
    Returns None when even hi is too expensive: there is no break-even in range."""
    if f(hi) > target:
        return None
    if f(lo) <= target:
        return lo
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) > target else (lo, m)
    return hi


# ---------------------------------------------------------------------------
# Harvester on its own: robot picking cost per kg vs the hand crew it replaces.
# Every input is an assumption until growers and quotes replace it.
HARVESTER = dict(
    crew_usd_h=22.0,      # all-in picker cost per hour (wage, H-2A housing/transport share, payroll)
    crew_kg_h=85.0,       # the season sim's crew rate; Florida mature-green crews may be far faster
    cycle_s=5.3,          # robot target, 2 arms (robots/README.md)
    kg_per_fruit=0.20,    # Florida round tomato, mature green
    hours_per_year=1500,  # one Florida season, long days
    life_years=5, rate=0.10, maint_frac=0.10,   # capital recovery + maintenance, share of capex per year
    fixed_usd_year=12_000,  # supervision (1 tech per 4 robots at $30/h), energy, connectivity
    price_discount=0.0,   # pilot price below crew cost (0.10-0.20 in the plan)
)
ROBOTS = [("Rev A.1 at 100 units (imported parts)", 36_400), ("Rev A.1 pilot BOM (imported parts)", 48_342),
          ("Rev A.1 built (BOM + assembly)", 51_942), ("Rev B US-sourced, pilot BOM", 125_395),
          ("Rev B US-sourced, built", 129_895)]


def crf(rate, years):
    return rate / (1 - (1 + rate) ** -years)


def harvester(robot_usd, p, **kw):
    a = dict(HARVESTER, **kw)
    if a["cycle_s"] <= 0 or a["hours_per_year"] <= 0 or a["crew_kg_h"] <= 0:
        raise ValueError("cycle_s, hours_per_year and crew_kg_h must be positive")
    annual = robot_usd * (crf(a["rate"], a["life_years"]) + a["maint_frac"]) + a["fixed_usd_year"]
    usd_h = annual / a["hours_per_year"]
    kg_h = 3600 / a["cycle_s"] * a["kg_per_fruit"] * p
    crew_usd_kg = a["crew_usd_h"] / a["crew_kg_h"]
    price = crew_usd_kg * (1 - a["price_discount"])          # what Agrobo is paid per kg picked
    return dict(robot_usd_per_h=usd_h, robot_kg_h=kg_h,
                robot_usd_per_kg=usd_h / kg_h if kg_h else float("inf"),
                crew_usd_per_kg=crew_usd_kg, price_usd_per_kg=price,
                crew_equivalents=kg_h / a["crew_kg_h"],
                margin_usd_per_season=(price * kg_h - usd_h) * a["hours_per_year"])


def harvester_break_even(robot_usd, **kw):
    """Pick success where robot $/kg equals the price per kg. None if not reachable even at 100%."""
    target = harvester(robot_usd, 1.0, **kw)["price_usd_per_kg"]
    return solve(lambda p: harvester(robot_usd, p, **kw)["robot_usd_per_kg"], target, lo=0.01, hi=1.0)


def max_robot_usd(p, **kw):
    """Highest robot price that still breaks even at pick success p."""
    a = dict(HARVESTER, **kw)
    r = harvester(0, p, **kw)
    annual_ok = r["price_usd_per_kg"] * r["robot_kg_h"] * a["hours_per_year"] - a["fixed_usd_year"]
    return max(0.0, annual_ok / (crf(a["rate"], a["life_years"]) + a["maint_frac"]))


def harvester_report():
    r2 = lambda x: None if x is None else round(x, 2)
    scenarios = [("Base: 85 kg/h crews, 1,500 h/yr", {}),
                 ("Pilot price 15% below crew cost", dict(price_discount=0.15)),
                 ("Two seasons or regions: 3,000 h/yr", dict(hours_per_year=3000)),
                 ("Fast mature-green crews: 150 kg/h", dict(crew_kg_h=150)),
                 ("Faster robot: 3.0 s/fruit", dict(cycle_s=3.0))]
    rows = []
    for name, usd in ROBOTS:
        row = dict(robot=name, robot_usd=usd, at_100pct=None, break_even={})
        full = harvester(usd, 1.0)
        row["at_100pct"] = dict(robot_usd_per_kg=round(full["robot_usd_per_kg"], 3),
                                crew_equivalents=round(full["crew_equivalents"], 2))
        for sname, kw in scenarios:
            row["break_even"][sname] = r2(harvester_break_even(usd, **kw))
        rows.append(row)
    return dict(
        method="Robot cost per hour = capex x (capital recovery at 10% over 5 years + 10% maintenance) + $12k/yr fixed, "
               "over hours per year. Robot kg/h = 3600 / cycle_s x kg per fruit x pick success. Break-even is the pick "
               "success where robot $/kg equals the price per kg (crew $/kg, less any pilot discount). None = not "
               "reachable even at 100%. All inputs are assumptions, not field data.",
        assumptions=HARVESTER, crew_usd_per_kg=round(HARVESTER["crew_usd_h"] / HARVESTER["crew_kg_h"], 3),
        robots=rows,
        max_robot_usd_at_55pct=round(max_robot_usd(0.55), -2),
        max_robot_usd_at_55pct_3000h=round(max_robot_usd(0.55, hours_per_year=3000), -2))


def main(results_dir):
    runs = sorted(Path(results_dir, "runs").glob("twin_s*/kpis.json"))
    models = [run_opex(json.loads(p.read_text())) for p in runs]
    mean = lambda xs: sum(xs) / len(xs)
    avg = lambda xs: None if None in xs else round(mean(xs), 2)   # None: not reachable at the sim's 95%
    conv = mean([c for _, c in models])
    out = dict(
        method=__doc__.split("\n\n")[2].replace("\n", " "),
        seeds=[p.parent.name for p in runs],
        conventional_usd_per_kg=round(conv, 3),
        points=[dict(label=l, pick_success=p, agrobo_usd_per_kg=round(mean([f(p) for f, _ in models]), 3)) for l, p in POINTS],
        break_even_pick_success=avg([solve(f, c) for f, c in models]),
        pick_success_for_usd_0_30=avg([solve(f, 0.30) for f, _ in models]),
    )
    Path(results_dir, "pick_sensitivity.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "harvester":
        out = harvester_report()
        dest = Path(sys.argv[2] if len(sys.argv) > 2 else "results", "harvester_break_even.json")
        dest.write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps(out, indent=2))
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "results")

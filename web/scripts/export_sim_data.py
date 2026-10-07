"""Export compact JSON for the website from the ROS 2 season simulation outputs.

Usage: python3 scripts/export_sim_data.py ../simulation/results src/data
Reads results/kpi_summary.json, results/runs/<run>/{events.jsonl,kpis.json} and
results/gazebo/*.json, and writes small files the Next.js app imports at build time.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "../simulation/results")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "src/data")
out.mkdir(parents=True, exist_ok=True)


def season(run):
    days = defaultdict(lambda: dict(harvestKg=0.0, gradeAKg=0.0, soldKg=0.0, revenue=0.0, tasks=defaultdict(float),
                                    toolChanges=0, orders={}, online=True, forwardKg=0.0))
    day, meta, strategy, phases, bt = 0, {}, None, [], None
    for line in open(src / "runs" / run / "events.jsonl"):
        e = json.loads(line)
        t = e.get("type")
        if "day" in e and isinstance(e["day"], int):
            day = max(day, e["day"]) if t in ("field_day", "work_plan") else day
        d = days[e.get("day", day) if isinstance(e.get("day"), int) else day]
        if t == "field_day":
            d.update(tempC=round(e["temp_c"], 1), liveWeeds=e["live_weeds"], ripeOnPlants=e["ripe_on_plants"],
                     fruitOnPlants=e["fruit_on_plants"], nStress=round(e["mean_n_stress"], 3))
        elif t == "lot_processed":
            d["harvestKg"] += e["kg"]
            d["gradeAKg"] += e["a"]
        elif t == "market_day":
            d.update(revenue=round(e["revenue"], 2), spot=round(e["spot"], 3), online=e["online"],
                     soldKg=round(e["sold_kg"], 2), inventoryKg=round(e["inventory_kg"], 2),
                     byBuyer={k: round(v, 2) for k, v in e["by_buyer"].items()})
        elif t == "work_plan":
            agg = defaultdict(int)
            for o in e["orders"]:
                agg[o["kind"]] += o.get("n", 1)
            d["orders"] = dict(agg)
            d["predictedRipe"] = e["predicted_ripe"]
        elif t == "robot_task":
            d["tasks"][e["task"]] += e["duration_h"]
        elif t == "tool_change":
            d["toolChanges"] += 1
        elif t == "forward_commit":
            d["forwardKg"] += e["kg"]
        elif t == "phase":
            phases.append({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if k not in ("type", "node")})
        elif t == "strategy":
            strategy = e["report"]
        elif t == "season_complete":
            meta, bt = e["metrics"], e["bt"]
    series = []
    for k in sorted(days):
        d = days[k]
        series.append(dict(day=k, **{kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in d.items() if kk != "tasks"},
                           tasks={kk: round(v, 3) for kk, v in d["tasks"].items()}))
    return dict(run=run, series=series, phases=phases, metrics=meta, bt=bt), strategy


for run in ("twin_s7", "notwin_s7"):
    s, strategy = season(run)
    s["kpis"] = json.load(open(src / "runs" / run / "kpis.json"))
    json.dump(s, open(out / f"season_{run}.json", "w"), separators=(",", ":"))
    if run == "twin_s7":
        json.dump(strategy, open(out / "strategy_report.json", "w"), indent=1)

json.dump(json.load(open(src / "kpi_summary.json")), open(out / "kpi_summary.json", "w"), indent=1)
gz = {}
for name in ("rtk", "odom"):
    g = json.load(open(src / "gazebo" / f"row_follow_{name}.json"))
    keep = {k: v for k, v in g.items() if not isinstance(v, (list, dict))}
    for k in ("track_sample", "truth_sample"):
        if k in g:
            keep[k] = g[k][::max(1, len(g[k]) // 300)]
    keep["waypoints"] = g.get("waypoints")
    gz[name] = keep
json.dump(gz, open(out / "gazebo_row_follow.json", "w"), separators=(",", ":"))
print("wrote", sorted(p.name for p in out.iterdir()))

# Per-hectare activity quantities averaged over all seeds, for the farm economics planner.
act = {}
for arm, prefix in (("twin", "twin_"), ("noTwin", "notwin_")):
    runs = [json.load(open(p / "kpis.json")) for p in sorted((src / "runs").iterdir()) if p.name.startswith(prefix)]
    def mean(f):
        return round(sum(f(k) for k in runs) / len(runs), 4)
    act[arm] = dict(
        seeds=[k["run"] for k in runs],
        robotHoursPerHa=mean(lambda k: k["autonomy"]["robot_hours"] / k["area_ha"]),
        energyKwhPerHa=mean(lambda k: k["autonomy"]["energy_kwh"] / k["area_ha"]),
        nKgPerHa=mean(lambda k: k["kpi_1_chemical_elimination"]["nitrogen_kg_per_ha"]),
        herbicideLPerHa=mean(lambda k: k["kpi_1_chemical_elimination"]["herbicide_l"] / k["area_ha"]),
        yieldKgPerHa=mean(lambda k: k["kpi_2_harvest_capture_and_quality"]["harvested_kg"] / k["area_ha"]),
        gradeAPct=mean(lambda k: k["kpi_2_harvest_capture_and_quality"]["grade_a_pct"]),
        revenuePerKg=mean(lambda k: k["kpi_3_unit_economics"]["revenue_per_kg"]),
        peakUgvHoursPerDayPerHa=mean(lambda k: k["kpi_3_unit_economics"]["fleet_sizing"]["peak_ugv_hours_per_day_per_ha"]),
        secondsPerFruit=mean(lambda k: k["kpi_2_harvest_capture_and_quality"]["seconds_per_fruit"]),
    )
json.dump(act, open(out / "activity_per_ha.json", "w"), indent=1)
print(json.dumps(act, indent=1))

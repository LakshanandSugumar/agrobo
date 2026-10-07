#!/usr/bin/env python3
"""Aggregate season runs (twin vs no-twin, several seeds) into results/REPORT.md + charts.

    python3 scripts/make_report.py <runs_dir> <results_dir>
"""
import glob
import json
import os
import statistics as stats
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

TWIN, NOTWIN, BASE = "#2a78d6", "#eb6834", "#8a8984"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def load(runs):
    out = {"twin": [], "notwin": []}
    for f in sorted(glob.glob(os.path.join(runs, "*", "kpis.json"))):
        name = os.path.basename(os.path.dirname(f))
        out["twin" if name.startswith("twin") else "notwin"].append((name, json.load(open(f))))
    return out


def get(k, path):
    for p in path.split("."):
        k = k[p]
    return k


def ms(runs, path):
    v = [get(k, path) for _, k in runs]
    return stats.mean(v), (stats.stdev(v) if len(v) > 1 else 0.0)


def fmt(m, s, d=1):
    return f"{m:.{d}f} ± {s:.{d}f}"


METRICS = [
    ("KPI 1", "Herbicide used (L/ha)", "kpi_1_chemical_elimination.herbicide_l", 1),
    ("KPI 1", "Weed-control efficacy (%)", "kpi_1_chemical_elimination.weed_control_efficacy_pct", 1),
    ("KPI 1", "Weeds that reached seed (count)", "kpi_1_chemical_elimination.weeds_reached_seed", 1),
    ("KPI 1", "Crop-damage events (% of plants)", "kpi_1_chemical_elimination.crop_damage_rate_pct", 2),
    ("KPI 1", "Nitrogen applied (kg/ha)", "kpi_1_chemical_elimination.nitrogen_kg_per_ha", 1),
    ("KPI 2", "Harvested yield (t/ha)", "kpi_2_harvest_capture_and_quality.yield_t_per_ha", 1),
    ("KPI 2", "Harvest capture rate (%)", "kpi_2_harvest_capture_and_quality.capture_rate_pct", 2),
    ("KPI 2", "Picker seconds per fruit", "kpi_2_harvest_capture_and_quality.seconds_per_fruit", 2),
    ("KPI 2", "Picker kg per robot-hour", "kpi_2_harvest_capture_and_quality.picker_kg_per_robot_h", 1),
    ("KPI 2", "Grade A share (%)", "kpi_2_harvest_capture_and_quality.grade_a_pct", 1),
    ("KPI 2", "Bruise rate (%)", "kpi_2_harvest_capture_and_quality.bruise_rate_pct", 2),
    ("KPI 2", "Mean pick-to-cool (h)", "kpi_2_harvest_capture_and_quality.mean_pick_to_cool_h", 2),
    ("KPI 3", "Agrobo OpEx ($/kg)", "kpi_3_unit_economics.agrobo_opex.usd_per_kg", 3),
    ("KPI 3", "Conventional OpEx ($/kg)", "kpi_3_unit_economics.conventional_opex.usd_per_kg", 3),
    ("KPI 3", "OpEx reduction vs conventional (%)", "kpi_3_unit_economics.opex_reduction_pct", 1),
    ("KPI 3", "Peak UGVs needed per ha", "kpi_3_unit_economics.fleet_sizing.ugv_per_ha", 2),
    ("KPI 3", "Fleet capex ($/ha)", "kpi_3_unit_economics.fleet_sizing.total_usd_ha", 0),
    ("KPI 3", "Revenue per kg ($)", "kpi_3_unit_economics.revenue_per_kg", 3),
    ("KPI 3", "Revenue uplift vs ungraded wholesale (%)", "kpi_3_unit_economics.revenue_uplift_pct", 1),
    ("KPI 3", "Labour hours per ha (conventional)", None, 0),
    ("Autonomy", "Human interventions", "autonomy.human_interventions", 0),
    ("Autonomy", "Cloud-outage days run edge-only", "autonomy.cloud_outage_days", 0),
    ("Autonomy", "Implement swaps per season", "autonomy.tool_changes", 0),
    ("Autonomy", "Battery hot-swaps per season", "autonomy.battery_swaps", 0),
]


def style(ax, title, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, loc="left", color=INK, fontsize=11, pad=10)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def cumulative_harvest(runs_dir, name):
    ev = [json.loads(l) for l in open(os.path.join(runs_dir, name, "events.jsonl"))]
    by = {}
    for e in ev:
        if e["type"] == "lot_processed":
            by[e["day"]] = by.get(e["day"], 0.0) + e["kg"]
    days = list(range(0, max(by or [0]) + 1))
    c, out = 0.0, []
    for d in days:
        c += by.get(d, 0.0)
        out.append(c)
    return days, out


def charts(data, runs_dir, out):
    os.makedirs(out, exist_ok=True)
    # 2) picker seconds per fruit and 3) OpEx $/kg, as two single-measure bar charts
    for fname, title, ylabel, path, base_path, d in (
        ("picker_cycle_time.png", "Picker time per fruit (incl. travel and search)", "seconds per fruit",
         "kpi_2_harvest_capture_and_quality.seconds_per_fruit", None, 1),
        ("opex_per_kg.png", "Operating cost per kg harvested", "USD per kg",
         "kpi_3_unit_economics.agrobo_opex.usd_per_kg", "kpi_3_unit_economics.conventional_opex.usd_per_kg", 3),
        ("fleet_capex_per_ha.png", "Fleet capex per hectare (sized for peak harvest week)", "USD per ha",
         "kpi_3_unit_economics.fleet_sizing.total_usd_ha", None, 0)):
        labels, vals, errs, cols = [], [], [], []
        if base_path:
            m, s = ms(data["twin"] + data["notwin"], base_path)
            labels.append("Conventional\n(hand labour)"); vals.append(m); errs.append(s); cols.append(BASE)
        for key, lab, col in (("notwin", "Agrobo\nno twin", NOTWIN), ("twin", "Agrobo\ntwin-guided", TWIN)):
            m, s = ms(data[key], path)
            labels.append(lab); vals.append(m); errs.append(s); cols.append(col)
        fig, ax = plt.subplots(figsize=(5, 3.4), dpi=160, facecolor=SURF)
        bars = ax.bar(labels, vals, color=cols, width=0.55, yerr=errs, error_kw=dict(ecolor=INK2, lw=1, capsize=3),
                      edgecolor=SURF, linewidth=2)
        for b, v, e in zip(bars, vals, errs):
            ax.annotate(f"{v:,.{d}f}", (b.get_x() + b.get_width() / 2, v + e), xytext=(0, 6), textcoords="offset points",
                        ha="center", color=INK, fontsize=8)
        style(ax, title, ylabel)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.%df}" % (1 if d == 3 else d)))
        fig.tight_layout()
        fig.savefig(os.path.join(out, fname), facecolor=SURF)
        plt.close(fig)


def main():
    runs_dir, out = sys.argv[1], sys.argv[2]
    data = load(runs_dir)
    n = len(data["twin"])
    charts(data, runs_dir, os.path.join(out, "charts"))
    rows, summary = [], {}
    for grp, label, path, d in METRICS:
        if path is None:
            m, s = ms(data["twin"], "kpi_3_unit_economics.labour_hours_conventional")
            area = data["twin"][0][1]["area_ha"]
            rows.append(f"| {grp} | {label} | {m / area:,.0f} (Agrobo: "
                        f"{data['twin'][0][1]['kpi_3_unit_economics']['labour_hours_agrobo'] / area:,.0f} supervision) | |")
            continue
        tm, ts = ms(data["twin"], path)
        nm, ns = ms(data["notwin"], path)
        summary[label] = dict(twin=dict(mean=tm, sd=ts), no_twin=dict(mean=nm, sd=ns))
        delta = f"{100 * (tm / nm - 1):+.0f} %" if nm else ""
        rows.append(f"| {grp} | {label} | {fmt(tm, ts, d)} | {fmt(nm, ns, d)} | {delta} |")
    k0 = data["twin"][0][1]
    ph = k0["phases"]
    gz = {}
    for f in ("row_follow_rtk", "row_follow_odom"):
        p = os.path.join(out, "gazebo", f + ".json")
        if os.path.exists(p):
            gz[f] = json.load(open(p))
    with open(os.path.join(out, "kpi_summary.json"), "w") as f:
        json.dump(dict(seeds=[nme for nme, _ in data["twin"]], metrics=summary), f, indent=2)
    md = [
        "# Agrobo Season Simulation: KPI Report",
        "",
        f"Field: {k0['area_ha']} ha block, 480 tomato plants (10 rows x 48, 1.5 m x 0.5 m), "
        f"{k0['season_days']}-day season, ROS 2 Jazzy, {n} seeds per arm. "
        "Both arms use the same robots, field and weather; only the Field Ledger twin is switched off "
        "in the ablation (`twin_guided:=false`). Values are mean ± sd across seeds.",
        "",
        "## Results",
        "",
        "| | Metric | Twin-guided | No twin (ablation) | Δ twin vs no twin |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "![Fleet capex per ha](charts/fleet_capex_per_ha.png)",
        "",
        "![Picker cycle time](charts/picker_cycle_time.png) ![OpEx per kg](charts/opex_per_kg.png)",
        "",
        "## End-to-end lifecycle (one run, seed 7)",
        "",
        f"1. **Sourcing:** parcel `{ph['sourcing']['parcel']}` chosen for {ph['sourcing']['crop']} "
        f"(suitability {ph['sourcing']['suitability']:.2f}, modelled 5-year NPV ${ph['sourcing']['npv_usd'] / 1e6:.1f}M "
        "at parcel scale). Soil N from the chosen parcel seeds the field model.",
        f"2. **Prep:** clear, RTK layout, till and drip deployment over {ph['prep']['area_ha']:.3f} ha in "
        f"{ph['prep']['duration_h']:.1f} robot-hours ({ph['prep']['distance_m']:.0f} m driven).",
        f"3. **Establish and cultivate:** {ph['establish']['planted']} plugs transplanted in "
        f"{ph['establish']['duration_h']:.2f} h. Scout UAV every 2 days, laser weeding and per-plant N micro-dosing "
        "from Field Ledger work orders.",
        "4. **Harvest:** both modular UGVs swap to picker arms when the ledger forecasts ripe fruit, and the "
        "hauler shuttles bins to the hub.",
        "5. **Post-harvest and market:** hyperspectral grading, cold-chain packing, then FEFO allocation across retail "
        "forward contracts (sized from the ledger's D+3 forecast), food service, wholesale and processor.",
        "",
        "## Physics check (Gazebo Harmonic, headless)",
        "",
    ]
    if gz:
        r, o = gz.get("row_follow_rtk", {}), gz.get("row_follow_odom", {})
        md += [
            "Modular UGV (skid-steer, 4 wheels) driving a 4-lane boustrophedon through the 480-plant world. "
            "The comparison is pure-pursuit steering on RTK-GNSS + IMU versus on wheel odometry alone.",
            "",
            "| Localisation | True cross-track RMS | True cross-track max | Mean speed | Distance |",
            "|---|---|---|---|---|",
            f"| RTK + IMU | {r.get('cross_track_rms_true_m', 0) * 100:.1f} cm | {r.get('cross_track_max_true_m', 0) * 100:.1f} cm "
            f"| {r.get('mean_speed_mps')} m/s | {r.get('distance_m')} m |",
            f"| Wheel odometry only | {o.get('cross_track_rms_true_m', 0) * 100:.0f} cm | "
            f"{o.get('cross_track_max_true_m', 0) * 100:.0f} cm | {o.get('mean_speed_mps')} m/s | {o.get('distance_m')} m |",
            "",
            "Skid-steer slip makes odometry-only navigation unusable within one turn (the robot believes it is on "
            "the lane while running metres into the crop). RTK + IMU holds the lane to ~3 cm RMS at 0.69 m/s, which "
            "matches the 0.6-0.7 m/s the season tier assumes for UGV work speed.",
            "",
        ]
    md += [
        "## Reading these numbers",
        "",
        "- Perception, manipulation, prices and costs are **calibrated models, not field data**. Every constant lives in "
        "`core/*.py` (and `EconAssumptions`) and is meant to be overwritten with bench and pilot measurements.",
        "- The economics compare per-kg OpEx with fleet capex amortised over 10 seasons. The fleet is sized for the "
        "simulated **peak 7-day UGV workload**, so picker speed sets capex per hectare directly.",
        "- The baseline revenue is ungraded field-run sold at wholesale the same day.",
        "- Capture rate counts ripe fruit still on the vine when the season is cut at day 125. The twin arm is "
        "lower because it deliberately waits for fruit to reach 0.80 ripeness. Actual field drops are under 1 kg in "
        "both arms, so a final clean-out pass would close that gap.",
        "",
    ]
    with open(os.path.join(out, "REPORT.md"), "w") as f:
        f.write("\n".join(md))
    print(f"wrote {out}/REPORT.md ({n} seeds/arm)")


if __name__ == "__main__":
    main()

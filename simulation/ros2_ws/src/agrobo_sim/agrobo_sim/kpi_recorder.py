"""/kpi_recorder: aggregates /agrobo/events and writes the season KPI report.

Output: <output_dir>/<run_name>/{events.jsonl, kpis.json}
Exits when it sees `season_complete` (the launch file then shuts everything down).
"""
import json
import os

import rclpy
from std_msgs.msg import String

from agrobo_sim.core.economics import (EconAssumptions, agrobo_opex, assumptions_dict, conventional_opex,
                                       fleet_capex_per_ha)
from agrobo_sim.core.market import MarketConfig
from agrobo_sim.ros_util import EVENTS, AgroboNode


def compute_kpis(events, area_override=None):
    by = {}
    for e in events:
        by.setdefault(e["type"], []).append(e)
    days = by.get("field_day", [])
    last = days[-1] if days else {}
    area = area_override or last.get("area_ha", 0.036)
    st = last.get("stats", {})
    tasks = by.get("robot_task", [])
    robots = {}
    for t in tasks:
        robots[t["robot_id"]] = t                                 # cumulative counters: keep the latest
    energy = sum(r["energy_kwh_total"] for r in robots.values())
    hours = sum(r["op_hours_total"] for r in robots.values())
    lots = by.get("lot_processed", [])
    harvested = sum(l["kg"] for l in lots)
    kg_a = sum(l["a"] for l in lots); kg_b = sum(l["b"] for l in lots)
    kg_c = sum(l["c"] for l in lots); kg_r = sum(l["rej"] for l in lots)
    harv = [t for t in tasks if t["task"] == "harvesting"]
    weed = [t for t in tasks if t["task"] == "weeding"]
    dose = [t for t in tasks if t["task"] == "dosing"]
    picked = sum(t["picked"] for t in harv)
    pick_h = sum(t["duration_h"] for t in harv)
    killed = sum(t["killed"] for t in weed)
    left_ripe_kg = (last.get("ripe_on_plants", 0) + last.get("overripe_on_plants", 0)) * 0.125
    dropped_kg = st.get("dropped_kg", 0.0)
    market = by.get("market_day", [])
    revenue = sum(m["revenue"] for m in market)
    spoiled = sum(m["spoiled_kg"] for m in market)
    mc = MarketConfig()
    harvest_by_day = {}
    for l in lots:
        harvest_by_day[l["day"]] = harvest_by_day.get(l["day"], 0.0) + l["kg"]
    spot = {m["day"]: m["spot"] for m in market}
    base_rev = sum(kg * 0.94 * spot.get(d, mc.spot_mean) * mc.wholesale_discount * mc.ungraded_discount
                   for d, kg in harvest_by_day.items())
    a = EconAssumptions()
    # UGV workload per sim-day (events are causally ordered by the day loop)
    ugv_day, cur = {}, 0
    for e in events:
        if e["type"] == "field_day":
            cur = e["day"]
        elif e["type"] == "robot_task" and e["robot_type"] == "ugv_modular":
            ugv_day[cur] = ugv_day.get(cur, 0.0) + e["duration_h"]
    series = [ugv_day.get(d, 0.0) for d in range(0, (last.get("day") or 0) + 1)]
    peak7 = max((sum(series[i:i + 7]) / 7 for i in range(max(1, len(series) - 6))), default=0.0)
    fleet = fleet_capex_per_ha(a, peak7 / area)
    n_kg = st.get("n_applied_g", 0.0) / 1000.0
    ag = agrobo_opex(a, area, hours, energy, n_kg, 0.0, harvested, fleet["total_usd_ha"])
    conv = conventional_opex(a, area, harvested)
    p2c = [l["pick_to_cool_h"] for l in lots]
    phases = {p["phase"]: p for p in by.get("phase", [])}
    cloud = (by.get("cloud_stats") or [{}])[-1]
    season = (by.get("season_complete") or [{}])[-1]
    seeded = st.get("weeds_seeded", 0)
    fd = [d for d in days]
    k = dict(
        run=season.get("run_name"), twin_guided=season.get("twin_guided"), season_days=last.get("day"),
        area_ha=round(area, 4),
        kpi_1_chemical_elimination=dict(
            herbicide_l=0.0, baseline_herbicide_l_per_ha=a.conv_herbicide_l_ha, herbicide_reduction_pct=100.0,
            weeds_killed=killed, weeds_alive_end=last.get("live_weeds"), weeds_reached_seed=seeded,
            weed_control_efficacy_pct=round(100 * killed / max(1, killed + (last.get("live_weeds") or 0)), 2),
            crop_damage_events=st.get("crop_damage_events", 0),
            crop_damage_rate_pct=round(100 * st.get("crop_damage_events", 0) / max(1, last.get("plants", 1)), 2),
            mean_weed_competition_index=round(sum(d["mean_weed_comp"] for d in fd) / max(1, len(fd)), 4),
            nitrogen_kg_per_ha=round(n_kg / area, 1), baseline_n_kg_per_ha=a.conv_n_kg_ha,
            nitrogen_reduction_pct=round(100 * (1 - (n_kg / area) / a.conv_n_kg_ha), 1)),
        kpi_2_harvest_capture_and_quality=dict(
            harvested_kg=round(harvested, 1), yield_t_per_ha=round(harvested / 1000 / area, 1),
            field_loss_kg=round(dropped_kg, 1), left_on_plant_ripe_kg=round(left_ripe_kg, 1),
            capture_rate_pct=round(100 * harvested / max(1e-6, harvested + dropped_kg + left_ripe_kg), 2),
            grade_a_pct=round(100 * kg_a / max(1e-6, harvested), 2),
            grade_mix_kg=dict(A=round(kg_a, 1), B=round(kg_b, 1), C=round(kg_c, 1), reject=round(kg_r, 1)),
            bruise_rate_pct=round(100 * sum(t["bruised"] for t in harv) / max(1, picked), 2),
            fruit_picked=picked,
            seconds_per_fruit=round(3600 * pick_h / max(1, picked), 2),
            picker_kg_per_robot_h=round(sum(t["mass_kg"] for t in harv) / max(1e-6, pick_h), 1),
            mean_pick_to_cool_h=round(sum(p2c) / max(1, len(p2c)), 2), max_pick_to_cool_h=round(max(p2c or [0]), 2)),
        kpi_3_unit_economics=dict(
            agrobo_opex=ag, conventional_opex=conv,
            fleet_sizing=dict(peak_7d_ugv_hours_per_day=round(peak7, 2),
                              peak_ugv_hours_per_day_per_ha=round(peak7 / area, 1), **fleet),
            opex_reduction_pct=round(100 * (1 - ag["total_usd"] / max(1e-6, conv["total_usd"])), 1),
            labour_hours_conventional=conv["labour_h"],
            labour_hours_agrobo=round(a.supervision_h_per_ha_season * area, 1),
            revenue_usd=round(revenue, 2), baseline_revenue_usd=round(base_rev, 2),
            revenue_uplift_pct=round(100 * (revenue / max(1e-6, base_rev) - 1), 1),
            revenue_per_kg=round(revenue / max(1e-6, harvested), 3), spoiled_kg=round(spoiled, 1),
            contract_penalties_usd=round((market[-1]["penalties_total"] if market else 0.0), 2)),
        autonomy=dict(
            human_interventions=0, robot_hours=round(hours, 1), energy_kwh=round(energy, 1),
            battery_swaps=sum(r.get("battery_swaps", 0) for r in robots.values()),
            tool_changes=len(by.get("tool_change", [])),
            cloud_outage_days=cloud.get("outage_days", 0), events_buffered_offline=cloud.get("events_buffered", 0),
            field_ops_completed_during_outage=sum(1 for e in by.get("edge_only", [])),
            per_robot={rid: dict(type=r["robot_type"], hours=round(r["op_hours_total"], 1),
                                 kwh=round(r["energy_kwh_total"], 1), km=round(r["odometer_m"] / 1000, 2))
                       for rid, r in robots.items()}),
        phases=phases, orchestrator=season.get("metrics"),
        assumptions=assumptions_dict(a),
    )
    return k


class KpiRecorder(AgroboNode):
    def __init__(self):
        super().__init__("kpi_recorder")
        self.declare_parameter("output_dir", "results")
        self.declare_parameter("run_name", "agrobo")
        self.events = []
        self.done = False
        self.create_subscription(String, "/agrobo/events", self.on_event, EVENTS)

    def on_event(self, m):
        e = json.loads(m.data)
        self.events.append(e)
        if e["type"] == "season_complete" and not self.done:
            self.done = True
            out = os.path.join(self.get_parameter("output_dir").value, self.get_parameter("run_name").value)
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, "events.jsonl"), "w") as f:
                for ev in self.events:
                    f.write(json.dumps(ev) + "\n")
            k = compute_kpis(self.events)
            with open(os.path.join(out, "kpis.json"), "w") as f:
                json.dump(k, f, indent=2)
            self.get_logger().info(f"KPI report written to {out}")


def main(args=None):
    rclpy.init(args=args)
    n = KpiRecorder()
    try:
        while rclpy.ok() and not n.done:
            rclpy.spin_once(n, timeout_sec=0.5)
    finally:
        n.destroy_node()
        rclpy.try_shutdown()

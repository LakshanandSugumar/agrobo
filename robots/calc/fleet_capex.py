"""Fleet capex per hectare: prototype model vs the real BOM. Writes calc/fleet_capex.json + .md"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
bom = json.load(open(os.path.join(HERE, "..", "bom", "cost_summary.json")))
calc = json.load(open(os.path.join(HERE, "results.json")))
om = bom["other_modules_pilot"]

model = dict(ugv_per_ha=1.23, parts=dict(ugv=1.23 * 55000, uav=12000 / 200, hauler=30000 / 8, hub=150000 / 40, prep=90000 / 60))

def real(price_key, ugv_per_ha, weeder="mech", vol=False):
    k = 0.75 if vol else 1.0                        # other modules at volume (rough)
    robot = bom["harvester_robot_vol100" if vol else "harvester_robot_pilot"] + (1500 if vol else 3600)   # + assembly/test labour
    weeder_unit = om["LW-1 laser weeder implement (2 heads)"] if weeder == "laser" else om["LW-1M mechanical aisle cultivator (alternative)"]
    per_ugv = robot + 0.5 * weeder_unit * k + 0.33 * om["SP-1 spot sprayer implement (replaces micro-doser)"] * k \
        + 0.5 * om["DK-1 dock/charger (serves ~2 UGVs)"] * k
    parts = dict(ugv=ugv_per_ha * per_ugv, uav=om["SU-1 scout UAV (ArduPilot quad, multispectral)"] * k / 200,
                 hauler=om["HL-1 hauler (AB-1 base + tote rack, no arms)"] * k / 8, hub=150000 / 40, prep=0.0)
    return dict(ugv_per_ha=ugv_per_ha, per_ugv=round(per_ugv), parts={a: round(b) for a, b in parts.items()},
                total=round(sum(parts.values())))

duty_adj = 18.0 / calc["duty_h_day"]
ugv_sim = 1.23 * duty_adj                            # sim cycle time (8.0 s/fruit), real duty cycle
ugv_target = ugv_sim * calc["robot_s_per_fruit"] / 8.0
rows = {
    "Prototype model": dict(ugv_per_ha=1.23, parts={k: round(v) for k, v in model["parts"].items()}, total=round(sum(model["parts"].values()))),
    "Real BOM, pilot prices, sim cycle time, mechanical weeder": real("pilot", ugv_sim),
    "Real BOM, pilot prices, sim cycle time, laser weeder": real("pilot", ugv_sim, "laser"),
    "Real BOM, 100-unit prices, sim cycle time, mechanical weeder": real("vol", ugv_sim, vol=True),
    "Real BOM, 100-unit prices, design-target cycle time, mechanical weeder": real("vol", ugv_target, vol=True),
}
json.dump(rows, open(os.path.join(HERE, "fleet_capex.json"), "w"), indent=1)
md = ["| Scenario | UGV/ha | $/UGV incl. share of implements + dock | UGVs $/ha | UAV | Hauler | Hub | Prep | **Total $/ha** | vs model |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
base = rows["Prototype model"]["total"]
for k, r in rows.items():
    p = r["parts"]
    md.append(f"| {k} | {r['ugv_per_ha']:.2f} | {r.get('per_ugv', 55000):,} | {p['ugv']:,} | {p['uav']:,} | {p['hauler']:,} | {p['hub']:,} | {p['prep']:,} | **{r['total']:,}** | {100*(r['total']/base-1):+.0f} % |")
open(os.path.join(HERE, "fleet_capex.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))

import type { Metadata } from "next";
import { HBars } from "@/components/charts";
import { PageHead } from "@/components/PageHead";
import { Card } from "@/components/ui";
import { kpi, kpiSummary } from "@/lib/data";
import { C } from "@/lib/palette";
import harvest from "@/data/harvester_break_even.json";
import pick from "@/data/pick_sensitivity.json";

export const metadata: Metadata = { title: "Simulation results" };

const GROUPS: [string, string, string[]][] = [
  ["KPI 1", "Chemical elimination at parity weed control", ["Herbicide used (L/ha)", "Weed-control efficacy (%)", "Weeds that reached seed (count)", "Crop-damage events (% of plants)", "Nitrogen applied (kg/ha)"]],
  ["KPI 2", "Harvest capture and cycle time", ["Harvested yield (t/ha)", "Harvest capture rate (%)", "Picker seconds per fruit", "Picker kg per robot-hour", "Grade A share (%)", "Bruise rate (%)", "Mean pick-to-cool (h)"]],
  ["KPI 3", "Unit economics", ["Agrobo OpEx ($/kg)", "Conventional OpEx ($/kg)", "OpEx reduction vs conventional (%)", "Peak UGVs needed per ha", "Fleet capex ($/ha)", "Revenue per kg ($)", "Revenue uplift vs ungraded wholesale (%)"]],
  ["Autonomy", "Running without people", ["Human interventions", "Cloud-outage days run edge-only", "Implement swaps per season", "Battery hot-swaps per season"]],
];

const f = (v: number) => (Math.abs(v) >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 }) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));

export default function Page() {
  const metrics = kpiSummary.metrics as Record<string, { twin: { mean: number; sd: number }; no_twin: { mean: number; sd: number } }>;
  const spf = kpi("Picker seconds per fruit");
  const capex = kpi("Fleet capex ($/ha)");
  return (
    <>
      <PageHead eyebrow="Simulation results" title="Twin on vs twin off, same robots, three seeds.">
        A 0.036 ha block of 480 tomato plants (10 rows × 48) over a 125-day season on ROS 2 Jazzy. Both arms use the same
        robots, field and weather; only the Field Ledger twin is switched off in the ablation. Values are mean ± sd over
        seeds 7, 11 and 23. Perception, manipulation, prices and costs are calibrated models, not field data.
      </PageHead>

      <section className="container-x grid gap-6 pb-12 md:grid-cols-3">
        <Card className="p-6">
          <div className="text-[15px] font-semibold">Operating cost, $/kg</div>
          <div className="mt-5">
            <HBars
              rows={[
                { label: "Agrobo, twin on", value: kpi("Agrobo OpEx ($/kg)").twin.mean, display: `$${kpi("Agrobo OpEx ($/kg)").twin.mean.toFixed(3)}`, color: C.agrobo },
                { label: "Agrobo, twin off", value: kpi("Agrobo OpEx ($/kg)").no_twin.mean, display: `$${kpi("Agrobo OpEx ($/kg)").no_twin.mean.toFixed(3)}`, color: C.blue },
                { label: "Conventional", value: kpi("Conventional OpEx ($/kg)").twin.mean, display: `$${kpi("Conventional OpEx ($/kg)").twin.mean.toFixed(3)}`, color: C.conventional },
              ]}
            />
          </div>
        </Card>
        <Card className="p-6">
          <div className="text-[15px] font-semibold">Picker seconds per fruit</div>
          <div className="mt-5">
            <HBars
              rows={[
                { label: "Twin on (predict-then-pick)", value: spf.twin.mean, display: `${spf.twin.mean.toFixed(1)} s`, color: C.agrobo },
                { label: "Twin off (search-then-pick)", value: spf.no_twin.mean, display: `${spf.no_twin.mean.toFixed(1)} s`, color: C.blue },
              ]}
            />
          </div>
        </Card>
        <Card className="p-6">
          <div className="text-[15px] font-semibold">Fleet capex per hectare</div>
          <div className="mt-5">
            <HBars
              rows={[
                { label: "Twin on", value: capex.twin.mean, display: `$${(capex.twin.mean / 1000).toFixed(0)}k`, color: C.agrobo },
                { label: "Twin off", value: capex.no_twin.mean, display: `$${(capex.no_twin.mean / 1000).toFixed(0)}k`, color: C.blue },
              ]}
            />
          </div>
        </Card>
      </section>

      <section id="pick-success" className="container-x scroll-mt-24 pb-12">
        <Card className="p-6">
          <div className="text-[15px] font-semibold">Pick-success sensitivity</div>
          <p className="mt-2 max-w-3xl text-[14px] leading-relaxed text-ink-2">
            The season sim assumes a 95% pick success rate. Our learnt picker gets 29% of fruit off today (22% cleanly, with
            no bruise and no neighbour knocked off), after about 6% of its planned training. Re-scaling harvest robot-hours,
            maintenance and the UGV fleet to lower pick rates (ignoring dropped and bruised fruit, which flatters us) gives
            whole-farm break-even with a conventional farm at about {(pick.break_even_pick_success * 100).toFixed(0)}% and
            $0.30/kg at about {(pick.pick_success_for_usd_0_30 * 100).toFixed(0)}%. That spreads the robot&apos;s cost over
            weeding and hauling too. The harvester on its own, below, needs more. An estimate on the runs above, not a new
            simulation run.
          </p>
          <div className="mt-5">
            <HBars
              rows={[
                ...pick.points.map((pt) => ({
                  label: `${pt.label}, ${(pt.pick_success * 100).toFixed(0)}%`,
                  value: pt.agrobo_usd_per_kg,
                  display: `$${pt.agrobo_usd_per_kg.toFixed(3)}/kg`,
                  color: pt.agrobo_usd_per_kg > pick.conventional_usd_per_kg ? C.muted : C.agrobo,
                })),
                { label: "Conventional hand crew", value: pick.conventional_usd_per_kg, display: `$${pick.conventional_usd_per_kg.toFixed(3)}/kg`, color: C.conventional },
              ]}
            />
          </div>
        </Card>
      </section>

      <section id="harvester" className="container-x scroll-mt-24 pb-12">
        <Card className="p-6">
          <div className="text-[15px] font-semibold">Harvester on its own: pick success needed to match a hand crew</div>
          <p className="mt-2 max-w-3xl text-[14px] leading-relaxed text-ink-2">
            Robot cost per hour is capital recovered at 10% over 5 years, 10% maintenance and $12k a year of fixed costs, over
            the hours it works. Robot output is 3,600 / {harvest.assumptions.cycle_s} s per fruit × {harvest.assumptions.kg_per_fruit} kg
            × pick success. A hand crew costs ${harvest.crew_usd_per_kg.toFixed(3)}/kg (${harvest.assumptions.crew_usd_h}/h at{" "}
            {harvest.assumptions.crew_kg_h} kg/h, our assumption until grower calls). &ldquo;Not reachable&rdquo; means the robot
            costs more per kg than the crew even at 100%.
          </p>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[720px] text-[14px]">
              <thead className="text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                <tr>
                  <th className="py-2 pr-3 font-normal">Robot</th>
                  {Object.keys(harvest.robots[0].break_even).map((k) => (
                    <th key={k} className="py-2 pr-3 text-right font-normal">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line border-t border-line">
                {harvest.robots.map((r) => (
                  <tr key={r.robot}>
                    <td className="py-3 pr-3">
                      <div className="font-medium">{r.robot}</div>
                      <div className="text-[12px] text-muted">${r.robot_usd.toLocaleString("en-US")}</div>
                    </td>
                    {Object.values(r.break_even as Record<string, number | null>).map((v, i) => (
                      <td key={i} className={`tabular py-3 pr-3 text-right ${v === null ? "text-tomato" : "font-semibold"}`}>
                        {v === null ? "Not reachable" : `${Math.round(v * 100)}%`}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-[12px] text-muted">
            The US-built robot needs a robot price of about ${(harvest.max_robot_usd_at_55pct / 1000).toFixed(1)}k to break
            even at 55% in one 1,500-hour season, or up to ${(harvest.max_robot_usd_at_55pct_3000h / 1000).toFixed(1)}k if it
            works 3,000 hours a year. Source: <code>simulation/tools/pick_sensitivity.py harvester</code>.
          </p>
        </Card>
      </section>

      <section className="container-x space-y-6 pb-24">
        {GROUPS.map(([tag, title, names]) => (
          <Card key={tag} className="overflow-hidden">
            <div className="flex items-baseline gap-3 border-b border-line px-5 py-4">
              <span className="font-mono text-[12px] text-brand">{tag}</span>
              <span className="text-[16px] font-semibold">{title}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-[14px]">
                <thead className="text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-5 py-2.5 font-normal">Metric</th>
                    <th className="px-5 py-2.5 text-right font-normal">Twin-guided</th>
                    <th className="px-5 py-2.5 text-right font-normal">No twin</th>
                    <th className="px-5 py-2.5 text-right font-normal">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {names.filter((n) => metrics[n]).map((n) => {
                    const m = metrics[n];
                    const d = m.no_twin.mean ? ((m.twin.mean - m.no_twin.mean) / Math.abs(m.no_twin.mean)) * 100 : 0;
                    return (
                      <tr key={n} className="border-t border-line">
                        <td className="px-5 py-2.5 text-ink-2">{n}</td>
                        <td className="tabular px-5 py-2.5 text-right font-medium">{f(m.twin.mean)} <span className="text-[12px] text-muted">± {f(m.twin.sd)}</span></td>
                        <td className="tabular px-5 py-2.5 text-right">{f(m.no_twin.mean)} <span className="text-[12px] text-muted">± {f(m.no_twin.sd)}</span></td>
                        <td className="tabular px-5 py-2.5 text-right text-muted">{m.no_twin.mean && Math.abs(d) >= 0.5 ? `${d > 0 ? "+" : ""}${d.toFixed(0)}%` : "–"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
        <Card className="p-6 text-[14px] leading-relaxed text-ink-2">
          <div className="text-[15px] font-semibold text-ink">Reading these numbers</div>
          <ul className="mt-3 list-disc space-y-1.5 pl-5">
            <li>The fleet is sized for the simulated peak 7-day UGV workload, so picker speed sets capex per hectare directly. Fleet capex is amortised over 10 seasons inside OpEx.</li>
            <li>The conventional baseline follows a fresh-market tomato cost study: hand harvest at 85 kg/h, 160 h/ha of hand weeding, 5.5 L/ha herbicide and 220 kg/ha nitrogen.</li>
            <li>The twin arm captures 93% of ripe fruit vs 96% because it deliberately waits for 0.80 ripeness; the gap is ripe fruit still on the vine at the day-125 cutoff, and a final clean-out pass closes it.</li>
            <li>Revenue uplift is against ungraded field-run sold at wholesale on the day.</li>
          </ul>
        </Card>
      </section>
    </>
  );
}

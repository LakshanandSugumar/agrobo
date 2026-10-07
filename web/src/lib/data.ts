import activity from "@/data/activity_per_ha.json";
import kpiSummary from "@/data/kpi_summary.json";
import notwin from "@/data/season_notwin_s7.json";
import strategy from "@/data/strategy_report.json";
import twin from "@/data/season_twin_s7.json";

type Arm = { mean: number; sd: number };
const metrics = kpiSummary.metrics as Record<string, { twin: Arm; no_twin: Arm }>;

export function kpi(name: string) {
  const m = metrics[name];
  if (!m) throw new Error(`unknown KPI ${name}`);
  return m;
}

export const KPI_NAMES = Object.keys(metrics);
export { activity, kpiSummary, notwin, strategy, twin };

export type SeasonDay = (typeof twin.series)[number];

export function compactSeason(s: typeof twin | typeof notwin) {
  let cumKg = 0, cumRev = 0;
  return s.series.map((d) => {
    cumKg += d.harvestKg ?? 0;
    cumRev += d.revenue ?? 0;
    return {
      day: d.day,
      tempC: "tempC" in d ? (d.tempC as number) : null,
      liveWeeds: "liveWeeds" in d ? (d.liveWeeds as number) : 0,
      ripeOnPlants: "ripeOnPlants" in d ? (d.ripeOnPlants as number) : 0,
      fruitOnPlants: "fruitOnPlants" in d ? (d.fruitOnPlants as number) : 0,
      predictedRipe: "predictedRipe" in d ? (d.predictedRipe as number) : 0,
      harvestKg: d.harvestKg ?? 0,
      gradeAKg: d.gradeAKg ?? 0,
      cumKg,
      revenue: d.revenue ?? 0,
      cumRev,
      spot: "spot" in d ? (d.spot as number) : null,
      online: d.online !== false,
      orders: (d.orders ?? {}) as Record<string, number>,
      tasks: (d.tasks ?? {}) as Record<string, number>,
      toolChanges: d.toolChanges ?? 0,
      nStress: "nStress" in d ? (d.nStress as number) : 0,
    };
  });
}
export type CompactDay = ReturnType<typeof compactSeason>[number];

export const fmt = {
  usd: (v: number, d = 0) => `$${v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d })}`,
  usdK: (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `$${(v / 1e3).toFixed(0)}k` : `$${v.toFixed(0)}`),
  num: (v: number, d = 0) => v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }),
  pct: (v: number, d = 0) => `${v.toFixed(d)}%`,
};

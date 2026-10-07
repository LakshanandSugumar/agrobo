// Parity checks: the TypeScript ports must reproduce the Python simulation's numbers.
import assert from "node:assert/strict";
import { test } from "node:test";
import kpis from "../src/data/kpi_summary.json";
import strategy from "../src/data/strategy_report.json";
import { planFarm } from "../src/lib/engine/planner";
import { simulateMarket } from "../src/lib/engine/market";
import { evaluate, suitability, type Parcel } from "../src/lib/engine/strategy";

const close = (a: number, b: number, rel: number, msg: string) =>
  assert.ok(Math.abs(a - b) <= Math.abs(b) * rel, `${msg}: ${a} vs ${b}`);

test("suitability factors match strategy.py for the parcel the sim chose", () => {
  const p = strategy.chosen.parcel as Parcel;
  const { factors } = suitability(p, "tomato");
  for (const [k, v] of Object.entries(strategy.chosen.factors)) {
    close(factors[k as keyof typeof factors], v as number, 0.002, `factor ${k}`);
  }
});

test("economics planner reproduces the 3-seed KPI summary at 1 ha", () => {
  const m = kpis.metrics;
  const twin = planFarm({ areaHa: 1, twin: true });
  const none = planFarm({ areaHa: 1, twin: false });
  close(twin.agrobo.usdPerKg, m["Agrobo OpEx ($/kg)"].twin.mean, 0.02, "twin OpEx/kg");
  close(none.agrobo.usdPerKg, m["Agrobo OpEx ($/kg)"].no_twin.mean, 0.02, "no-twin OpEx/kg");
  close(twin.conventional.usdPerKg, m["Conventional OpEx ($/kg)"].twin.mean, 0.02, "conventional OpEx/kg");
  close(twin.fleet.totalUsdHa, m["Fleet capex ($/ha)"].twin.mean, 0.02, "twin capex/ha");
  close(none.fleet.totalUsdHa, m["Fleet capex ($/ha)"].no_twin.mean, 0.02, "no-twin capex/ha");
});

test("market replay reproduces the logged contract penalties and sells every kg", () => {
  const r = simulateMarket({}, 11, 0.036);
  close(r.penalties, 20.42, 0.01, "contract penalties ($, seed-7 block)");
  close(r.harvestedKg, 1981.1, 0.01, "harvest replayed");
  assert.equal(Math.round(r.spoiledKg), 0);
});

test("land screen is deterministic per seed and respects the crop lock", () => {
  const a = evaluate(40, 2026, "tomato");
  const b = evaluate(40, 2026, "tomato");
  assert.equal(a.chosen?.parcel.parcel_id, b.chosen?.parcel.parcel_id);
  assert.ok(a.ranked.every((r) => r.crop === "tomato"));
  assert.ok(a.ranked.every((r, i) => i === 0 || a.ranked[i - 1].rankKey >= r.rankKey));
});

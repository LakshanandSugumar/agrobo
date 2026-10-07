// Phase 5, B2B algorithmic selling. TypeScript port of simulation/.../core/market.py,
// replayed over the real daily harvest and grade mix from the twin-guided ROS 2 season.
//
// Channels: retail forward contracts (Grade A, committed D+3 from the Field Ledger forecast),
// food-service spot (daily cap), terminal-market wholesale, and processor (Grade C).
// Policy: FEFO, contracts first, then best spot bid; hold stock through price dips while
// shelf life allows. Baseline: no grading, no contracts, field-run sold wholesale same day.
import season from "@/data/season_twin_s7.json";
import { Rng } from "./rng";

export interface MarketConfig {
  contract_price: number;
  contract_penalty: number;
  contract_hedge: number;
  spot_mean: number;
  spot_sigma: number;
  spot_glut_drop: number;
  foodservice_cap_kg_per_ha: number;
  wholesale_discount: number;
  processor_price: number;
  ungraded_discount: number;
  use_forward_contracts: boolean;
}

export const DEFAULT_MARKET: MarketConfig = {
  contract_price: 1.95,
  contract_penalty: 0.5,
  contract_hedge: 0.8,
  spot_mean: 1.6,
  spot_sigma: 0.22,
  spot_glut_drop: 0.35,
  foodservice_cap_kg_per_ha: 1250, // 45 kg/day on the 0.036 ha sim block
  wholesale_discount: 0.82,
  processor_price: 0.22,
  ungraded_discount: 0.88,
  use_forward_contracts: true,
};

type Grade = "A" | "B" | "C";
interface Inv { lot: string; grade: Grade; kg: number; expiry: number }
export type Buyer = "retail_contract" | "foodservice_spot" | "wholesale" | "processor";

const SHELF_LIFE_D = 14;
const SIM_AREA_HA = season.kpis.area_ha;
const mix = season.kpis.kpi_2_harvest_capture_and_quality.grade_mix_kg;
// The sim logs each commitment against its delivery day as hedge x forecast (hedge 0.8)
const SIM_HEDGE = 0.8;
const ledgerForecast = new Map(season.series.filter((d) => d.forwardKg > 0).map((d) => [d.day, d.forwardKg / SIM_HEDGE]));
const B_SHARE_OF_NON_A = mix.B / (mix.B + mix.C + mix.reject);

export function simulateMarket(overrides: Partial<MarketConfig> = {}, seed = 11, areaHa = 1) {
  const c: MarketConfig = { ...DEFAULT_MARKET, ...overrides };
  const rng = new Rng(seed);
  const scale = areaHa / SIM_AREA_HA;
  const days = season.series;
  const lastDay = days[days.length - 1].day;
  const priceCache = new Map<number, number>();
  const spot = (d: number) => {
    if (!priceCache.has(d)) {
      const glut = c.spot_glut_drop * Math.exp(-(((d - 95) / 15) ** 2));
      priceCache.set(d, Math.max(0.6, c.spot_mean - glut + rng.normal(0, c.spot_sigma)));
    }
    return priceCache.get(d)!;
  };
  const harvest = new Map<number, { a: number; b: number; c: number; total: number }>();
  for (const d of days) {
    const total = d.harvestKg * scale;
    const a = d.gradeAKg * scale;
    const rest = Math.max(0, total - a);
    harvest.set(d.day, { a, b: rest * B_SHARE_OF_NON_A, c: rest * (1 - B_SHARE_OF_NON_A), total });
  }
  const online = new Map(days.map((d) => [d.day, d.online !== false]));

  let inv: Inv[] = [];
  const commitments = new Map<number, number>();
  const byBuyer: Record<Buyer, { kg: number; revenue: number }> = {
    retail_contract: { kg: 0, revenue: 0 }, foodservice_spot: { kg: 0, revenue: 0 },
    wholesale: { kg: 0, revenue: 0 }, processor: { kg: 0, revenue: 0 },
  };
  let penalties = 0, spoiled = 0, baseline = 0, revenue = 0;
  const daily: { day: number; spot: number; revenue: number; baseline: number; inventoryKg: number; committedKg: number; online: boolean }[] = [];

  const sell = (i: Inv, kg: number, buyer: Buyer, price: number) => {
    i.kg -= kg;
    byBuyer[buyer].kg += kg;
    byBuyer[buyer].revenue += kg * price;
    return kg * price;
  };

  for (let day = 0; day <= lastDay; day++) {
    let rev = 0;
    const h = harvest.get(day);
    if (h && h.total > 0) {
      (["A", "B", "C"] as Grade[]).forEach((g) => {
        const kg = g === "A" ? h.a : g === "B" ? h.b : h.c;
        if (kg > 1e-9) inv.push({ lot: `d${day}-${g}`, grade: g, kg, expiry: day + SHELF_LIFE_D });
      });
      baseline += h.total * 0.94 * spot(day) * c.wholesale_discount * c.ungraded_discount;
    }
    // Field Ledger D+3 Grade A forecast (replayed from the sim) -> forward contract commitment
    const forecastA = ledgerForecast.get(day + 3) ?? 0;
    if (c.use_forward_contracts && forecastA > 0) {
      commitments.set(day + 3, (commitments.get(day + 3) ?? 0) + c.contract_hedge * forecastA * scale);
    }
    for (const i of inv) if (i.expiry <= day && i.kg > 1e-9) { spoiled += i.kg; i.kg = 0; }
    inv = inv.filter((i) => i.kg > 1e-9).sort((x, y) => x.expiry - y.expiry);
    // 1) contracts
    let need = commitments.get(day) ?? 0;
    const committedKg = need;
    commitments.delete(day);
    for (const i of inv) {
      if (need <= 1e-9) break;
      if (i.grade === "A") {
        const q = Math.min(i.kg, need);
        rev += sell(i, q, "retail_contract", c.contract_price);
        need -= q;
      }
    }
    if (need > 1e-9) { penalties += need * c.contract_penalty; rev -= need * c.contract_penalty; }
    const isOnline = online.get(day) ?? true;
    if (isOnline) {
      const p = spot(day);
      let fsLeft = c.foodservice_cap_kg_per_ha * areaHa;
      for (const i of inv) {
        if (i.kg <= 1e-9) continue;
        if (i.grade === "C") { rev += sell(i, i.kg, "processor", c.processor_price); continue; }
        const shelfLeft = i.expiry - day;
        const cheap = p < c.spot_mean - c.spot_sigma;
        const upcoming = [...commitments.keys()].some((d) => d > day);
        if (i.grade === "A" && shelfLeft > 3 && upcoming) continue; // hold for upcoming contracts
        if (cheap && shelfLeft > 4) continue; // wait out a price dip
        if (fsLeft > 0) {
          const q = Math.min(i.kg, fsLeft);
          rev += sell(i, q, "foodservice_spot", p * (i.grade === "A" ? 1.05 : 0.95));
          fsLeft -= q;
        }
        if (i.kg > 1e-9) rev += sell(i, i.kg, "wholesale", p * c.wholesale_discount);
      }
    }
    inv = inv.filter((i) => i.kg > 1e-9);
    revenue += rev;
    daily.push({ day, spot: spot(day), revenue: rev, baseline: 0, inventoryKg: inv.reduce((s, i) => s + i.kg, 0), committedKg, online: isOnline });
  }
  // cumulative baseline per day for the chart
  let cumBase = 0;
  for (const d of daily) {
    const h = harvest.get(d.day);
    if (h) cumBase += h.total * 0.94 * spot(d.day) * c.wholesale_discount * c.ungraded_discount;
    d.baseline = cumBase;
  }
  const harvested = [...harvest.values()].reduce((s, h) => s + h.total, 0);
  return {
    config: c,
    areaHa,
    harvestedKg: harvested,
    revenue,
    baselineRevenue: baseline,
    upliftPct: (revenue / Math.max(baseline, 1e-6) - 1) * 100,
    revenuePerKg: revenue / Math.max(harvested, 1e-6),
    penalties,
    spoiledKg: spoiled,
    unsoldKg: inv.reduce((s, i) => s + i.kg, 0),
    byBuyer,
    daily,
  };
}

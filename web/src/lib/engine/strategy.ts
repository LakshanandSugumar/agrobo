// Phase 1, Sourcing & Strategy. TypeScript port of
// simulation/ros2_ws/src/agrobo_sim/agrobo_sim/core/strategy.py
// (FAO-style fuzzy land suitability, crop-selection matrix, 5-year NPV).
import { Rng } from "./rng";

export type CropId = "tomato" | "strawberry" | "bell_pepper" | "lettuce";

export interface Crop {
  label: string;
  y: number; // yield t/ha
  p: number; // farm-gate $/kg
  inputs: number; // $/ha/yr
  demand: number;
  labour: number; // h/ha conventional
  auto: number; // automation fit
  ph: [number, number];
  ffd: number; // frost-free days needed
}

export const CROPS: Record<CropId, Crop> = {
  tomato: { label: "Tomato", y: 55, p: 1.35, inputs: 28000, demand: 0.9, labour: 1450, auto: 0.85, ph: [6.0, 6.8], ffd: 150 },
  strawberry: { label: "Strawberry", y: 40, p: 3.2, inputs: 46000, demand: 0.85, labour: 2300, auto: 0.6, ph: [5.5, 6.5], ffd: 140 },
  bell_pepper: { label: "Bell pepper", y: 35, p: 1.5, inputs: 22000, demand: 0.7, labour: 1250, auto: 0.7, ph: [6.0, 7.0], ffd: 160 },
  lettuce: { label: "Lettuce", y: 30, p: 0.95, inputs: 9000, demand: 0.8, labour: 600, auto: 0.9, ph: [6.0, 7.0], ffd: 70 },
};

export interface Parcel {
  parcel_id: string;
  lat: number;
  lon: number;
  area_ha: number;
  ph: number;
  om_pct: number;
  n_ppm: number;
  slope_pct: number;
  drainage: number;
  well_m3_h: number;
  ffd: number;
  km_to_dc: number;
  land_usd_ha: number;
  lte_coverage: number;
}

export type FactorKey = "ph" | "om" | "slope" | "drainage" | "water" | "season" | "logistics" | "connectivity";

export const FACTOR_WEIGHTS: Record<FactorKey, number> = {
  ph: 1.0, om: 0.6, slope: 1.2, drainage: 0.8, water: 1.2, season: 1.0, logistics: 0.7, connectivity: 0.3,
};

export const FACTOR_LABELS: Record<FactorKey, string> = {
  ph: "Soil pH", om: "Organic matter", slope: "Slope (robot-safe)", drainage: "Drainage", water: "Water supply",
  season: "Season length", logistics: "Distance to market", connectivity: "Connectivity",
};

export function tri(x: number, lo: number, optLo: number, optHi: number, hi: number): number {
  if (x <= lo || x >= hi) return 0;
  if (x >= optLo && x <= optHi) return 1;
  return x < optLo ? (x - lo) / (optLo - lo) : (hi - x) / (hi - optHi);
}

export function synthParcels(n: number, seed: number): Parcel[] {
  const rng = new Rng(seed);
  const out: Parcel[] = [];
  for (let i = 0; i < n; i++) {
    out.push({
      parcel_id: `P-${String(seed % 1000).padStart(3, "0")}-${String(i).padStart(3, "0")}`,
      lat: 36 + rng.normal(0, 0.6),
      lon: -120 + rng.normal(0, 0.6),
      area_ha: rng.uniform(8, 120),
      ph: rng.normal(6.6, 0.6),
      om_pct: rng.gamma(4, 0.7),
      n_ppm: rng.normal(28, 8),
      slope_pct: Math.abs(rng.normal(2.5, 2.5)),
      drainage: rng.uniform(0.3, 1.0),
      well_m3_h: rng.gamma(3, 15),
      ffd: rng.normal(205, 25),
      km_to_dc: rng.gamma(3, 25),
      land_usd_ha: rng.normal(32000, 9000),
      lte_coverage: rng.uniform(0.2, 1.0),
    });
  }
  return out;
}

export function suitability(parcel: Parcel, crop: CropId): { score: number; factors: Record<FactorKey, number> } {
  const c = CROPS[crop];
  const [lo, hi] = c.ph;
  const f: Record<FactorKey, number> = {
    ph: tri(parcel.ph, lo - 0.8, lo, hi, hi + 0.8),
    om: tri(parcel.om_pct, 0.5, 2.0, 6.0, 12.0),
    slope: tri(parcel.slope_pct, -1, 0, 3.0, 8.0), // robots: >8 % is a no-go
    drainage: parcel.drainage,
    water: Math.min(1, parcel.well_m3_h / 40),
    season: Math.min(1, parcel.ffd / (c.ffd + 30)),
    logistics: Math.exp(-parcel.km_to_dc / 120),
    connectivity: 0.6 + 0.4 * parcel.lte_coverage, // edge autonomy keeps this soft
  };
  // weighted geometric mean: one zero kills the parcel
  let num = 0, den = 0;
  for (const k of Object.keys(f) as FactorKey[]) {
    num += FACTOR_WEIGHTS[k] * Math.log(Math.max(f[k], 1e-6));
    den += FACTOR_WEIGHTS[k];
  }
  return { score: Math.exp(num / den), factors: f };
}

export function npv(parcel: Parcel, crop: CropId, ha?: number, years = 5, rate = 0.12, robotCapexUsdHa = 38000) {
  const c = CROPS[crop];
  const area = ha ?? parcel.area_ha;
  const capex = area * (robotCapexUsdHa + 3200); // robots + drip/hub infrastructure
  const cash = [-capex];
  for (let t = 1; t <= years; t++) {
    const ramp = Math.min(1, 0.7 + 0.15 * t);
    const rev = area * c.y * 1000 * c.p * ramp * 0.92;
    // 88 % of labour automated; land lease $1,800/ha
    const opex = area * (c.inputs + c.labour * 0.12 * 22 + 4200 + 0.08 * robotCapexUsdHa + 1800);
    cash.push(rev - opex);
  }
  const value = cash.reduce((s, v, i) => s + v / (1 + rate) ** i, 0);
  return { value, cash };
}

export interface RankedOption {
  parcel: Parcel;
  crop: CropId;
  score: number;
  factors: Record<FactorKey, number>;
  npv: number;
  cash: number[];
  rankKey: number;
}

export function evaluate(nCandidates = 40, seed = 2026, cropLock: CropId | null = "tomato") {
  const parcels = synthParcels(nCandidates, seed);
  const ranked: RankedOption[] = [];
  for (const p of parcels) {
    for (const crop of Object.keys(CROPS) as CropId[]) {
      const { score, factors } = suitability(p, crop);
      if (score < 0.35) continue;
      const { value, cash } = npv(p, crop);
      const c = CROPS[crop];
      const marginIdx = c.demand * c.auto * score;
      ranked.push({ parcel: p, crop, score, factors, npv: value, cash, rankKey: (marginIdx * Math.max(value, 0)) / p.area_ha });
    }
  }
  ranked.sort((a, b) => b.rankKey - a.rankKey);
  const pool = cropLock ? ranked.filter((r) => r.crop === cropLock) : ranked;
  return {
    method: "Weighted-geometric FAO suitability × (demand × automation fit) × NPV per ha",
    candidates: nCandidates,
    viableCombinations: ranked.length,
    cropLock,
    parcels,
    ranked: pool.slice(0, 10),
    chosen: pool[0] ?? null,
  };
}

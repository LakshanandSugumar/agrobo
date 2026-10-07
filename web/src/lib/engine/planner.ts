// Farm economics planner: scales the per-hectare activity measured in the ROS 2
// season runs (robot hours, kWh, N, yield, peak UGV workload) to any farm size and
// prices it with the economics model. Twin vs no-twin uses the ablation arms.
import activity from "@/data/activity_per_ha.json";

import { agroboOpex, conventionalOpex, DEFAULT_ASSUMPTIONS, EconAssumptions, fleetCapexPerHa } from "./economics";

const UPLIFT = 0.401; // revenue uplift vs ungraded wholesale, 3-seed mean

export interface PlanInput {
  areaHa: number;
  labourUsdH?: number;
  electricityUsdKwh?: number;
  twin?: boolean;
  seasonsPerYear?: number;
}

export function planFarm(input: PlanInput) {
  const areaHa = Math.min(Math.max(input.areaHa, 0.5), 5000);
  const a: EconAssumptions = {
    ...DEFAULT_ASSUMPTIONS,
    labour_usd_h: input.labourUsdH ?? DEFAULT_ASSUMPTIONS.labour_usd_h,
    electricity_usd_kwh: input.electricityUsdKwh ?? DEFAULT_ASSUMPTIONS.electricity_usd_kwh,
  };
  const act = input.twin === false ? activity.noTwin : activity.twin;
  const harvestedKg = act.yieldKgPerHa * areaHa;
  const fleet = fleetCapexPerHa(a, act.peakUgvHoursPerDayPerHa);
  const agrobo = agroboOpex(
    a, areaHa, act.robotHoursPerHa * areaHa, act.energyKwhPerHa * areaHa, act.nKgPerHa * areaHa,
    act.herbicideLPerHa * areaHa, harvestedKg, fleet.totalUsdHa,
  );
  const conventional = conventionalOpex(a, areaHa, harvestedKg);
  // Revenue per kg is measured in the sim (graded, contract-led selling). The baseline sells
  // ungraded field-run at wholesale the same day; the sim measured a ~40 % uplift over it.
  const agroboRevenue = harvestedKg * act.revenuePerKg;
  const conventionalRevenue = agroboRevenue / (1 + UPLIFT);
  const fleetCapex = fleet.totalUsdHa * areaHa;
  // Payback is deliberately conservative: operating-cost savings only (no revenue uplift),
  // amortisation excluded because it is the capex being paid back.
  const seasonsPerYear = Math.min(Math.max(input.seasonsPerYear ?? 1, 1), 3);
  const cashOpexAgrobo = agrobo.totalUsd - agrobo.lines.fleet_amortisation;
  const annualCashGain = seasonsPerYear * (conventional.totalUsd - cashOpexAgrobo);
  return {
    areaHa,
    twin: input.twin !== false,
    harvestedKg,
    assumptions: a,
    fleet: { ...fleet, totalUsd: fleetCapex, ugvCount: Math.ceil(fleet.ugvPerHa * areaHa) },
    agrobo: { ...agrobo, labourH: a.supervision_h_per_ha_season * areaHa, revenue: agroboRevenue },
    conventional: { ...conventional, revenue: conventionalRevenue },
    opexReductionPct: (1 - agrobo.usdPerKg / conventional.usdPerKg) * 100,
    labourHoursRemoved: conventional.labourH - a.supervision_h_per_ha_season * areaHa,
    herbicideLAvoided: a.conv_herbicide_l_ha * areaHa,
    nitrogenKgAvoided: (a.conv_n_kg_ha - act.nKgPerHa) * areaHa,
    // fleet amortisation is already inside OpEx; payback = capex / (gross margin gain per year)
    seasonsPerYear,
    annualCashGain,
    revenueUplift: agroboRevenue - conventionalRevenue,
    paybackYears: fleetCapex / Math.max(1, annualCashGain),
    source: { seeds: act.seeds, secondsPerFruit: act.secondsPerFruit, gradeAPct: act.gradeAPct },
  };
}

// Season OpEx model: Agrobo fleet vs conventional fresh-market tomato.
// TypeScript port of simulation/.../core/economics.py. Rates are modeled assumptions.
export interface EconAssumptions {
  labour_usd_h: number;
  electricity_usd_kwh: number;
  robot_maint_usd_h: number;
  supervision_h_per_ha_season: number;
  amort_seasons: number;
  ugv_modular_usd: number;
  ugv_hours_per_day: number;
  uav_usd: number;
  uav_ha: number;
  hauler_usd: number;
  hauler_ha: number;
  hub_usd: number;
  hub_ha: number;
  prep_ugv_usd: number;
  prep_ha: number;
  herbicide_usd_l: number;
  n_fert_usd_kg: number;
  conv_harvest_kg_per_h: number;
  conv_weeding_h_ha: number;
  conv_herbicide_l_ha: number;
  conv_n_kg_ha: number;
  conv_other_labour_h_ha: number;
  conv_machinery_usd_ha: number;
}

export const DEFAULT_ASSUMPTIONS: EconAssumptions = {
  labour_usd_h: 22.0,
  electricity_usd_kwh: 0.16,
  robot_maint_usd_h: 1.1,
  supervision_h_per_ha_season: 18.0,
  amort_seasons: 10,
  ugv_modular_usd: 55000,
  ugv_hours_per_day: 18,
  uav_usd: 12000,
  uav_ha: 200,
  hauler_usd: 30000,
  hauler_ha: 8,
  hub_usd: 150000,
  hub_ha: 40,
  prep_ugv_usd: 90000,
  prep_ha: 60,
  herbicide_usd_l: 28,
  n_fert_usd_kg: 2.4,
  conv_harvest_kg_per_h: 85,
  conv_weeding_h_ha: 160,
  conv_herbicide_l_ha: 5.5,
  conv_n_kg_ha: 220,
  conv_other_labour_h_ha: 260,
  conv_machinery_usd_ha: 2600,
};

const round = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;
const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

export function fleetCapexPerHa(a: EconAssumptions, peakUgvHoursPerDayPerHa: number) {
  const ugvPerHa = peakUgvHoursPerDayPerHa / a.ugv_hours_per_day;
  const parts = {
    ugv: ugvPerHa * a.ugv_modular_usd,
    uav: a.uav_usd / a.uav_ha,
    hauler: a.hauler_usd / a.hauler_ha,
    hub: a.hub_usd / a.hub_ha,
    prep: a.prep_ugv_usd / a.prep_ha,
  };
  return { ugvPerHa: round(ugvPerHa, 3), parts, totalUsdHa: sum(parts) };
}

export function agroboOpex(
  a: EconAssumptions,
  areaHa: number,
  robotHours: number,
  energyKwh: number,
  nAppliedKg: number,
  herbicideL: number,
  harvestedKg: number,
  fleetCapexUsdHa: number,
) {
  const lines = {
    energy: energyKwh * a.electricity_usd_kwh,
    maintenance: robotHours * a.robot_maint_usd_h,
    supervision: a.supervision_h_per_ha_season * areaHa * a.labour_usd_h,
    fleet_amortisation: (fleetCapexUsdHa * areaHa) / a.amort_seasons,
    nitrogen: nAppliedKg * a.n_fert_usd_kg,
    herbicide: herbicideL * a.herbicide_usd_l,
  };
  const total = sum(lines);
  return { lines, totalUsd: total, usdPerKg: total / Math.max(harvestedKg, 1e-6) };
}

export function conventionalOpex(a: EconAssumptions, areaHa: number, harvestedKg: number) {
  const labourH = harvestedKg / a.conv_harvest_kg_per_h + (a.conv_weeding_h_ha + a.conv_other_labour_h_ha) * areaHa;
  const lines = {
    labour: labourH * a.labour_usd_h,
    machinery: a.conv_machinery_usd_ha * areaHa,
    nitrogen: a.conv_n_kg_ha * areaHa * a.n_fert_usd_kg,
    herbicide: a.conv_herbicide_l_ha * areaHa * a.herbicide_usd_l,
  };
  const total = sum(lines);
  return { lines, totalUsd: total, labourH, usdPerKg: total / Math.max(harvestedKg, 1e-6) };
}

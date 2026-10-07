import { CROPS, CropId, npv, Parcel, suitability } from "@/lib/engine/strategy";
import { MODELED_NOTE, num, readJson } from "@/lib/http";

// POST /api/land/score  { parcel: {ph, om_pct, slope_pct, ...}, area_ha? }
// Scores one parcel you describe against every crop.
export async function POST(req: Request) {
  const body = await readJson(req);
  const p = (body.parcel ?? {}) as Record<string, unknown>;
  const parcel: Parcel = {
    parcel_id: "CUSTOM",
    lat: num(p.lat, 36.5, -90, 90),
    lon: num(p.lon, -120, -180, 180),
    area_ha: num(p.area_ha, 40, 0.5, 10000),
    ph: num(p.ph, 6.5, 3, 10),
    om_pct: num(p.om_pct, 2.8, 0, 20),
    n_ppm: num(p.n_ppm, 28, 0, 200),
    slope_pct: num(p.slope_pct, 2, 0, 40),
    drainage: num(p.drainage, 0.8, 0, 1),
    well_m3_h: num(p.well_m3_h, 45, 0, 500),
    ffd: num(p.ffd, 200, 0, 365),
    km_to_dc: num(p.km_to_dc, 60, 0, 1000),
    land_usd_ha: num(p.land_usd_ha, 32000, 0, 1e6),
    lte_coverage: num(p.lte_coverage, 0.6, 0, 1),
  };
  const crops = (Object.keys(CROPS) as CropId[]).map((crop) => {
    const s = suitability(parcel, crop);
    const v = npv(parcel, crop);
    return { crop, label: CROPS[crop].label, score: s.score, factors: s.factors, npv: v.value, cash: v.cash, viable: s.score >= 0.35 };
  });
  crops.sort((a, b) => b.score - a.score);
  return Response.json({ parcel, crops, note: MODELED_NOTE });
}

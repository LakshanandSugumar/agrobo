import { CROPS, CropId, evaluate } from "@/lib/engine/strategy";
import { MODELED_NOTE, num, readJson } from "@/lib/http";

// POST /api/land/evaluate  { seed?, candidates?, crop? ("tomato" | ... | "any") }
export async function POST(req: Request) {
  const body = await readJson(req);
  const seed = Math.round(num(body.seed, 2026, 1, 999999));
  const candidates = Math.round(num(body.candidates, 40, 5, 200));
  const crop = typeof body.crop === "string" && body.crop in CROPS ? (body.crop as CropId) : body.crop === "any" ? null : "tomato";
  const r = evaluate(candidates, seed, crop);
  return Response.json({ ...r, note: MODELED_NOTE + " Parcels are synthesised; production uses SoilGrids, USGS 3DEP and county parcel data." });
}

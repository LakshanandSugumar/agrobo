import { planFarm } from "@/lib/engine/planner";
import { MODELED_NOTE, num, readJson } from "@/lib/http";

// POST /api/economics  { areaHa, labourUsdH?, electricityUsdKwh?, twin?, seasonsPerYear? }
export async function POST(req: Request) {
  const body = await readJson(req);
  const plan = planFarm({
    areaHa: num(body.areaHa, 40, 0.5, 5000),
    labourUsdH: num(body.labourUsdH, 22, 5, 80),
    electricityUsdKwh: num(body.electricityUsdKwh, 0.16, 0.02, 1),
    twin: body.twin !== false,
    seasonsPerYear: num(body.seasonsPerYear, 1, 1, 3),
  });
  return Response.json({ ...plan, note: MODELED_NOTE + " Activity per hectare comes from the 3-seed ROS 2 season runs." });
}

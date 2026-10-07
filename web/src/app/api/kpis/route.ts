import kpis from "@/data/kpi_summary.json";

// GET /api/kpis -> 3-seed KPI summary, twin-guided vs ablation
export async function GET() {
  return Response.json({ ...kpis, note: "Mean and sd across seeds 7, 11, 23. Modeled, not field data." });
}

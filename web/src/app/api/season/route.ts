import notwin from "@/data/season_notwin_s7.json";
import twin from "@/data/season_twin_s7.json";

// GET /api/season?arm=twin|notwin  -> day-by-day output of the ROS 2 season run (seed 7)
export async function GET(req: Request) {
  const arm = new URL(req.url).searchParams.get("arm") === "notwin" ? notwin : twin;
  return Response.json(arm);
}

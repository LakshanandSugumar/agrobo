import { DEFAULT_MARKET, simulateMarket } from "@/lib/engine/market";
import { MODELED_NOTE, num, readJson } from "@/lib/http";

// POST /api/market  { seed?, areaHa?, config?: Partial<MarketConfig> }
export async function POST(req: Request) {
  const body = await readJson(req);
  const cfg = (body.config ?? {}) as Record<string, unknown>;
  const d = DEFAULT_MARKET;
  const r = simulateMarket(
    {
      contract_price: num(cfg.contract_price, d.contract_price, 0.5, 5),
      contract_hedge: num(cfg.contract_hedge, d.contract_hedge, 0, 1.2),
      spot_mean: num(cfg.spot_mean, d.spot_mean, 0.5, 5),
      spot_sigma: num(cfg.spot_sigma, d.spot_sigma, 0, 1),
      spot_glut_drop: num(cfg.spot_glut_drop, d.spot_glut_drop, 0, 1.5),
      use_forward_contracts: cfg.use_forward_contracts !== false,
    },
    Math.round(num(body.seed, 11, 1, 999999)),
    num(body.areaHa, 1, 0.1, 5000),
  );
  return Response.json({ ...r, note: MODELED_NOTE + " Harvest volumes, grades and ledger forecasts are replayed from the twin-guided season run (seed 7). Spot prices are drawn per seed and stock is sold through to the last day, so totals differ from the logged run (+40% uplift, 3-seed mean)." });
}

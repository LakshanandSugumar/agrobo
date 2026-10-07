"use client";

import { useEffect, useState } from "react";
import type { simulateMarket } from "@/lib/engine/market";
import { C } from "@/lib/palette";
import { LineChart, StackBar } from "../charts";
import { postJson, Segmented, Slider } from "../Field";
import { Card, Modeled } from "../ui";

type Result = ReturnType<typeof simulateMarket> & { note: string };
const usd = (v: number, d = 0) => `$${v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d })}`;
const BUYER: Record<string, [string, string]> = {
  retail_contract: ["Retail forward contracts", C.agrobo],
  foodservice_spot: ["Food-service spot", C.blue],
  wholesale: ["Terminal wholesale", C.conventional],
  processor: ["Processor (Grade C)", C.purple],
};

export function MarketDesk() {
  const [contractPrice, setContractPrice] = useState(1.95);
  const [hedge, setHedge] = useState(0.8);
  const [spot, setSpot] = useState(1.6);
  const [vol, setVol] = useState(0.22);
  const [glut, setGlut] = useState(0.35);
  const [contracts, setContracts] = useState<"on" | "off">("on");
  const [seed, setSeed] = useState(11);
  const [res, setRes] = useState<Result | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      postJson<Result>("/api/market", {
        seed, areaHa: 1,
        config: { contract_price: contractPrice, contract_hedge: hedge, spot_mean: spot, spot_sigma: vol, spot_glut_drop: glut, use_forward_contracts: contracts === "on" },
      }).then(setRes).catch(() => {});
    }, 120);
    return () => clearTimeout(t);
  }, [contractPrice, hedge, spot, vol, glut, contracts, seed]);

  let cum = 0;
  const cumRev = res?.daily.map((d) => {
    cum += d.revenue;
    return [d.day, cum] as [number, number];
  });

  return (
    <div className="container-x grid gap-6 pb-24 lg:grid-cols-[320px_1fr]">
      <Card className="h-fit space-y-5 p-5 lg:sticky lg:top-32">
        <div className="text-[15px] font-semibold">Market conditions</div>
        <div>
          <div className="mb-2 text-[13px] text-ink-2">Forward contracts from the twin&apos;s forecast</div>
          <Segmented label="Contracts" value={contracts} onChange={setContracts} options={[["on", "On"], ["off", "Off"]]} />
        </div>
        <Slider label="Retail contract price" value={contractPrice} min={1} max={3} step={0.05} onChange={setContractPrice} format={(v) => `${usd(v, 2)}/kg`} />
        <Slider label="Hedge (share of forecast pre-sold)" value={hedge} min={0.2} max={1.1} step={0.05} onChange={setHedge} format={(v) => `${Math.round(v * 100)}%`} />
        <Slider label="Average spot price" value={spot} min={0.8} max={2.6} step={0.05} onChange={setSpot} format={(v) => `${usd(v, 2)}/kg`} />
        <Slider label="Daily price volatility" value={vol} min={0} max={0.6} step={0.01} onChange={setVol} format={(v) => `±${usd(v, 2)}`} />
        <Slider label="Mid-season glut (price drop)" value={glut} min={0} max={1} step={0.05} onChange={setGlut} format={(v) => `−${usd(v, 2)}`} />
        <button onClick={() => setSeed((s) => s + 1)} className="w-full rounded-full border border-line-2 py-2 text-[13px] hover:border-ink">
          Draw new price path (seed {seed})
        </button>
        <p className="text-[12px] leading-relaxed text-muted">{res?.note}</p>
      </Card>

      {res && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Kpi label="Revenue per ha" value={usd(res.revenue)} sub={`${usd(res.revenuePerKg, 2)}/kg`} />
            <Kpi label="vs field-run wholesale" value={`${res.upliftPct >= 0 ? "+" : ""}${res.upliftPct.toFixed(0)}%`} sub={`baseline ${usd(res.baselineRevenue)}`} />
            <Kpi label="Contract shortfall penalties" value={usd(res.penalties)} sub="when the forecast over-promises" />
            <Kpi label="Spoiled" value={`${res.spoiledKg.toFixed(0)} kg`} sub="FEFO, 14-day shelf life" />
          </div>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-semibold">Cumulative revenue per hectare</div>
              <Modeled />
            </div>
            <div className="mt-4">
              <LineChart
                ariaLabel="Cumulative revenue, Agrobo selling engine versus ungraded wholesale baseline"
                series={[
                  { name: "Agrobo selling engine", color: C.agrobo, points: cumRev ?? [], area: true },
                  { name: "Ungraded wholesale, same day", color: C.conventional, points: res.daily.map((d) => [d.day, d.baseline]), dashed: true },
                ]}
                bands={res.daily.filter((d) => !d.online).map((d) => [d.day, d.day] as [number, number])}
                yFormat={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`)}
              />
            </div>
          </Card>
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Where the harvest was sold</div>
              <div className="mt-1 text-[13px] text-muted">{(res.harvestedKg / 1000).toFixed(1)} t per ha, by revenue</div>
              <div className="mt-5">
                <StackBar
                  format={(v) => usd(v)}
                  parts={Object.entries(res.byBuyer).map(([k, v]) => ({ label: BUYER[k][0], value: v.revenue, color: BUYER[k][1] }))}
                />
              </div>
            </Card>
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Spot price the engine traded against</div>
              <div className="mt-3">
                <LineChart
                  height={200}
                  ariaLabel="Daily spot price"
                  yMin={0}
                  series={[{ name: "Spot $/kg", color: C.blue, points: res.daily.map((d) => [d.day, d.spot]) }]}
                  yFormat={(v) => `$${v.toFixed(2)}`}
                />
              </div>
            </Card>
          </div>
          <Card className="p-6">
            <div className="text-[15px] font-semibold">How the engine decides</div>
            <ol className="mt-4 grid gap-4 text-[14px] leading-relaxed text-ink-2 md:grid-cols-4">
              <li><b className="text-ink">1. Pre-sell.</b> Each day the Field Ledger forecasts Grade A volume ripening 3 days out; the hedge share is committed to retail contracts.</li>
              <li><b className="text-ink">2. Deliver.</b> Contracts are filled first-expiring-first-out. Shortfalls pay a penalty, so over-hedging costs money.</li>
              <li><b className="text-ink">3. Route.</b> The rest goes to the best live bid: food-service up to its daily cap, then terminal wholesale. Grade C goes to processors.</li>
              <li><b className="text-ink">4. Wait.</b> When spot falls more than one sigma below normal and shelf life allows, stock is held. Contracts still deliver during outages.</li>
            </ol>
          </Card>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card className="p-4">
      <div className="text-[12px] text-muted">{label}</div>
      <div className="tabular mt-1 text-[24px] font-semibold tracking-tight">{value}</div>
      <div className="mt-0.5 text-[12px] text-muted">{sub}</div>
    </Card>
  );
}

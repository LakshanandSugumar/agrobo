"use client";

import { useCallback, useEffect, useState } from "react";
import type { CropId, FactorKey, Parcel } from "@/lib/engine/strategy";
import { postJson, Segmented, Slider } from "../Field";
import { Card } from "../ui";

const FACTOR_LABELS: Record<FactorKey, string> = {
  ph: "Soil pH", om: "Organic matter", slope: "Slope (robot-safe)", drainage: "Drainage", water: "Water supply",
  season: "Season length", logistics: "Distance to market", connectivity: "Connectivity",
};
const CROP_LABEL: Record<string, string> = { tomato: "Tomato", strawberry: "Strawberry", bell_pepper: "Bell pepper", lettuce: "Lettuce" };

interface Ranked { parcel: Parcel; crop: CropId; score: number; factors: Record<FactorKey, number>; npv: number; cash: number[] }
interface EvalResult { candidates: number; viableCombinations: number; parcels: Parcel[]; ranked: Ranked[]; chosen: Ranked | null; method: string; note: string }
interface ScoreResult { crops: { crop: CropId; label: string; score: number; factors: Record<FactorKey, number>; npv: number; cash: number[]; viable: boolean }[] }

const usdM = (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${(v / 1e3).toFixed(0)}k`);

export function LandScout() {
  const [mode, setMode] = useState<"region" | "parcel">("region");
  return (
    <div className="container-x pb-24">
      <div className="mb-6">
        <Segmented label="Mode" value={mode} onChange={setMode} options={[["region", "Screen a region"], ["parcel", "Score my parcel"]]} />
      </div>
      {mode === "region" ? <Region /> : <MyParcel />}
    </div>
  );
}

function Region() {
  const [seed, setSeed] = useState(2026);
  const [n, setN] = useState(40);
  const [crop, setCrop] = useState<string>("tomato");
  const [res, setRes] = useState<EvalResult | null>(null);
  const [sel, setSel] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = useCallback(async (s: number, count: number, c: string) => {
    setLoading(true);
    setErr(null);
    try {
      setRes(await postJson<EvalResult>("/api/land/evaluate", { seed: s, candidates: count, crop: c }));
      setSel(0);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    let alive = true;
    postJson<EvalResult>("/api/land/evaluate", { seed: 2026, candidates: 40, crop: "tomato" })
      .then((r) => alive && setRes(r))
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  const chosen = res?.ranked[sel];
  const lats = res?.parcels.map((p) => p.lat) ?? [0];
  const lons = res?.parcels.map((p) => p.lon) ?? [0];
  const [la0, la1, lo0, lo1] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const rankedIds = new Map(res?.ranked.map((r, i) => [r.parcel.parcel_id, i]) ?? []);

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <Card className="h-fit p-5">
        <div className="text-[15px] font-semibold">Search</div>
        <div className="mt-5 space-y-5">
          <Slider label="Candidate parcels" value={n} min={10} max={150} step={5} onChange={setN} />
          <label className="block text-[13px]">
            <span className="text-ink-2">Crop</span>
            <select value={crop} onChange={(e) => setCrop(e.target.value)} className="mt-1.5 w-full rounded-lg border border-line-2 bg-card px-3 py-2 text-[14px]">
              <option value="tomato">Tomato</option>
              <option value="strawberry">Strawberry</option>
              <option value="bell_pepper">Bell pepper</option>
              <option value="lettuce">Lettuce</option>
              <option value="any">Best crop per parcel</option>
            </select>
          </label>
          <label className="block text-[13px]">
            <span className="text-ink-2">Region seed</span>
            <div className="mt-1.5 flex gap-2">
              <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="tabular w-full rounded-lg border border-line-2 bg-card px-3 py-2 text-[14px]" />
              <button onClick={() => setSeed(Math.floor(Math.random() * 99999) + 1)} className="rounded-lg border border-line-2 px-3 text-[13px] hover:border-ink" aria-label="Random seed">
                ↻
              </button>
            </div>
          </label>
          <button onClick={() => run(seed, n, crop)} disabled={loading} className="w-full rounded-full bg-ink py-2.5 text-[14px] font-medium text-paper hover:bg-brand-ink disabled:opacity-60">
            {loading ? "Scoring…" : "Run screen"}
          </button>
          {res && (
            <p className="text-[12px] leading-relaxed text-muted">
              {res.viableCombinations} viable parcel-crop pairs out of {res.candidates * 4}. {res.note}
            </p>
          )}
          {err && <p className="text-[13px] text-tomato">{err}</p>}
        </div>
      </Card>

      <div className="space-y-6">
        <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-semibold">Candidate map</div>
              <div className="flex items-center gap-2 text-[11px] text-muted">
                low <span className="h-2 w-16 rounded-full" style={{ background: "linear-gradient(90deg,#dcebe2,#1f7a4d,#0b3d2a)" }} /> high suitability
              </div>
            </div>
            <svg viewBox="0 0 400 300" className="mt-3 w-full rounded-xl bg-[#f3f1ea]" role="img" aria-label="Map of candidate parcels">
              {Array.from({ length: 9 }, (_, i) => (
                <line key={`v${i}`} x1={i * 50} x2={i * 50} y1={0} y2={300} stroke="#e6e3d8" />
              ))}
              {Array.from({ length: 7 }, (_, i) => (
                <line key={`h${i}`} x1={0} x2={400} y1={i * 50} y2={i * 50} stroke="#e6e3d8" />
              ))}
              {res?.parcels.map((p) => {
                const x = 20 + ((p.lon - lo0) / Math.max(1e-6, lo1 - lo0)) * 360;
                const y = 280 - ((p.lat - la0) / Math.max(1e-6, la1 - la0)) * 260;
                const ri = rankedIds.get(p.parcel_id);
                const best = res.ranked.find((r) => r.parcel.parcel_id === p.parcel_id);
                const s = best?.score ?? 0;
                const r = 4 + Math.sqrt(p.area_ha) * 0.8;
                const isSel = ri === sel;
                return (
                  <g key={p.parcel_id} onClick={() => ri !== undefined && setSel(ri)} className={ri !== undefined ? "cursor-pointer" : ""}>
                    <circle cx={x} cy={y} r={r + (isSel ? 4 : 0)} fill={s ? `color-mix(in oklab, #0b3d2a ${Math.round(s * 100)}%, #dcebe2)` : "#d9d6cc"} stroke={isSel ? "#0e1a14" : "#fff"} strokeWidth={isSel ? 2.5 : 1.5}>
                      <title>{`${p.parcel_id} · ${p.area_ha.toFixed(0)} ha${best ? ` · suitability ${best.score.toFixed(2)}` : " · not in top 10"}`}</title>
                    </circle>
                    {ri !== undefined && ri < 3 && (
                      <text x={x} y={y + 3.5} textAnchor="middle" fontSize="10" fontWeight="600" fill="#fff" pointerEvents="none">
                        {ri + 1}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
            <p className="mt-2 text-[12px] text-muted">Circle size is parcel area. Gray parcels are outside the top 10 for this crop. Click a ranked parcel.</p>
          </Card>

          {chosen && (
            <Card className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-[12px] text-muted">#{sel + 1} · {chosen.parcel.parcel_id}</div>
                  <div className="mt-1 text-[22px] font-semibold tracking-tight">
                    {CROP_LABEL[chosen.crop]} · {chosen.parcel.area_ha.toFixed(0)} ha
                  </div>
                </div>
                <div className="text-right">
                  <div className="tabular text-[28px] font-semibold text-brand">{chosen.score.toFixed(2)}</div>
                  <div className="text-[11px] text-muted">suitability</div>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {(Object.keys(chosen.factors) as FactorKey[]).map((k) => (
                  <div key={k} className="grid grid-cols-[130px_1fr_40px] items-center gap-2 text-[12.5px]">
                    <span className="text-ink-2">{FACTOR_LABELS[k]}</span>
                    <div className="h-2 rounded-full bg-[#efede6]">
                      <div className="h-2 rounded-full" style={{ width: `${chosen.factors[k] * 100}%`, background: chosen.factors[k] < 0.5 ? "#c2410c" : "#1f7a4d" }} />
                    </div>
                    <span className="tabular text-right text-ink">{chosen.factors[k].toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-5 border-t border-line pt-4">
                <div className="flex items-baseline justify-between text-[13px]">
                  <span className="text-ink-2">5-year NPV at 12%</span>
                  <span className="tabular text-[18px] font-semibold">{usdM(chosen.npv)}</span>
                </div>
                <CashBars cash={chosen.cash} />
              </div>
            </Card>
          )}
        </div>

        {res && (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-[13.5px]">
                <thead className="bg-[#f3f1ea] text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-3">#</th>
                    <th className="px-4 py-3">Parcel</th>
                    <th className="px-4 py-3">Crop</th>
                    <th className="px-4 py-3 text-right">Area</th>
                    <th className="px-4 py-3 text-right">Suitability</th>
                    <th className="px-4 py-3 text-right">NPV</th>
                    <th className="px-4 py-3 text-right">Land price</th>
                  </tr>
                </thead>
                <tbody>
                  {res.ranked.map((r, i) => (
                    <tr key={r.parcel.parcel_id + r.crop} onClick={() => setSel(i)} className={`cursor-pointer border-t border-line ${i === sel ? "bg-brand-soft" : "hover:bg-[#faf9f5]"}`}>
                      <td className="px-4 py-2.5 text-muted">{i + 1}</td>
                      <td className="px-4 py-2.5 font-mono">{r.parcel.parcel_id}</td>
                      <td className="px-4 py-2.5">{CROP_LABEL[r.crop]}</td>
                      <td className="tabular px-4 py-2.5 text-right">{r.parcel.area_ha.toFixed(0)} ha</td>
                      <td className="tabular px-4 py-2.5 text-right">{r.score.toFixed(3)}</td>
                      <td className="tabular px-4 py-2.5 text-right">{usdM(r.npv)}</td>
                      <td className="tabular px-4 py-2.5 text-right">{usdM(r.parcel.land_usd_ha)}/ha</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function CashBars({ cash }: { cash: number[] }) {
  const m = Math.max(...cash.map(Math.abs));
  return (
    <div className="mt-3">
      <div className="flex h-28 items-center gap-2">
        {cash.map((v, i) => (
          <div key={i} className="flex h-full flex-1 flex-col" title={`Year ${i}: ${usdM(v)}`}>
            <div className="flex flex-1 items-end">
              {v > 0 && <div className="w-full rounded-t" style={{ height: `${(v / m) * 100}%`, background: "#1f7a4d" }} />}
            </div>
            <div className="h-px bg-line-2" />
            <div className="flex flex-1 items-start">
              {v < 0 && <div className="w-full rounded-b" style={{ height: `${(-v / m) * 100}%`, background: "#c2410c" }} />}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-2 text-center text-[11px] text-muted">
        {cash.map((_, i) => (
          <span key={i} className="flex-1">Y{i}</span>
        ))}
      </div>
      <p className="mt-1 text-[11px] text-muted">Year 0 is fleet and infrastructure capex. Ramp to full yield by year 2.</p>
    </div>
  );
}

const PARCEL_DEFAULTS = { area_ha: 40, ph: 6.4, om_pct: 2.8, slope_pct: 2, drainage: 0.8, well_m3_h: 45, ffd: 200, km_to_dc: 60, lte_coverage: 0.6 };

function MyParcel() {
  const [p, setP] = useState(PARCEL_DEFAULTS);
  const [res, setRes] = useState<ScoreResult | null>(null);
  const set = (k: keyof typeof PARCEL_DEFAULTS) => (v: number) => setP((o) => ({ ...o, [k]: v }));
  useEffect(() => {
    const t = setTimeout(() => {
      postJson<ScoreResult>("/api/land/score", { parcel: p }).then(setRes).catch(() => setRes(null));
    }, 150);
    return () => clearTimeout(t);
  }, [p]);
  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <Card className="h-fit space-y-5 p-5">
        <div className="text-[15px] font-semibold">Describe your land</div>
        <Slider label="Area" value={p.area_ha} min={2} max={400} step={1} onChange={set("area_ha")} format={(v) => `${v} ha`} />
        <Slider label="Soil pH" value={p.ph} min={4.5} max={8.5} step={0.1} onChange={set("ph")} format={(v) => v.toFixed(1)} />
        <Slider label="Organic matter" value={p.om_pct} min={0.2} max={12} step={0.1} onChange={set("om_pct")} format={(v) => `${v.toFixed(1)}%`} />
        <Slider label="Slope" value={p.slope_pct} min={0} max={12} step={0.5} onChange={set("slope_pct")} format={(v) => `${v}%`} />
        <Slider label="Drainage class" value={p.drainage} min={0} max={1} step={0.05} onChange={set("drainage")} format={(v) => v.toFixed(2)} />
        <Slider label="Well capacity" value={p.well_m3_h} min={0} max={120} step={1} onChange={set("well_m3_h")} format={(v) => `${v} m³/h`} />
        <Slider label="Frost-free days" value={p.ffd} min={60} max={330} step={5} onChange={set("ffd")} />
        <Slider label="Distance to distribution centre" value={p.km_to_dc} min={0} max={400} step={5} onChange={set("km_to_dc")} format={(v) => `${v} km`} />
        <Slider label="LTE coverage" value={p.lte_coverage} min={0} max={1} step={0.05} onChange={set("lte_coverage")} format={(v) => `${Math.round(v * 100)}%`} />
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {res?.crops.map((c) => (
          <Card key={c.crop} className={`p-5 ${c.viable ? "" : "opacity-70"}`}>
            <div className="flex items-start justify-between">
              <div>
                <div className="text-[18px] font-semibold">{c.label}</div>
                <div className={`mt-1 text-[12px] font-medium ${c.viable ? "text-brand" : "text-tomato"}`}>{c.viable ? "Viable" : "Below viability threshold (0.35)"}</div>
              </div>
              <div className="text-right">
                <div className="tabular text-[26px] font-semibold">{c.score.toFixed(2)}</div>
                <div className="text-[11px] text-muted">suitability</div>
              </div>
            </div>
            <div className="mt-4 space-y-1.5">
              {(Object.keys(c.factors) as FactorKey[]).map((k) => (
                <div key={k} className="grid grid-cols-[120px_1fr_34px] items-center gap-2 text-[12px]">
                  <span className="text-ink-2">{FACTOR_LABELS[k]}</span>
                  <div className="h-1.5 rounded-full bg-[#efede6]">
                    <div className="h-1.5 rounded-full" style={{ width: `${c.factors[k] * 100}%`, background: c.factors[k] < 0.5 ? "#c2410c" : "#1f7a4d" }} />
                  </div>
                  <span className="tabular text-right">{c.factors[k].toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-between border-t border-line pt-3 text-[13px]">
              <span className="text-ink-2">5-year NPV</span>
              <span className="tabular font-semibold">{usdM(c.npv)}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

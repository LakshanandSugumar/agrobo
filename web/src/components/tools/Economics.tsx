"use client";

import { useEffect, useState } from "react";
import type { planFarm } from "@/lib/engine/planner";
import { C } from "@/lib/palette";
import { HBars, StackBar } from "../charts";
import { postJson, Segmented, Slider } from "../Field";
import { Card, Modeled } from "../ui";

type Plan = ReturnType<typeof planFarm> & { note: string };
const usd = (v: number, d = 0) => `$${v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d })}`;
const n0 = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 });
const LINE_LABEL: Record<string, string> = {
  energy: "Energy", maintenance: "Robot maintenance", supervision: "Remote supervision", fleet_amortisation: "Fleet amortisation",
  nitrogen: "Nitrogen", herbicide: "Herbicide", labour: "Labour", machinery: "Machinery",
};

export function Economics() {
  const [acres, setAcres] = useState(100);
  const [labour, setLabour] = useState(22);
  const [power, setPower] = useState(0.16);
  const [twin, setTwin] = useState<"on" | "off">("on");
  const [seasons, setSeasons] = useState<"1" | "2">("1");
  const [plan, setPlan] = useState<Plan | null>(null);
  const areaHa = acres * 0.404686;

  useEffect(() => {
    const t = setTimeout(() => {
      postJson<Plan>("/api/economics", { areaHa, labourUsdH: labour, electricityUsdKwh: power, twin: twin === "on", seasonsPerYear: Number(seasons) }).then(setPlan).catch(() => {});
    }, 120);
    return () => clearTimeout(t);
  }, [areaHa, labour, power, twin, seasons]);

  return (
    <div className="container-x grid gap-6 pb-24 lg:grid-cols-[320px_1fr]">
      <Card className="h-fit space-y-5 p-5 lg:sticky lg:top-32">
        <div className="text-[15px] font-semibold">Your farm</div>
        <Slider label="Planted area" value={acres} min={5} max={2000} step={5} onChange={setAcres} format={(v) => `${n0(v)} ac · ${(v * 0.404686).toFixed(0)} ha`} />
        <Slider label="Farm labour rate" value={labour} min={8} max={45} step={0.5} onChange={setLabour} format={(v) => `${usd(v, 2)}/h`} />
        <Slider label="Electricity" value={power} min={0.05} max={0.45} step={0.01} onChange={setPower} format={(v) => `${usd(v, 2)}/kWh`} />
        <div>
          <div className="mb-2 text-[13px] text-ink-2">Field Ledger twin</div>
          <Segmented label="Twin" value={twin} onChange={setTwin} options={[["on", "On"], ["off", "Off (ablation)"]]} />
        </div>
        <div>
          <div className="mb-2 text-[13px] text-ink-2">Crop cycles per year</div>
          <Segmented label="Seasons per year" value={seasons} onChange={setSeasons} options={[["1", "1"], ["2", "2 (double-crop)"]]} />
        </div>
        <p className="text-[12px] leading-relaxed text-muted">
          Crop: fresh-market tomato. Robot hours, energy, nitrogen, yield and peak fleet workload per hectare come from the
          three ROS 2 season runs and scale with area. {plan?.note}
        </p>
      </Card>

      {plan && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Kpi label="Cost per kg" value={usd(plan.agrobo.usdPerKg, 3)} sub={`vs ${usd(plan.conventional.usdPerKg, 3)} conventional`} />
            <Kpi label="Operating cost cut" value={`${plan.opexReductionPct.toFixed(0)}%`} sub="per kg, per season" />
            <Kpi label="Labour hours removed" value={n0(plan.labourHoursRemoved)} sub="per season" />
            <Kpi label="Fleet payback" value={`${plan.paybackYears.toFixed(1)} yr`} sub="on operating savings alone" />
          </div>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-semibold">Operating cost per kg</div>
              <Modeled />
            </div>
            <div className="mt-5">
              <HBars
                format={(v) => usd(v, 3)}
                rows={[
                  { label: `Agrobo${plan.twin ? " (twin on)" : " (twin off)"}`, value: plan.agrobo.usdPerKg, color: C.agrobo },
                  { label: "Conventional fresh-market farm", value: plan.conventional.usdPerKg, color: C.conventional },
                ]}
              />
            </div>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Where Agrobo&apos;s cost goes</div>
              <div className="mt-1 text-[13px] text-muted">{usd(plan.agrobo.totalUsd)} per season</div>
              <div className="mt-5">
                <Breakdown lines={plan.agrobo.lines} />
              </div>
            </Card>
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Where the conventional cost goes</div>
              <div className="mt-1 text-[13px] text-muted">{usd(plan.conventional.totalUsd)} per season</div>
              <div className="mt-5">
                <Breakdown lines={plan.conventional.lines} />
              </div>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Fleet you&apos;d need</div>
              <div className="mt-1 text-[13px] text-muted">Sized for the simulated peak 7-day harvest workload, 18 h/day per robot.</div>
              <div className="mt-5 grid grid-cols-2 gap-4">
                <Big v={n0(plan.fleet.ugvCount)} k="Modular UGVs" />
                <Big v={n0(Math.max(1, Math.ceil(plan.areaHa / plan.assumptions.uav_ha)))} k="Scout drones" />
                <Big v={n0(Math.max(1, Math.ceil(plan.areaHa / plan.assumptions.hauler_ha)))} k="Haulers" />
                <Big v={n0(Math.max(1, Math.ceil(plan.areaHa / plan.assumptions.hub_ha)))} k="Grading + cold hubs" />
              </div>
              <div className="mt-5 flex justify-between border-t border-line pt-4 text-[14px]">
                <span className="text-ink-2">Fleet capex</span>
                <span className="tabular font-semibold">{usd(plan.fleet.totalUsd)} · {usd(plan.fleet.totalUsdHa)}/ha</span>
              </div>
            </Card>
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Chemicals avoided per season</div>
              <div className="mt-5 space-y-4">
                <Big v={`${n0(plan.herbicideLAvoided)} L`} k="Herbicide (laser weeding)" />
                <Big v={`${n0(plan.nitrogenKgAvoided)} kg`} k="Nitrogen (per-plant micro-dosing)" />
                <Big v={`${n0(plan.harvestedKg / 1000)} t`} k={`Harvest at ${(plan.harvestedKg / plan.areaHa / 1000).toFixed(1)} t/ha`} />
                <Big v={usd(plan.revenueUplift)} k="Extra revenue from graded, contract-led selling (not in payback)" />
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card className="p-4">
      <div className="text-[12px] text-muted">{label}</div>
      <div className="tabular mt-1 text-[26px] font-semibold tracking-tight">{value}</div>
      <div className="mt-0.5 text-[12px] text-muted">{sub}</div>
    </Card>
  );
}

function Big({ v, k }: { v: string; k: string }) {
  return (
    <div>
      <div className="tabular text-[24px] font-semibold tracking-tight">{v}</div>
      <div className="text-[12.5px] text-muted">{k}</div>
    </div>
  );
}

// colour follows the cost line, never its rank
const LINE_COLOR: Record<string, string> = {
  fleet_amortisation: C.agrobo, labour: C.conventional, maintenance: C.blue, machinery: C.blue,
  supervision: C.purple, energy: "#8a948f", nitrogen: "#b9b5a8", herbicide: "#5b6660",
};
function Breakdown({ lines }: { lines: Record<string, number> }) {
  const parts = Object.entries(lines)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({ label: LINE_LABEL[k] ?? k, value: v, color: LINE_COLOR[k] ?? "#ccc" }));
  return <StackBar parts={parts} format={(v) => usd(v)} />;
}

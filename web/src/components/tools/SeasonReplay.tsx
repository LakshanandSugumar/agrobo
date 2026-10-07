"use client";

import { useEffect, useState } from "react";
import type { CompactDay } from "@/lib/data";
import { C } from "@/lib/palette";
import { LineChart } from "../charts";
import { Segmented } from "../Field";
import { Card, Modeled } from "../ui";

const TASKS: [string, string, string][] = [
  ["scouting", "Scouting (UAV)", C.blue],
  ["weeding", "Laser weeding", C.agrobo],
  ["dosing", "N micro-dosing", C.purple],
  ["harvesting", "Harvesting", C.conventional],
  ["hauling", "Hauling", "#8a948f"],
];

export function SeasonReplay({ twin, notwin, bt, phases }: { twin: CompactDay[]; notwin: CompactDay[]; bt: string; phases: Record<string, unknown>[] }) {
  const [arm, setArm] = useState<"twin" | "notwin">("twin");
  const [day, setDay] = useState(70);
  const [playing, setPlaying] = useState(false);
  const days = arm === "twin" ? twin : notwin;
  const d = days.find((x) => x.day === day) ?? days[days.length - 1];
  const last = days[days.length - 1].day;

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setDay((v) => (v >= last ? 1 : v + 1)), 350);
    return () => clearInterval(t);
  }, [playing, last]);

  const outages = days.filter((x) => !x.online).map((x) => [x.day, x.day] as [number, number]);
  const upTo = (f: (x: CompactDay) => number) => days.filter((x) => x.day <= day).map((x) => [x.day, f(x)] as [number, number]);
  const robotH = (x: CompactDay) => Object.values(x.tasks).reduce((s, v) => s + v, 0);
  const dom: [number, number] = [0, last];
  const maxOf = (f: (x: CompactDay) => number) => Math.max(...twin.map(f), ...notwin.map(f));

  return (
    <div className="container-x space-y-6 pb-24">
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Segmented label="Arm" value={arm} onChange={setArm} options={[["twin", "Twin-guided"], ["notwin", "No twin (ablation)"]]} />
          <div className="flex items-center gap-3">
            <button onClick={() => setPlaying((p) => !p)} className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-paper hover:bg-brand-ink">
              {playing ? "Pause" : "Play season"}
            </button>
            <Modeled />
          </div>
        </div>
        <div className="mt-5 flex items-center gap-4">
          <span className="tabular w-20 text-[13px] text-muted">Day {day}</span>
          <input type="range" min={1} max={last} value={day} onChange={(e) => { setPlaying(false); setDay(Number(e.target.value)); }} className="w-full" aria-label="Season day" />
          <span className="tabular w-10 text-right text-[13px] text-muted">{last}</span>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-5">
        <Tile k="Temperature" v={d.tempC !== null ? `${d.tempC.toFixed(1)} °C` : "–"} />
        <Tile k="Fruit tracked" v={d.fruitOnPlants.toLocaleString()} />
        <Tile k="Ripe on plants" v={d.ripeOnPlants.toLocaleString()} />
        <Tile k="Live weeds" v={String(d.liveWeeds)} />
        <Tile k="Cloud link" v={d.online ? "Online" : "Edge-only"} warn={!d.online} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="text-[15px] font-semibold">Harvest, cumulative kg</div>
            <div className="mt-4">
              <LineChart
                ariaLabel="Cumulative harvest to the selected day"
                series={[
                  { name: arm === "twin" ? "Twin-guided" : "No twin", color: arm === "twin" ? C.agrobo : C.conventional, points: upTo((x) => x.cumKg), area: true },
                ]}
                bands={outages.filter(([a]) => a <= day)}
                xDomain={dom}
                yMaxFixed={maxOf((x) => x.cumKg)}
                yFormat={(v) => `${v.toFixed(0)} kg`}
              />
            </div>
          </Card>
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Live weeds in the block</div>
              <div className="mt-3">
                <LineChart height={200} xDomain={dom} yMaxFixed={maxOf((x) => x.liveWeeds)} ariaLabel="Live weeds per day" series={[{ name: "Live weeds", color: C.agrobo, points: upTo((x) => x.liveWeeds) }]} yFormat={(v) => v.toFixed(0)} />
              </div>
              <p className="mt-2 text-[12px] text-muted">Laser weeding holds pressure down with zero herbicide. No weed reached seed.</p>
            </Card>
            <Card className="p-6">
              <div className="text-[15px] font-semibold">Robot hours per day</div>
              <div className="mt-3">
                <LineChart height={200} xDomain={dom} yMaxFixed={maxOf(robotH)} ariaLabel="Robot hours per day" series={[{ name: "Robot hours", color: C.blue, points: upTo(robotH) }]} yFormat={(v) => v.toFixed(2)} />
              </div>
              <p className="mt-2 text-[12px] text-muted">All robots on a 0.036 ha block. Harvest drives the peak, which sizes the fleet.</p>
            </Card>
          </div>
        </div>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="text-[15px] font-semibold">Day {d.day} work orders</div>
            <div className="mt-3 space-y-2 text-[13.5px]">
              {Object.keys(d.orders).length === 0 && <div className="text-muted">No field orders today.</div>}
              {Object.entries(d.orders).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="capitalize text-ink-2">{k}</span>
                  <span className="tabular font-medium">{v} targets</span>
                </div>
              ))}
              <div className="flex justify-between border-t border-line pt-2">
                <span className="text-ink-2">Fruit forecast ripe (twin)</span>
                <span className="tabular font-medium">{d.predictedRipe}</span>
              </div>
            </div>
            <div className="mt-5 text-[13px] font-medium">Robot time</div>
            <div className="mt-2 space-y-1.5 text-[13px]">
              {TASKS.filter(([k]) => d.tasks[k]).map(([k, label, color]) => (
                <div key={k} className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-ink-2"><span className="h-2 w-2 rounded-full" style={{ background: color }} />{label}</span>
                  <span className="tabular">{d.tasks[k] * 60 < 1 ? "<1" : (d.tasks[k] * 60).toFixed(0)} min</span>
                </div>
              ))}
              {TASKS.every(([k]) => !d.tasks[k]) && <div className="text-muted">Fleet idle or charging.</div>}
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4 text-[13px]">
              <div><div className="text-muted">Harvested</div><div className="tabular font-medium">{d.harvestKg.toFixed(1)} kg</div></div>
              <div><div className="text-muted">Grade A</div><div className="tabular font-medium">{d.harvestKg ? ((d.gradeAKg / d.harvestKg) * 100).toFixed(0) : 0}%</div></div>
              <div><div className="text-muted">Sold today</div><div className="tabular font-medium">${d.revenue.toFixed(2)}</div></div>
              <div><div className="text-muted">Spot price</div><div className="tabular font-medium">{d.spot ? `$${d.spot.toFixed(2)}/kg` : "–"}</div></div>
            </div>
          </Card>
          <Card className="p-5">
            <div className="text-[15px] font-semibold">Before day 1</div>
            <ol className="mt-3 space-y-2 text-[13px] text-ink-2">
              {phases.map((p, i) => (
                <li key={i}>
                  <span className="font-medium capitalize text-ink">{String(p.phase)}:</span>{" "}
                  {p.phase === "sourcing" && `parcel ${p.parcel} chosen for ${p.crop}, suitability ${Number(p.suitability).toFixed(2)}`}
                  {p.phase === "prep" && `${Number(p.duration_h).toFixed(1)} robot-hours, ${Number(p.distance_m).toFixed(0)} m driven`}
                  {p.phase === "establish" && `${p.planted} plugs transplanted in ${(Number(p.duration_h) * 60).toFixed(0)} min`}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>

      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-[15px] font-semibold">The behaviour tree that ran this season</div>
          <span className="font-mono text-[12px] text-muted">/mission_orchestrator · py_trees</span>
        </div>
        <pre className="mt-4 max-h-[420px] overflow-auto rounded-xl bg-night p-4 font-mono text-[12px] leading-relaxed text-[#c9d3cd]">{bt}</pre>
      </Card>
    </div>
  );
}

function Tile({ k, v, warn }: { k: string; v: string; warn?: boolean }) {
  return (
    <Card className="p-4">
      <div className="text-[12px] text-muted">{k}</div>
      <div className={`tabular mt-1 text-[20px] font-semibold ${warn ? "text-tomato" : ""}`}>{v}</div>
    </Card>
  );
}

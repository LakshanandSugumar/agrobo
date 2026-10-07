"use client";

import { useEffect, useMemo, useState } from "react";
import type { CompactDay } from "@/lib/data";

const TASK_LABEL: Record<string, string> = {
  scouting: "UAV scouting pass",
  harvesting: "Predict-then-pick harvest",
  weeding: "Laser weeding, per-weed targets",
  dosing: "Per-plant nitrogen micro-dose",
  hauling: "Bins hauled to cold hub",
  prep: "Field prep and drip layout",
  transplant: "Transplanting 480 plugs",
};

/** Replays the logged twin-guided ROS 2 season (seed 7) one day at a time. */
export function LedgerConsole({ days }: { days: CompactDay[] }) {
  const [i, setI] = useState(78);
  const [playing, setPlaying] = useState(true);
  useEffect(() => {
    if (!playing) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const t = setInterval(() => setI((v) => (v + 1 >= days.length ? 40 : v + 1)), 900);
    return () => clearInterval(t);
  }, [playing, days.length]);
  const d = days[i];
  const recent = useMemo(() => {
    const out: { day: number; text: string }[] = [];
    for (let k = i; k >= 0 && out.length < 5; k--) {
      const x = days[k];
      for (const task of Object.keys(x.tasks)) out.push({ day: x.day, text: TASK_LABEL[task] ?? task });
      if (!x.online) out.push({ day: x.day, text: "Cloud link down. Running edge-only" });
    }
    return out.slice(0, 5);
  }, [i, days]);
  const spark = days.slice(Math.max(0, i - 40), i + 1);
  const maxKg = Math.max(1, ...days.map((x) => x.harvestKg));

  return (
    <div className="rounded-2xl border border-night-line bg-night-2/90 p-4 font-mono text-[12px] text-[#c9d3cd] shadow-2xl shadow-black/40 backdrop-blur md:p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${d.online ? "bg-lime pulse-dot" : "bg-[#f59e6b]"}`} />
          <span className="text-white">field_ledger</span>
          <span className="text-[#6f8479]">/ block A · tomato · 480 plants</span>
        </div>
        <button
          onClick={() => setPlaying((p) => !p)}
          className="rounded border border-night-line px-2 py-0.5 text-[11px] text-[#a9b8b0] hover:text-white"
          aria-label={playing ? "Pause replay" : "Play replay"}
        >
          {playing ? "pause" : "play"}
        </button>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Cell k="season day" v={`${d.day} / 125`} />
        <Cell k="fruit tracked" v={d.fruitOnPlants.toLocaleString()} />
        <Cell k="ripe forecast" v={d.predictedRipe.toLocaleString()} accent />
        <Cell k="harvested" v={`${d.cumKg.toFixed(0)} kg`} />
      </div>
      <div className="mt-4">
        <div className="mb-1 flex justify-between text-[11px] text-[#6f8479]">
          <span>daily harvest, kg</span>
          <span>{d.harvestKg.toFixed(1)} kg today</span>
        </div>
        <svg viewBox="0 0 410 48" className="h-12 w-full" aria-hidden>
          {spark.map((x, k) => (
            <rect
              key={x.day}
              x={k * 10}
              y={48 - (x.harvestKg / maxKg) * 46}
              width="7"
              height={Math.max(1, (x.harvestKg / maxKg) * 46)}
              rx="1.5"
              fill={x.online ? "#d7f36b" : "#f59e6b"}
              opacity={k === spark.length - 1 ? 1 : 0.55}
            />
          ))}
        </svg>
      </div>
      <div className="mt-3 space-y-1.5 border-t border-night-line pt-3">
        {recent.map((r, k) => (
          <div key={k} className="flex gap-3">
            <span className="text-[#6f8479]">d{String(r.day).padStart(3, "0")}</span>
            <span className={k === 0 ? "text-white" : ""}>{r.text}</span>
          </div>
        ))}
        {recent.length === 0 && <div className="text-[#6f8479]">waiting for first work order…</div>}
      </div>
      <input
        type="range"
        min={1}
        max={days.length - 1}
        value={i}
        onChange={(e) => {
          setPlaying(false);
          setI(Number(e.target.value));
        }}
        className="mt-4 w-full"
        aria-label="Season day"
      />
      <div className="mt-1 text-[10px] text-[#6f8479]">Replay of a logged ROS 2 season run. Simulated, not field data.</div>
    </div>
  );
}

function Cell({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <div className="rounded-lg border border-night-line bg-night/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-[#6f8479]">{k}</div>
      <div className={`tabular mt-0.5 text-[16px] ${accent ? "text-lime" : "text-white"}`}>{v}</div>
    </div>
  );
}

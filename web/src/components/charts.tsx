"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

export interface Series {
  name: string;
  color: string;
  points: [number, number][];
  dashed?: boolean;
  area?: boolean;
}

const fmtDefault = (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(v < 10 ? 2 : 0));

function niceMax(v: number) {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}

export interface YSpec {
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export function LineChart({
  series, height = 260, xLabel = "Day", yFormat, y, bands = [], yMin = 0, ariaLabel, xDomain, yMaxFixed,
}: {
  /** fixed axes, e.g. so a replay keeps the full-season frame while it draws */
  xDomain?: [number, number];
  yMaxFixed?: number;
  series: Series[]; height?: number; xLabel?: string;
  /** client callers only; server components pass the serializable `y` spec */
  yFormat?: (v: number) => string;
  y?: YSpec;
  bands?: [number, number][]; yMin?: number; ariaLabel: string;
}) {
  const fmtY = yFormat ?? (y ? (v: number) => `${y.prefix ?? ""}${v.toLocaleString("en-US", { maximumFractionDigits: y.decimals ?? 0, minimumFractionDigits: y.decimals ?? 0 })}${y.suffix ?? ""}` : fmtDefault);
  const ref = useRef<SVGSVGElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  // draw in real pixels so text stays 11px however wide the card is
  const [W, setW] = useState(720);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const gid = useId().replace(/:/g, "");
  const H = W < 500 ? Math.round(height * 0.85) : height, L = 52, R = 16, T = 14, B = 34;
  const { xMin, xMax, yMax, xs } = useMemo(() => {
    const all = series.flatMap((s) => s.points);
    const xsSet = Array.from(new Set(all.map((p) => p[0]))).sort((a, b) => a - b);
    return {
      xMin: xDomain ? xDomain[0] : Math.min(...all.map((p) => p[0])),
      xMax: xDomain ? xDomain[1] : Math.max(...all.map((p) => p[0])),
      yMax: niceMax(yMaxFixed ?? Math.max(...all.map((p) => p[1]))),
      xs: xsSet,
    };
  }, [series, xDomain, yMaxFixed]);
  const sx = (x: number) => L + ((x - xMin) / Math.max(1e-9, xMax - xMin)) * (W - L - R);
  const sy = (y: number) => T + (1 - (y - yMin) / Math.max(1e-9, yMax - yMin)) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => yMin + f * (yMax - yMin));
  const nX = W < 500 ? 3 : 5;
  const xTicks = Array.from({ length: nX + 1 }, (_, i) => Math.round(xMin + (i / nX) * (xMax - xMin)));

  const onMove = (e: React.PointerEvent) => {
    const svg = ref.current;
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * W;
    const xv = xMin + ((x - L) / (W - L - R)) * (xMax - xMin);
    let best = xs[0];
    for (const v of xs) if (Math.abs(v - xv) < Math.abs(best - xv)) best = v;
    setHover(best);
  };

  const hoverVals = hover === null ? [] : series.map((s) => ({ s, p: s.points.find((p) => p[0] === hover) }));
  const tipLeft = hover === null ? 0 : (sx(hover) / W) * 100;

  return (
    <div className="relative" ref={box}>
      <svg
        ref={ref}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full touch-none select-none"
        role="img"
        aria-label={ariaLabel}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
      >
        <defs>
          {series.map((s, i) => (
            <linearGradient key={i} id={`${gid}-g${i}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={s.color} stopOpacity="0.18" />
              <stop offset="1" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>
        {bands.map(([a, b], i) => (
          <rect key={i} x={sx(a - 0.5)} y={T} width={Math.max(2, sx(b + 0.5) - sx(a - 0.5))} height={H - T - B} fill="#c2410c" opacity="0.07" />
        ))}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} stroke="#e2e0d6" strokeWidth="1" />
            <text x={L - 8} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="#66716b" className="tabular">
              {fmtY(t)}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={t} x={sx(t)} y={H - 12} textAnchor="middle" fontSize="11" fill="#66716b" className="tabular">
            {t}
          </text>
        ))}
        <text x={W - R} y={H - 0} textAnchor="end" fontSize="10" fill="#66716b">
          {xLabel}
        </text>
        {series.map((s, i) => {
          const d = s.points.map((p, j) => `${j ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
          return (
            <g key={s.name}>
              {s.area && s.points.length > 1 && (
                <path d={`${d}L${sx(s.points[s.points.length - 1][0])},${sy(yMin)}L${sx(s.points[0][0])},${sy(yMin)}Z`} fill={`url(#${gid}-g${i})`} />
              )}
              <path d={d} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dashed ? "5 4" : undefined} strokeLinejoin="round" />
            </g>
          );
        })}
        {hover !== null && (
          <g>
            <line x1={sx(hover)} x2={sx(hover)} y1={T} y2={H - B} stroke="#0e1a14" strokeOpacity="0.25" />
            {hoverVals.map(({ s, p }) =>
              p ? <circle key={s.name} cx={sx(p[0])} cy={sy(p[1])} r="4.5" fill={s.color} stroke="#fff" strokeWidth="2" /> : null,
            )}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div
          className="pointer-events-none absolute top-2 z-10 min-w-[150px] rounded-lg border border-line bg-card px-3 py-2 text-[12px] shadow-lg"
          style={{ left: `${tipLeft}%`, transform: `translateX(${tipLeft > 60 ? "-105%" : "8%"})` }}
        >
          <div className="mb-1 font-medium text-ink">
            {xLabel} {hover}
          </div>
          {hoverVals.map(({ s, p }) => (
            <div key={s.name} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-ink-2">
                <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                {s.name}
              </span>
              <span className="tabular font-medium text-ink">{p ? fmtY(p[1]) : "–"}</span>
            </div>
          ))}
        </div>
      )}
      {series.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-4 text-[12px] text-ink-2">
          {series.map((s) => (
            <span key={s.name} className="flex items-center gap-1.5">
              <svg width="18" height="6" aria-hidden>
                <line x1="0" x2="18" y1="3" y2="3" stroke={s.color} strokeWidth="2" strokeDasharray={s.dashed ? "4 3" : undefined} />
              </svg>
              {s.name}
            </span>
          ))}
          {bands.length > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm bg-tomato/15" /> Cloud outage (ran on edge)
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export interface BarRow {
  label: string;
  value: number;
  color: string;
  note?: string;
  /** pre-formatted value, for server callers that cannot pass `format` */
  display?: string;
}

/** Horizontal bars with direct value labels. One measure, one scale. */
export function HBars({ rows, format, max }: { rows: BarRow[]; format?: (v: number) => string; max?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const m = max ?? Math.max(...rows.map((r) => r.value)) * 1.08;
  return (
    <div className="space-y-3">
      {rows.map((r, i) => (
        <div key={r.label} onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
          <div className="mb-1 flex items-baseline justify-between text-[13px]">
            <span className="text-ink-2">{r.label}</span>
            <span className="tabular font-semibold text-ink">{r.display ?? (format ? format(r.value) : r.value)}</span>
          </div>
          <div className="h-3 w-full rounded-full bg-[#efede6]">
            <div
              className="h-3 rounded-full transition-[width] duration-500"
              style={{ width: `${Math.max(1, (r.value / m) * 100)}%`, background: r.color, opacity: hover === null || hover === i ? 1 : 0.55 }}
            />
          </div>
          {r.note && <div className="mt-1 text-[12px] text-muted">{r.note}</div>}
        </div>
      ))}
    </div>
  );
}

/** Stacked composition bar (e.g. sales channels), 2px gaps between segments. */
export function StackBar({ parts, format }: { parts: { label: string; value: number; color: string }[]; format: (v: number) => string }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  return (
    <div>
      <div className="flex h-4 w-full gap-[2px] overflow-hidden rounded-full">
        {parts.filter((p) => p.value > 0).map((p) => (
          <div key={p.label} title={`${p.label}: ${format(p.value)}`} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <div className="mt-3 grid gap-y-1.5 text-[13px]">
        {parts.map((p) => (
          <div key={p.label} className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-ink-2">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
              {p.label}
            </span>
            <span className="tabular text-ink">{format(p.value)} · {((p.value / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

import { BOM_LINES, ratio, usd } from "@/lib/data";

// Horizontal bars: imported vs US-sourced extended cost per robot, for lines that have a US source.
export function GapBars({ dark = false }: { dark?: boolean }) {
  const rows = BOM_LINES.filter((l) => l.usUnit != null)
    .map((l) => ({ l, a: l.importUnit * l.qty, b: (l.usUnit as number) * l.qty }))
    .sort((x, y) => y.b - x.b)
    .slice(0, 6);
  const max = Math.max(...rows.map((r) => r.b));
  const sub = dark ? "text-[#8b9aab]" : "text-muted";
  return (
    <div className="space-y-5">
      <div className={`flex flex-wrap gap-4 text-[12px] ${sub}`}>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#8b9aab]" />Imported (rev A.1)</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-signal" />US-sourced (rev B)</span>
      </div>
      {rows.map(({ l, a, b }) => (
        <div key={l.part}>
          <div className="flex items-baseline justify-between gap-3 text-[14px]">
            <span className={dark ? "text-white" : "text-ink"}>
              {l.part}{l.qty > 1 ? ` ×${l.qty}` : ""}
            </span>
            <span className={`tabular font-mono text-[13px] ${sub}`}>
              {usd(a)} → <span className={dark ? "text-white" : "text-ink"}>{usd(b)}</span>{" "}
              <span className="text-signal">{ratio(l)!.toFixed(1)}×</span>
            </span>
          </div>
          <div className="mt-1.5 space-y-1">
            <div className="h-2 rounded-sm bg-[#8b9aab]" style={{ width: `${Math.max(0.8, (a / max) * 100)}%` }} />
            <div className="h-2 rounded-sm bg-signal" style={{ width: `${(b / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

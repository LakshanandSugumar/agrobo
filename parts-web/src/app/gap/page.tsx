import type { Metadata } from "next";
import { GapBars } from "@/components/GapBars";
import { Card, Estimate, SectionHead } from "@/components/ui";
import { BOM_LINES, ROBOT, premiumPct, ratio, usd } from "@/lib/data";

export const metadata: Metadata = {
  title: "The cost gap",
  description: "Line by line: what an imported vs a US-sourced field robot costs, from a real harvester bill of materials.",
};

export default function Gap() {
  const shares = [
    { k: "Assembled in the US from imported subparts", v: ROBOT.shareUsAssembled, c: "bg-steel" },
    { k: "US-made, or US maker with origin to confirm", v: ROBOT.shareUsLikely, c: "bg-signal" },
    { k: "No US source today", v: ROBOT.shareNoUsSource, c: "bg-[#8b9aab]" },
  ];
  return (
    <>
      <section className="border-b border-line py-16 md:py-20">
        <div className="container-x">
          <SectionHead eyebrow="The cost gap" title={`A US-sourced field robot costs ${premiumPct(ROBOT.importBuilt, ROBOT.usBuilt)}% more. Here is where.`}>
            From the Agrobo harvester bill of materials, priced twice in November 2026: rev A.1 with the cheapest parts, and rev B with a
            US-made or US-assembled part wherever one exists. Prices are list prices, quotes and estimates at pilot quantity.
          </SectionHead>
          <div className="mt-6"><Estimate /></div>
        </div>
      </section>

      <section className="py-14 md:py-16">
        <div className="container-x">
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-[14px]">
              <thead className="border-b border-line text-[12px] uppercase tracking-[0.04em] text-muted">
                <tr>
                  <th className="px-5 py-3 font-medium">Part</th>
                  <th className="px-5 py-3 font-medium">Imported</th>
                  <th className="px-5 py-3 text-right font-medium">Unit</th>
                  <th className="px-5 py-3 font-medium">US option</th>
                  <th className="px-5 py-3 text-right font-medium">Unit</th>
                  <th className="px-5 py-3 text-right font-medium">Gap</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {BOM_LINES.map((l) => {
                  const r = ratio(l);
                  return (
                    <tr key={l.part} className="border-b border-line last:border-0">
                      <td className="px-5 py-3 font-medium">{l.part}{l.qty > 1 ? ` ×${l.qty}` : ""}</td>
                      <td className="px-5 py-3 text-ink-2">{l.importSrc}</td>
                      <td className="px-5 py-3 text-right">${l.importUnit.toLocaleString("en-US")}</td>
                      <td className={`px-5 py-3 ${l.usUnit == null ? "font-medium text-signal" : "text-ink-2"}`}>{l.usSrc}</td>
                      <td className="px-5 py-3 text-right">{l.usUnit == null ? "–" : `$${l.usUnit.toLocaleString("en-US")}`}</td>
                      <td className="px-5 py-3 text-right font-medium">{r == null ? "none" : `${r.toFixed(1)}×`}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
          <p className="mt-3 text-[13px] text-muted">Selected lines. Frames, plates, printed parts, totes, pumps and wiring were already US-made at almost the same price.</p>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <Card className="p-6 md:p-8">
              <div className="mb-6 text-[15px] font-medium">Biggest lines per robot</div>
              <GapBars />
            </Card>
            <Card className="p-6 md:p-8">
              <div className="text-[15px] font-medium">US-sourced robot, by origin of value</div>
              <div className="mt-6 flex h-4 overflow-hidden rounded-full">
                {shares.map((s) => <div key={s.k} className={s.c} style={{ width: `${s.v * 100}%` }} />)}
              </div>
              <ul className="mt-6 space-y-3 text-[14px]">
                {shares.map((s) => (
                  <li key={s.k} className="flex items-center justify-between gap-4">
                    <span className="flex items-center gap-2 text-ink-2"><span className={`h-2.5 w-2.5 shrink-0 rounded-sm ${s.c}`} />{s.k}</span>
                    <span className="tabular font-medium">{(s.v * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
              <p className="mt-6 border-t border-line pt-4 text-[14px] leading-relaxed text-ink-2">
                Even with every swap, this robot can be labelled “Assembled in USA” but not “Made in USA”. More than half its value is US
                assembly of imported subparts, mostly the arms. A US-made joint is what changes that.
              </p>
              <div className="mt-4 text-[14px] text-muted">Per robot, built: {usd(ROBOT.importBuilt)} imported, {usd(ROBOT.usBuilt)} US-sourced.</div>
            </Card>
          </div>
        </div>
      </section>
    </>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { PageHead } from "@/components/PageHead";
import { Card } from "@/components/ui";

export const metadata: Metadata = { title: "Platform" };

const TOOLS = [
  ["/platform/land", "Land Scout", "Phase 1", "Screen a region of candidate parcels or score your own. See every factor, the crop ranking and a 5-year NPV.", "strategy.py → /api/land/*"],
  ["/platform/economics", "Farm economics", "Phases 2-4", "Size the fleet for your acreage, price it at local rates, and compare cost per kg with a conventional farm.", "economics.py + season runs → /api/economics"],
  ["/platform/market", "Market desk", "Phase 5", "Run the B2B selling engine over the simulated harvest and stress it with price shocks and gluts.", "market.py → /api/market"],
  ["/platform/season", "Season replay", "All phases", "Scrub through 125 logged days: work orders, robot time, weeds, ripeness forecasts, sales and outages.", "events.jsonl → /api/season"],
];

export default function Page() {
  return (
    <>
      <PageHead eyebrow="Platform" title="The operating system for an autonomous farm.">
        These are the decision layers of Agrobo, running live. Each tool calls a public API that executes the models from
        our ROS 2 simulation, so what you see here is what the simulated farm did.
      </PageHead>
      <section className="container-x grid gap-4 pb-24 md:grid-cols-2">
        {TOOLS.map(([href, t, tag, d, src]) => (
          <Link key={href} href={href} className="group">
            <Card className="h-full p-6 transition group-hover:border-ink/40">
              <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{tag}</div>
              <div className="mt-3 flex items-center justify-between">
                <h2 className="text-[24px] font-semibold tracking-tight">{t}</h2>
                <span className="text-[20px] text-muted transition group-hover:translate-x-1 group-hover:text-ink">→</span>
              </div>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{d}</p>
              <div className="mt-5 font-mono text-[12px] text-brand">{src}</div>
            </Card>
          </Link>
        ))}
      </section>
    </>
  );
}

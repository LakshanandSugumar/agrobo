import Link from "next/link";

export const STAGES = [
  {
    n: "01",
    name: "Source",
    title: "Find and underwrite the land",
    software: "Scores every candidate parcel on soil, slope, water, season, market distance and connectivity, then matches crops by demand and margin and runs a 5-year NPV.",
    machines: "None. This stage is pure software.",
    you: "Approve the parcel and the crop plan.",
    demo: "/platform/land",
    demoLabel: "Run Land Scout",
  },
  {
    n: "02",
    name: "Prepare",
    title: "Clear, lay out and plumb the field",
    software: "Generates the RTK row grid, coverage paths and drip layout from the parcel boundary.",
    machines: "A prep UGV clears, tills and lays drip tape along centimetre-accurate lanes.",
    you: "Nothing. Prep for the sim block took 2.4 robot-hours.",
    demo: "/technology#physics",
    demoLabel: "See the row-following test",
  },
  {
    n: "03",
    name: "Grow",
    title: "Scout, weed and feed each plant",
    software: "The Field Ledger tracks every plant, fruit and weed and turns them into per-target work orders.",
    machines: "A scout drone flies every two days. Modular UGVs laser-weed and micro-dose nitrogen plant by plant.",
    you: "Nothing. Zero herbicide, zero human interventions in the simulated season.",
    demo: "/platform/season",
    demoLabel: "Replay the season",
  },
  {
    n: "04",
    name: "Harvest",
    title: "Pick on the forecast, not the search",
    software: "Forecasts which fruit will be ripe on which day and hands the picker an exact list with positions.",
    machines: "The same UGVs swap to picker arms. A hauler shuttles bins to the cold hub.",
    you: "Nothing. Fruit reaches cooling in under 30 minutes on average.",
    demo: "/results",
    demoLabel: "See picker results",
  },
  {
    n: "05",
    name: "Sell",
    title: "Grade, pack and sell B2B",
    software: "Grades every lot, pre-sells the 3-day forecast on retail contracts and routes the rest to the best live bid.",
    machines: "A hyperspectral grading line and an automated cold-chain packer at the hub.",
    you: "Get paid. Graded, contract-led selling earned ~40% more per kg than field-run wholesale.",
    demo: "/platform/market",
    demoLabel: "Open the Market desk",
  },
];

export function Lifecycle() {
  return (
    <div className="mt-12 grid gap-4 lg:grid-cols-5">
      {STAGES.map((s) => (
        <div key={s.n} className="group flex flex-col rounded-2xl border border-line bg-card p-5 transition hover:border-ink/40">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[12px] text-muted">{s.n}</span>
            <span className="rounded-full bg-brand-soft px-2.5 py-0.5 text-[12px] font-medium text-brand-ink">{s.name}</span>
          </div>
          <h3 className="mt-4 text-[17px] font-semibold leading-snug tracking-tight">{s.title}</h3>
          <dl className="mt-4 space-y-3 text-[13.5px] leading-relaxed">
            <Row k="Software" v={s.software} />
            <Row k="Machines" v={s.machines} />
            <Row k="You" v={s.you} />
          </dl>
          <Link href={s.demo} className="mt-auto pt-5 text-[13.5px] font-medium text-brand hover:text-brand-ink">
            {s.demoLabel} →
          </Link>
        </div>
      ))}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted">{k}</dt>
      <dd className="mt-0.5 text-ink-2">{v}</dd>
    </div>
  );
}

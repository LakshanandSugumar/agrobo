import Link from "next/link";
import { LineChart } from "@/components/charts";
import { Faq } from "@/components/Faq";
import { IdleFilm, WatchFilmButton } from "@/components/IdleFilm";
import { LedgerConsole } from "@/components/LedgerConsole";
import { Lifecycle } from "@/components/Lifecycle";
import { ButtonLink, Card, Modeled, SectionHead, Stat } from "@/components/ui";
import { compactSeason, fmt, kpi, notwin, twin } from "@/lib/data";
import { C } from "@/lib/palette";

export default function Home() {
  const days = compactSeason(twin);
  const daysNo = compactSeason(notwin);
  const opex = kpi("Agrobo OpEx ($/kg)").twin.mean;
  const conv = kpi("Conventional OpEx ($/kg)").twin.mean;
  const reduction = kpi("OpEx reduction vs conventional (%)").twin.mean;
  const spf = kpi("Picker seconds per fruit");
  const capex = kpi("Fleet capex ($/ha)");
  const ugv = kpi("Peak UGVs needed per ha");
  const gradeA = kpi("Grade A share (%)");
  const cool = kpi("Mean pick-to-cool (h)");
  const conventionalLabour = twin.kpis.kpi_3_unit_economics.conventional_opex;
  const labourShare = (conventionalLabour.lines.labour / conventionalLabour.total_usd) * 100;

  return (
    <>
      <IdleFilm />
      {/* HERO */}
      <section className="relative overflow-hidden bg-night text-white">
        <div className="grid-bg pointer-events-none absolute inset-0 opacity-60" />
        <div className="rows-bg pointer-events-none absolute inset-0" />
        <div className="container-x relative grid items-center gap-12 py-16 md:py-24 lg:grid-cols-[1.1fr_1fr]">
          <div>
            <Link href="/results" className="inline-flex items-center gap-2 rounded-full border border-night-line bg-night-2 px-3 py-1 text-[13px] text-[#c9d3cd] hover:border-[#5d7266]">
              <span className="rounded-full bg-lime px-1.5 py-px text-[11px] font-semibold text-ink">NEW</span>
              Full 125-day season simulated end to end in ROS 2 →
            </Link>
            <h1 className="mt-6 text-[44px] font-semibold leading-[1.02] tracking-[-0.035em] md:text-[68px]">
              The farm that <span className="font-serif font-normal italic text-lime">runs itself.</span>
            </h1>
            <p className="mt-6 max-w-xl text-[18px] leading-relaxed text-[#b7c4bd] md:text-[20px]">
              Agrobo is an autonomous farm operator. We automate the dirty work of farming, from buying the land to selling
              the crop. Software makes the decisions, a small modular fleet does the field work, and one plant-level digital
              twin runs it all.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/early-access" variant="lime">Get early access</ButtonLink>
              <ButtonLink href="/platform" variant="ghost-dark">Try the live platform →</ButtonLink>
            </div>
            <WatchFilmButton className="mt-6" />
            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-[#8fa197]">
              <span>ROS 2 Jazzy</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>Gazebo Harmonic</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>16 nodes, 5 lifecycle phases</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>0 human interventions</span>
            </div>
          </div>
          <LedgerConsole days={days} />
        </div>
      </section>

      {/* STAT STRIP */}
      <section className="border-b border-line bg-card">
        <div className="container-x py-12">
          <div className="mb-8 flex items-center justify-between gap-4">
            <p className="text-[14px] text-muted">One simulated tomato season, mean of 3 seeds, versus a conventional fresh-market baseline.</p>
            <Modeled />
          </div>
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <Stat value={`−${reduction.toFixed(0)}%`} label="Operating cost per kg" sub={`${fmt.usd(opex, 3)} vs ${fmt.usd(conv, 2)} conventional`} />
            <Stat value="0 L" label="Herbicide" sub={`${kpi("Weed-control efficacy (%)").twin.mean.toFixed(1)}% weeds killed by laser`} />
            <Stat value={`${spf.twin.mean.toFixed(1)} s`} label="Per fruit picked" sub={`vs ${spf.no_twin.mean.toFixed(1)} s without the twin`} />
            <Stat value="17 h" label="Human hours per hectare" sub="Remote supervision vs 1,056 h hand labour" />
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="container-x py-20 md:py-28">
        <div className="grid gap-12 lg:grid-cols-2">
          <SectionHead eyebrow="The problem" title="Farming still runs on work nobody wants to do.">
            Hand weeding, hand picking, spreadsheet crop plans and phone-call selling. In our conventional baseline,
            labour is {labourShare.toFixed(0)}% of the cost of growing a kilo of tomatoes, and the crew is getting harder to
            hire every season. Point solutions automate one task and leave the farm to stitch it together.
          </SectionHead>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ["Land", "Picked on gut feel and a broker's spreadsheet.", "Scored on 8 GIS factors and a 5-year NPV."],
              ["Field work", "Crews for weeding, scouting, dosing and picking.", "A shared modular fleet, steered by the twin."],
              ["Chemicals", "Blanket herbicide and broadcast nitrogen.", "Laser weeding and per-plant micro-doses."],
              ["Selling", "Ungraded field-run sold on the day.", "Graded lots, forward contracts, best live bid."],
            ].map(([k, before, after]) => (
              <Card key={k} className="p-5">
                <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{k}</div>
                <p className="mt-3 text-[14px] text-muted line-through decoration-tomato/50">{before}</p>
                <p className="mt-2 text-[15px] font-medium text-ink">{after}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* LIFECYCLE */}
      <section id="lifecycle" className="scroll-mt-20 border-y border-line bg-[#f1efe7] py-20 md:py-28">
        <div className="container-x">
          <SectionHead eyebrow="How it works" title={<>Five phases. One operator. <span className="font-serif font-normal italic">No crew.</span></>}>
            We don&apos;t put a robot on every job. Sourcing, planning and selling are software. Machines only do the physical,
            repetitive work, and the same modular robot swaps tools to do most of it.
          </SectionHead>
          <Lifecycle />
        </div>
      </section>

      {/* MOAT */}
      <section className="bg-night py-20 text-white md:py-28">
        <div className="container-x grid gap-14 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <SectionHead dark eyebrow="The moat" title={<>The Field Ledger: <span className="font-serif font-normal italic text-lime">predict, then pick.</span></>}>
              Every plant, fruit and weed gets a persistent record fused from drone and ground-robot observations. Ripeness is
              forecast forward in thermal time, so the fleet acts on where the field will be, not where it was. Pickers get a
              list of exact fruit to take today. The market desk sells tomorrow&apos;s harvest before it is picked. The ledger
              runs on the edge hub, so the farm keeps working through cloud outages.
            </SectionHead>
            <div className="mt-8 grid grid-cols-3 gap-3 font-mono text-[12px]">
              {[
                ["Observe", "UAV + UGV cameras, every 2 days"],
                ["Forecast", "Per-fruit ripeness in degree-days"],
                ["Act", "Per-target work orders and pre-sales"],
              ].map(([a, b], i) => (
                <div key={a} className="rounded-xl border border-night-line bg-night-2 p-3">
                  <div className="text-lime">0{i + 1} {a}</div>
                  <div className="mt-1 text-[#a9b8b0]">{b}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-night-line bg-night-2 p-6">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-medium">Same robots, twin on vs off</div>
              <Modeled dark />
            </div>
            <p className="mt-1 text-[13px] text-[#8fa197]">Ablation over 3 seeds. Only the Field Ledger is switched off.</p>
            <div className="mt-6 grid grid-cols-[1.4fr_1fr_1fr] gap-2 pb-2 font-mono text-[11px] uppercase tracking-wider text-[#6f8479]">
              <span />
              <span className="text-right">Twin on</span>
              <span className="text-right">Twin off</span>
            </div>
            <div className="divide-y divide-night-line border-t border-night-line">
              {[
                ["Seconds per fruit", spf.twin.mean.toFixed(1), spf.no_twin.mean.toFixed(1), true],
                ["UGVs needed per ha at peak", ugv.twin.mean.toFixed(2), ugv.no_twin.mean.toFixed(2), true],
                ["Fleet capex per ha", fmt.usdK(capex.twin.mean), fmt.usdK(capex.no_twin.mean), true],
                ["Grade A share", fmt.pct(gradeA.twin.mean, 1), fmt.pct(gradeA.no_twin.mean, 1), false],
                ["Pick to cold room", `${(cool.twin.mean * 60).toFixed(0)} min`, `${(cool.no_twin.mean * 60).toFixed(0)} min`, true],
                ["Operating cost per kg", fmt.usd(opex, 3), fmt.usd(kpi("Agrobo OpEx ($/kg)").no_twin.mean, 3), true],
              ].map(([k, a, b]) => (
                <div key={k as string} className="grid grid-cols-[1.4fr_1fr_1fr] items-center gap-2 py-3 text-[14px]">
                  <span className="text-[#c9d3cd]">{k}</span>
                  <span className="tabular text-right font-semibold text-lime">{a}</span>
                  <span className="tabular text-right text-[#8fa197]">{b}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* SEASON CHART */}
      <section className="container-x py-20 md:py-28">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <SectionHead eyebrow="Proof, in simulation" title="A whole season, start to sale, with nobody in the field.">
            Cumulative harvest from the logged ROS 2 runs. The twin-guided fleet waits for market-optimal ripeness, then
            picks faster with fewer robots. Shaded days are cloud outages the farm rode through on the edge.
          </SectionHead>
          <ButtonLink href="/platform/season" variant="secondary">Open season replay →</ButtonLink>
        </div>
        <Card className="mt-10 p-5 md:p-7">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-[15px] font-medium">Cumulative harvest, kg (0.036 ha block, seed 7)</div>
            <Modeled />
          </div>
          <LineChart
            ariaLabel="Cumulative harvest by day, twin-guided versus no twin"
            series={[
              { name: "Twin-guided", color: C.agrobo, points: days.map((d) => [d.day, d.cumKg]), area: true },
              { name: "No twin (ablation)", color: C.conventional, points: daysNo.map((d) => [d.day, d.cumKg]), dashed: true },
            ]}
            bands={days.filter((d) => !d.online).map((d) => [d.day, d.day] as [number, number])}
            y={{ suffix: " kg" }}
          />
        </Card>
      </section>

      {/* PLATFORM */}
      <section className="border-y border-line bg-card py-20 md:py-28">
        <div className="container-x">
          <SectionHead eyebrow="The platform" title="Don't take our word for it. Run the models.">
            Every tool below calls the same logic that runs inside our simulation, ported to a public API.
          </SectionHead>
          <div className="mt-12 grid gap-4 md:grid-cols-2">
            {[
              ["/platform/land", "Land Scout", "Screen candidate parcels, see why each scores the way it does, and get a 5-year NPV per crop.", "Phase 1 · Source"],
              ["/platform/economics", "Farm economics", "Size the fleet for your acreage and compare cost per kg, labour and chemicals with a conventional farm.", "Phases 2-4"],
              ["/platform/market", "Market desk", "Replay the simulated harvest through our B2B selling engine and stress it with price shocks.", "Phase 5 · Sell"],
              ["/platform/season", "Season replay", "Step through all 125 days: work orders, robots, weeds, ripeness forecasts and sales.", "All phases"],
            ].map(([href, t, d, tag]) => (
              <Link key={href} href={href} className="group rounded-2xl border border-line bg-paper p-6 transition hover:border-ink/40 hover:bg-card">
                <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{tag}</div>
                <div className="mt-3 flex items-center justify-between">
                  <h3 className="text-[22px] font-semibold tracking-tight">{t}</h3>
                  <span className="text-[20px] text-muted transition group-hover:translate-x-1 group-hover:text-ink">→</span>
                </div>
                <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{d}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* BUSINESS MODEL */}
      <section className="container-x py-20 md:py-28">
        <SectionHead eyebrow="Business model" title="We get paid when the farm makes money.">
          Agrobo operates farms as a service. Landowners and growers bring the land; we bring the software, the fleet and the
          buyers.
        </SectionHead>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            ["Operate", "Farming as a service", "We run the whole lifecycle on your land for a per-kilo operating fee plus a share of the margin we create."],
            ["Fleet", "Robots as a service", "Growers who want to keep operating lease the modular fleet and Field Ledger per hectare per season."],
            ["Market", "B2B exchange", "Graded, forecast-backed produce sold to retail, food-service and processors, with a take rate on each trade."],
          ].map(([k, t, d]) => (
            <Card key={k} className="p-6">
              <div className="eyebrow">{k}</div>
              <h3 className="mt-3 text-[20px] font-semibold tracking-tight">{t}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{d}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ROADMAP */}
      <section className="border-y border-line bg-[#f1efe7] py-20 md:py-24">
        <div className="container-x">
          <SectionHead eyebrow="Where we are" title="Simulation first. Then the field." />
          <ol className="mt-10 grid gap-4 md:grid-cols-4">
            {[
              ["Done", "Full-lifecycle simulation", "16 ROS 2 nodes, behaviour-tree orchestration, twin vs no-twin ablation, Gazebo physics check."],
              ["Next", "Bench-test the picker", "Replace modeled grasp success and cycle times with measurements on real plants."],
              ["Then", "Pilot season", "One block of tomatoes run end to end, with the sim recalibrated on pilot data."],
              ["After", "First operated farms", "Farming-as-a-service contracts with landowners, second crop added."],
            ].map(([k, t, d], i) => (
              <li key={t} className={`rounded-2xl border p-5 ${i === 0 ? "border-brand bg-card" : "border-line bg-paper"}`}>
                <div className={`font-mono text-[11px] uppercase tracking-[0.08em] ${i === 0 ? "text-brand" : "text-muted"}`}>{k}</div>
                <h3 className="mt-2 text-[17px] font-semibold">{t}</h3>
                <p className="mt-1.5 text-[14px] leading-relaxed text-ink-2">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* FAQ */}
      <section className="container-x grid gap-10 py-20 md:py-28 lg:grid-cols-[1fr_1.6fr]">
        <SectionHead eyebrow="FAQ" title="Questions we get." />
        <Faq
          items={[
            ["Are these numbers from a real farm?", "Not yet. Every performance figure on this site comes from our ROS 2 simulation of a full tomato season. The software logic (planning, orchestration, the twin, selling) is real code; crop growth, perception accuracy, grasp success, prices and costs are calibrated models that we will replace with pilot measurements. We label simulated figures everywhere."],
            ["Why not a robot for every task?", "Most of the cost and risk in farming is in decisions and coordination, not just motion. Land selection, crop planning, scheduling and selling are software. Where physical work is needed we use one modular UGV that swaps tools (weeder, doser, picker arm), which is why the twin cuts the fleet you need per hectare."],
            ["What is the Field Ledger?", "A plant-level digital twin running on the farm's edge hub. It tracks every plant, fruit and weed, forecasts ripeness in thermal time, and turns that into per-target work orders and forward sales. Switching it off in the same simulation makes picking 39% slower and the fleet 36% larger."],
            ["What happens when the internet goes down?", "The farm keeps running. The ledger and the behaviour tree live on the edge; only forward contracts need the cloud. Our simulated season included 12 cloud outage days, and field work carried on through every one of them."],
            ["Which crops?", "Tomatoes first: high value, high labour, and a well-understood ripeness signal. Land Scout already scores strawberry, bell pepper and lettuce, and the architecture is crop-agnostic."],
            ["Can I see the code?", "The simulation and this website live in one repository. Ask us for access through the early-access form."],
          ]}
        />
      </section>

      {/* CTA */}
      <section className="container-x pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-brand-ink px-6 py-14 text-white md:px-14 md:py-20">
          <div className="rows-bg pointer-events-none absolute inset-0" />
          <div className="relative max-w-2xl">
            <h2 className="text-[34px] font-semibold leading-[1.08] tracking-[-0.02em] md:text-[48px]">
              Own land? Grow produce? Buy it by the truckload?
            </h2>
            <p className="mt-4 text-[17px] text-[#b7c4bd]">
              We&apos;re choosing pilot partners for our first operated season. Tell us about your acres or your demand.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/early-access" variant="lime">Become a pilot partner</ButtonLink>
              <ButtonLink href="/platform/economics" variant="ghost-dark">Model your farm →</ButtonLink>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

import Link from "next/link";
import { HBars, LineChart } from "@/components/charts";
import { Faq } from "@/components/Faq";
import { IdleFilm, WatchFilmButton } from "@/components/IdleFilm";
import { LedgerConsole } from "@/components/LedgerConsole";
import { ButtonLink, Card, Modeled, SectionHead, Stat } from "@/components/ui";
import harvest from "@/data/harvester_break_even.json";
import { compactSeason, fmt, kpi, notwin, twin } from "@/lib/data";
import { C } from "@/lib/palette";

// Scenario keys as written by simulation/tools/pick_sensitivity.py.
const ONE_SEASON = "Base: 85 kg/h crews, 1,500 h/yr";
const TWO_SEASONS = "Two seasons or regions: 3,000 h/yr";
const PILOT_PRICE = "Pilot price 15% below crew cost";

type Robot = (typeof harvest.robots)[number];
const robot = (name: string): Robot => {
  const r = harvest.robots.find((x) => x.robot.startsWith(name));
  if (!r) throw new Error(`unknown robot ${name}`);
  return r;
};
const be = (r: Robot, scenario: string) => (r.break_even as Record<string, number | null>)[scenario] ?? null;
const pct = (v: number | null) => (v === null ? "Not reachable" : `${Math.round(v * 100)}%`);

// Rev B origin shares by $ (robots/docs/05_REVB_MADE_IN_USA.md).
const ORIGIN = [
  { label: "US-made (vendor states it)", value: 8.6, color: C.agrobo },
  { label: "US maker, country-of-origin letter pending", value: 28.3, color: C.blue },
  { label: "Assembled in the US from imported subparts", value: 56.6, color: C.purple },
  { label: "No US source yet: LFP cells, Jetson compute, wrist depth camera, tyres", value: 6.4, color: C.conventional },
];

const SUPPLIERS: [string, string][] = [
  ["Arms", "Standard Bots Spark, Glen Cove NY"],
  ["Lidar", "Ouster OS0, San Francisco CA"],
  ["Stereo cameras", "Carnegie Robotics, Pittsburgh PA"],
  ["Drive motors + reducers", "Motenergy, Hartford WI · Winsmith, Springville NY"],
  ["GNSS + IMU", "Hemisphere, Tempe AZ · VectorNav, Dallas TX"],
  ["Safety", "Banner, Minneapolis MN · FORT Robotics, Philadelphia PA"],
  ["Gripper actuators", "Teknic, Victor NY · Ultra Motion, Cutchogue NY"],
  ["Frame", "80/20, Columbia City IN · SendCutSend, Reno NV"],
];

export default function Home() {
  const days = compactSeason(twin);
  const daysNo = compactSeason(notwin);
  const spf = kpi("Picker seconds per fruit");
  const capex = kpi("Fleet capex ($/ha)");
  const ugv = kpi("Peak UGVs needed per ha");
  const gradeA = kpi("Grade A share (%)");
  const cool = kpi("Mean pick-to-cool (h)");

  const volume = robot("Rev A.1 at 100 units");
  const revABuilt = robot("Rev A.1 built");
  const revB = robot("Rev B US-sourced, built");
  const crew = harvest.crew_usd_per_kg;
  const a = harvest.assumptions;

  return (
    <>
      <IdleFilm />
      {/* HERO */}
      <section className="relative overflow-hidden bg-night text-white">
        <div className="grid-bg pointer-events-none absolute inset-0 opacity-60" />
        <div className="rows-bg pointer-events-none absolute inset-0" />
        <div className="container-x relative grid items-center gap-12 py-16 md:py-24 lg:grid-cols-[1.1fr_1fr]">
          <div>
            <Link href="/results#pick-success" className="inline-flex items-center gap-2 rounded-full border border-night-line bg-night-2 px-3 py-1 text-[13px] text-[#c9d3cd] hover:border-[#5d7266]">
              <span className="rounded-full bg-lime px-1.5 py-px text-[11px] font-semibold text-ink">SIM</span>
              Picker training: 22% clean picks today, 55% is the goal →
            </Link>
            <h1 className="mt-6 text-[44px] font-semibold leading-[1.02] tracking-[-0.035em] md:text-[68px]">
              The tomato picker, <span className="font-serif font-normal italic text-lime">built in America.</span>
            </h1>
            <p className="mt-6 max-w-xl text-[18px] leading-relaxed text-[#b7c4bd] md:text-[20px]">
              Agrobo builds AI harvesting robots for Florida&apos;s fresh-market tomato growers, who can&apos;t book enough
              pickers. Our own gripper, a per-plant digital twin that tells the robot which fruit to take today, and a price
              per bucket set below what your crew costs, with a hand crew on call if the robot falls short.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/early-access" variant="lime">Become a pilot grower</ButtonLink>
              <ButtonLink href="#economics" variant="ghost-dark">See the honest numbers →</ButtonLink>
            </div>
            <WatchFilmButton className="mt-6" />
            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-[#8fa197]">
              <span>Designed and assembled in the USA</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>Own EE-1 gripper</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>ROS 2 + MuJoCo</span>
              <span className="h-1 w-1 rounded-full bg-[#3b5246]" />
              <span>Simulated results labelled</span>
            </div>
          </div>
          <LedgerConsole days={days} />
        </div>
      </section>

      {/* STAT STRIP */}
      <section className="border-b border-line bg-card">
        <div className="container-x py-12">
          <div className="mb-8 flex items-center justify-between gap-4">
            <p className="text-[14px] text-muted">
              Where the harvester stands today. Pick rates and cycle times are from simulation; the robot has not been built
              yet. Crew costs are our assumptions until grower calls replace them.
            </p>
            <Modeled />
          </div>
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <Stat value="22%" label="Clean picks in sim today" sub="Learnt picker, after 1.3M of 20M training steps" />
            <Stat value={pct(be(revB, TWO_SEASONS))} label="Needed to beat a crew" sub={`US-built robot working ${fmt.num(3000)} h a year`} />
            <Stat value={`${spf.twin.mean.toFixed(1)} s`} label="Per fruit with the twin" sub={`vs ${spf.no_twin.mean.toFixed(1)} s searching without it`} />
            <Stat value="93.6%" label="Of rev B parts value US-sourced" sub="Made or assembled in the US" />
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="container-x py-20 md:py-28">
        <div className="grid gap-12 lg:grid-cols-2">
          <SectionHead eyebrow="The problem" title="Florida's tomato harvest runs on a crew that's harder to book every year.">
            Fresh-market tomatoes are picked by hand, several passes a season. In Southwest Florida most of that work is done by
            H-2A crews that growers recruit months ahead and house and transport. When the crew is short in a peak week, ripe
            fruit stays on the vine. Picking is the job growers most want off their plate.
          </SectionHead>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ["Crew", "Book H-2A crews months ahead, pay housing and transport.", "Book robots by the bucket, with a crew on call as backup."],
              ["Picking", "Every picker searches every plant on every pass.", "The twin lists the exact fruit to take today."],
              ["Risk", "A short crew in peak week leaves fruit in the field.", "A per-bucket price below crew cost, with a hand-crew guarantee."],
              ["Data", "Yield is a guess until the trailer is weighed.", "Per-plant counts and a pick forecast before every pass."],
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

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="scroll-mt-20 border-y border-line bg-[#f1efe7] py-20 md:py-28">
        <div className="container-x">
          <SectionHead eyebrow="How it works" title={<>Scan. Pick. Hand off. <span className="font-serif font-normal italic">Every pass.</span></>}>
            One robot straddles the bed with two arms. It doesn&apos;t search the plant: the twin has already told it where the
            ripe fruit is.
          </SectionHead>
          <ol className="mt-12 grid gap-4 md:grid-cols-3">
            {[
              ["01 Scan", "Know the field", "Cameras on the robot and a scouting drone keep a record of every plant and fruit, and forecast ripeness forward in degree-days, so each pass starts with a pick list."],
              ["02 Pick", "Two arms, our own hand", "The EE-1 gripper holds the fruit with a 65 mm suction plunger, closes three soft Fin-Ray fingers around it and pulls. Target: 9 s per fruit per arm, 5.3 s per fruit per robot."],
              ["03 Hand off", "Into the bucket, on the record", "Fruit rolls into field buckets on the robot. Every pick, miss and drop is logged per plant, and missed fruit goes on the hand crew's list."],
            ].map(([k, t, d]) => (
              <li key={k}>
                <Card className="h-full p-6">
                  <div className="font-mono text-[12px] text-brand">{k}</div>
                  <h3 className="mt-3 text-[20px] font-semibold tracking-tight">{t}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{d}</p>
                </Card>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* MOAT */}
      <section className="bg-night py-20 text-white md:py-28">
        <div className="container-x grid gap-14 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <SectionHead dark eyebrow="Why ours picks faster" title={<>The Field Ledger: <span className="font-serif font-normal italic text-lime">predict, then pick.</span></>}>
              Earlier picking robots failed on speed: they spent most of each cycle finding the fruit. Our per-plant twin does the
              finding before the robot arrives. Every plant and fruit gets a persistent record fused from drone and robot
              cameras, ripeness is forecast in thermal time, and the arms get a list of exact fruit to take. The ledger runs on
              the robot, so it keeps working with no signal in the field.
            </SectionHead>
            <div className="mt-8 grid grid-cols-3 gap-3 font-mono text-[12px]">
              {[
                ["Observe", "Drone + robot cameras, every 2 days"],
                ["Forecast", "Per-fruit ripeness in degree-days"],
                ["Act", "Per-fruit pick list for each pass"],
              ].map(([x, y], i) => (
                <div key={x} className="rounded-xl border border-night-line bg-night-2 p-3">
                  <div className="text-lime">0{i + 1} {x}</div>
                  <div className="mt-1 text-[#a9b8b0]">{y}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-night-line bg-night-2 p-6">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-medium">Same robots, twin on vs off</div>
              <Modeled dark />
            </div>
            <p className="mt-1 text-[13px] text-[#8fa197]">Season simulation, 3 seeds, 95% pick success assumed. Only the Field Ledger is switched off.</p>
            <div className="mt-6 grid grid-cols-[1.4fr_1fr_1fr] gap-2 pb-2 font-mono text-[11px] uppercase tracking-wider text-[#6f8479]">
              <span />
              <span className="text-right">Twin on</span>
              <span className="text-right">Twin off</span>
            </div>
            <div className="divide-y divide-night-line border-t border-night-line">
              {[
                ["Seconds per fruit", spf.twin.mean.toFixed(1), spf.no_twin.mean.toFixed(1)],
                ["Robots needed per ha at peak", ugv.twin.mean.toFixed(2), ugv.no_twin.mean.toFixed(2)],
                ["Fleet capex per ha", fmt.usdK(capex.twin.mean), fmt.usdK(capex.no_twin.mean)],
                ["Grade A share", fmt.pct(gradeA.twin.mean, 1), fmt.pct(gradeA.no_twin.mean, 1)],
                ["Pick to cold room", `${(cool.twin.mean * 60).toFixed(0)} min`, `${(cool.no_twin.mean * 60).toFixed(0)} min`],
              ].map(([k, on, off]) => (
                <div key={k} className="grid grid-cols-[1.4fr_1fr_1fr] items-center gap-2 py-3 text-[14px]">
                  <span className="text-[#c9d3cd]">{k}</span>
                  <span className="tabular text-right font-semibold text-lime">{on}</span>
                  <span className="tabular text-right text-[#8fa197]">{off}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ECONOMICS */}
      <section id="economics" className="container-x scroll-mt-20 py-20 md:py-28">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.15fr]">
          <SectionHead eyebrow="The honest numbers" title="When does a robot beat a crew?">
            At 100% pick success one robot does the work of about {revB.at_100pct.crew_equivalents} pickers. What it costs per
            kilo depends on its price, the hours it works and how many fruit it actually gets off. A hand crew costs about{" "}
            {fmt.usd(crew, 2)}/kg in our model (${a.crew_usd_h}/h at {a.crew_kg_h} kg/h). An imported-parts robot at volume
            beats that at {pct(be(volume, ONE_SEASON))} pick success in one Florida season. Our US-built robot costs{" "}
            {fmt.usdK(revB.robot_usd)}, and in one {fmt.num(a.hours_per_year)}-hour season it can&apos;t beat a crew even at 100%.
            It does at {pct(be(revB, TWO_SEASONS))} if it works a second harvest further north in summer, the way crews already
            follow the harvest, or once the robot price falls to about {fmt.usdK(harvest.max_robot_usd_at_55pct)}. That is why we
            are building the gripper, and next the joints, ourselves.
          </SectionHead>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="text-[15px] font-medium">Pick success needed to match crew cost</div>
              <Modeled />
            </div>
            <p className="mt-1 text-[13px] text-muted">
              Capital recovered at {Math.round(a.rate * 100)}% over {a.life_years} years, {Math.round(a.maint_frac * 100)}% maintenance, $12k/yr
              fixed costs, {a.cycle_s} s per fruit, {a.kg_per_fruit} kg per fruit.
            </p>
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[480px] text-[14px]">
                <thead className="text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                  <tr>
                    <th className="py-2 pr-3 font-normal">Robot</th>
                    <th className="py-2 pr-3 text-right font-normal">1 season</th>
                    <th className="py-2 pr-3 text-right font-normal">2 seasons</th>
                    <th className="py-2 text-right font-normal">Priced 15% below crew</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line border-t border-line">
                  {[
                    ["Imported parts, at 100 units", volume],
                    ["Imported parts, first build", revABuilt],
                    ["US-built rev B, first build", revB],
                  ].map(([label, r]) => {
                    const rr = r as Robot;
                    return (
                      <tr key={label as string}>
                        <td className="py-3 pr-3">
                          <div className="font-medium">{label as string}</div>
                          <div className="text-[12px] text-muted">{fmt.usdK(rr.robot_usd)} per robot</div>
                        </td>
                        {[ONE_SEASON, TWO_SEASONS, PILOT_PRICE].map((s) => (
                          <td key={s} className={`tabular py-3 pr-3 text-right ${be(rr, s) === null ? "text-tomato" : "font-semibold"}`}>
                            {pct(be(rr, s))}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-6">
              <div className="mb-3 text-[13px] font-medium">Robot cost per kg at 100% pick success, one season</div>
              <HBars
                rows={[
                  { label: "Imported parts, at 100 units", value: volume.at_100pct.robot_usd_per_kg, display: `${fmt.usd(volume.at_100pct.robot_usd_per_kg, 3)}/kg`, color: C.agrobo },
                  { label: "US-built rev B, first build", value: revB.at_100pct.robot_usd_per_kg, display: `${fmt.usd(revB.at_100pct.robot_usd_per_kg, 3)}/kg`, color: C.blue },
                  { label: "Hand crew", value: crew, display: `${fmt.usd(crew, 3)}/kg`, color: C.conventional },
                ]}
              />
            </div>
            <p className="mt-5 text-[12px] leading-relaxed text-muted">
              From <code>simulation/tools/pick_sensitivity.py</code>. Fast mature-green crews (150 kg/h) push break-even far
              higher, which is why our first grower calls measure crew rates before anything else.
            </p>
          </Card>
        </div>
      </section>

      {/* BUILT IN AMERICA */}
      <section id="made-in-usa" className="scroll-mt-20 bg-night py-20 text-white md:py-28">
        <div className="container-x grid gap-14 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <SectionHead dark eyebrow="Built in America" title={<>Starting with <span className="font-serif font-normal italic text-lime">the hand.</span></>}>
              EE-1 is our own gripper: three soft TPU Fin-Ray fingers around a 65 mm suction plunger, with a depth camera in the
              wrist. It is designed in-house and built from US-made printing, actuators and fittings. Rev B of the harvester swaps
              every part that has a US source, and costs 2.5 times the imported version because of it. We say
              &ldquo;designed and assembled in the USA&rdquo;, not &ldquo;Made in USA&rdquo;: the FTC reserves that label for
              all or virtually all US content, and we will use it when it is true.
            </SectionHead>
            <dl className="mt-8 grid gap-x-6 gap-y-3 text-[14px] sm:grid-cols-2">
              {SUPPLIERS.map(([k, v]) => (
                <div key={k} className="border-t border-night-line pt-3">
                  <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-[#6f8479]">{k}</dt>
                  <dd className="mt-1 text-[#c9d3cd]">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="self-start rounded-2xl border border-night-line bg-night-2 p-6">
            <div className="text-[15px] font-medium">Rev B parts, by share of BOM value</div>
            <p className="mt-1 text-[13px] text-[#8fa197]">{fmt.usdK(revB.robot_usd)} per robot built, pilot quantity, from list prices and quotes.</p>
            <div className="mt-6 space-y-4">
              {ORIGIN.map((o) => (
                <div key={o.label}>
                  <div className="mb-1 flex items-baseline justify-between gap-4 text-[13px]">
                    <span className="text-[#c9d3cd]">{o.label}</span>
                    <span className="tabular font-semibold text-white">{o.value.toFixed(1)}%</span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-night">
                    <div className="h-3 rounded-full" style={{ width: `${o.value}%`, background: o.color }} />
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-6 text-[13px] leading-relaxed text-[#8fa197]">
              The parts with no US source are the plan for what we build next. The gripper comes first, then joints, sold to
              other robot makers who want US-built parts too.
            </p>
          </div>
        </div>
      </section>

      {/* SEASON CHART */}
      <section className="container-x py-20 md:py-28">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <SectionHead eyebrow="Proof, in simulation" title="The twin picks at the right day, with fewer robots.">
            Cumulative harvest from the logged ROS 2 season runs. The twin-guided fleet waits for market-ready fruit, then picks
            faster. This run assumes 95% pick success, which our picker has not reached yet. Shaded days are network outages
            the robots worked through.
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
            Every tool below calls the same logic that runs inside our simulation. The harvester comes first; land and selling
            tools are later add-ons we have already prototyped.
          </SectionHead>
          <div className="mt-12 grid gap-4 md:grid-cols-2">
            {[
              ["/platform/season", "Season replay", "Step through all 125 days: pick lists, robots, ripeness forecasts and harvest.", "Harvester"],
              ["/platform/economics", "Farm economics", "Size the fleet for your acreage and compare cost per kg with a hand crew.", "Harvester"],
              ["/platform/land", "Land Scout", "Screen candidate parcels and get a 5-year profit estimate per crop.", "Later add-on"],
              ["/platform/market", "Market desk", "Replay the simulated harvest through a B2B selling engine.", "Later add-on"],
            ].map(([href, t, d, tag]) => (
              <Link key={href} href={href} className="group rounded-2xl border border-line bg-paper p-6 transition hover:border-ink/40 hover:bg-card">
                <div className={`font-mono text-[11px] uppercase tracking-[0.08em] ${tag === "Harvester" ? "text-brand" : "text-muted"}`}>{tag}</div>
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
        <SectionHead eyebrow="Business model" title="Paid per bucket, not per robot.">
          Growers don&apos;t buy or lease a robot. They pay for fruit in the bucket, at a price below what their crew cost them
          last season, and we carry the risk.
        </SectionHead>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            ["Pick", "Per-bucket picking", "Each field bucket is priced 10 to 20% below your crew's cost last season. Paid from the first pass of the pilot."],
            ["Backup", "Hand-crew guarantee", "If the robots fall short on a pass, a hand crew follows through your labour contractor at our cost, so no ripe fruit is left behind."],
            ["Data", "Field Ledger included", "Per-plant counts, pick forecasts and a record of every pick, so you can plan crews and sales before the pass."],
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
          <SectionHead eyebrow="Where we are" title="Simulation and design done. Now the bench, then the field." />
          <ol className="mt-10 grid gap-4 md:grid-cols-4">
            {[
              ["Done", "Picker in simulation", "MuJoCo picking environment and RL training: 22% clean picks after 1.3M of 20M steps. Full-season ROS 2 sim with the per-plant twin."],
              ["Done", "Harvester designed", "CAD, BOM, schematics and build plan for the imported-parts rev A.1 and the US-sourced rev B."],
              ["Next", "Full training run + gripper bench test", "Finish the 20M-step run, then test EE-1 on real mature-green fruit and replace modelled cycle times with measured ones."],
              ["Then", "Spring 2027 pilot", "One Southwest Florida grower, 2 to 5 acres, paid per bucket from day one. After that, US-built grippers for other robot makers."],
            ].map(([k, t, d]) => (
              <li key={t} className={`rounded-2xl border p-5 ${k === "Done" ? "border-brand bg-card" : "border-line bg-paper"}`}>
                <div className={`font-mono text-[11px] uppercase tracking-[0.08em] ${k === "Done" ? "text-brand" : "text-muted"}`}>{k}</div>
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
            ["Are these numbers from a real farm?", "Not yet, and the robot has not been built. Pick rates and cycle times come from our simulations: the learnt picker gets 22% of fruit off cleanly today, after 1.3M of a planned 20M training steps. Crew rates and costs are our assumptions until grower calls replace them. Every simulated figure on this site is labelled."],
            ["Why Florida tomatoes?", "Fresh-market tomatoes are still picked by hand, several passes a season, mostly by H-2A crews that are costly and hard to book. Southwest Florida grows them through the winter, so the robot works while most US fields are idle, and can follow the harvest north in summer."],
            ["Why build in the USA if it costs more?", `Our US-sourced rev B costs ${fmt.usdK(revB.robot_usd)} per robot against ${fmt.usdK(revABuilt.robot_usd)} with imported parts. Tariffs and export rules make imported robot parts a moving target, and we want to own the hardest parts, the hand and the joints. Rev B still beats a crew at about ${pct(be(revB, TWO_SEASONS))} pick success if it works two harvests a year, and every dollar we take out of the arm and gripper goes into the grower's price.`],
            ["What if the robot misses fruit?", "The twin knows which ripe fruit the robot skipped or dropped on each pass. A hand crew follows through the grower's labour contractor at our cost, so the grower never pays more for picking than their crew would have cost."],
            ["What is the Field Ledger?", `A per-plant digital twin running on the robot. It tracks every plant and fruit, forecasts ripeness in thermal time and turns that into a pick list for each pass. Switching it off in the same simulation raises the time per fruit from ${spf.twin.mean.toFixed(1)} s to ${spf.no_twin.mean.toFixed(1)} s and the robots needed per hectare from ${ugv.twin.mean.toFixed(2)} to ${ugv.no_twin.mean.toFixed(2)}.`],
            ["Do you sell the gripper?", "Not yet. EE-1 is our own design, built from US-sourced parts apart from its wrist depth camera. Once it passes field tests we plan to sell it, and later our joints, to other robot makers who want US-built parts."],
            ["Can I see the code?", "The simulation, training code, robot design and this website live in one repository. Ask us for access through the early-access form."],
          ]}
        />
      </section>

      {/* CTA */}
      <section className="container-x pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-brand-ink px-6 py-14 text-white md:px-14 md:py-20">
          <div className="rows-bg pointer-events-none absolute inset-0" />
          <div className="relative max-w-2xl">
            <h2 className="text-[34px] font-semibold leading-[1.08] tracking-[-0.02em] md:text-[48px]">
              Grow fresh-market tomatoes in Florida?
            </h2>
            <p className="mt-4 text-[17px] text-[#b7c4bd]">
              We&apos;re choosing one grower for a paid spring 2027 pilot on 2 to 5 acres. Tell us about your crew, your beds and
              your picks, and we&apos;ll show you the numbers for your farm.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/early-access" variant="lime">Become a pilot grower</ButtonLink>
              <ButtonLink href="#economics" variant="ghost-dark">See the numbers →</ButtonLink>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

import Image from "next/image";
import { GapBars } from "@/components/GapBars";
import { ButtonLink, Card, Estimate, SectionHead, StageTag } from "@/components/ui";
import { NOT_DOING, PRODUCTS, ROBOT, premiumPct, usd } from "@/lib/data";

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-night text-white">
        <div className="blueprint absolute inset-0 opacity-70" aria-hidden />
        <div className="container-x relative grid items-center gap-12 py-16 md:grid-cols-[1.15fr_1fr] md:py-24">
          <div>
            <div className="eyebrow">Robots made in America</div>
            <h1 className="mt-4 text-[40px] font-semibold leading-[1.04] tracking-[-0.03em] md:text-[64px]">
              The robot parts America imports, designed to be built here.
            </h1>
            <p className="mt-6 max-w-xl text-[18px] leading-relaxed text-[#a7b4c2]">
              Every US field robot today is either built on imported hands and joints or costs about 2.5× more. We are starting with the
              two parts that drive that gap: a soft food gripper and a robot joint actuator.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/products" variant="signal">See the products</ButtonLink>
              <ButtonLink href="/partners" variant="ghost-dark">Become a design partner</ButtonLink>
            </div>
            <div className="mt-10 flex flex-wrap gap-x-6 gap-y-2 font-mono text-[12px] uppercase tracking-[0.06em] text-[#8b9aab]">
              <span><span className="text-signal">●</span> Pre-production</span>
              <span>First product: EE-1, in design</span>
              <span>0 units shipped</span>
            </div>
          </div>
          <div className="rounded-2xl border border-night-line bg-[#dfe6ec] p-4">
            <Image src="/ee1-render.png" alt="CAD render of the EE-1 gripper: three blue flexible fingers around an orange suction cup on a green cylindrical housing" width={1400} height={1200} priority className="h-auto w-full rounded-xl" />
            <div className="mt-3 flex items-center justify-between px-1 font-mono text-[11px] uppercase tracking-[0.06em] text-[#4a5866]">
              <span>EE-1 soft food gripper</span>
              <span>CAD render · not yet built</span>
            </div>
          </div>
        </div>
      </section>

      {/* The gap */}
      <section className="py-20 md:py-28">
        <div className="container-x">
          <SectionHead eyebrow="The gap" title="We priced our own robot both ways.">
            We built the bill of materials for our tomato-harvesting robot twice: once with the cheapest parts, mostly imported, and once
            with a US-made or US-assembled part wherever one exists. The US version costs {premiumPct(ROBOT.importBuilt, ROBOT.usBuilt)}% more,
            and most of the difference is the arms.
          </SectionHead>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            <Card className="p-6">
              <div className="text-[13px] text-muted">Per robot, built</div>
              <div className="tabular mt-2 text-[32px] lg:text-[36px] font-semibold tracking-[-0.03em]">{usd(ROBOT.importBuilt)} <span className="text-[20px] text-muted">→</span> <span className="text-signal">{usd(ROBOT.usBuilt)}</span></div>
              <div className="mt-1 text-[14px] text-ink-2">Imported vs US-sourced, pilot quantity</div>
            </Card>
            <Card className="p-6">
              <div className="text-[13px] text-muted">Two 6-axis arms</div>
              <div className="tabular mt-2 text-[32px] lg:text-[36px] font-semibold tracking-[-0.03em]">{usd(ROBOT.armsImportPair)} <span className="text-[20px] text-muted">→</span> <span className="text-signal">{usd(ROBOT.armsUsPair)}</span></div>
              <div className="mt-1 text-[14px] text-ink-2">Only one US-assembled cobot fits. Joints are most of its cost.</div>
            </Card>
            <Card className="p-6">
              <div className="text-[13px] text-muted">Value with no US source at all</div>
              <div className="tabular mt-2 text-[32px] lg:text-[36px] font-semibold tracking-[-0.03em]">{(ROBOT.shareNoUsSource * 100).toFixed(1)}%</div>
              <div className="mt-1 text-[14px] text-ink-2">Battery cells, the AI computer, close-range depth cameras</div>
            </Card>
          </div>
          <div className="mt-6 grid gap-6 md:grid-cols-[1.3fr_1fr]">
            <Card className="p-6 md:p-8">
              <div className="mb-6 flex items-center justify-between gap-3">
                <div className="text-[15px] font-medium">Biggest lines, imported vs US-sourced</div>
                <Estimate />
              </div>
              <GapBars />
            </Card>
            <Card className="flex flex-col justify-between bg-steel-soft p-6 md:p-8">
              <div>
                <div className="text-[15px] font-medium">What this tells us</div>
                <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
                  Frames, plates, totes and printed parts were already US-made at almost the same price. The gap sits in a few precision
                  parts: arms and their joints, lidar, GNSS and drive motors. Those are where a US maker can win on more than patriotism.
                </p>
              </div>
              <ButtonLink href="/gap" variant="secondary" className="mt-6 self-start">See every line</ButtonLink>
            </Card>
          </div>
        </div>
      </section>

      {/* Products */}
      <section className="border-y border-line bg-card py-20 md:py-28">
        <div className="container-x">
          <SectionHead eyebrow="What we make" title="Start with the hand. Then the joint.">
            The gripper needs about $25k of tooling, so we can build it now. The joint actuator is the bigger prize and needs a first
            production line.
          </SectionHead>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {PRODUCTS.map((p) => (
              <a key={p.id} href={`/products#${p.id}`} className="group rounded-2xl border border-line bg-paper p-6 transition hover:border-ink">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[13px] text-muted">{p.code}</span>
                  <StageTag stage={p.stage} />
                </div>
                <div className="mt-5 text-[20px] font-semibold tracking-[-0.01em]">{p.name}</div>
                <p className="mt-2 text-[14px] leading-relaxed text-ink-2">{p.summary}</p>
                <div className="mt-5 border-t border-line pt-4 text-[13px] text-muted">To start: {p.startCost}</div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* What we buy */}
      <section className="py-20 md:py-28">
        <div className="container-x grid gap-12 md:grid-cols-[1fr_1.4fr]">
          <SectionHead eyebrow="What we buy instead" title="We don't try to make everything.">
            Some imported parts need a $100M plant or already have strong US makers. For those we are a customer, not a competitor.
          </SectionHead>
          <div className="grid gap-4 sm:grid-cols-2">
            {NOT_DOING.map((n) => (
              <Card key={n.what} className="p-5">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[16px] font-semibold">{n.what}</div>
                  <StageTag stage="We buy" />
                </div>
                <p className="mt-2 text-[14px] leading-relaxed text-ink-2">{n.why}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Labels / honesty */}
      <section id="claims" className="scroll-mt-20 bg-night py-20 text-white md:py-28">
        <div className="container-x">
          <SectionHead dark eyebrow="Our labels" title="We will say “Made in USA” only when it is true.">
            Under the FTC rule, “Made in USA” means all or virtually all of a product is made here, including its significant parts. Today
            none of our designs meet that, so we label each part by what it actually is.
          </SectionHead>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {[
              { label: "Designed in USA", now: "Everything we make", desc: "Design, CAD and test happen here." },
              { label: "Assembled in USA", now: "Our goal for first units", desc: "Final assembly here, with any imported parts named on the spec sheet." },
              { label: "Made in USA", now: "Not claimed yet", desc: "Only when all significant parts are US-made. Cells and chips are the hardest." },
            ].map((c) => (
              <div key={c.label} className="rounded-2xl border border-night-line bg-night-2 p-6">
                <div className="font-mono text-[12px] uppercase tracking-[0.06em] text-signal">{c.now}</div>
                <div className="mt-3 text-[22px] font-semibold">{c.label}</div>
                <p className="mt-2 text-[14px] leading-relaxed text-[#a7b4c2]">{c.desc}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 max-w-3xl text-[14px] leading-relaxed text-[#8b9aab]">
            Every spec sheet will list the country of origin of each major part, so a robot maker can work out their own claim.
          </p>
        </div>
      </section>

      {/* Why us */}
      <section className="py-20 md:py-28">
        <div className="container-x grid gap-12 md:grid-cols-2">
          <SectionHead eyebrow="Why us" title="We are our own first user.">
            Our sister company, Agrobo, is building a tomato-harvesting robot. Its picking hand is the EE-1, and its arms are where the joint
            actuator will go. Each part will be tested on a working field robot before we sell it to anyone else.
          </SectionHead>
          <div className="grid gap-4">
            {[
              ["Built from a real BOM", "Our numbers come from a 71-line bill of materials we priced both ways, not a market report."],
              ["Field-first design", "Designed to be sealed for mud and washdown and sized for 5-10 kg payload cobots."],
              ["Honest origin labels", "We publish where every major part comes from."],
            ].map(([t, d]) => (
              <Card key={t} className="p-5">
                <div className="text-[16px] font-semibold">{t}</div>
                <p className="mt-1.5 text-[14px] leading-relaxed text-ink-2">{d}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24">
        <div className="container-x">
          <div className="rounded-3xl bg-signal px-6 py-12 text-white md:px-14 md:py-16">
            <div className="max-w-2xl">
              <h2 className="text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] md:text-[42px]">Building a robot in the US? Tell us what you import.</h2>
              <p className="mt-4 text-[17px] leading-relaxed text-white/85">
                We are looking for a few robot makers in ag, food and logistics to shape the first gripper and joint specs with us.
              </p>
              <ButtonLink href="/partners" variant="primary" className="mt-8">Become a design partner</ButtonLink>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

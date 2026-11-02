import type { Metadata } from "next";
import Image from "next/image";
import { ButtonLink, Card, SectionHead, StageTag } from "@/components/ui";
import { PRODUCTS } from "@/lib/data";

export const metadata: Metadata = {
  title: "Products",
  description: "EE-1 soft food gripper, J-series joint actuator, wheel drive module and battery pack: status, design targets and what each needs to start.",
};

export default function Products() {
  const [ee1, ...rest] = PRODUCTS;
  return (
    <>
      <section className="border-b border-line py-16 md:py-20">
        <div className="container-x">
          <SectionHead eyebrow="Products" title="Four parts, in the order we can build them.">
            Nothing here is for sale yet. These are design targets, with the status of each stated plainly.
          </SectionHead>
        </div>
      </section>

      <section id={ee1.id} className="scroll-mt-20 py-16 md:py-20">
        <div className="container-x grid items-start gap-10 md:grid-cols-[1fr_1.1fr]">
          <div className="rounded-2xl border border-line bg-[#dfe6ec] p-4">
            <Image src="/ee1-render.png" alt="CAD render of the EE-1 gripper" width={1400} height={1200} className="h-auto w-full rounded-xl" />
            <div className="mt-3 px-1 font-mono text-[11px] uppercase tracking-[0.06em] text-[#4a5866]">CAD render · not yet built</div>
          </div>
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-[14px] text-muted">{ee1.code}</span>
              <StageTag stage={ee1.stage} />
            </div>
            <h2 className="mt-3 text-[34px] font-semibold tracking-[-0.02em] md:text-[44px]">{ee1.name}</h2>
            <p className="mt-4 text-[17px] leading-relaxed text-ink-2">{ee1.summary}</p>
            <div className="mt-6 rounded-xl border border-signal/30 bg-signal-soft px-4 py-3 text-[14px] text-ink">
              <span className="font-medium">Status:</span> {ee1.status}
            </div>
            <ul className="mt-6 grid gap-2.5">
              {ee1.bullets.map((b) => (
                <li key={b} className="flex gap-3 text-[15px] text-ink-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />
                  {b}
                </li>
              ))}
            </ul>
            <div className="mt-6 grid grid-cols-2 gap-4 border-t border-line pt-6 text-[14px]">
              <div>
                <div className="text-muted">To start production</div>
                <div className="mt-1 font-medium">{ee1.startCost}</div>
              </div>
              <div>
                <div className="text-muted">First user</div>
                <div className="mt-1 font-medium">Agrobo tomato harvester, 2 per robot</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-line bg-card py-16 md:py-20">
        <div className="container-x grid gap-6 lg:grid-cols-3">
          {rest.map((p) => (
            <Card key={p.id} className="scroll-mt-20 bg-paper p-6">
              <div id={p.id} className="flex items-center justify-between">
                <span className="font-mono text-[13px] text-muted">{p.code}</span>
                <StageTag stage={p.stage} />
              </div>
              <h3 className="mt-4 text-[22px] font-semibold tracking-[-0.01em]">{p.name}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{p.summary}</p>
              <ul className="mt-4 grid gap-2">
                {p.bullets.map((b) => (
                  <li key={b} className="flex gap-2.5 text-[14px] text-ink-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-steel" />
                    {b}
                  </li>
                ))}
              </ul>
              <div className="mt-5 space-y-1 border-t border-line pt-4 text-[13px]">
                <div><span className="text-muted">Status:</span> {p.status}</div>
                <div><span className="text-muted">To start:</span> {p.startCost}</div>
              </div>
            </Card>
          ))}
        </div>
        <div className="container-x mt-10">
          <ButtonLink href="/partners">Shape these specs with us</ButtonLink>
        </div>
      </section>
    </>
  );
}

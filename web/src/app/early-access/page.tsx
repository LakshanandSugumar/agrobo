import type { Metadata } from "next";
import { EarlyAccessForm } from "@/components/EarlyAccessForm";

export const metadata: Metadata = { title: "Early access" };

export default function Page() {
  return (
    <section className="container-x grid gap-12 py-16 md:py-24 lg:grid-cols-[1fr_1.3fr]">
      <div>
        <div className="eyebrow">Early access</div>
        <h1 className="mt-3 text-[40px] font-semibold leading-[1.05] tracking-[-0.03em] md:text-[56px]">
          Let&apos;s pick your <span className="font-serif font-normal italic">first robot-harvested rows.</span>
        </h1>
        <p className="mt-5 text-[17px] leading-relaxed text-ink-2">
          We&apos;re choosing one Southwest Florida fresh-market tomato grower for a paid spring 2027 pilot on 2 to 5 acres,
          priced per bucket below your crew cost with a hand crew on call. Robot makers who want a US-built gripper can
          sign up here too.
        </p>
        <ul className="mt-8 space-y-3 text-[15px]">
          {["A per-bucket price worked out from your crew's last season", "A pick forecast for one of your blocks", "A seat in our first pilot season"].map((t) => (
            <li key={t} className="flex gap-3">
              <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-brand text-[11px] text-white">✓</span>
              {t}
            </li>
          ))}
        </ul>
      </div>
      <EarlyAccessForm />
    </section>
  );
}

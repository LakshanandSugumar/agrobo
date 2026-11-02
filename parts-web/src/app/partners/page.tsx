import type { Metadata } from "next";
import { InquiryForm } from "@/components/InquiryForm";
import { SectionHead } from "@/components/ui";

export const metadata: Metadata = {
  title: "Design partners",
  description: "Robot makers building in the US: tell us what you import and shape the first gripper and joint specs.",
};

export default function Partners() {
  return (
    <section className="py-16 md:py-24">
      <div className="container-x grid gap-12 md:grid-cols-[1fr_1.4fr]">
        <div>
          <SectionHead eyebrow="Design partners" title="Help us decide what to build second.">
            We are looking for robot makers in agriculture, food and logistics who want US-built parts. Tell us what you import and how
            many robots you build.
          </SectionHead>
          <ul className="mt-8 space-y-4 text-[15px] text-ink-2">
            {[
              "Early say in the gripper and joint specs",
              "First test units at cost when they exist",
              "Country of origin for every major part, in writing",
            ].map((t) => (
              <li key={t} className="flex gap-3"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" />{t}</li>
            ))}
          </ul>
          <p className="mt-8 text-[13px] leading-relaxed text-muted">
            We are pre-production and have not shipped a part. We will not share your details with anyone.
          </p>
        </div>
        <InquiryForm />
      </div>
    </section>
  );
}

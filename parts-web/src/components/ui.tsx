import Link from "next/link";
import type { ReactNode } from "react";
import type { Stage } from "@/lib/data";

export function ButtonLink({
  href, children, variant = "primary", className = "",
}: { href: string; children: ReactNode; variant?: "primary" | "secondary" | "signal" | "ghost-dark"; className?: string }) {
  const styles = {
    primary: "bg-ink text-paper hover:bg-steel",
    secondary: "border border-line-2 bg-card text-ink hover:border-ink",
    signal: "bg-signal text-white hover:bg-[#c03f0c]",
    "ghost-dark": "border border-night-line text-white hover:border-[#5f7387]",
  }[variant];
  return (
    <Link href={href} className={`inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-[15px] font-medium transition ${styles} ${className}`}>
      {children}
    </Link>
  );
}

export function SectionHead({ eyebrow, title, children, dark = false }: {
  eyebrow: string; title: ReactNode; children?: ReactNode; dark?: boolean;
}) {
  return (
    <div className="max-w-3xl">
      <div className="eyebrow">{eyebrow}</div>
      <h2 className={`mt-3 text-[30px] font-semibold leading-[1.1] tracking-[-0.02em] md:text-[42px] ${dark ? "text-white" : "text-ink"}`}>{title}</h2>
      {children && <p className={`mt-4 text-[17px] leading-relaxed ${dark ? "text-[#a7b4c2]" : "text-ink-2"}`}>{children}</p>}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-card ${className}`}>{children}</div>;
}

const STAGE_STYLE: Record<Stage, string> = {
  Now: "bg-signal text-white",
  Next: "bg-steel text-white",
  Later: "border border-line-2 text-ink-2",
  "We buy": "border border-line-2 text-muted",
};

export function StageTag({ stage }: { stage: Stage }) {
  return <span className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.06em] ${STAGE_STYLE[stage]}`}>{stage}</span>;
}

export function Estimate({ dark = false }: { dark?: boolean }) {
  return (
    <span
      title="List prices, quotes and engineering estimates at pilot quantity, from Agrobo's harvester bill of materials (rev A.1 imported vs rev B US-sourced, Nov 2026)."
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.06em] ${dark ? "border-night-line text-[#a7b4c2]" : "border-line-2 text-muted"}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-signal" />
      BOM estimate
    </span>
  );
}

import Link from "next/link";
import type { ReactNode } from "react";

export function ButtonLink({
  href, children, variant = "primary", className = "",
}: { href: string; children: ReactNode; variant?: "primary" | "secondary" | "lime" | "ghost-dark"; className?: string }) {
  const styles = {
    primary: "bg-ink text-paper hover:bg-brand-ink",
    secondary: "border border-line-2 bg-card text-ink hover:border-ink",
    lime: "bg-lime text-ink hover:bg-[#e3fa8f]",
    "ghost-dark": "border border-night-line text-white hover:border-[#5d7266]",
  }[variant];
  return (
    <Link href={href} className={`inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-[15px] font-medium transition ${styles} ${className}`}>
      {children}
    </Link>
  );
}

export function Modeled({ className = "", dark = false }: { className?: string; dark?: boolean }) {
  return (
    <span
      title="Output of Agrobo's ROS 2 season simulation. Perception, manipulation, prices and costs are calibrated models, not field data."
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.06em] ${
        dark ? "border-night-line text-[#a9b8b0]" : "border-line-2 text-muted"
      } ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dark ? "bg-lime" : "bg-brand"}`} />
      Simulated
    </span>
  );
}

export function SectionHead({ eyebrow, title, children, dark = false, center = false }: {
  eyebrow: string; title: ReactNode; children?: ReactNode; dark?: boolean; center?: boolean;
}) {
  return (
    <div className={`max-w-3xl ${center ? "mx-auto text-center" : ""}`}>
      <div className={`eyebrow ${dark ? "!text-lime" : ""}`}>{eyebrow}</div>
      <h2 className={`mt-3 text-[32px] font-semibold leading-[1.1] tracking-[-0.02em] md:text-[44px] ${dark ? "text-white" : "text-ink"}`}>
        {title}
      </h2>
      {children && <p className={`mt-4 text-[17px] leading-relaxed ${dark ? "text-[#a9b8b0]" : "text-ink-2"}`}>{children}</p>}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-card ${className}`}>{children}</div>;
}

export function Stat({ value, label, sub, dark = false }: { value: ReactNode; label: string; sub?: string; dark?: boolean }) {
  return (
    <div>
      <div className={`tabular text-[34px] font-semibold tracking-[-0.03em] md:text-[44px] ${dark ? "text-white" : "text-ink"}`}>{value}</div>
      <div className={`mt-1 text-[14px] font-medium ${dark ? "text-[#dfe7e2]" : "text-ink"}`}>{label}</div>
      {sub && <div className={`mt-0.5 text-[13px] ${dark ? "text-[#8fa197]" : "text-muted"}`}>{sub}</div>}
    </div>
  );
}

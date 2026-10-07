import Link from "next/link";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="bg-night text-[#c9d3cd]">
      <div className="container-x grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Logo dark className="text-white" />
          <p className="mt-4 max-w-xs text-[14px] leading-relaxed text-[#8fa197]">
            The autonomous farm operator. We automate farming&apos;s dirty work, from the land deal to the last sale.
          </p>
        </div>
        <FooterCol
          title="Product"
          links={[
            ["/platform", "Platform"],
            ["/platform/land", "Land Scout"],
            ["/platform/economics", "Farm economics"],
            ["/platform/market", "Market desk"],
            ["/platform/season", "Season replay"],
          ]}
        />
        <FooterCol
          title="Company"
          links={[
            ["/technology", "Technology"],
            ["/results", "Simulation results"],
            ["/early-access", "Early access"],
          ]}
        />
        <FooterCol
          title="Developers"
          links={[
            ["/technology#api", "Public API"],
            ["/api/kpis", "KPI feed (JSON)"],
            ["/api/health", "Status"],
          ]}
        />
      </div>
      <div className="border-t border-night-line">
        <div className="container-x flex flex-col justify-between gap-2 py-6 text-[12px] text-[#7d8f85] md:flex-row">
          <span>© {2026} Agrobo. All rights reserved.</span>
          <span>
            Performance figures on this site come from Agrobo&apos;s ROS 2 simulation and are modeled, not field-measured.
          </span>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-[#7d8f85]">{title}</div>
      <ul className="mt-4 space-y-2.5 text-[14px]">
        {links.map(([href, label]) => (
          <li key={href}>
            <Link href={href} className="hover:text-white">
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

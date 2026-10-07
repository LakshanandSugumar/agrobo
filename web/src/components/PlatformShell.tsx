"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  ["/platform", "Overview"],
  ["/platform/land", "Land Scout"],
  ["/platform/economics", "Farm economics"],
  ["/platform/market", "Market desk"],
  ["/platform/season", "Season replay"],
];

export function PlatformTabs() {
  const path = usePathname();
  return (
    <div className="sticky top-16 z-40 border-b border-line bg-paper/90 backdrop-blur">
      <div className="container-x flex gap-1 overflow-x-auto py-2">
        {TABS.map(([href, label]) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`whitespace-nowrap rounded-full px-3.5 py-1.5 text-[14px] transition ${
                active ? "bg-ink text-paper" : "text-ink-2 hover:bg-[#ecebe3]"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

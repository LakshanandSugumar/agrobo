"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Logo } from "./Logo";

const LINKS = [
  { href: "/#lifecycle", label: "How it works" },
  { href: "/platform", label: "Platform" },
  { href: "/technology", label: "Technology" },
  { href: "/results", label: "Results" },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  const path = usePathname();
  return (
    <header className="sticky top-0 z-50 border-b border-line/80 bg-paper/85 backdrop-blur-md">
      <div className="container-x flex h-16 items-center justify-between">
        <Link href="/" aria-label="Agrobo home" onClick={() => setOpen(false)}>
          <Logo />
        </Link>
        <nav className="hidden items-center gap-8 text-[14px] text-ink-2 md:flex">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`transition-colors hover:text-ink ${path.startsWith(l.href) && l.href !== "/#lifecycle" ? "text-ink font-medium" : ""}`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <Link href="/platform" className="text-[14px] text-ink-2 hover:text-ink">
            Try the demo
          </Link>
          <Link
            href="/early-access"
            className="rounded-full bg-ink px-4 py-2 text-[14px] font-medium text-paper transition hover:bg-brand-ink"
          >
            Get early access
          </Link>
        </div>
        <button
          className="rounded-md p-2 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>
      {open && (
        <nav className="border-t border-line bg-paper md:hidden">
          <div className="container-x flex flex-col py-3">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} className="py-3 text-[16px]" onClick={() => setOpen(false)}>
                {l.label}
              </Link>
            ))}
            <Link
              href="/early-access"
              onClick={() => setOpen(false)}
              className="mt-2 rounded-full bg-ink px-4 py-3 text-center font-medium text-paper"
            >
              Get early access
            </Link>
          </div>
        </nav>
      )}
    </header>
  );
}

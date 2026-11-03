import { COMPANY } from "@/lib/data";

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="7" fill={dark ? "#ffffff" : "#0f1720"} />
        <path d="M9 23V9h14M9 16h10" stroke="#d9480f" strokeWidth="3.2" fill="none" strokeLinecap="square" />
      </svg>
      <span className={`text-[17px] font-semibold tracking-[-0.01em] ${dark ? "text-white" : "text-ink"}`}>{COMPANY.name}</span>
      <span
        title="The company name is not decided yet"
        className={`rounded border px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.06em] ${dark ? "border-night-line text-[#8b9aab]" : "border-line-2 text-muted"}`}
      >
        working name
      </span>
    </span>
  );
}

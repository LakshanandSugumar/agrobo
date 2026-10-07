export function Logo({ className = "", dark = false }: { className?: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <svg viewBox="0 0 64 64" className="h-7 w-7" aria-hidden>
        <rect width="64" height="64" rx="14" fill={dark ? "#d7f36b" : "#0b3d2a"} />
        <path d="M14 46c10-2 16-9 18-20 2 11 8 18 18 20" fill="none" stroke={dark ? "#0b3d2a" : "#d7f36b"} strokeWidth="5" strokeLinecap="round" />
        <circle cx="32" cy="18" r="5" fill={dark ? "#0b3d2a" : "#d7f36b"} />
      </svg>
      <span className="text-[19px]">agrobo</span>
    </span>
  );
}

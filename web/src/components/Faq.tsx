export function Faq({ items }: { items: [string, string][] }) {
  return (
    <div className="divide-y divide-line rounded-2xl border border-line bg-card">
      {items.map(([q, a]) => (
        <details key={q} className="group px-5 py-4 md:px-6">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[16px] font-medium">
            {q}
            <span className="text-muted transition group-open:rotate-45">+</span>
          </summary>
          <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{a}</p>
        </details>
      ))}
    </div>
  );
}

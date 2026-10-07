import type { ReactNode } from "react";
import { Modeled } from "./ui";

export function PageHead({ eyebrow, title, children, modeled = true }: { eyebrow: string; title: ReactNode; children?: ReactNode; modeled?: boolean }) {
  return (
    <div className="container-x pb-8 pt-12 md:pt-16">
      <div className="flex flex-wrap items-center gap-3">
        <span className="eyebrow">{eyebrow}</span>
        {modeled && <Modeled />}
      </div>
      <h1 className="mt-3 max-w-4xl text-[36px] font-semibold leading-[1.06] tracking-[-0.03em] md:text-[52px]">{title}</h1>
      {children && <p className="mt-4 max-w-3xl text-[17px] leading-relaxed text-ink-2">{children}</p>}
    </div>
  );
}

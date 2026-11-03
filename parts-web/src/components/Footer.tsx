import Link from "next/link";
import { COMPANY } from "@/lib/data";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="bg-night text-[#c5cfda]">
      <div className="container-x grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Logo dark />
          <p className="mt-4 max-w-sm text-[14px] leading-relaxed text-[#8b9aab]">
            Pre-production. We have not shipped a part. Prices and specs are design targets and estimates from our own robot&apos;s bill of
            materials, not quotes or test results.
          </p>
        </div>
        <div className="text-[14px]">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-[#6f8091]">Company</div>
          <ul className="mt-3 space-y-2">
            <li><Link href="/products" className="hover:text-white">Products</Link></li>
            <li><Link href="/gap" className="hover:text-white">The cost gap</Link></li>
            <li><Link href="/partners" className="hover:text-white">Design partners</Link></li>
          </ul>
        </div>
        <div className="text-[14px]">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-[#6f8091]">Sister company</div>
          <p className="mt-3 leading-relaxed text-[#8b9aab]">
            Our first user will be Agrobo, an AI tomato harvester. These parts are designed for its robot and will be tested on it first.
          </p>
        </div>
      </div>
      <div className="border-t border-night-line">
        <div className="container-x flex flex-wrap justify-between gap-2 py-5 text-[12px] text-[#6f8091]">
          <span>© 2026 {COMPANY.legal}</span>
          <span>Designed in the USA</span>
        </div>
      </div>
    </footer>
  );
}

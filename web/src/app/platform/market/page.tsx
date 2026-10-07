import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { MarketDesk } from "@/components/tools/MarketDesk";

export const metadata: Metadata = { title: "Market desk" };

export default function Page() {
  return (
    <>
      <PageHead eyebrow="Phase 5 · Sell" title="Market desk">
        Our B2B selling engine, replayed over the real day-by-day harvest, grade mix and Field Ledger forecasts from the
        simulated season. Change the market and watch how the policy responds. The baseline is what most farms do today:
        sell ungraded field-run at wholesale the same day.
      </PageHead>
      <MarketDesk />
    </>
  );
}

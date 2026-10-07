import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { SeasonReplay } from "@/components/tools/SeasonReplay";
import { compactSeason, notwin, twin } from "@/lib/data";

export const metadata: Metadata = { title: "Season replay" };

export default function Page() {
  return (
    <>
      <PageHead eyebrow="All phases" title="Season replay">
        Every day of a logged 125-day ROS 2 season: what the Field Ledger saw, the work orders it issued, what each robot
        did and what was sold. Switch to the ablation to watch the same robots work without the twin.
      </PageHead>
      <SeasonReplay twin={compactSeason(twin)} notwin={compactSeason(notwin)} bt={twin.bt ?? ""} phases={twin.phases} />
    </>
  );
}

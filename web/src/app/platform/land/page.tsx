import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { LandScout } from "@/components/tools/LandScout";

export const metadata: Metadata = { title: "Land Scout" };

export default function Page() {
  return (
    <>
      <PageHead eyebrow="Phase 1 · Source" title="Land Scout">
        The strategy engine from our simulation, live. It scores each parcel on eight GIS factors with a weighted geometric
        mean (one deal-breaker kills the parcel), weights crops by market demand and automation fit, and runs a 5-year NPV
        with the robot fleet in the capex. Parcels here are synthesised; production pulls SoilGrids, USGS 3DEP slope and
        county parcel data.
      </PageHead>
      <LandScout />
    </>
  );
}

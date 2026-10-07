import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { Economics } from "@/components/tools/Economics";

export const metadata: Metadata = { title: "Farm economics" };

export default function Page() {
  return (
    <>
      <PageHead eyebrow="Phases 2-4 · Prepare, grow, harvest" title="What would your farm cost to run on Agrobo?">
        Pick an acreage and local rates. We scale the robot hours, energy, nitrogen, yield and peak fleet workload measured
        in our simulated seasons, then price them with the same economics model the simulation uses.
      </PageHead>
      <Economics />
    </>
  );
}

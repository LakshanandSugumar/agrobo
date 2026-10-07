import type { Metadata } from "next";
import { PageHead } from "@/components/PageHead";
import { PathPlot } from "@/components/PathPlot";
import { Card, Modeled, SectionHead } from "@/components/ui";

export const metadata: Metadata = { title: "Technology" };

const STACK = [
  ["Source", "Survey UAV, soil-probe UGV with VIS-NIR spectrometer, RTK base", "Pedotransfer regressors, kriged soil maps with variance", "GIS ingest, fuzzy land suitability, crop matrix, NPV/IRR, parcel ranking API"],
  ["Prepare", "Electric prep UGV with ISOBUS implements, 3D LiDAR, dual-antenna RTK", "LiDAR obstacle segmentation, traversability costmaps", "Field-layout generator, coverage planner, as-built map that keys the Field Ledger"],
  ["Grow", "Scout UAV (RGB + multispectral), modular UGV with laser weeder and micro-doser", "YOLO11-seg crop/weed (TensorRT INT8 on Jetson Orin), NDRE N-stress, fire/no-fire verify", "Field Ledger twin, per-target work orders, scouting scheduler"],
  ["Harvest", "Picker implement: 2 × 6-DoF arms, soft tactile grippers, eye-in-hand stereo; hauler UGV", "Fruit segmentation with ripeness head, 6D peduncle pose, grasp policy with RL residual", "Forecast-driven harvest planner, robot-to-row allocation, bin traceability"],
  ["Sell", "Hyperspectral grading line, delta-robot packer, forced-air pre-cooler, cold room", "Spectral grading (ripeness, firmness, bruise), shelf-life model", "B2B selling engine, buyer portal, EDI, lot-level traceability"],
];

const NODES = [
  ["/field_world", "Ground-truth farm: growth, weeds, soil, weather"],
  ["/strategy_engine", "GIS suitability, crop matrix, NPV"],
  ["/fleet_path_planner", "Boustrophedon coverage and 2-opt target tours"],
  ["/prep_ugv", "Clear, lay out, till, drip, transplant"],
  ["/scout_uav", "Survey passes, SensorFrame per strip"],
  ["/perception_weed_classifier", "Frames → weed detections"],
  ["/perception_crop_health", "Frames → nitrogen stress"],
  ["/perception_ripeness_estimator", "Frames → fruit + ripeness"],
  ["/ugv_alpha, /ugv_beta", "Modular UGVs: weeder, doser, picker arm"],
  ["/hauler_ugv", "Bins from field to hub"],
  ["/hub_grading_station", "Hyperspectral grading, packing, shelf life"],
  ["/market_engine", "Contracts, spot, wholesale, processor"],
  ["/cloud_sync", "Rural LTE outages, store-and-forward"],
  ["/mission_orchestrator", "Behaviour tree + Field Ledger + work-order auction"],
  ["/kpi_recorder", "Event bus → KPIs"],
  ["/gz_row_follower", "Pure pursuit on Gazebo, cross-track report"],
];

const API = [
  ["POST", "/api/land/evaluate", "{ seed, candidates, crop }", "Ranked parcel-crop pairs with factor scores and 5-year cash flow"],
  ["POST", "/api/land/score", "{ parcel: { ph, om_pct, slope_pct, … } }", "Suitability and NPV of one parcel for every crop"],
  ["POST", "/api/economics", "{ areaHa, labourUsdH, electricityUsdKwh, twin }", "Fleet size, capex, OpEx per kg vs conventional, payback"],
  ["POST", "/api/market", "{ seed, areaHa, config }", "Season of B2B selling over the simulated harvest"],
  ["GET", "/api/season?arm=twin|notwin", "", "Day-by-day log of the ROS 2 season run"],
  ["GET", "/api/kpis", "", "3-seed KPI summary, twin vs ablation"],
  ["POST", "/api/waitlist", "{ name, email, company, acres, … }", "Early-access signup"],
];

export default function Page() {
  return (
    <>
      <PageHead eyebrow="Technology" title="One twin, one modular fleet, one behaviour tree." modeled={false}>
        Agrobo is a full-stack system: hardware where work is physical, edge AI where decisions must survive a dead LTE
        link, and cloud software for everything else. The whole lifecycle runs today as a ROS 2 Jazzy simulation with a
        Gazebo Harmonic physics tier.
      </PageHead>

      <section className="container-x pb-16">
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-[13.5px]">
              <thead className="bg-[#f3f1ea] text-left font-mono text-[11px] uppercase tracking-wider text-muted">
                <tr>
                  <th className="px-5 py-3">Phase</th>
                  <th className="px-5 py-3">Hardware</th>
                  <th className="px-5 py-3">Edge AI</th>
                  <th className="px-5 py-3">Cloud / SaaS</th>
                </tr>
              </thead>
              <tbody>
                {STACK.map(([p, h, a, c]) => (
                  <tr key={p} className="border-t border-line align-top">
                    <td className="px-5 py-4 font-semibold">{p}</td>
                    <td className="px-5 py-4 text-ink-2">{h}</td>
                    <td className="px-5 py-4 text-ink-2">{a}</td>
                    <td className="px-5 py-4 text-ink-2">{c}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </section>

      <section className="border-y border-line bg-card py-20">
        <div className="container-x grid gap-12 lg:grid-cols-[1fr_1.3fr]">
          <SectionHead eyebrow="Simulation" title="Two fidelity tiers behind the same ROS 2 interfaces.">
            No single physics engine can run a 125-day season at plant level. The season tier runs every node with a crop
            model and kinematic motion in about two minutes. The physics tier puts the same robot in Gazebo to check
            wheel slip, RTK noise and row keeping. Manipulation training in Isaac Lab is next.
          </SectionHead>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["Season tier", "ROS 2 nodes + crop model", "All 5 phases, agronomy, perception error, logistics, market, KPIs", "~1-2 min / season"],
              ["Physics tier", "Gazebo Harmonic via ros_gz", "Wheel-terrain contact, RTK/IMU noise, cross-track error", "Real time, headless"],
              ["Manipulation tier", "Isaac Sim / Isaac Lab", "Deformable-fruit grasping, RL residual policy", "Next milestone"],
            ].map(([t, e, w, time], i) => (
              <div key={t} className={`rounded-2xl border p-5 ${i === 2 ? "border-dashed border-line-2" : "border-line bg-paper"}`}>
                <div className="font-semibold">{t}</div>
                <div className="mt-1 font-mono text-[12px] text-brand">{e}</div>
                <p className="mt-3 text-[13.5px] leading-relaxed text-ink-2">{w}</p>
                <div className="mt-3 text-[12px] text-muted">{time}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="physics" className="container-x scroll-mt-24 py-20">
        <div className="flex flex-wrap items-center gap-3">
          <span className="eyebrow">Physics check</span>
          <Modeled />
        </div>
        <h2 className="mt-3 max-w-3xl text-[30px] font-semibold leading-tight tracking-[-0.02em] md:text-[40px]">
          A skid-steer robot holds the crop lane to about 3 cm on RTK. On odometry alone it ends up metres into the crop.
        </h2>
        <Card className="mt-8 p-5 md:p-7">
          <PathPlot />
        </Card>
      </section>

      <section className="bg-night py-20 text-white">
        <div className="container-x">
          <SectionHead dark eyebrow="ROS 2 graph" title="16 nodes. Every physical effect goes through one service.">
            Robots never mutate the world directly; they call /field/interact. That keeps the sim honest and makes each
            perception model a drop-in: replace infer() with a TensorRT network and the topic contract stays the same.
          </SectionHead>
          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {NODES.map(([n, d]) => (
              <div key={n} className="rounded-xl border border-night-line bg-night-2 p-4">
                <div className="font-mono text-[13px] text-lime">{n}</div>
                <div className="mt-1.5 text-[13px] text-[#a9b8b0]">{d}</div>
              </div>
            ))}
          </div>
          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-night-line bg-night-2 p-5">
              <div className="text-[15px] font-medium">Season behaviour tree (py_trees, edge hub)</div>
              <pre className="mt-4 overflow-x-auto font-mono text-[12px] leading-relaxed text-[#c9d3cd]">{`agrobo_season [Sequence*]
├─ phase1_sourcing   sourced? | evaluate_parcels
├─ phase2_prep       prepped? | prep_field
├─ phase3_establish  planted? | transplant
└─ season_loop [Repeat until day 125]
   └─ daily_cycle
      ├─ scouting      scout_due? → scout_field
      ├─ plan_work     Field Ledger → work orders → auction
      ├─ field_ops     [Parallel] lane_ugv_alpha, lane_ugv_beta
      ├─ logistics     haul_to_hub → hub_process_lots
      ├─ cloud_gate    link_up? → publish forecast | edge_only
      ├─ sell_inventory
      └─ advance_day`}</pre>
            </div>
            <div className="rounded-2xl border border-night-line bg-night-2 p-5">
              <div className="text-[15px] font-medium">How a robot switches jobs</div>
              <p className="mt-3 text-[14px] leading-relaxed text-[#a9b8b0]">
                There are no hard-coded modes. Each day the Field Ledger becomes prioritised work orders. Harvest wins when
                25 or more fruit are forecast ripe. Weeding triggers at 12 tracked weeds or a 4-day-old track. Dosing
                triggers on chlorosis. A swap-minimising auction assigns orders, and each UGV runs IDLE → TOOL_SWAP →
                HARVEST / WEED / DOSE → IDLE, hot-swapping its battery below 15%.
              </p>
              <p className="mt-3 text-[14px] leading-relaxed text-[#a9b8b0]">
                When the LTE link drops, the cloud gate falls back to edge-only mode: field work continues, contracted
                deliveries still ship, and events are replicated when the link returns.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="api" className="container-x scroll-mt-24 py-20">
        <SectionHead eyebrow="Public API" title="The platform is an API first.">
          Every tool on this site is a thin client over these endpoints, which run the simulation&apos;s models ported to
          TypeScript.
        </SectionHead>
        <Card className="mt-8 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-[13.5px]">
              <tbody>
                {API.map(([m, p, b, d]) => (
                  <tr key={p} className="border-t border-line first:border-t-0 align-top">
                    <td className="px-5 py-3.5">
                      <span className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold ${m === "GET" ? "bg-[#e6eefb] text-[#1d4fa3]" : "bg-brand-soft text-brand-ink"}`}>{m}</span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-[13px]">{p}</td>
                    <td className="px-5 py-3.5 font-mono text-[12px] text-muted">{b}</td>
                    <td className="px-5 py-3.5 text-ink-2">{d}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <pre className="mt-6 overflow-x-auto rounded-xl bg-night p-4 font-mono text-[12.5px] text-[#c9d3cd]">{`curl -s -X POST $SITE/api/economics -H 'content-type: application/json' \\
  -d '{"areaHa": 40, "labourUsdH": 22, "twin": true}' | jq '.agrobo.usdPerKg, .conventional.usdPerKg'`}</pre>
      </section>

      <section className="border-t border-line bg-[#f1efe7] py-20">
        <div className="container-x grid gap-10 lg:grid-cols-2">
          <SectionHead eyebrow="Honesty section" title="What is real code, and what is a model." />
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-5">
              <div className="font-semibold text-brand">Real code, ships to the robots</div>
              <ul className="mt-3 space-y-1.5 text-[14px] text-ink-2">
                <li>ROS 2 graph and all interfaces</li>
                <li>Behaviour tree and work-order auction</li>
                <li>Field Ledger twin and forecasting</li>
                <li>Coverage and tour planning</li>
                <li>Logistics, grading flow, selling engine</li>
              </ul>
            </Card>
            <Card className="p-5">
              <div className="font-semibold text-tomato">Calibrated stand-ins, replaced by pilot data</div>
              <ul className="mt-3 space-y-1.5 text-[14px] text-ink-2">
                <li>Crop physiology</li>
                <li>Perception network accuracy</li>
                <li>Grasp success, cycle-time constants, bruising</li>
                <li>Prices and costs</li>
              </ul>
            </Card>
          </div>
        </div>
      </section>
    </>
  );
}

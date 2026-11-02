// Every number on the site comes from here, so it can be checked in one place.
// Source: Agrobo harvester BOMs in robots/bom/ (rev A.1, imported; rev B, US-sourced, 2026-11-01).
// Prices are list prices, quotes or estimates at pilot quantity, not negotiated volume prices.

export const COMPANY = {
  // Working name. The company name is not decided yet.
  name: "Forgeline",
  legal: "Forgeline (working name, not incorporated)",
  tagline: "US-built robot hands and joints",
  email: "hello@example.com", // placeholder until a domain exists
};

export type Line = {
  part: string;
  qty: number;
  importSrc: string;
  importUnit: number;
  usSrc: string;
  usUnit: number | null; // null = no US source today
  note?: string;
};

export const BOM_LINES: Line[] = [
  { part: "6-axis arm", qty: 2, importSrc: "FAIRINO FR5, China", importUnit: 6999, usSrc: "Standard Bots Spark, assembled in NY", usUnit: 29500 },
  { part: "3D lidar", qty: 1, importSrc: "Livox Mid-360, China", importUnit: 749, usSrc: "Ouster OS0-64, US-built units", usUnit: 12000 },
  { part: "RTK heading GNSS", qty: 1, importSrc: "ArduSimple, Spain", importUnit: 650, usSrc: "Hemisphere Vector VR1000, AZ", usUnit: 4500 },
  { part: "Stereo camera", qty: 2, importSrc: "ZED X, France", importUnit: 599, usSrc: "Carnegie Robotics MultiSense S27, PA", usUnit: 1995 },
  { part: "Wheel drive", qty: 4, importSrc: "OZO hub motor, France", importUnit: 465, usSrc: "Motenergy motor + Winsmith reducer", usUnit: 1500 },
  { part: "Motor controllers (set)", qty: 1, importSrc: "Flipsky VESC x4, China", importUnit: 660, usSrc: "Roboteq dual x2", usUnit: 1800 },
  { part: "Gripper servo", qty: 2, importSrc: "DYNAMIXEL XM430, Korea", importUnit: 290, usSrc: "Teknic ClearPath, NY", usUnit: 350, note: "Inside our EE-1 gripper" },
  { part: "LFP cells", qty: 32, importSrc: "EVE LF105, China", importUnit: 52, usSrc: "No small-volume US source", usUnit: null, note: "US cell plants sell to automakers and grid" },
  { part: "Edge AI computer", qty: 1, importSrc: "NVIDIA Jetson Orin, Asia", importUnit: 3499, usSrc: "No US-made option", usUnit: null },
  { part: "Close-range depth camera", qty: 2, importSrc: "RealSense D405", importUnit: 272, usSrc: "No US option works at 0.1 m", usUnit: null },
];

export const ROBOT = {
  importBuilt: 51942, // rev A.1 per robot incl. assembly and test
  usBuilt: 129895, // rev B per robot incl. assembly and test
  armsImportPair: 2 * 6999,
  armsUsPair: 2 * 29500,
  shareUsAssembled: 0.566, // assembled in the US from imported subparts
  shareUsLikely: 0.369, // US-made or US maker, origin to confirm
  shareNoUsSource: 0.064,
};

export const ratio = (l: Line) => (l.usUnit == null ? null : l.usUnit / l.importUnit);
export const premiumPct = (a: number, b: number) => Math.round((b / a - 1) * 100);

export const usd = (n: number) =>
  n >= 10000 ? `$${(n / 1000).toFixed(1).replace(/\.0$/, "")}k` : `$${n.toLocaleString("en-US")}`;

export type Stage = "Now" | "Next" | "Later" | "We buy";

export const PRODUCTS: {
  id: string;
  code: string;
  name: string;
  stage: Stage;
  status: string;
  summary: string;
  bullets: string[];
  startCost: string;
  rfs: boolean;
}[] = [
  {
    id: "ee1",
    code: "EE-1",
    name: "Soft food gripper",
    stage: "Now",
    status: "Designed, CAD and printable parts done. Not yet built or tested on real fruit.",
    summary:
      "A three-finger gripper for picking soft produce. Suction draws the fruit in, flexible fingers wrap it without point loads, a wrist twist detaches it at the stem.",
    bullets: [
      "3 TPU Fin-Ray fingers, target grip 3.6 ± 0.55 N",
      "40 mm bellows suction cup that touches first and confirms the seal",
      "ISO 9409-1-50-4 flange, fits most cobots",
      "Eye-in-hand depth camera mount",
      "Sealed housing, IP65 target; fingers are weekly consumables",
      "US parts path: Teknic servo, Ultra Motion actuator, US-made TPU",
    ],
    startCost: "~$25k of printers, moulds and a test rig",
    rfs: true,
  },
  {
    id: "j1",
    code: "J-series",
    name: "Robot joint actuator",
    stage: "Next",
    status: "Concept. Needs a hardware co-founder and a seed round.",
    summary:
      "A frameless BLDC motor, strain-wave gear and absolute encoder in one sealed module, the building block of an arm. Joints are most of an arm's cost, and arms are most of the gap between an imported and a US-sourced robot.",
    bullets: [
      "Motor, strain-wave gear, encoder and driver in one housing",
      "Sized first for 5-10 kg payload cobot arms",
      "Magnets bought from a US recycler, not made by us",
      "Hard parts: gear tooth cutting, heat treatment, encoder accuracy",
    ],
    startCost: "$1-3M first line (gear cutting, heat treat, winding, test)",
    rfs: true,
  },
  {
    id: "wd1",
    code: "WD-1",
    name: "Wheel drive module",
    stage: "Later",
    status: "Concept. An assembly product on top of bought motors.",
    summary:
      "Motor, reducer and controller as one bolt-on module for field robots, replacing four separate purchases from four vendors.",
    bullets: ["Recycled-aluminium housing", "Sealed for mud and washdown", "One CAN interface"],
    startCost: "$0.3-1M (assembly and test)",
    rfs: true,
  },
  {
    id: "bp1",
    code: "BP-1",
    name: "Field robot battery pack",
    stage: "Later",
    status: "Concept. Pack assembly only; the cells would still be imported until US cells are sold in small volume.",
    summary:
      "A rugged LFP pack assembled in the US for field robots, with second-life EV modules as an option.",
    bullets: ["48 V class", "Second-life EV module option", "Cells imported until ~2027"],
    startCost: "$0.2-0.5M for pack assembly",
    rfs: true,
  },
];

export const NOT_DOING = [
  {
    what: "Rare-earth magnets",
    why: "China made about 94% of sintered magnets in 2024, but a plant costs $100M+ and US recyclers already lead. We plan to buy US-recycled magnets for our motors.",
  },
  {
    what: "Lidar and cameras",
    why: "Optics needs $10M+ and specialist talent, and US makers exist. We buy them.",
  },
  {
    what: "LFP cells",
    why: "A cell plant is a $1B+ business. We would assemble packs, not make cells.",
  },
  {
    what: "Totes, covers, aluminium frames",
    why: "Already made in the US at close to import prices. There is no gap to win.",
  },
];

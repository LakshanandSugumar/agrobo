import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { BOM_LINES, ROBOT, premiumPct, ratio } from "../src/lib/data";
import { parseInquiry } from "../src/lib/inquiry";

test("headline numbers match the rev B BOM summary", () => {
  assert.equal(premiumPct(ROBOT.importBuilt, ROBOT.usBuilt), 150);
  const share = ROBOT.shareUsAssembled + ROBOT.shareUsLikely + ROBOT.shareNoUsSource;
  assert.ok(Math.abs(share - 1) < 0.002, `origin shares sum to ${share}`);
  assert.equal(ROBOT.armsUsPair, 59000);
});

test("ratios are computed, and lines without a US source say so", () => {
  const arm = BOM_LINES.find((l) => l.part === "6-axis arm")!;
  assert.equal(ratio(arm)!.toFixed(1), "4.2");
  for (const l of BOM_LINES.filter((l) => l.usUnit == null)) assert.match(l.usSrc, /No /);
});

test("inquiry validation", () => {
  assert.equal(typeof parseInquiry({ name: "", email: "a@b.co" }), "string");
  assert.equal(typeof parseInquiry({ name: "A", email: "nope" }), "string");
  const q = parseInquiry({ name: " A ", email: "A@B.CO", imports: "x".repeat(5000) });
  assert.ok(typeof q !== "string");
  assert.equal(q.email, "a@b.co");
  assert.equal(q.imports.length, 1000);
});

// FTC: "Made in USA" needs all or virtually all US content. No page may claim it outright;
// the phrase may only appear where the copy says we don't claim it yet.
test("no unqualified Made in USA claim in site copy", () => {
  const files: string[] = [];
  const walk = (d: string) => {
    for (const f of readdirSync(d)) {
      const p = path.join(d, f);
      if (statSync(p).isDirectory()) walk(p);
      else if (/\.tsx?$/.test(p)) files.push(p);
    }
  };
  walk(path.join(__dirname, "../src"));
  for (const f of files) {
    const src = readFileSync(f, "utf8");
    for (const m of src.matchAll(/made in (the )?usa/gi)) {
      const around = src.slice(Math.max(0, m.index! - 160), m.index! + 160);
      assert.match(around, /not|only when|Not claimed/i, `${f}: "${m[0]}" without a qualifier`);
    }
  }
});

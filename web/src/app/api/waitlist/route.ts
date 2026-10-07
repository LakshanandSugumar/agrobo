import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { readJson } from "@/lib/http";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const clip = (v: unknown, n = 200) => (typeof v === "string" ? v.trim().slice(0, n) : "");

// POST /api/waitlist  { name, email, company?, role?, acres?, crop?, message? }
// Delivery: if WAITLIST_WEBHOOK_URL is set (Slack, Zapier, Formspree, a CRM), the lead is
// POSTed there. Otherwise it is appended to .data/waitlist.jsonl, which only persists on a
// long-running server (not on serverless hosts).
export async function POST(req: Request) {
  const b = await readJson(req);
  const lead = {
    name: clip(b.name, 120),
    email: clip(b.email, 200).toLowerCase(),
    company: clip(b.company, 160),
    role: clip(b.role, 60),
    acres: clip(b.acres, 20),
    crop: clip(b.crop, 60),
    message: clip(b.message, 1000),
    at: new Date().toISOString(),
  };
  if (clip(b.website)) return Response.json({ ok: true }); // honeypot
  if (!lead.name || !EMAIL.test(lead.email)) {
    return Response.json({ ok: false, error: "Please give your name and a valid email." }, { status: 400 });
  }
  const hook = process.env.WAITLIST_WEBHOOK_URL;
  try {
    if (hook) {
      const r = await fetch(hook, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: `New Agrobo lead: ${lead.name} <${lead.email}> ${lead.company} (${lead.acres} acres, ${lead.role})`, ...lead }),
      });
      if (!r.ok) throw new Error(`webhook ${r.status}`);
    } else {
      const dir = path.join(process.cwd(), ".data");
      await mkdir(dir, { recursive: true });
      await appendFile(path.join(dir, "waitlist.jsonl"), JSON.stringify(lead) + "\n");
    }
  } catch (e) {
    console.error("waitlist delivery failed", e);
    return Response.json({ ok: false, error: "We couldn't save that just now. Please try again in a minute." }, { status: 502 });
  }
  return Response.json({ ok: true });
}

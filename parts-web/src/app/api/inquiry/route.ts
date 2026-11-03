import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { parseInquiry } from "@/lib/inquiry";

// POST /api/inquiry  { name, email, company?, interest?, imports?, volume? }
// If INQUIRY_WEBHOOK_URL is set (Slack, Zapier, Formspree, a CRM) the inquiry is POSTed there.
// Otherwise it is appended to .data/inquiries.jsonl, which only persists on a long-running server.
export async function POST(req: Request) {
  let b: Record<string, unknown> = {};
  try {
    const j = await req.json();
    if (j && typeof j === "object") b = j as Record<string, unknown>;
  } catch {}
  if (typeof b.website === "string" && b.website.trim()) return Response.json({ ok: true }); // honeypot
  const q = parseInquiry(b);
  if (typeof q === "string") return Response.json({ ok: false, error: q }, { status: 400 });
  const hook = process.env.INQUIRY_WEBHOOK_URL;
  try {
    if (hook) {
      const r = await fetch(hook, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: `New parts inquiry: ${q.name} <${q.email}> ${q.company} (${q.interest})`, ...q }),
      });
      if (!r.ok) throw new Error(`webhook ${r.status}`);
    } else {
      const dir = path.join(process.cwd(), ".data");
      await mkdir(dir, { recursive: true });
      await appendFile(path.join(dir, "inquiries.jsonl"), JSON.stringify(q) + "\n");
    }
  } catch (e) {
    console.error("inquiry delivery failed", e);
    return Response.json({ ok: false, error: "We couldn't save that just now. Please try again in a minute." }, { status: 502 });
  }
  return Response.json({ ok: true });
}

"use client";

import { useState } from "react";

export function InquiryForm() {
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [err, setErr] = useState("");
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState("sending");
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      const r = await fetch("/api/inquiry", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
      const j = await r.json();
      if (!r.ok || !j.ok) throw new Error(j.error ?? "Something went wrong.");
      setState("done");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setState("error");
    }
  }
  if (state === "done") {
    return (
      <div className="rounded-2xl border border-signal bg-signal-soft p-8">
        <div className="text-[22px] font-semibold">Thanks, we got it.</div>
        <p className="mt-2 text-ink-2">The founder reads every one of these and will reply personally.</p>
      </div>
    );
  }
  const input = "mt-1.5 w-full rounded-lg border border-line-2 bg-card px-3 py-2.5 text-[15px] outline-none focus:border-ink";
  return (
    <form onSubmit={submit} className="grid gap-4 rounded-2xl border border-line bg-card p-6 md:grid-cols-2 md:p-8">
      <label className="text-[13px] text-ink-2">Name<input name="name" required className={input} autoComplete="name" /></label>
      <label className="text-[13px] text-ink-2">Work email<input name="email" type="email" required className={input} autoComplete="email" /></label>
      <label className="text-[13px] text-ink-2">Company<input name="company" className={input} autoComplete="organization" /></label>
      <label className="text-[13px] text-ink-2">
        Most interested in
        <select name="interest" className={input} defaultValue="EE-1 gripper">
          <option>EE-1 gripper</option>
          <option>Joint actuator</option>
          <option>Wheel drive module</option>
          <option>Battery pack</option>
          <option>Something else</option>
        </select>
      </label>
      <label className="text-[13px] text-ink-2 md:col-span-2">
        Which parts do you import today, and from where?
        <textarea name="imports" rows={3} placeholder="e.g. 6-axis arms from China, hub motors from Europe" className={input} />
      </label>
      <label className="text-[13px] text-ink-2">
        Robots per year
        <select name="volume" className={input} defaultValue="Prototype only">
          <option>Prototype only</option>
          <option>1-10</option>
          <option>10-100</option>
          <option>100+</option>
        </select>
      </label>
      <input name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />
      <div className="flex flex-wrap items-end gap-4">
        <button disabled={state === "sending"} className="rounded-full bg-ink px-6 py-3 text-[15px] font-medium text-paper hover:bg-steel disabled:opacity-60">
          {state === "sending" ? "Sending…" : "Send"}
        </button>
        {state === "error" && <span className="text-[14px] text-signal">{err}</span>}
      </div>
    </form>
  );
}

"use client";

import { useState } from "react";

export function EarlyAccessForm() {
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [err, setErr] = useState("");
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState("sending");
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    try {
      const r = await fetch("/api/waitlist", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
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
      <div className="rounded-2xl border border-brand bg-brand-soft p-8">
        <div className="text-[22px] font-semibold">You&apos;re on the list.</div>
        <p className="mt-2 text-ink-2">We&apos;ll be in touch as we line up pilot partners for the first operated season.</p>
      </div>
    );
  }
  const input = "mt-1.5 w-full rounded-lg border border-line-2 bg-card px-3 py-2.5 text-[15px] outline-none focus:border-ink";
  return (
    <form onSubmit={submit} className="grid gap-4 rounded-2xl border border-line bg-card p-6 md:grid-cols-2 md:p-8">
      <label className="text-[13px] text-ink-2">Name<input name="name" required className={input} autoComplete="name" /></label>
      <label className="text-[13px] text-ink-2">Work email<input name="email" type="email" required className={input} autoComplete="email" /></label>
      <label className="text-[13px] text-ink-2">Company or farm<input name="company" className={input} autoComplete="organization" /></label>
      <label className="text-[13px] text-ink-2">
        I am a…
        <select name="role" className={input} defaultValue="Landowner">
          <option>Landowner</option>
          <option>Grower</option>
          <option>Produce buyer</option>
          <option>Investor</option>
          <option>Engineer</option>
          <option>Other</option>
        </select>
      </label>
      <label className="text-[13px] text-ink-2">Acres (if any)<input name="acres" inputMode="numeric" className={input} /></label>
      <label className="text-[13px] text-ink-2">Crop<input name="crop" placeholder="Tomato, berries, leafy greens…" className={input} /></label>
      <label className="text-[13px] text-ink-2 md:col-span-2">Anything else?<textarea name="message" rows={3} className={input} /></label>
      <input name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />
      <div className="flex flex-wrap items-center gap-4 md:col-span-2">
        <button disabled={state === "sending"} className="rounded-full bg-ink px-6 py-3 text-[15px] font-medium text-paper hover:bg-brand-ink disabled:opacity-60">
          {state === "sending" ? "Sending…" : "Request early access"}
        </button>
        {state === "error" && <span className="text-[14px] text-tomato">{err}</span>}
      </div>
    </form>
  );
}

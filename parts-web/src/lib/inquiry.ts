export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const clip = (v: unknown, n = 200) => (typeof v === "string" ? v.trim().slice(0, n) : "");

export type Inquiry = { name: string; email: string; company: string; interest: string; imports: string; volume: string; at: string };

// Returns the cleaned inquiry, or an error string.
export function parseInquiry(b: Record<string, unknown>): Inquiry | string {
  const q = {
    name: clip(b.name, 120),
    email: clip(b.email, 200).toLowerCase(),
    company: clip(b.company, 160),
    interest: clip(b.interest, 60),
    imports: clip(b.imports, 1000),
    volume: clip(b.volume, 60),
    at: new Date().toISOString(),
  };
  if (!q.name || !EMAIL.test(q.email)) return "Please give your name and a valid work email.";
  return q;
}

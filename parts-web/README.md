# parts-web: US-built robot parts company site

Website for the second company: making in the US the robot parts US robot makers now import, starting with
the EE-1 soft food gripper, then a joint actuator. **"Forgeline" is a working name**; change it in
`src/lib/data.ts` (`COMPANY`), which every page reads.

Next.js 16 + TypeScript + Tailwind 4, same stack as `../web`. Vercel-ready: set the project root to `parts-web`.

```bash
npm ci
npm run dev     # http://localhost:3000
npm test        # data checks + "no unqualified Made in USA claim" guard
npm run build
```

## Pages
- `/` hero, the cost gap, product roadmap, what we buy instead, origin labels, design-partner CTA
- `/products` EE-1 in detail, then J-series joint, WD-1 wheel drive, BP-1 pack
- `/gap` line-by-line imported vs US-sourced BOM
- `/partners` design-partner form -> `POST /api/inquiry`

## Data and honesty rules
- Every number lives in `src/lib/data.ts`, taken from `robots/bom/` (rev A.1) and the rev B US-sourced BOM
  (`robots/bom/revB_summary.json`, PR #2): $51,942 vs $129,895 per robot built.
- The site claims no production, customers or sales. "Made in USA" appears only where the copy says we do
  not claim it (FTC: all or virtually all US content); `tests/site.test.ts` fails otherwise.
- The EE-1 image is a CAD render from `robots/cad/renders/`, labelled as not yet built.

## Form delivery
Set `INQUIRY_WEBHOOK_URL` (Slack, Zapier, Formspree, a CRM) at deploy. Without it, inquiries go to
`.data/inquiries.jsonl`, which does not persist on serverless hosts.

## Not done
- Not deployed. Needs Laksh's OK.
- `COMPANY.email` is a placeholder.

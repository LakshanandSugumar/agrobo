# Agrobo website

Next.js 16 (App Router, Cache Components) + TypeScript + Tailwind CSS 4.

## Pages

| Route | What it shows |
|---|---|
| `/` | Landing page: hero with a live replay of the logged season, lifecycle, Field Ledger moat, ablation, business model, FAQ |
| `/platform` | Overview of the four live tools |
| `/platform/land` | **Land Scout**: screen synthetic parcels or score your own (port of `strategy.py`) |
| `/platform/economics` | **Farm economics**: fleet size, capex, OpEx/kg vs conventional for any acreage (`economics.py` + sim activity) |
| `/platform/market` | **Market desk**: B2B selling engine over the simulated harvest (port of `market.py`) |
| `/platform/season` | **Season replay**: all 125 days of the logged ROS 2 run, twin vs ablation |
| `/technology` | Stack per phase, ROS 2 graph, behaviour tree, Gazebo row-following result, API reference |
| `/results` | Full 3-seed KPI table |
| `/early-access` | Signup form → `POST /api/waitlist` |

## API

| Method | Path | Body |
|---|---|---|
| POST | `/api/land/evaluate` | `{ seed, candidates, crop }` (`crop` may be `"any"`) |
| POST | `/api/land/score` | `{ parcel: { area_ha, ph, om_pct, slope_pct, drainage, well_m3_h, ffd, km_to_dc, lte_coverage } }` |
| POST | `/api/economics` | `{ areaHa, labourUsdH, electricityUsdKwh, twin, seasonsPerYear }` |
| POST | `/api/market` | `{ seed, areaHa, config: { contract_price, contract_hedge, spot_mean, spot_sigma, spot_glut_drop, use_forward_contracts } }` |
| GET | `/api/season?arm=twin\|notwin` | – |
| GET | `/api/kpis` | – |
| POST | `/api/waitlist` | `{ name, email, company?, role?, acres?, crop?, message? }` |
| GET | `/api/health` | – |

## Layout

```
src/app/            pages and route handlers
src/components/     UI, charts (hand-rolled SVG), interactive tools
src/lib/engine/     TypeScript ports of the simulation models
src/data/           JSON exported from ../simulation/results (committed; rebuild with npm run export-data)
scripts/            export_sim_data.py
tests/              parity tests against the Python simulation
```

## Homepage film

If a visitor stays at the top of the homepage without scrolling, clicking or typing for 4 seconds, the brand film fades in over the whole window and plays muted (browsers only allow autoplay without sound). Any scroll, click or key returns to the page. It auto-plays once per browser session, never for visitors with reduced motion turned on, and the hero's "Watch the film" button replays it with sound.

To swap in a new cut, drop new files into `public/film/` with the same names, or change `src/lib/film.ts`. Web encodes from a master:

```bash
ffmpeg -i master.mp4 -c:v libx264 -preset slow -crf 25 -maxrate 4M -bufsize 8M -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart public/film/agrobo-film.mp4
ffmpeg -i master.mp4 -c:v libvpx-vp9 -crf 38 -b:v 1.8M -maxrate 2.5M -row-mt 1 -cpu-used 4 -c:a libopus -b:a 112k public/film/agrobo-film.webm
ffmpeg -ss 3 -i master.mp4 -frames:v 1 -vf scale=1600:-2 -q:v 4 public/film/agrobo-film-poster.jpg
```

## Notes

- Parcel draws use a seeded JS RNG, so a given seed produces different parcels from the Python run; the scoring logic is identical (see the parity test).
- The market replay draws its own spot-price path per seed and sells stock through to the last day, so its totals differ from the logged run (which measured +40% revenue vs field-run wholesale, 3-seed mean).
- Fleet payback on `/platform/economics` counts operating-cost savings only, not the selling-engine revenue uplift.

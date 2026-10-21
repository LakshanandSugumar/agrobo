# Agrobo film

`out/agrobo-film.mp4`: 86 s, 1920×1080, 30 fps, H.264 + AAC. Rendered entirely from code; every number on screen comes from the season simulation export in `agrobo-web/web/src/data` and is labeled Simulated.

## Story
1. Dawn: "Everyone wants to own land. Almost no one wants to farm it."
2. The customer taps "Start my farm" on a monthly plan. "One subscription. Everything after this, Agrobo does."
3. Sourcing: 40 parcels scored, P-026-020 (suitability 0.94) acquired.
4. Prep: RTK survey, clearing and tilling, drip irrigation.
5. Cultivation: plants grow day 0 to 84, drone scouting, per-plant twin tags, laser weeding, 0 L herbicide.
6. Harvest: ripeness detection, a precision pick inside a watch-bezel HUD, 8.0 s per fruit.
7. Market: hyperspectral grading, cold chain, live market, revenue climbs to $74,135 per hectare.
8. Payout notification at dinner: "125 days. Zero human interventions. Zero hours of your time. You were home for dinner."
9. Close: "AGROBO. Own the farm. Not the work."

## Persuasion choices and the research behind them
- Narrative over feature list. People persuaded through a story ("narrative transportation") argue back less (Green & Brock, 2000).
- Show the work. Visibly showing the effort behind a service raises perceived value and trust (Buell & Norton, 2011, "labor illusion"), so every phase is shown, not just claimed.
- Precise numbers (8.0 s, 97.6 %, $74,135) read as more credible than round ones (Janiszewski & Uy, 2008). Labelling them Simulated keeps that credibility honest.
- Buying back time is a strong happiness driver (Whillans et al., 2017), which is the payoff for time-poor wealthy buyers: speed, zero interventions, zero hours.
- Status and ownership pull hardest on people who feel less powerful (Rucker & Galinsky, 2008), so "own land" is the opening hook and the visual language is luxury: black, champagne gold, a watch-bezel precision ring.
- Gender: averages differ less than the stereotype suggests. Men lean a little more toward agentic cues (control, precision, achievement) and women process more of the detail and weigh communal cues (family, time together) a little more (Meyers-Levy & Maheswaran, 1991). The film carries both in every scene (precision HUD plus the dinner payoff) instead of splitting audiences.
- Peak-end rule: viewers remember the emotional peak and the ending (Kahneman et al., 1993), so the payout plus dinner beat is the peak and the logo lands on the resolved chord.

## Rebuild
```
python3 scripts/export_data.py          # sim numbers -> data.js
python3 scripts/audio.py                # out/score.wav
for w in 0 1 2 3; do node scripts/render.mjs video $w 4 out/segs & done; wait
# concat out/segs/seg*.mp4 and mux with out/score.wav (see scripts/finish.sh)
```
Preview any moment: open `film.html?t=50` in Chromium.

## v2: photoreal (2026-10-10)
`out/agrobo-film-v2.mp4` is 86 s, 1920×1080 at 24 fps, with the same story, score and Simulated labels as v1. The visuals are path-traced 3D: Blender Cycles with a physical sky and procedural plants, soil, robots and props. `out/agrobo-film-v2-share.mp4` is the same film in a lighter encode (~41 MB) for sending. v1 is unchanged.

Pipeline (all under `v2/`):
1. `scenes/shots.py <shot> <f0> <f1> <spp>` renders each shot. `render_queue.sh` runs them all and is resumable.
2. `finish.sh` interpolates the 12 fps renders to 24 fps.
3. It then composites the v1 HUD over the plates via `overlay.js`/`film2.html`. Phone screens are warped by homography, and the harvest ring tracks the fruit.
4. Finally it muxes in `out/score.wav`.

The 3D farm is also packaged for robot training in `/mnt/project-files/agrobo-world`.

## v3: closer to real footage (2026-10-19)
`out/agrobo-film-v3.mp4` keeps the story, score and Simulated labels; `out/agrobo-film-v3-share.mp4` is a lighter copy for sending. v1 and v2 are unchanged.

What changed from v2, each fixing something that read as CG:
- **Plants:** tomato leaves are image-textured, with lobed, serrated, veined leaflets (`v3/scenes/textures.py`). They have per-plant colour variation, translucency and fine hairs. Stems are continuous, plants vary and lean, and the odd plant is missing.
- **Fruit:** tomatoes are lobed, with a star calyx and a curved, knuckled pedicel, shoulder colour and broken highlights.
- **Landscape:**
  - real-looking hedgerow trees, built from leaf cards, with shrubs between them;
  - pasture instead of a flat void;
  - mounded, crumbly soil beds;
  - a cloud layer and aerial haze.
- **Robots:** worn powder-coat with dust toward the ground and in crevices, plus bolts, seams, fenders, logo and beacon. The packhouse is lit by a real HDRI (CC0, Poly Haven via @pmndrs/assets).
- **Camera and lens:** handheld drift, motion blur, bloom, slight chromatic aberration and vignette.

Rebuild: `bash v3/render_queue.sh` (about 4.5 h on 4 CPU cores, resumable), then `bash v3/finish.sh`.

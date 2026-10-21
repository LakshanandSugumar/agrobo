// ---------- v3: photoreal plates under the v1 typography and HUD ----------
let PLATE = null;
const CACHE = {};
function loadImg(url) { return new Promise(res => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; }); }
window.setPlate = async (url, keep) => {
  if (!url) { PLATE = null; return; }
  if (CACHE[url]) { PLATE = CACHE[url]; return; }
  const im = await loadImg(url); PLATE = im; if (keep) CACHE[url] = im;
};
function plate(scale = 1, cx = 960, cy = 540) {
  if (!PLATE) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); return; }
  ctx.save(); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  ctx.translate(cx, cy); ctx.scale(scale, scale); ctx.translate(-cx, -cy); ctx.drawImage(PLATE, 0, 0, W, H); ctx.restore();
}
const OFF = makeCanvas(W, H);
// screen quad from Blender: [TL, TR, BL] normalised -> pixels
const quad = q => q.map(([x, y]) => [x * W, y * H]);
// projective warp of a source rect onto a 4-corner quad [TL, TR, BL, BR] via a triangle mesh
function homography(Q, sw, sh) {
  const [[x0, y0], [x1, y1], [x3, y3], [x2, y2]] = Q; // TL, TR, BL, BR -> square map (0,0)(1,0)(1,1)(0,1)
  const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2, sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
  const den = dx1 * dy2 - dx2 * dy1, g = (sx * dy2 - dx2 * sy) / den, h = (dx1 * sy - sx * dy1) / den;
  const a = x1 - x0 + g * x1, b = x3 - x0 + h * x3, d = y1 - y0 + g * y1, e = y3 - y0 + h * y3;
  return (u, v) => { u /= sw; v /= sh; const w = g * u + h * v + 1; return [(a * u + b * v + x0) / w, (d * u + e * v + y0) / w]; };
}
function tri(src, s0, s1, s2, d0, d1, d2) {
  ctx.save(); ctx.beginPath(); const cx = (d0[0] + d1[0] + d2[0]) / 3, cy = (d0[1] + d1[1] + d2[1]) / 3, ex = p => [p[0] + (p[0] - cx) * .02 + Math.sign(p[0] - cx) * .6, p[1] + (p[1] - cy) * .02 + Math.sign(p[1] - cy) * .6];
  const e0 = ex(d0), e1 = ex(d1), e2 = ex(d2); ctx.moveTo(...e0); ctx.lineTo(...e1); ctx.lineTo(...e2); ctx.closePath(); ctx.clip();
  const den = (s1[0] - s0[0]) * (s2[1] - s0[1]) - (s2[0] - s0[0]) * (s1[1] - s0[1]);
  const a = ((d1[0] - d0[0]) * (s2[1] - s0[1]) - (d2[0] - d0[0]) * (s1[1] - s0[1])) / den, c = ((d2[0] - d0[0]) * (s1[0] - s0[0]) - (d1[0] - d0[0]) * (s2[0] - s0[0])) / den;
  const b = ((d1[1] - d0[1]) * (s2[1] - s0[1]) - (d2[1] - d0[1]) * (s1[1] - s0[1])) / den, d = ((d2[1] - d0[1]) * (s1[0] - s0[0]) - (d1[1] - d0[1]) * (s2[0] - s0[0])) / den;
  ctx.transform(a, b, c, d, d0[0] - a * s0[0] - c * s0[1], d0[1] - b * s0[0] - d * s0[1]); ctx.drawImage(src, 0, 0); ctx.restore();
}
function mapQuad(src, sx, sy, sw, sh, Q, alpha = 1) {
  const Hm = homography(Q, sw, sh), NX = 8, NY = 16; ctx.save(); ctx.globalAlpha *= alpha;
  for (let j = 0; j < NY; j++) for (let i = 0; i < NX; i++) {
    const u0 = i * sw / NX, u1 = (i + 1) * sw / NX, v0 = j * sh / NY, v1 = (j + 1) * sh / NY;
    const A = Hm(u0, v0), B = Hm(u1, v0), Cc = Hm(u1, v1), D = Hm(u0, v1);
    tri(src, [u0, v0], [u1, v0], [u1, v1], A, B, Cc); tri(src, [u0, v0], [u1, v1], [u0, v1], A, Cc, D);
  }
  ctx.restore();
}
function withCtx(c2, fn) { const prev = ctx; ctx = c2; ctx.save(); try { fn(); } finally { ctx.restore(); ctx = prev; } }
function sideShade(x0, x1, a = .65) { const g = ctx.createLinearGradient(x0, 0, x1, 0); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`); ctx.fillStyle = g; ctx.fillRect(Math.min(x0, x1), 0, Math.abs(x1 - x0), H); }

// phone UI for the subscribe beat, drawn into a 324x704 screen at (0,0)
function subScreen(u) {
  const x0 = 0, y0 = 0, sw = 324, sh = 704, cx = sw / 2, post = seg(u, 4.9, 5.4);
  let g = ctx.createLinearGradient(0, 0, 0, sh); g.addColorStop(0, '#0e1a14'); g.addColorStop(1, '#070b09'); ctx.fillStyle = g; ctx.fillRect(0, 0, sw, sh);
  rrect(sw / 2 - 55, 12, 110, 30, 15); ctx.fillStyle = '#000'; ctx.fill();
  txt('9:41', 34, 34, { font: SANS(15, 600) });
  ctx.save(); ctx.globalAlpha *= 1 - post;
  txt('AGROBO', cx, 98, { font: SERIF(500, 26), color: P.gold, ls: 9, align: 'center' });
  txt('Your farm.', cx, 168, { font: SERIF(300, 40), align: 'center' });
  txt('Fully autonomous.', cx, 212, { font: SERIF(300, 40, 1), color: P.gold2, align: 'center' });
  rrect(18, 250, sw - 36, 330, 22); ctx.fillStyle = 'rgba(255,255,255,.04)'; ctx.fill(); ctx.strokeStyle = 'rgba(214,181,109,.35)'; ctx.lineWidth = 1; ctx.stroke();
  txt('AUTONOMOUS FARM PLAN', 40, 288, { font: MONO(12, 600), color: P.gold, ls: 2 });
  txt('One monthly subscription', 40, 314, { font: SANS(15), color: 'rgba(242,236,223,.6)' });
  ['Land sourcing & acquisition', 'Clearing, tilling, irrigation', 'Planting, scouting, weeding', 'Robotic harvest', 'Grading & cold chain', 'Selling & payouts'].forEach((s, i) => {
    const a = seg(u, .9 + i * .28, 1.3 + i * .28); if (!a) return; const yy = 360 + i * 38;
    ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = P.gold; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(50, yy - 5, 9, 0, 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(45, yy - 5); ctx.lineTo(49, yy - 1); ctx.lineTo(56, yy - 10); ctx.stroke(); ctx.restore();
    txt(s, 70 + (1 - a) * 10, yy, { font: SANS(15), alpha: a }); });
  const by = 610; rrect(18, by, sw - 36, 58, 29);
  if (u <= 4.25) { g = ctx.createLinearGradient(0, by, sw, by); g.addColorStop(0, '#b8954f'); g.addColorStop(.5, '#f3dea4'); g.addColorStop(1, '#b8954f'); ctx.fillStyle = g; ctx.fill();
    txt('Start my farm', cx, by + 36, { font: SANS(18, 600), color: '#1a1408', align: 'center' }); }
  else { ctx.fillStyle = '#123a2a'; ctx.fill(); ctx.strokeStyle = P.gold; ctx.lineWidth = 1.5; ctx.stroke(); txt('Subscribed  ✓', cx, by + 36, { font: SANS(18, 600), color: P.gold2, align: 'center' }); }
  const rp = seg(u, 4.22, 5.0); if (rp > 0) { ctx.strokeStyle = `rgba(243,222,164,${1 - rp})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx + 30, by + 30, 10 + rp * 120, 0, 7); ctx.stroke(); }
  if (u > 3.6 && u < 4.6) glowDot(cx + 30, by + 30, 30, '#ffffff', .35 * fade(u, 3.6, 4.6, .4, .3));
  ctx.restore();
  if (post > 0) { ctx.save(); ctx.globalAlpha *= post; const ry = 250;
    ctx.strokeStyle = 'rgba(214,181,109,.2)'; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(cx, ry, 54, 0, 7); ctx.stroke();
    ctx.strokeStyle = P.gold; ctx.beginPath(); ctx.arc(cx, ry, 54, u * 4, u * 4 + 1.6); ctx.stroke();
    txt('Agrobo is on it.', cx, ry + 120, { font: SERIF(300, 34), align: 'center' });
    ['› Scanning 40 parcels', '› Matching soil to crop', '› Forecasting demand', '› Planning the season'].forEach((s, i) => txt(s, 50, ry + 180 + i * 30, { font: MONO(13), color: P.gold2, alpha: seg(u, 5.5 + i * .35, 5.8 + i * .35) }));
    ctx.restore(); }
}
// lock screen + notification for the payout beat, 356x736 screen
function payScreen(u) {
  const sw = 356, sh = 736, cx = sw / 2, on = seg(u, .4, .8);
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, sw, sh); if (!on) return;
  ctx.save(); ctx.globalAlpha *= on;
  const g = ctx.createLinearGradient(0, 0, 0, sh); g.addColorStop(0, '#1a2a22'); g.addColorStop(1, '#08100c'); ctx.fillStyle = g; ctx.fillRect(0, 0, sw, sh);
  txt('7:42', cx, 138, { font: SANS(84, 300), align: 'center' }); txt('Harvest day', cx, 178, { font: SANS(17), align: 'center', color: 'rgba(242,236,223,.6)' });
  if (u > .8) { const notif = eback(seg(u, .8, 1.3)); ctx.save(); ctx.translate(cx, 248 + (1 - notif) * -80); ctx.globalAlpha *= seg(u, .8, 1.0);
    rrect(-160, -10, 320, 168, 22); ctx.fillStyle = 'rgba(40,36,30,.95)'; ctx.fill(); ctx.strokeStyle = 'rgba(214,181,109,.35)'; ctx.stroke();
    rrect(-140, 10, 34, 34, 9); const ig = ctx.createLinearGradient(-140, 10, -106, 44); ig.addColorStop(0, '#f3dea4'); ig.addColorStop(1, '#a8843f'); ctx.fillStyle = ig; ctx.fill();
    txt('A', -123, 35, { font: SERIF(500, 24), color: '#1a1408', align: 'center' });
    txt('AGROBO', -94, 33, { font: SANS(13, 600), color: 'rgba(242,236,223,.7)', ls: 1.5 }); txt('now', 140, 33, { font: SANS(13), color: 'rgba(242,236,223,.5)', align: 'right' });
    txt('Your harvest is sold.', -140, 76, { font: SANS(18, 600) });
    txt(`Season revenue: $${fmt(S.revenuePerHa)} per hectare.`, -140, 104, { font: SANS(15), color: 'rgba(242,236,223,.85)' });
    txt('Payout on its way.', -140, 128, { font: SANS(15), color: 'rgba(242,236,223,.85)' });
    txt('SIMULATED', 140, 146, { font: MONO(10, 600), color: P.gold, align: 'right', ls: 1.5 }); ctx.restore(); }
  ctx.restore();
}

function sDawn2(u, d) {
  plate(1.0);
  const g = ctx.createLinearGradient(0, LB, 0, 520); g.addColorStop(0, 'rgba(0,0,0,.35)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, LB, W, 400);
  reveal('Everyone wants to own land.', 960, 330, u, .9, 3.7, { align: 'center', font: SERIF(300, 82), glow: 30, glowColor: 'rgba(0,0,0,.7)' });
  reveal('Almost no one wants to farm it.', 960, 330, u, 4.0, d, { align: 'center', font: SERIF(300, 82, 1), color: P.gold2, glow: 30, glowColor: 'rgba(0,0,0,.7)' });
}
function pushAbout(Q) { const cx = (Q[0][0] + Q[1][0] + Q[2][0] + Q[3][0]) / 4, cy = (Q[0][1] + Q[1][1] + Q[2][1] + Q[3][1]) / 4; return [cx, cy]; }
function sSubscribe2(u, d) {
  const Q0 = quad(PLATES.desk.screen), [cx, cy] = pushAbout(Q0);
  const k = 1 + .06 * eio(seg(u, 0, 7)) + 2.4 * Math.pow(seg(u, 7.0, 8), 2);
  ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.translate(-cx, -cy);
  plate(1); withCtx(OFF.getContext('2d'), () => { ctx.clearRect(0, 0, 324, 704); subScreen(u); });
  mapQuad(OFF, 0, 0, 324, 704, Q0, seg(u, .2, .9));
  glowDot(cx, cy, 380, '#8fd4b0', .05 * seg(u, .2, .9));
  ctx.restore();
  ctx.globalAlpha = 1 - seg(u, 6.9, 7.6);
  shade(0, 1);
  reveal('One subscription.', 1000, 830, u, 1.3, d, { font: SERIF(300, 84), glow: 24, glowColor: 'rgba(0,0,0,.8)' });
  ctx.font = SERIF(300, 48, 1); const w1 = ctx.measureText('Everything after this, ').width;
  reveal('Everything after this,', 1002, 900, u, 5.0, d, { font: SERIF(300, 48, 1), color: 'rgba(242,236,223,.85)', glow: 20, glowColor: 'rgba(0,0,0,.8)' });
  reveal('Agrobo does.', 1002 + w1, 900, u, 5.6, d, { font: SERIF(300, 48, 1), color: P.gold2, glow: 20, glowColor: 'rgba(0,0,0,.8)' });
  ctx.globalAlpha = 1;
}
function sPrep2(u, d) {
  plate(1); shade();
  const ha = fade(u, .6, d);
  hudRow('RTK POSITIONING', '2.7 cm RMS', 1290, 196, ha); hudRow('ROUTE', `${fmt(S.prepM)} m`, 1530, 196, ha); hudRow('PREP TIME', `${S.prepH} h`, 1690, 196, ha);
  caption('It prepares it.', u, .8, d);
  const steps = [['CLEARED', 1.2], ['SURVEYED', 2.4], ['TILLED', 4.5], ['IRRIGATED', 7.0]]; let x = 142;
  steps.forEach(([s, t]) => { const on = seg(u, t, t + .3); ctx.font = MONO(15, 600); ctx.letterSpacing = '3px'; const w = ctx.measureText(s).width;
    txt(s, x, 922, { font: MONO(15, 600), ls: 3, color: on ? P.gold2 : 'rgba(242,236,223,.3)', alpha: fade(u, .8, d) }); x += w + 40; });
}
function sCultivate2(u, d) {
  plate(1); shade();
  const day = 2 + 82 * seg(u, 0, d), ha = fade(u, .5, d);
  txt('DAY', 1290, 210, { font: MONO(13), color: 'rgba(242,236,223,.55)', ls: 2.5, alpha: ha }); txt(String(Math.floor(day)).padStart(3, '0') + ` / ${S.seasonDays}`, 1290, 252, { font: MONO(34, 600), alpha: ha });
  hudRow('HERBICIDE', '0.0 L', 1530, 210, ha, { color: P.gold2 }); hudRow('WEED CONTROL', `${S.weedControl} %`, 1680, 210, ha);
  hudRow('PLANTS TRACKED', `${S.planted} twins`, 140, 210, fade(u, 1.2, d));
  caption('It grows every plant like it’s the only one.', u, .8, 6.0);
  caption('A digital twin for every plant. A laser for every weed.', u, 6.4, d, { font: SERIF(300, 54) });
}
function sHarvest2(u, d) {
  plate(1); shade(0, 1);
  const tr = PLATES.harvest.track, fi = Math.min(tr.length - 1, Math.floor(u * 12)), fj = Math.min(tr.length - 1, fi + 1), fr = u * 12 - fi;
  const T = [lerp(tr[fi][0], tr[fj][0], fr) * W, lerp(tr[fi][1], tr[fj][1], fr) * H];
  const ba = fade(u, 1.7, 5.4, .6, .5);
  if (ba) { ctx.save(); ctx.translate(...T); ctx.globalAlpha = ba * .9;
    for (let k = 0; k < 60; k++) { const a = k / 60 * 6.283 + u * .05, big = k % 5 === 0; ctx.strokeStyle = big ? P.gold2 : 'rgba(214,181,109,.6)'; ctx.lineWidth = big ? 2.4 : 1;
      ctx.beginPath(); ctx.moveTo(Math.cos(a) * 190, Math.sin(a) * 190); ctx.lineTo(Math.cos(a) * (big ? 210 : 200), Math.sin(a) * (big ? 210 : 200)); ctx.stroke(); }
    const sw = seg(u, 2.4, 7.3); ctx.strokeStyle = P.gold2; ctx.lineWidth = 3; ctx.shadowBlur = 14; ctx.shadowColor = P.gold; ctx.beginPath(); ctx.arc(0, 0, 226, -Math.PI / 2, -Math.PI / 2 + sw * 6.283); ctx.stroke();
    ctx.restore(); }
  const det = fade(u, 1.9, 4.4, .3, .3); if (det) { brackets(T[0] - 130, T[1] - 130, 260, 260, 28, '#ff8a6a', 2, det);
    txt('RIPE 0.97', T[0] + 250, T[1] - 90, { font: MONO(18, 600), color: '#ff8a6a', alpha: det, glow: 10, glowColor: 'rgba(0,0,0,.8)' });
    txt('TWIN FORECAST: TODAY ✓', T[0] + 250, T[1] - 60, { font: MONO(14), color: P.cream, alpha: det, glow: 10, glowColor: 'rgba(0,0,0,.8)' }); }
  const ta = fade(u, 2.4, d, .4);
  sideShade(1300, 1920, .55 * ta);
  txt('CYCLE TIME', 1500, 650, { font: MONO(13), color: 'rgba(242,236,223,.65)', ls: 2.5, alpha: ta });
  const cyc = Math.min(S.secondsPerFruit, S.secondsPerFruit * seg(u, 2.4, 7.3));
  txt(cyc.toFixed(1) + ' s', 1500, 730, { font: SERIF(500, 86), color: P.gold2, alpha: ta });
  txt('per fruit', 1500, 764, { font: MONO(15), color: 'rgba(242,236,223,.7)', alpha: ta });
  const sa = fade(u, 7.6, d, .5);
  txt(`${fmt(S.fruitPicked)} fruit picked  ·  ${S.bruise} % bruised`, 1500, 812, { font: MONO(15), alpha: sa });
  txt(`${S.secondsPerFruitNoTwin} s → ${S.secondsPerFruit} s with the plant twin`, 1500, 840, { font: MONO(15), color: P.gold, alpha: sa });
  caption('It picks with a watchmaker’s precision.', u, .8, d);
}
function sMarket2(u, d) {
  plate(1); shade(); sideShade(900, 1920, .55);
  // hide v1 conveyor drawing: reuse only the terminal panel + HUD by clipping the v1 scene to the right half
  ctx.save(); ctx.beginPath(); ctx.rect(1060, 0, 860, H); ctx.clip();
  const keep = ctx.fillRect; ctx.fillRect = function (x, y, w, h) { if (x === 0 && y === 0 && w === W && h === H) return; return keep.call(this, x, y, w, h); };
  const bk = window.bokeh; window.bokeh = () => {};
  try { sMarketPanel(u, d); } finally { ctx.fillRect = keep; window.bokeh = bk; }
  ctx.restore();
  hudRow('GRADE A', `${S.gradeA} %`, 140, 760, fade(u, .8, d)); hudRow('PICK TO COLD', `${S.pickToCool} h`, 360, 760, fade(u, 1.1, d)); hudRow('SPOILAGE', '0 kg', 610, 760, fade(u, 1.4, d));
  hudRow('HYPERSPECTRAL GRADING', '400–1000 nm', 140, 196, fade(u, .6, d));
  caption('It sells to the best buyer.', u, .8, 5.6);
  caption('Then it pays you.', u, 6.0, d, { color: P.gold2, font: SERIF(300, 64, 1) });
}
function sPayout2(u, d) {
  const Q0 = quad(PLATES.dinner.screen), [cx, cy] = pushAbout(Q0);
  const shake = u > .8 && u < 1.3 ? Math.sin(u * 140) * 3 * (1 - seg(u, .8, 1.3)) : 0;
  const k = 1 + .07 * eio(seg(u, 0, d));
  ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.translate(-cx, -cy);
  plate(1); ctx.translate(shake, 0);
  withCtx(OFF.getContext('2d'), () => { ctx.clearRect(0, 0, 356, 736); payScreen(u); });
  mapQuad(OFF, 0, 0, 356, 736, Q0);
  glowDot(cx, cy, 300, '#8fd4b0', .08 * seg(u, .4, .8));
  ctx.restore();
  const dim = seg(u, 6.4, 7.2); ctx.fillStyle = `rgba(0,0,0,${.55 * dim})`; ctx.fillRect(0, 0, W, H);
  ctx.globalAlpha = 1 - seg(u, 6.3, 6.9);
  sideShade(1150, 1920, .6);
  reveal(`${S.seasonDays} days.`, 1780, 420, u, 2.0, d, { font: SERIF(300, 80), align: 'right' });
  reveal('Zero human interventions.', 1780, 510, u, 3.2, d, { font: SERIF(300, 56), align: 'right' });
  reveal('Zero hours of your time.', 1780, 590, u, 4.4, d, { font: SERIF(300, 56, 1), color: P.gold2, align: 'right' });
  ctx.globalAlpha = 1;
  reveal('You were home for dinner.', 960, 560, u, 7.0, d, { align: 'center', font: SERIF(300, 96, 1), color: P.cream, glow: 40, glowColor: 'rgba(255,170,90,.35)' });
}
const sMarketPanel = sMarket;
SCENES = [
  { a: 0, b: 7, f: sDawn2 }, { a: 7, b: 15, f: sSubscribe2 }, { a: 15, b: 25, f: sSourcing, ph: 1, name: 'SOURCING & STRATEGY' },
  { a: 25, b: 34, f: sPrep2, ph: 2, name: 'INFRASTRUCTURE & PREP' }, { a: 34, b: 46, f: sCultivate2, ph: 3, name: 'CULTIVATION & MAINTENANCE' },
  { a: 46, b: 56, f: sHarvest2, ph: 4, name: 'ROBOTIC HARVESTING' }, { a: 56, b: 66, f: sMarket2, ph: 5, name: 'POST-HARVEST & MARKET' },
  { a: 66, b: 76, f: sPayout2, sim: 1 }, { a: 76, b: 86, f: sClose },
];

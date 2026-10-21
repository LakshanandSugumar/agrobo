// node composite.mjs stills t1,t2 | video <worker> <workers>
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'child_process';
import fs from 'fs';
const ROOT = '/mnt/project-files/agrobo-film', FR = ROOT + '/v2/frames', FPS = 24, DUR = 86;
const SHOTS = [[0, 7, 'dawn'], [7, 15, 'desk', 1], [25, 34, 'till'], [34, 46, 'cultivate'], [46, 56, 'harvest'], [56, 66, 'pack'], [66, 76, 'dinner', 1]];
function plateFor(t) {
  for (const [a, b, name, still] of SHOTS) if (t >= a && t < b) {
    if (still) return [`v2/frames/${name}/f_0001.png`, true];
    const dir = `${FR}/${name}24`; const n = fs.readdirSync(dir).filter(f => f.endsWith('.png')).length;
    const i = Math.min(n, Math.floor((t - a) * FPS) + 1); return [`v2/frames/${name}24/f_${String(i).padStart(4, '0')}.png`, false];
  }
  return [null, false];
}
const [mode, a, b] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', e => console.error('PAGEERR', e.message)); page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
await page.goto('file://' + ROOT + '/film2.html'); await page.evaluate(() => window.ready);
async function frame(t) { const [url, keep] = plateFor(t); await page.evaluate(async ([t, url, keep]) => { await setPlate(url, keep); render(t); }, [t, url, keep]); }
if (mode === 'stills') {
  fs.mkdirSync(ROOT + '/v2/stills', { recursive: true });
  for (const t of a.split(',')) { await frame(parseFloat(t)); await page.screenshot({ path: `${ROOT}/v2/stills/t${t}.jpg`, type: 'jpeg', quality: 85 }); }
} else {
  const w = +a, n = +b, total = FPS * DUR, per = Math.ceil(total / n), f0 = w * per, f1 = Math.min(total, f0 + per);
  fs.mkdirSync(ROOT + '/v2/segs', { recursive: true });
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', `${ROOT}/v2/segs/seg${w}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    await frame(f / FPS); const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 200 === 0) console.log(`w${w} ${f}/${f1}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close();

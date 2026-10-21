// Usage: node render.mjs stills t1,t2,...   |   node render.mjs video <worker> <workers> <outdir>
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'child_process';
import path from 'path';
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const FPS = 30, DUR = 86;
const [mode, a, b, c] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files', '--disable-gpu-vsync'] }).catch(() => chromium.launch({ args: ['--allow-file-access-from-files'] }));
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', e => console.error('PAGEERR', e.message));
await page.goto('file://' + ROOT + '/film.html');
await page.evaluate(() => window.ready);
if (mode === 'stills') {
  for (const t of a.split(',')) { await page.evaluate(t => render(t), parseFloat(t)); await page.screenshot({ path: `${b || ROOT + '/out/stills'}/t${t}.jpg`, type: 'jpeg', quality: 85 }); }
} else {
  const w = +a, n = +b, total = FPS * DUR, per = Math.ceil(total / n), f0 = w * per, f1 = Math.min(total, f0 + per);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', `${c}/seg${w}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => render(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 0) console.log(`w${w} frame ${f}/${f1} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await browser.close();

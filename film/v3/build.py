"""Assemble film3.html (v1 typography + photoreal plates) and plates.js from render outputs."""
import json, pathlib, ast
ROOT = pathlib.Path('/mnt/project-files/agrobo-film'); FR = ROOT / 'v3' / 'frames'
pl = {}
for k in ('desk', 'dinner'):
    pl[k] = {'screen': ast.literal_eval((FR / k / 'screen.json').read_text())}
tr = FR / 'harvest' / 'track.json'
pl['harvest'] = {'track': ast.literal_eval(tr.read_text()) if tr.exists() else [[.5, .5]]}
(FR / 'plates.js').write_text('window.PLATES = ' + json.dumps(pl) + ';\n')
s = (ROOT / 'film.html').read_text()
s = s.replace("const C = document.getElementById('c'), ctx = C.getContext('2d');", "const C = document.getElementById('c'); let ctx = C.getContext('2d');")
s = s.replace('<script src="data.js"></script>', '<script src="data.js"></script>\n<script src="v3/frames/plates.js"></script>')
s = s.replace("const SCENES = [", "let SCENES = [").replace("<title>Agrobo Film</title>", "<title>Agrobo Film v3</title>")
s = s.replace("ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .07;", "ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .035;")
s = s.replace("window.ready = (async () => {", (ROOT / 'v3' / 'overlay.js').read_text() + "\nwindow.ready = (async () => {")
s = s.replace("buildTextures(); buildParcels(); buildField(); WORDMARK = makeCanvas(1400, 240);",
              "buildTextures(); buildParcels(); buildField(); WORDMARK = makeCanvas(1400, 240);\n  TERRAIN = (await loadImg('v3/frames/aerial/f_0001.png')) || TERRAIN;")
(ROOT / 'film3.html').write_text(s); print('ok')

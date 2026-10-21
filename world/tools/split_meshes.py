#!/usr/bin/env python3
"""Post-process exported OBJs for Gazebo (run by export_assets.py; safe to re-run).

* Leaves are single-sided planes and Gazebo culls back faces, so leaf faces get a reversed twin.
* Each tomato on a fruiting plant becomes its own small static model (<plant>_fruit_<k>, labelled 1 ripe / 2 turning /
  3 unripe) that the world generator places with the same pose as its plant. Gazebo's bounding-box and instance
  cameras work per model, so this gives one box and one instance per tomato, and the generator can write every
  fruit's world position and ripeness as ground truth. The plant model keeps the foliage (label 5).
"""
import glob, json, os, re, shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')
FRUIT = {'x_fruit_red': (1, 'ripe'), 'x_fruit_turning': (2, 'turning'), 'x_fruit_green': (3, 'unripe')}
DOUBLE = ('x_leaf', 'x_weed')
LABEL = '<plugin filename="gz-sim-label-system" name="gz::sim::systems::Label"><label>{}</label></plugin>'


def parse(path):
    v, vt, vn, faces, mtl, obj, lib = [], [], [], [], None, None, None
    for ln in open(path):
        k = ln.split(' ', 1)[0]
        if k == 'v': v.append(ln.split()[1:4])
        elif k == 'vt': vt.append(ln.split()[1:])
        elif k == 'vn': vn.append(ln.split()[1:])
        elif k == 'usemtl': mtl = ln.split()[1]
        elif k == 'o': obj = ln.split()[1]
        elif k == 'mtllib': lib = ln.split()[1]
        elif k == 'f': faces.append((mtl, [[int(x) if x else 0 for x in c.split('/')] for c in ln.split()[1:]], obj))
    return dict(v=v, vt=vt, vn=vn, faces=faces, lib=lib)


def write(path, m, faces, mtllib):
    """Write only the vertices these faces use; leaf faces get a reversed, normal-flipped twin. Returns the centroid."""
    maps = [{}, {}, {}]; out = [[], [], []]; src = [m['v'], m['vt'], m['vn']]; body = []; cur = None
    def idx(slot, i, flip=False):
        key = (i, flip)
        if key not in maps[slot]:
            vals = src[slot][i - 1]
            if flip: vals = [str(-float(x)) for x in vals]
            out[slot].append(vals); maps[slot][key] = len(out[slot])
        return maps[slot][key]
    def face(cs, flip):
        return 'f ' + ' '.join('/'.join([str(idx(0, c[0])), str(idx(1, c[1])) if len(c) > 1 and c[1] else '',
                                         str(idx(2, c[2], flip)) if len(c) > 2 and c[2] else '']).rstrip('/') for c in cs)
    for mtl, cs, _ in faces:
        if mtl != cur: body.append(f'usemtl {mtl}'); cur = mtl
        body.append(face(cs, False))
        if mtl and mtl.startswith(DOUBLE): body.append(face(list(reversed(cs)), True))
    lines = [f'mtllib {mtllib}'] + ['v ' + ' '.join(x) for x in out[0]] + ['vt ' + ' '.join(x) for x in out[1]] + \
            ['vn ' + ' '.join(x) for x in out[2]] + body
    open(path, 'w').write('\n'.join(lines) + '\n')
    return [sum(float(x[i]) for x in out[0]) / len(out[0]) for i in range(3)]


def model_sdf(name, visuals, extra=''):
    return f'''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="{name}">
    <static>true</static>
    <link name="link">
{visuals}{extra}
    </link>
  </model>
</sdf>
'''


for d in sorted(glob.glob(f'{ROOT}/*')):
    name = os.path.basename(d); src = f'{d}/meshes/{name}.obj'
    if not os.path.exists(src) or re.search(r'_fruit_\d+$', name): continue
    m = parse(src); lib = m['lib']
    if name.startswith('tomato_plant_'):
        for old in glob.glob(f'{ROOT}/{name}_fruit_*'): shutil.rmtree(old)
        for old in glob.glob(f'{d}/meshes/{name}_*.obj'): os.remove(old)
        write(f'{d}/meshes/{name}_foliage.obj', m, [f for f in m['faces'] if f[0] not in FRUIT], lib)
        coll = re.search(r'<collision.*?</collision>', open(f'{d}/model.sdf').read(), re.S).group(0)
        open(f'{d}/model.sdf', 'w').write(model_sdf(name,
            f'      <visual name="foliage"><geometry><mesh><uri>model://{name}/meshes/{name}_foliage.obj</uri></mesh></geometry>\n'
            f'        {LABEL.format(5)}</visual>', '\n      ' + coll))
        fruit = []
        for k, o in enumerate(dict.fromkeys(f[2] for f in m['faces'] if f[0] in FRUIT)):
            fs = [f for f in m['faces'] if f[2] == o]; lab, cls = FRUIT[fs[0][0]]; fn = f'{name}_fruit_{k}'
            os.makedirs(f'{ROOT}/{fn}/meshes', exist_ok=True); shutil.copy(f'{d}/meshes/{lib}', f'{ROOT}/{fn}/meshes/{lib}')
            c = write(f'{ROOT}/{fn}/meshes/{fn}.obj', m, fs, lib)
            open(f'{ROOT}/{fn}/model.sdf', 'w').write(model_sdf(fn,
                f'      <visual name="visual"><geometry><mesh><uri>model://{fn}/meshes/{fn}.obj</uri></mesh></geometry>\n'
                f'        {LABEL.format(lab)}</visual>'))
            open(f'{ROOT}/{fn}/model.config', 'w').write(f'<?xml version="1.0"?>\n<model><name>{fn}</name><version>1.0</version>'
                f'<sdf version="1.9">model.sdf</sdf><description>Fruit {k} of {name} ({cls}); place with the plant pose.</description></model>\n')
            fruit.append({'model': fn, 'class': cls, 'label': lab, 'xyz': [round(x, 4) for x in c]})
        json.dump(fruit, open(f'{d}/fruit.json', 'w'), indent=1)
        print(name, f'foliage + {len(fruit)} fruit models')
    elif any(f[0] and f[0].startswith(DOUBLE) for f in m['faces']):
        write(f'{d}/meshes/{name}_2s.obj', m, m['faces'], lib)
        s = open(f'{d}/model.sdf').read().replace(f'meshes/{name}.obj', f'meshes/{name}_2s.obj'); open(f'{d}/model.sdf', 'w').write(s)
        print(name, 'leaves made double-sided')

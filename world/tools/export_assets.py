"""Export the film's procedural farm assets as Gazebo models (OBJ+MTL visuals, simple collisions).
Run: <blender-python> export_assets.py      (uses ../scenes/lib.py, copied from the film)"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scenes'))
import bpy, bmesh, lib
from mathutils import Vector
ROOT = '/mnt/project-files/agrobo-world/models'

FLAT = {}
def flat(name, rgb, rough=.6, metal=0.):
    if name not in FLAT: FLAT[name] = lib.mat_basic('x_' + name, rgb, rough=rough, metal=metal)
    return FLAT[name]

def flatten_materials(objs):
    """glTF/OBJ cannot carry procedural node textures: map each material to a flat PBR colour."""
    table = {'leaf': ('leaf', (.06, .2, .04)), 'stem': ('stem', (.09, .16, .05)), 'tom_g': ('fruit_green', (.18, .32, .05)),
             'tom_o': ('fruit_turning', (.6, .22, .03)), 'tom_r': ('fruit_red', (.5, .03, .015)), 'paint': ('paint', (.035, .04, .042)),
             'gold': ('gold', (.83, .66, .34), .25, 1), 'tyre': ('tyre', (.012, .012, .012)), 'alu': ('alu', (.7, .7, .72), .3, 1),
             'glass': ('glass', (.02, .02, .02)), 'light': ('light', (1, .93, .8)), 'pv': ('pv', (.02, .03, .06)), 'weed': ('weed', (.2, .25, .05)),
             'white': ('white', (.78, .78, .76)), 'graph': ('graphite', (.025, .027, .03)), 'sil': ('silicone', (.03, .03, .033)),
             'cf': ('carbon', (.015, .015, .015)), 'body': ('paint', (.05, .055, .06)), 'prop': ('prop', (.02, .02, .02)), 'lens': ('glass', (.01, .01, .01))}
    for o in objs:
        if o.type != 'MESH': continue
        for i, m in enumerate(o.data.materials):
            if m is None: continue
            key = next((k for k in table if k in m.name), None)
            if key:
                args = table[key]; o.data.materials[i] = flat(args[0], args[1], *(args[2:] if len(args) > 2 else ()))

def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)

# Gazebo semantic label per model (matches the COCO class ids in synth/generate_dataset.py; 5 plant, 6 UGV, 7 UAV)
LABELS = {'tomato_fruit_red': 1, 'tomato_fruit_turning': 2, 'tomato_fruit_green': 3, 'weed_seedling': 4,
          'tomato_plant': 5, 'agrobo_ugv': 6, 'agrobo_scout_uav': 7}

def export(name, objs, collision_sdf, mass=None, static=True, desc=''):
    lab = next((v for k, v in LABELS.items() if name.startswith(k)), None)
    label = '' if lab is None else f'<plugin filename="gz-sim-label-system" name="gz::sim::systems::Label"><label>{lab}</label></plugin>\n    '
    d = f'{ROOT}/{name}'; os.makedirs(f'{d}/meshes', exist_ok=True)
    flatten_materials(objs)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.wm.obj_export(filepath=f'{d}/meshes/{name}.obj', export_selected_objects=True, up_axis='Z', forward_axis='Y',
                          apply_modifiers=True, export_materials=True, export_uv=True, export_normals=True)
    inertial = '' if mass is None else f'<inertial><mass>{mass}</mass></inertial>'
    open(f'{d}/model.sdf', 'w').write(f'''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="{name}">
    <static>{'true' if static else 'false'}</static>
    {label}<link name="link">{inertial}
      <visual name="visual"><geometry><mesh><uri>model://{name}/meshes/{name}.obj</uri></mesh></geometry></visual>
      {collision_sdf}
    </link>
  </model>
</sdf>
''')
    open(f'{d}/model.config', 'w').write(f'''<?xml version="1.0"?>
<model><name>{name}</name><version>1.0</version><sdf version="1.9">model.sdf</sdf>
  <author><name>Agrobo</name></author><description>{desc}</description></model>
''')
    print('exported', name)

def all_desc(o):
    out = [o]
    for c in o.children: out += all_desc(c)
    return out

lib.reset((64, 64))
leaf, stem = lib.mat_leaf('leaf'), lib.mat_basic('stem', (.09, .16, .05))
fm = [lib.mat_tomato('tom_g', (.18, .32, .05)), lib.mat_tomato('tom_o', (.55, .18, .02)), lib.mat_tomato('tom_r', (.45, .03, .015))]
# tomato plants: 3 growth stages x 3 shape variants
for stage, (h, scale, fruit, mats) in {'seedling': (.35, .5, 0, fm[:1]), 'vegetative': (.7, .85, 0, fm[:1]), 'fruiting': (.9, 1.0, 5, fm)}.items():
    for v in range(3):
        clear(); root = lib.tomato_plant(f'p', 40 + v, height=h, leaves=9 + 2 * v if stage != 'seedling' else 5, mat_leaf_=leaf, mat_stem=stem, fruit_mats=mats, fruit=fruit)
        root.scale = (scale,) * 3; objs = all_desc(root)
        r = .04  # stem only: foliage is soft, so robots may brush through leaves but not the stem
        export(f'tomato_plant_{stage}_{v}', objs,
               f'<collision name="stem"><pose>0 0 {h * scale / 2} 0 0 0</pose><geometry><cylinder><radius>{r:.2f}</radius><length>{h * scale:.2f}</length></cylinder></geometry></collision>',
               desc=f'Procedural tomato plant, {stage} stage, variant {v}. Visual matches the Agrobo film; collision is the stem only.')
# fruit at three ripeness levels (dynamic, graspable)
for k, (nm, m) in enumerate(zip(('green', 'turning', 'red'), fm)):
    clear(); o = lib.add_prim('uv_sphere', 'fruit', m, None, radius=.035, segments=32, ring_count=16); o.scale = (1, 1, .87); lib.smooth(o)
    c = lib.add_prim('cone', 'calyx', stem, None, vertices=5, radius1=.02, radius2=0, depth=.01, location=(0, 0, .03))
    export(f'tomato_fruit_{nm}', [o, c], '<collision name="c"><geometry><sphere><radius>0.033</radius></sphere></geometry></collision>', mass=.12, static=False,
           desc=f'Tomato fruit, {nm}. 0.12 kg, sphere collision for grasp training.')
# weed
clear(); bm = bmesh.new(); R = random.Random(3)
for j in range(9):
    a = j / 9 * 6.28; lib.leaflet(bm, Vector((0, 0, 0)), Vector((math.cos(a), math.sin(a), .5)), .08, .03, .02, segs=3)
w = lib.mesh_obj('weed', bm, lib.mat_leaf('weed', (.15, .2, .04), (.28, .3, .07)))
export('weed_seedling', [w], '', desc='Broadleaf weed seedling (visual only) for weeding/perception tasks.')
# robots (visual meshes; drive plugins stay in agrobo_sim's own robot models)
for tool in ('tiller', 'laser'):
    clear(); u = lib.ugv('ugv', tool=tool); objs = all_desc(u)
    export(f'agrobo_ugv_{tool}', objs, '<collision name="body"><pose>0 0 0.5 0 0 0</pose><geometry><box><size>1.7 1.2 0.8</size></box></geometry></collision>',
           desc=f'Agrobo modular UGV with {tool} implement (visual + box collision).')
clear(); dr = lib.drone('drone'); export('agrobo_scout_uav', all_desc(dr), '<collision name="body"><geometry><box><size>1.3 1.3 0.3</size></box></geometry></collision>',
                                         desc='Agrobo scout quadrotor (visual + box collision).')
print('DONE')

# Gazebo post-processing: double-sided leaves, one labelled visual per fruit
import runpy; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_meshes.py"), run_name="__main__")

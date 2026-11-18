"""blender -b --python tools/render.py -- [--only name,name] [--samples 24]
Renders into model/r/ (ignored): the matched views of tools/views.json (same framing as the reference figure crop,
transparent background so the alpha channel is the silhouette) and presentation views of every variant.
Run build.py first (and once more with --m18-livery figure for the Fig. B-3 matches)."""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return argv[argv.index(k) + 1] if k in argv else d
ONLY = [s for s in arg('--only', '').split(',') if s]; SAMPLES = int(arg('--samples', 24))
VIEWS = json.load(open(os.path.join(HERE, 'tools', 'views.json')))
os.makedirs(os.path.join(HERE, 'r'), exist_ok=True)

def setup(stem):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'work', stem + '.blend'))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1); bg.inputs[1].default_value = 0.9
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.sensor_fit = 'HORIZONTAL'; cam.data.sensor_width = 36.0; cam.data.clip_start = 0.005; cam.data.clip_end = 10
    return sc, cam

def lights(sc, cam_dir):
    """Key from the upper left of the camera, soft fill from the right."""
    up = Vector((0, 0, 1)); right = cam_dir.cross(up).normalized()
    for name, v, e, s in (('key', -cam_dir * 0.5 - right * 0.45 + up * 0.55, 6.0, 0.5), ('fill', -cam_dir * 0.5 + right * 0.6 + up * 0.15, 2.0, 0.8)):
        l = bpy.data.lights.new(name, 'AREA'); l.energy = e; l.size = s; o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
        o.location = v; o.rotation_euler = (-v).to_track_quat('-Z', 'Y').to_euler()

def aim(cam, az, el, dist, roll=0.0, look=(0, 0, 0)):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))      # from the model towards the camera
    cam.location = Vector(look) + d * dist
    q = (-d).to_track_quat('-Z', 'Y'); cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = q @ Matrix.Rotation(math.radians(roll), 4, 'Z').to_quaternion()
    return -d

for name, v in VIEWS.items():
    if name.startswith('_') or (ONLY and name not in ONLY): continue
    if not os.path.exists(os.path.join(HERE, 'work', v['stem'] + '.blend')): print('MISSING', v['stem']); continue
    sc, cam = setup(v['stem'])
    x0, y0, x1, y1 = v['crop']; Wp, Hp = x1 - x0, y1 - y0
    sc.render.resolution_x = Wp; sc.render.resolution_y = Hp; sc.render.resolution_percentage = 200
    d = v['dist_mm'] / 1000.0; fpx = v['px_per_mm'] * 1000.0 * d                         # pixels of focal length
    cam.data.lens = fpx / Wp * 36.0
    cd = aim(cam, v['az'], v['el'], d, v['roll'])
    # put the model origin on the anchor pixel with the lens shift (shift is in units of the sensor width here)
    cam.data.shift_x = -(v['anchor_px'][0] - Wp / 2) / Wp
    cam.data.shift_y = (v['anchor_px'][1] - Hp / 2) / Wp
    lights(sc, cd)
    sc.render.filepath = os.path.join(HERE, 'r', 'match_' + name + '.png'); bpy.ops.render.render(write_still=True); print('RENDERED match', name, flush=True)

PRES = ['grenade_frag', 'grenade_impact', 'grenade_flash', 'grenade_smoke-red', 'grenade_smoke-yellow', 'grenade_smoke-green', 'grenade_smoke-violet', 'grenade_smoke-white']
for stem in PRES:
    if ONLY and stem not in ONLY and 'pres' not in ONLY: continue
    if not os.path.exists(os.path.join(HERE, 'work', stem + '.blend')): continue
    for view, az, el in (('front', 0, 4), ('lever', 90, 4), ('back', 180, 4), ('three_quarter', 35, 22), ('top', 20, 80)):
        sc, cam = setup(stem); sc.render.resolution_x = 640; sc.render.resolution_y = 800; sc.render.resolution_percentage = 100
        cam.data.lens = 150; cd = aim(cam, az, el, 0.62, look=(0, 0, 0.012)); lights(sc, cd)
        sc.render.filepath = os.path.join(HERE, 'r', f'{stem}_{view}.png'); bpy.ops.render.render(write_still=True)
    print('RENDERED views', stem, flush=True)

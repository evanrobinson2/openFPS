"""blender -b model/build/shotgun590.blend --python model/tools/render.py -- [--only name,name] [--samples 24]

Writes PNGs to model/build/r/. `match_right` and `match_right_alpha` use the reference photo's framing exactly
(orthographic, same pixel grid as refs-local/commons-atf-mossberg-590.jpg at 2x), so model/tools/compare.py can
lay one over the other. The rest are presentation views."""
import bpy, math, sys, os, json
from mathutils import Vector
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return argv[argv.index(k) + 1] if k in argv else d
only = arg('--only', ''); SAMPLES = int(arg('--samples', 24))
INV = json.load(open(os.path.join(HERE, 'inventory.json'))); TR = json.load(open(os.path.join(HERE, 'reference_trace.json')))
K = TR['frame']['mm_per_px']; X0 = TR['anchors_px']['receiver_front_x']; Y0 = TR['frame']['y_axis0']; PW, PH = 1148, 263
MM = 0.001
def bl(x, y, z): return Vector((x * MM, -z * MM, y * MM))          # model mm (X left, Y up, Z muzzle) -> Blender
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'PNG'
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 0.8
def light(name, loc, energy, size, tgt=(0, -40, 0)):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size; o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
    o.location = bl(*loc); o.rotation_euler = (bl(*tgt) - bl(*loc)).to_track_quat('-Z', 'Y').to_euler(); return o
light('key', (-900, 1500, 500), 60, 2.5); light('fill', (1500, 500, -300), 40, 2.5); light('rim', (300, 1200, -900), 40, 2.0)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
def shot(name, loc, target, ortho=None, lens=50, res=(1600, 900), alpha=False):
    if only and name not in only.split(','): return
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.film_transparent = alpha
    cam.location = bl(*loc); cam.rotation_euler = (bl(*target) - bl(*loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO' if ortho else 'PERSP'; cam.data.clip_start = 0.01; cam.data.clip_end = 20
    if ortho: cam.data.ortho_scale = ortho * MM
    else: cam.data.lens = lens
    os.makedirs(os.path.join(HERE, 'build', 'r'), exist_ok=True)
    sc.render.filepath = os.path.join(HERE, 'build', 'r', name + '.png'); bpy.ops.render.render(write_still=True); print('RENDERED', name, flush=True)
O = bpy.data.objects
for n in ('shell_head', 'shell_hull'): O[n].hide_render = True

# the reference photo's framing: pixel (X0, Y0) is the model origin; the photo is PW x PH px at K mm per px
cz, cy = (PW / 2 - X0) * K, (Y0 - PH / 2) * K
shot('match_right', (-2000, cy, cz), (0, cy, cz), ortho=PW * K, res=(PW * 2, PH * 2))
shot('match_right_alpha', (-2000, cy, cz), (0, cy, cz), ortho=PW * K, res=(PW * 2, PH * 2), alpha=True)
shot('right', (-2000, -60, 0), (0, -60, 0), ortho=1120, res=(1600, 520))
shot('left', (2000, -60, 0), (0, -60, 0), ortho=1120, res=(1600, 520))
shot('top', (0, 2000, 0.01), (0, 0, 0), ortho=1120, res=(1600, 300))
shot('three_quarter', (-700, 330, 900), (0, -40, 60), lens=70)
shot('closeup_right_receiver', (-420, 30, -60), (0, -15, -95), lens=85, res=(1200, 700))
shot('closeup_left_receiver', (420, 10, -100), (0, -20, -110), lens=85, res=(1200, 700))
eye = INV['sockets']['socket_ads_eye']
shot('first_person', (eye[0], eye[1], eye[2]), (0, eye[1] - 12, 2000), lens=24)
shot('first_person_hip', (90, 95, -560), (-25, -10, 500), lens=22)

# action open: slide and bolt at the rear of the stroke, bolt lock down
P = INV['params']; S, lm = P['stroke'], P['lost_motion']
def move(name, dx=0, dy=0, dz=0): O[name].location = O[name].location + Vector((dx * MM, -dz * MM, dy * MM))
if not only or 'action_open' in only:
    move('slide_assembly', dz=-S); move('bolt_slide_group', dz=-S); move('bolt_group', dz=-(S - lm)); O['bolt_lock'].rotation_euler = (math.radians(7), 0, 0)
    shot('action_open', (-560, 120, 380), (0, -20, -20), lens=70)
    move('slide_assembly', dz=S); move('bolt_slide_group', dz=S); move('bolt_group', dz=(S - lm)); O['bolt_lock'].rotation_euler = (0, 0, 0)
# exploded into the manual's field-strip assemblies (pp. 10 to 14)
if not only or 'exploded' in only:
    for n, d in (('barrel_assembly', (0, 90, 60)), ('magazine_cap_group', (0, -10, 110)), ('slide_assembly', (0, -95, 60)), ('bolt_group', (0, 150, -40)), ('bolt_slide_group', (0, 105, -40)),
                 ('trigger_housing_group', (0, -95, -10)), ('trigger_housing_pin', (-90, 0, 0)), ('cartridge_stop', (-80, -40, 0)), ('cartridge_interrupter', (80, -40, 0)), ('elevator_group', (0, -150, 20))):
        move(n, *d)
    shot('exploded', (-1050, 520, 1250), (0, -10, 30), lens=62)

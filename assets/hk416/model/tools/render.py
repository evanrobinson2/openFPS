"""blender -b work/hk416_lod0.blend --python tools/render.py -- [--only name,name] [--px 1280] [--samples 32]
Presentation renders (r/right.png, left, top, front, three_quarter, first_person, exploded) and the five
close-up comparison renders (r/closeup_*.png, same viewpoints as refs/closeup-*.jpg). Cycles, CPU."""
import bpy, math, sys, os, json
from mathutils import Vector
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return argv[argv.index(k) + 1] if k in argv else d
only = arg('--only', ''); PXW = int(arg('--px', 1280)); SAMPLES = int(arg('--samples', 32))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.render.film_transparent = False; sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'PNG'
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.78, 0.79, 0.80, 1); bg.inputs[1].default_value = 0.7
def light(name, loc, energy, size):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size; o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector((0, -0.05, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
lights = [light('key', (-1.2, -0.9, 1.3), 120, 1.2), light('fill', (1.3, -0.2, 0.7), 60, 1.5), light('rim', (0.2, 1.4, 0.9), 80, 1.0), light('under', (0.0, -0.1, -1.0), 15, 2.0)]
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
C = Vector((0, 0.0, -0.035))              # weapon centre (Blender coords: X = left side, -Y = muzzle)
def shot(name, loc, target, ortho=None, lens=50, aspect=16 / 9, up='Y'):
    if only and name not in only.split(','): return
    sc.render.resolution_x = PXW; sc.render.resolution_y = int(PXW / aspect)
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', up).to_euler()
    cam.data.type = 'ORTHO' if ortho else 'PERSP'; cam.data.clip_start = 0.005; cam.data.clip_end = 20
    if ortho: cam.data.ortho_scale = ortho
    else: cam.data.lens = lens
    sc.render.filepath = os.path.join(HERE, 'r', name + '.png'); bpy.ops.render.render(write_still=True); print('RENDERED', name, flush=True)

shot('right', (-2, C.y, C.z), C, ortho=0.90, aspect=2.6)
shot('left', (2, C.y, C.z), C, ortho=0.90, aspect=2.6)
shot('top', (0, C.y, 2), C, ortho=0.90, aspect=4.0)
shot('front', (0, -2, -0.03), (0, 0, -0.03), ortho=0.34, aspect=1.0)
shot('three_quarter', (-0.62, -0.78, 0.30), (0, -0.02, -0.04), lens=70)
eye = bpy.data.objects['socket_ads_eye'].matrix_world.translation
shot('first_person', eye + Vector((0, 0.0, 0.0)), eye + Vector((0, -1, 0)), lens=24)
shot('first_person_hip', Vector((0.085, 0.42, 0.085)), Vector((-0.02, -0.4, 0.0)), lens=22)
# close-up comparisons (viewpoints estimated from refs/closeup-*.jpg)
shot('closeup_front_sight', (0.20, -0.02, 0.20), (0.0, -0.20, 0.03), lens=60, aspect=500 / 280)
shot('closeup_handguard_front', (0.55, -0.20, 0.22), (0.0, -0.21, 0.0), lens=60, aspect=500 / 280)
shot('closeup_left_lower_controls', (0.30, 0.13, -0.01), (0.0, 0.13, -0.03), lens=85, aspect=500 / 280)
shot('closeup_rear_sight_charging_handle', (0.22, 0.02, 0.17), (0.0, 0.14, 0.03), lens=60, aspect=500 / 280)
dc = bpy.data.objects['dust_cover']; dc.rotation_euler = (0, math.radians(-175), 0)
shot('closeup_right_receiver', (-0.36, 0.0, 0.10), (0.0, 0.07, -0.01), lens=70, aspect=500 / 280)
dc.rotation_euler = (0, 0, 0)
# exploded view: each region slides out along its assembly direction
if not only or 'exploded' in only:
    off = dict(upper=(0, 0, 0.07), lower=(0, 0, -0.03), handguard=(0, -0.10, 0.07), barrel_assembly=(0, -0.30, 0.07), stock=(0, 0.14, -0.03), grip=(0, 0.03, -0.11),
               magazine=(0, -0.02, -0.16), sights=(0, 0, 0.17), controls=(0.0, 0, -0.03), fasteners=(-0.09, 0, -0.03))
    for g, d in off.items(): bpy.data.objects[g].location = d
    for nm, d in (('charging_handle', (0, 0.06, 0.10)), ('bolt_carrier', (0, 0.0, -0.045)), ('dust_cover', (-0.05, 0, 0)), ('trigger', (0, 0, -0.03)), ('selector_lever_l', (0.05, 0, 0)),
                  ('bolt_catch', (0.05, 0, 0)), ('mag_release_button', (-0.05, 0, 0)), ('buffer_tube', (0, -0.07, 0)), ('castle_nut', (0, -0.04, 0)), ('receiver_end_plate', (0, -0.02, 0)),
                  ('buttplate', (0, 0.03, 0)), ('buttpad', (0, 0.06, 0)), ('flash_hider', (0, -0.05, 0)), ('gas_block', (0, -0.02, -0.03)), ('gas_piston_tube', (0, 0, 0.03)), ('front_sight_arm', (0, 0, 0.03)), ('rear_sight_arm', (0, 0, 0.03))):
        o = bpy.data.objects[nm]; o.location = o.location + Vector(d)
    shot('exploded', (-0.95, -1.05, 0.55), (0.02, -0.06, 0.0), lens=60)

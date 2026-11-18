"""Renders and the fit check for an optic recipe (the same file sits in each optic's model/ folder).

    blender -b work/<name>.blend --python render.py -- [--rifle /path/to/hk416.glb] [--px 1280] [--samples 48]

Writes ../renders/*.jpg. With --rifle (a local build of assets/hk416/model/build.py, never committed) it also mounts the
optic on the rifle's socket_optic with the sights folded, renders it there, and writes fit.json: every optic part that
intersects a rifle part, and the clearances that matter. Cycles, CPU.
"""
import bpy, math, sys, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return argv[argv.index(k) + 1] if k in argv else d
PXW = int(arg('--px', 1280)); SAMPLES = int(arg('--samples', 48)); RIFLE = arg('--rifle', '')
OUT = os.path.join(HERE, '..', 'renders'); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
optic_objs = list(bpy.data.objects)
root = next(o for o in optic_objs if o.parent is None)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.78, 0.79, 0.80, 1); bg.inputs[1].default_value = 0.8
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
LIGHTS = []
def light(loc, energy, size, look):
    l = bpy.data.lights.new('l', 'AREA'); l.energy = energy; l.size = size; o = bpy.data.objects.new('l', l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); LIGHTS.append(o)
def shot(name, loc, target, ortho=None, lens=70, aspect=16 / 9):
    sc.render.resolution_x = PXW; sc.render.resolution_y = int(PXW / aspect)
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO' if ortho else 'PERSP'; cam.data.clip_start = 0.002; cam.data.clip_end = 20
    if ortho: cam.data.ortho_scale = ortho
    else: cam.data.lens = lens
    sc.render.filepath = os.path.join(OUT, name + '.jpg'); bpy.ops.render.render(write_still=True); print('RENDERED', name, flush=True)

meshes = [o for o in optic_objs if o.type == 'MESH']
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
C = (lo + hi) / 2; size = (hi - lo).length
for loc, e, s in (((-0.5, -0.4, 0.6), 30, 0.6), ((0.6, -0.1, 0.35), 14, 0.8), ((0.1, 0.6, 0.4), 18, 0.5), ((0, 0, -0.5), 4, 1.0)):
    light(Vector(loc) + C, e, s, C)
shot('three_quarter_left', C + Vector((0.55, -0.62, 0.34)) * size * 3.4, C, lens=85)
shot('three_quarter_right_rear', C + Vector((-0.55, 0.62, 0.30)) * size * 3.4, C, lens=85)
shot('left', C + Vector((2, 0, 0)), C, ortho=size * 1.05, aspect=2.0)
shot('right', C + Vector((-2, 0, 0)), C, ortho=size * 1.05, aspect=2.0)
shot('top', C + Vector((0, 0, 2)), C, ortho=size * 1.05, aspect=2.0)
shot('front', C + Vector((0, -2, 0)), C, ortho=(hi.z - lo.z) * 1.5, aspect=1.0)
eye = bpy.data.objects['socket_eye'].matrix_world.translation.copy()
shot('from_the_eye', eye, eye + Vector((0, -1, 0)), lens=60, aspect=1.0)

if RIFLE:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=RIFLE)
    rifle = [o for o in bpy.data.objects if o not in before]
    for n in ('front_sight_arm', 'rear_sight_arm'):
        o = bpy.data.objects[n]; o.rotation_mode = 'XYZ'; o.rotation_euler = (math.radians(90), 0, 0)      # the rifle's sights_down pose
    bpy.context.view_layer.update()
    so = bpy.data.objects['socket_optic'].matrix_world.translation.copy()
    root.location = so; bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    def tree(o):
        me = o.evaluated_get(dg).to_mesh(); mw = o.matrix_world
        return BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    def zrange(o):
        zs = [(o.matrix_world @ Vector(c)).z for c in o.bound_box]; return min(zs), max(zs)
    rm = [o for o in rifle if o.type == 'MESH']; rt = {o.name: tree(o) for o in rm}
    hits = []
    for o in meshes:
        t = tree(o)
        for n, r in rt.items():
            if t.overlap(r): hits.append([o.name, n])
    names = {o.name: o for o in rm}
    low = min(zrange(o)[0] for o in meshes if not o.name.startswith('mount'))
    fit = dict(rifle='assets/hk416 (local --fast build of model/build.py), sights folded', socket_optic_m=[round(v, 5) for v in so],
               intersections=hits, intersections_note='pairs of (optic part, rifle part) whose surfaces cross; an empty list means the optic fits',
               lowest_point_of_the_optic_body_over_rail_mm=round((low - so.z) * 1000, 2),
               folded_rear_sight_top_over_rail_mm=round((max(zrange(o)[1] for o in rm if o.name.startswith('rear_sight')) - so.z) * 1000, 2),
               charging_handle_top_over_rail_mm=round((zrange(names['charging_handle'])[1] - so.z) * 1000, 2))
    fit['clearance_over_folded_rear_sight_mm'] = round(fit['lowest_point_of_the_optic_body_over_rail_mm'] - fit['folded_rear_sight_top_over_rail_mm'], 2)
    json.dump(fit, open(os.path.join(HERE, 'fit.json'), 'w'), indent=1); print('FIT', len(hits), 'intersections', hits[:12], {k: v for k, v in fit.items() if k.endswith('_mm')}, flush=True)
    for l in LIGHTS: l.location = l.location + so
    Cm = C + so; eye = bpy.data.objects['socket_eye'].matrix_world.translation.copy()
    shot('mounted_three_quarter', Cm + Vector((0.42, -0.36, 0.26)), Cm + Vector((0, 0.02, -0.03)), lens=70)
    shot('mounted_right', Cm + Vector((-2, 0.02, -0.04)), Cm + Vector((0, 0.02, -0.04)), ortho=0.42, aspect=2.0)
    shot('mounted_from_the_eye', eye, eye + Vector((0, -1, 0)), lens=40, aspect=1.0)

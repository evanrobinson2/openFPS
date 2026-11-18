"""blender -b work/g44v.blend --python tools/render.py -- <view> [<view> ...]
Views: match_left (orthographic, the camera, scale and framing of the dimension image: 1654 x 1042 px at 5.785 px/mm, written as
an RGBA mask render for tools/compare.py), left, right, top, rear, three_quarter, internals (frame, slide and tube hidden),
lock_open, field_strip.  Beauty renders go to ../renders/<view>.jpg, the matched render to work/match_left.png."""
import bpy, sys, os, math, json
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clipeval
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
views = sys.argv[sys.argv.index('--') + 1:]
sc = bpy.context.scene
R = json.load(open(os.path.join(HERE, 'outlines.json')))['ruler']; K, XR, YB = R['px_per_mm'], R['x_slide_rear'], R['y_bore']
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
w = bpy.data.worlds.new('w'); sc.world = w; sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.3; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.57, 0.6, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
def light(loc, energy, size=0.5):
    d = bpy.data.lights.new('l', 'AREA'); d.energy = energy; d.size = size; o = bpy.data.objects.new('l', d); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, -0.08, -0.04)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
for loc, e in (((0.5, -0.3, 0.5), 14), ((-0.5, -0.2, 0.4), 9), ((0.0, 0.5, 0.3), 6), ((0.2, -0.6, -0.2), 4)): light(loc, e)
cam_d = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cam_d); sc.collection.objects.link(cam); sc.camera = cam
def look(loc, target, ortho=None, lens=85):
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho: cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
    else: cam_d.type = 'PERSP'; cam_d.lens = lens
    cam_d.clip_start = 0.01; cam_d.clip_end = 10
def clip(name, frame): clipeval.pose(name, frame)
def hide(names, h=True):
    for o in bpy.data.objects:
        if any(o.name.startswith(n) for n in names): o.hide_render = h
acc = [o for o in bpy.data.objects if o.parent and o.parent.name == 'accessories']
C = (0.0, -0.075, -0.045)
for v in views:
    clip('', 1); hide([''], False); sc.render.film_transparent = False
    for o in acc: o.hide_render = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000; out = os.path.join(HERE, '..', 'renders', v + '.jpg'); sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
    if v == 'match_left':
        sc.render.resolution_x, sc.render.resolution_y = 1654, 1042; sc.render.film_transparent = True
        sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; out = os.path.join(HERE, 'work', 'match_left.png')
        look((1.0, -(XR - 827) / K * 1e-3, (YB - 521) / K * 1e-3), (0.0, -(XR - 827) / K * 1e-3, (YB - 521) / K * 1e-3), ortho=1654 / K * 1e-3)
    elif v == 'left': look((1.0, C[1], C[2]), C, ortho=0.26)
    elif v == 'right': look((-1.0, C[1], C[2]), C, ortho=0.26)
    elif v == 'top': look((0, -0.085, 1.0), (0, -0.0851, 0), ortho=0.22)
    elif v == 'rear': look((0, 1.0, -0.047), (0, 0, -0.047), ortho=0.2)
    elif v == 'three_quarter': look((0.42, -0.50, 0.16), (0, -0.09, -0.04), lens=85)
    elif v == 'internals':
        hide(['p17_frame', 'p01_slide', 'p31_magazine_tube', 'placeholder', 'p35', 'p15', 'p16a', 'p14']); hide(['p17_frame_guide'], False); look((-0.40, -0.42, 0.22), (0, -0.07, -0.03), lens=85)
    elif v == 'internals_left':
        hide(['p17_frame', 'p01_slide', 'p31_magazine_tube', 'placeholder', 'p35', 'p15', 'p16a', 'p14']); hide(['p17_frame_guide'], False); look((1.0, C[1], C[2]), C, ortho=0.26)
    elif v == 'lock_open': clip('slide_lock_open', 24); look((1.0, C[1] + 0.02, C[2]), (0, C[1] + 0.02, C[2]), ortho=0.30)
    elif v == 'field_strip': clip('field_strip', 150); look((0.7, -0.75, 0.35), (0, -0.16, -0.045), lens=70)
    elif v == 'accessories':
        for o in acc: o.hide_render = False
        look((1.0, C[1] + 0.03, C[2]), (0, C[1] + 0.03, C[2]), ortho=0.33)
    sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('rendered', v, out)

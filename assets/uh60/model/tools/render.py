"""Perspective look-check renders of a saved build.

    python3 tools/render.py work/uh60_lod1.blend out.jpg --eye STA,BL,WL --at STA,BL,WL [--fov 50] [--px 1100x650]
            [--samples 24] [--clip name=frame ...] [--lamp]  (--lamp adds a point light at the eye, for interiors)
Positions are in the aircraft frame, inches (BL + = left).
"""
import bpy, sys, math
from mathutils import Vector, Matrix
a = sys.argv[1:]
def arg(k, d=None):
    return a[a.index(k) + 1] if k in a else d
IN = 0.0254; STA0, WL0 = 341.2, 183.7
def W(s):
    x = [float(v) for v in s.split(',')]; return Vector((x[1] * IN, (x[0] - STA0) * IN, (x[2] - WL0) * IN))
bpy.ops.wm.open_mainfile(filepath=a[0])
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(arg('--samples', 24)); sc.cycles.use_denoising = True
px = arg('--px', '1100x650').split('x'); sc.render.resolution_x, sc.render.resolution_y = int(px[0]), int(px[1]); sc.render.resolution_percentage = 100
cam = bpy.data.cameras.new('c'); cam.lens_unit = 'FOV'; cam.angle = math.radians(float(arg('--fov', 50))); cam.clip_start = 0.02; cam.clip_end = 500
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
eye, at = W(arg('--eye')), W(arg('--at'))
co.location = eye; co.rotation_euler = (at - eye).to_track_quat('-Z', 'Y').to_euler()
# pose clips: move every NLA strip named X to frame f
poses = dict(p.split('=') for p in a[a.index('--clip') + 1:] if '=' in p) if '--clip' in a else {}
for o in bpy.data.objects:
    ad = o.animation_data
    if not ad: continue
    for tr in ad.nla_tracks:
        if tr.name in poses:
            for st in tr.strips:
                act = st.action; ad.action = act
                sc.frame_set(int(poses[tr.name])); bpy.context.view_layer.update()
                loc, rot = o.location.copy(), o.rotation_euler.copy(); ad.action = None; o.location, o.rotation_euler = loc, rot
        tr.mute = True
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']
try:
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(float(arg('--sun', 140)))
    nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.35
except Exception as e:
    bg.inputs[0].default_value = (0.8, 0.85, 0.9, 1)
# ground
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.001)); g = bpy.context.object
gm = bpy.data.materials.new('ground'); gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.22, 0.22, 0.21, 1); gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
g.data.materials.append(gm)
if '--lamp' in a:
    l = bpy.data.lights.new('l', 'POINT'); l.energy = float(arg('--lampw', 60)); lo = bpy.data.objects.new('l', l); sc.collection.objects.link(lo); lo.location = eye + Vector((0, 0, 0.1))
sc.view_settings.view_transform = 'Standard' if 'Standard' in [v.name for v in type(sc.view_settings).bl_rna.properties['view_transform'].enum_items] else sc.view_settings.view_transform
sc.render.filepath = a[1]; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
bpy.ops.render.render(write_still=True); print('wrote', a[1])

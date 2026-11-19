"""Render a built .blend.  python3 tools/render.py -- --blend work/x.blend --out renders_work --shots a,b [--px 1600] [--samples 24] [--ground] [--hide name,name]
Cycles on the CPU. Orthographic shots with a cut use camera clipping, and switch shadows off so the inside is lit."""
import bpy, sys, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path[:0] = [HERE, os.path.join(HERE, 'tools')]
import spec, shots as SH
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, arg('--blend')))
OUT = os.path.join(HERE, arg('--out', 'work/r')); os.makedirs(OUT, exist_ok=True)
names = arg('--shots', 'port_side').split(','); PXW = int(arg('--px', 1600)); SAMPLES = int(arg('--samples', 24))
def bl(p): return Vector((-p[1], p[0] - spec.L / 2, p[2]))
def bd(d): return Vector((-d[1], d[0], d[2]))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.transparent_max_bounces = 16
sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 92
sc.render.threads_mode = 'AUTO'
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
bgc = tuple(float(v) for v in arg('--bg', '0.80,0.81,0.83').split(','))
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (*bgc, 1); bg.inputs[1].default_value = float(arg('--amb', 0.9))
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = float(arg('--sun', 3.0)); sun.data.angle = math.radians(8)
def aim_sun(d):
    sun.rotation_euler = bd(d).to_track_quat('-Z', 'Y').to_euler()
aim_sun((0.45, 0.55, -0.7))
if '--ground' in argv:
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, spec.Z_GROUND))
    g = bpy.context.object; m = bpy.data.materials.new('ground'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.40, 0.38, 1); m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    g.data.materials.append(m)
for nm in (arg('--hide', '') or '').split(','):
    for o in bpy.data.objects:
        if nm and (o.name == nm or o.name.startswith(nm)):
            o.hide_render = True
            for ch in o.children_recursive: ch.hide_render = True
pose = arg('--pose')          # clip:frame[,clip:frame] : show the ship part-way through one or more clips
if pose:
    import posing
    posing.pose({item.split(':')[0]: int(item.split(':')[1]) for item in pose.split(',')})
if '--no-interior-lights' not in argv:      # soft lamps down both decks so the inside reads in renders (not part of the model)
    for s in (3.2, 7.2, 10.0, 12.4, 15.5, 18.5, 22.8):
        for z, e in ((spec.Z_MAIN + 1.9, 180), (spec.Z_LOWER + 1.9, 180)):
            if s < 4 and z < 0: continue
            lt = bpy.data.objects.new('lamp', bpy.data.lights.new('lamp', 'POINT')); sc.collection.objects.link(lt)
            lt.data.energy = e * float(arg('--lamps', 1.0)); lt.data.shadow_soft_size = 0.35; lt.location = bl((s, 0.0, z if s > 4 else 1.35))
figs = arg('--figures')       # "s,y,z;s,y,z" : 1.80 m scale figures standing at those points (not part of the model)
if figs:
    sys.path.insert(0, os.path.join(HERE, 'modules'))
    import kit, figure
    mb = kit.MB()
    for item in figs.split(';'):
        s, y, z = [float(v) for v in item.split(',')]
        mb.merge(figure.figure_mb(s, y, z))
    kit.finish('scale_figures', mb, None)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
def set_shadows(on):
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.visible_shadow = on
            try: o.visible_diffuse = on; o.visible_glossy = on
            except Exception: pass
for name in names:
    if name in SH.ORTHO:
        s = SH.ORTHO[name]; R = bd(s['right']).normalized(); U = bd(s['up']).normalized(); B = R.cross(U)
        dist = 60.0
        cam.matrix_world = Matrix((( R.x, U.x, B.x, 0), (R.y, U.y, B.y, 0), (R.z, U.z, B.z, 0), (0, 0, 0, 1)))
        cam.location = bl(s['centre']) + B * dist
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = s['width']
        cut = s.get('cut')
        cam.data.clip_start = (dist - cut) if cut is not None else 0.1; cam.data.clip_end = 200
        sc.render.resolution_x = PXW; sc.render.resolution_y = int(PXW / s['aspect'])
        set_shadows(cut is None)
        # light from the viewer's upper left
        v = -B * 0.8 - U * 0.5 + R * 0.35
        sun.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
    else:
        s = SH.PERSP[name]; eye, tgt = bl(s['eye']), bl(s['target'])
        cam.location = eye; cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'PERSP'; cam.data.lens = s['lens']; cam.data.clip_start = 0.05; cam.data.clip_end = 500
        sc.render.resolution_x = PXW; sc.render.resolution_y = int(PXW * 9 / 16)
        set_shadows(True); aim_sun((0.45, 0.55, -0.7))
    sc.render.filepath = os.path.join(OUT, name + '.jpg')
    bpy.ops.render.render(write_still=True); print('RENDERED', name, flush=True)

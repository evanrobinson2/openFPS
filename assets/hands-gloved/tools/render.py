"""blender -b --python tools/render.py -- scene.npz out.png
Generic renderer for simulation-generated pictures.  scene.npz holds: n meshes as V_<i> (mm, asset frame: +X left,
+Y up, +Z muzzle), F_<i>, and meta (json): materials per mesh, camera (eye, target, up, fov_deg or ortho_mm), size."""
import bpy, sys, json, math, numpy as np
from mathutils import Vector, Matrix
argv = sys.argv[sys.argv.index('--') + 1:]; z = np.load(argv[0], allow_pickle=False); meta = json.loads(str(z['meta'])); out = argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
MATS = dict(  # name: (rgb, roughness, metallic)
    glove_back_knit=((0.36, 0.26, 0.15), 0.92, 0.0), glove_palm_synthetic_leather=((0.30, 0.21, 0.12), 0.70, 0.0),
    glove_fingertip=((0.22, 0.15, 0.09), 0.62, 0.0), glove_cuff=((0.045, 0.045, 0.05), 0.85, 0.0), glove_flex_rib=((0.27, 0.19, 0.105), 0.8, 0.0),
    glove_tab=((0.30, 0.22, 0.13), 0.55, 0.0), glove_terry=((0.40, 0.29, 0.17), 1.0, 0.0), glove_seam=((0.20, 0.14, 0.08), 0.9, 0.0),
    sleeve_fabric=((0.55, 0.56, 0.55), 0.95, 0.0), rifle=((0.045, 0.046, 0.05), 0.55, 0.35), rifle_polymer=((0.05, 0.05, 0.052), 0.65, 0.0),
    red=((0.8, 0.05, 0.05), 0.6, 0.0), bone=((0.85, 0.82, 0.72), 0.6, 0.0), skin=((0.62, 0.45, 0.36), 0.6, 0.0))
def mat(name):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; c, r, me = MATS.get(name, ((0.5, 0.5, 0.5), 0.7, 0.0))
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = r; b.inputs['Metallic'].default_value = me; return m
def to_bl(V): V = np.asarray(V, float) * 0.001; return np.c_[V[:, 0], -V[:, 2], V[:, 1]]
for i, m in enumerate(meta['meshes']):
    V = to_bl(z[f'V_{i}']); F = z[f'F_{i}']; me = bpy.data.meshes.new(m['name']); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    o = bpy.data.objects.new(m['name'], me); sc.collection.objects.link(o)
    if 'mats' in m:
        for nm in m['mats']: me.materials.append(mat(nm))
        me.polygons.foreach_set('material_index', z[f'M_{i}'].astype(np.int32)); me.update()
    else: me.materials.append(mat(m.get('mat', 'rifle')))
    if m.get('smooth', True):
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        if m.get('autosmooth'):
            md = o.modifiers.new('n', 'NODES') if False else None
cam = meta['camera']; cd = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
W, H = meta.get('size', [1280, 853]); sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
if 'cv' in cam:
    # a fitted photo camera: world (asset frame, mm) -> camera (OpenCV: x right, y down, z forward) as R, t; focal length and principal point in pixels
    R = np.array(cam['cv']['R'], float); tv = np.array(cam['cv']['t'], float); eye_a = -R.T @ tv; A2B = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.0]])
    Rb = A2B @ R.T @ np.diag([1.0, -1.0, -1.0]); e = A2B @ eye_a * 0.001
    co.matrix_world = Matrix(((Rb[0, 0], Rb[0, 1], Rb[0, 2], e[0]), (Rb[1, 0], Rb[1, 1], Rb[1, 2], e[1]), (Rb[2, 0], Rb[2, 1], Rb[2, 2], e[2]), (0, 0, 0, 1)))
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = cam['cv']['f'] * 36.0 / W; cd.shift_x = -(cam['cv']['c'][0] - W / 2) / W; cd.shift_y = (cam['cv']['c'][1] - H / 2) / W
else:
    eye = Vector(to_bl([cam['eye']])[0]); tgt = Vector(to_bl([cam['target']])[0]); up = Vector((cam.get('up', [0, 1, 0])[0], -cam.get('up', [0, 1, 0])[2], cam.get('up', [0, 1, 0])[1]))
    fwd = (tgt - eye).normalized(); right = fwd.cross(up).normalized(); up2 = right.cross(fwd)
    co.matrix_world = Matrix((( right.x, up2.x, -fwd.x, eye.x), (right.y, up2.y, -fwd.y, eye.y), (right.z, up2.z, -fwd.z, eye.z), (0, 0, 0, 1)))
    if 'ortho_mm' in cam: cd.type = 'ORTHO'; cd.ortho_scale = cam['ortho_mm'] * 0.001
    else:
        cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.lens = 18.0 / math.tan(math.radians(cam['fov_deg']) / 2)
        cd.shift_x = cam.get('shift', [0, 0])[0]; cd.shift_y = cam.get('shift', [0, 0])[1]
cd.clip_start = 0.01; cd.clip_end = 50
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (*meta.get('sky', [0.80, 0.83, 0.88]), 1); bg.inputs[1].default_value = meta.get('sky_strength', 0.9)
sd = bpy.data.lights.new('sun', 'SUN'); sd.energy = meta.get('sun', 2.2); sd.angle = 0.35; so = bpy.data.objects.new('sun', sd); sc.collection.objects.link(so)
d = Vector(to_bl([meta.get('sun_dir', [0.3, -1.0, 0.25])])[0]).normalized(); so.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'CYCLES'; sc.cycles.samples = meta.get('samples', 24); sc.cycles.use_denoising = True
try:
    sc.cycles.device = 'GPU'; pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'METAL'; pr.get_devices()
    for dv in pr.devices: dv.use = True
except Exception as e: print('gpu', e)
sc.view_settings.view_transform = 'Standard'; sc.render.film_transparent = False
sc.render.image_settings.file_format = 'JPEG' if out.lower().endswith('.jpg') else 'PNG'; sc.render.image_settings.quality = 90
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('RENDERED', out)

"""Generic QD 5.56 mm suppressor: Blender recipe.

    blender -b --python build.py                 # meshes, clips, GLBs, checks, all renders
    blender -b --python build.py -- --fast       # meshes, clips, GLBs and checks only
    blender -b --python build.py -- --only section,cutaway [--px 1400] [--samples 40]

Everything is written to build/ (ignored by git: meshes are build outputs) except the renders (../renders/*.jpg)
and build_stats.json. Every dimension comes from geom.py, which the gas simulation shares.

Frame, as the HK416 model: Blender Z up, metres, muzzle toward -Y, shooter's left +X (glTF: +Z down-range, +Y up).
The origin is `socket_mount`, which sits on the rifle's `socket_muzzle` (the tip of the flash hider): parent the
`suppressor` node to that socket with an identity transform.

Nodes: suppressor (root) > can_body > mount_body, tube, blast_sleeve, blast_baffle, baffle_2..6, end_cap, panels;
suppressor > lock_collar > collar_index; suppressor > jaw_1..3; suppressor > socket_mount, socket_exit, socket_thermal.
Clips (24 fps, one NLA track each): qd_attach, qd_detach. The rest pose is attached and locked.
"""
import bpy, bmesh, json, math, os, struct, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geom

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d): return argv[argv.index(k) + 1] if k in argv else d
FAST = '--fast' in argv; ONLY = arg('--only', ''); PXW = int(arg('--px', 1400)); SAMPLES = int(arg('--samples', 40))
SEGS = 72; MM = 1e-3
BUILD = os.path.join(HERE, 'build'); RENDERS = os.path.join(os.path.dirname(HERE), 'renders')
os.makedirs(BUILD, exist_ok=True); os.makedirs(RENDERS, exist_ok=True)

MATS = dict(   # name: (base colour, metallic, roughness)
    CanBody=((0.035, 0.036, 0.038, 1), 0.85, 0.52),      # matte black high-temperature finish
    CanCollar=((0.020, 0.020, 0.022, 1), 0.90, 0.38),    # black nitride, a little glossier
    Baffle=((0.24, 0.23, 0.215, 1), 1.00, 0.58),         # bare nickel alloy, lightly heat-tinted
    Panel=((0.050, 0.051, 0.054, 1), 0.70, 0.66),        # plain placeholder panel: a shade lighter, no marks
    CutFace=((0.80, 0.42, 0.12, 1), 0.00, 0.60),         # section faces of the cutaway renders (not a real surface)
    Rifle=((0.10, 0.10, 0.105, 1), 0.80, 0.45),          # stand-in muzzle device for the section renders
    CutFaceRifle=((0.42, 0.45, 0.48, 1), 0.00, 0.60),    # section faces of the stand-in rifle parts
)

def material(name):
    m = bpy.data.materials.get(name)
    if m: return m
    col, met, rough = MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = col; b.inputs['Metallic'].default_value = met; b.inputs['Roughness'].default_value = rough
    return m

def to_xyz(s, r, th):
    return (r * math.cos(th) * MM, -(s - geom.S_MOUNT) * MM, r * math.sin(th) * MM)

def finish(name, bm, mat, coll, parent, cut_faces=(), cut_mat='CutFace'):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); ob = bpy.data.objects.new(name, me)
    me.materials.append(material(mat))
    if cut_faces:
        me.materials.append(material('CutFaceRifle' if mat == 'Rifle' else cut_mat))
        for f in cut_faces: f.material_index = 1
    for f in bm.faces: f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) > math.radians(28): e.smooth = False
    bm.to_mesh(me); bm.free()
    coll.objects.link(ob); ob.parent = parent
    return ob

def lathe(name, poly, mat, coll, parent, sweep=2 * math.pi, th0=0.0, segs=SEGS, detail_name=None):
    """Revolve the closed (s, r) polygon about the bore. A partial sweep gets flat section faces."""
    full = sweep > 2 * math.pi - 1e-6
    n_th = segs if full else max(2, int(round(segs * sweep / (2 * math.pi)))) + 1
    bm = bmesh.new(); rings = []
    for a in range(n_th):
        th = th0 + sweep * a / (n_th if full else n_th - 1)
        rings.append([bm.verts.new(to_xyz(*geom.detail(detail_name or name, s, r, th), th)) for s, r in poly])
    npnt = len(poly)
    for a in range(n_th if full else n_th - 1):
        r0, r1 = rings[a], rings[(a + 1) % n_th]
        for i in range(npnt):
            j = (i + 1) % npnt
            try: bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            except ValueError: pass
    cut = []
    if not full: cut = [bm.faces.new(rings[0]), bm.faces.new(list(reversed(rings[-1])))]
    return finish(name, bm, mat, coll, parent, cut)

def arc_solid(name, s0, s1, r0, r1, th_c, arc, mat, coll, parent, segs=12):
    """A closed arc segment (a jaw, or a thin panel) centred on angle th_c (degrees)."""
    bm = bmesh.new(); a0 = math.radians(th_c - arc / 2); rings = []
    for k in range(segs + 1):
        th = a0 + math.radians(arc) * k / segs
        rings.append([bm.verts.new(to_xyz(s, r, th)) for s, r in ((s0, r0), (s0, r1), (s1, r1), (s1, r0))])
    for k in range(segs):
        for i in range(4):
            j = (i + 1) % 4; bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    return finish(name, bm, mat, coll, parent)

def empty(name, loc, coll, parent, kind='ARROWS', size=0.01):
    e = bpy.data.objects.new(name, None); e.empty_display_type = kind; e.empty_display_size = size
    e.location = loc; coll.objects.link(e); e.parent = parent; return e

JAW_TH = [90.0 + 120.0 * k for k in range(geom.G['jaws'])]
# exploded view: how far down-range each part is moved, mm (the internals come out of the front of the tube)
EXPLODE = dict(lock_collar=-62.0, mount_body=-30.0, tube=0.0, blast_sleeve=150.0, end_cap=150.0 + 40.0 + 6 * 34.0 + 6.0)
for _i in range(geom.G['n_baffles']): EXPLODE[geom.baffle_name(_i)] = 150.0 + 40.0 + _i * 34.0

def build(tag, sweep=2 * math.pi, th0=0.0, explode=0.0, with_rifle=False):
    """tag '' is the asset itself; other tags are render-only variants (their object names get the tag as a suffix)."""
    sfx = '' if not tag else '_' + tag
    coll = bpy.data.collections.new(tag or 'asset'); bpy.context.scene.collection.children.link(coll)
    root = empty('suppressor' + sfx, (0, 0, 0), coll, None, 'PLAIN_AXES', 0.02)
    body = empty('can_body' + sfx, (0, 0, 0), coll, root, 'PLAIN_AXES', 0.01)
    P = geom.parts(); objs = {}
    order = list(P.keys())
    for nm, part in P.items():
        par = root if nm == 'lock_collar' else body
        ob = lathe(nm + sfx, part['poly'], part['mat'], coll, par, sweep, th0, detail_name=nm)
        if explode: ob.location.y = -MM * EXPLODE[nm]
        objs[nm] = ob
    j = geom.jaw()
    for k, th in enumerate(JAW_TH):
        nm = 'jaw_%d' % (k + 1)
        if sweep < 2 * math.pi - 1e-6 and not (math.degrees(th0) <= th <= math.degrees(th0 + sweep) or math.degrees(th0) <= th + 360 <= math.degrees(th0 + sweep)): continue
        ob = arc_solid(nm + sfx, j['s0'], j['s1'], j['r_in'], j['r_out'], th, j['arc_deg'], j['mat'], coll, root)
        if explode: ob.location.y = -MM * (EXPLODE['lock_collar'] - 22.0)
        objs[nm] = ob
    if not tag or explode:
        for nm, pn in geom.panels().items():
            par = objs['lock_collar'] if pn.get('on') else body
            r = (18.4 if pn.get('on') else geom.R_OUT) - 0.02
            ob = arc_solid(nm + sfx, pn['s0'], pn['s1'], r, r + 0.12, pn['th_deg'], pn['arc_deg'], 'Panel', coll, par, segs=16)
            if explode and not pn.get('on'): ob.location.y = objs['tube'].location.y
            objs[nm] = ob
    if not tag:
        for nm, sk in geom.sockets().items():
            x, y, z = sk['pos']; objs[nm] = empty(nm, (x, -z, y), coll, root)          # asset frame (+Z down-range, +Y up) -> Blender
    if with_rifle:                                          # stand-in for the rifle's flash hider and barrel, section renders only
        lathe('rifle_flash_hider' + sfx, geom.hider_poly(), 'Rifle', coll, root, sweep, th0)
        lathe('rifle_barrel' + sfx, [(-40, 2.8), (-40, 8.9), (geom.S_HIDER0 - 9, 8.9), (geom.S_HIDER0 - 9, geom.G['jam_ring_r']), (geom.S_HIDER0, geom.G['jam_ring_r']),
                                      (geom.S_HIDER0, 6.2), (geom.S_CROWN, 6.2), (geom.S_CROWN, 2.8)], 'Rifle', coll, root, sweep, th0)
    return coll, root, objs

# ------------------------------------------------------------------ clips (24 fps, one NLA track per clip)
def bake_clips(root, objs):
    C = geom.clips(); reg = {}
    def keys(ob, clip, path, index, pairs):
        ad = ob.animation_data or ob.animation_data_create()
        act = bpy.data.actions.get('%s.%s' % (clip, ob.name)) or bpy.data.actions.new('%s.%s' % (clip, ob.name))
        ad.action = act; ob.rotation_mode = 'XYZ'
        rest_l = ob.location.copy(); rest_r = ob.rotation_euler.copy()
        for fr, v in pairs:
            if path == 'location': ob.location = rest_l.copy(); ob.location[index] = rest_l[index] + v
            else: ob.rotation_euler = rest_r.copy(); ob.rotation_euler[index] = rest_r[index] + v
            ob.keyframe_insert(path, index=index, frame=fr)
        ob.location = rest_l; ob.rotation_euler = rest_r
        reg.setdefault(clip, set()).add(ob.name)
    def close(ob, clip):
        ad = ob.animation_data; act = ad.action
        tr = ad.nla_tracks.new(); tr.name = clip; tr.strips.new(clip, 1, act); tr.mute = True      # muted: the rest pose stays the rest pose
        ad.action = None
    for clip, c in C.items():
        keys(root, clip, 'location', 1, [(f, -v * MM) for f, v in c['suppressor_slide_mm']])           # down-range is -Y
        keys(root, clip, 'rotation_euler', 1, [(f, math.radians(v)) for f, v in c['suppressor_roll_deg']])
        close(root, clip)
        keys(objs['lock_collar'], clip, 'rotation_euler', 1, [(f, math.radians(v)) for f, v in c['lock_collar_turn_deg']])
        close(objs['lock_collar'], clip)
        for k, th in enumerate(JAW_TH):
            ob = objs['jaw_%d' % (k + 1)]; a = math.radians(th)
            keys(ob, clip, 'location', 0, [(f, v * MM * math.cos(a)) for f, v in c['jaw_out_mm']])
            keys(ob, clip, 'location', 2, [(f, v * MM * math.sin(a)) for f, v in c['jaw_out_mm']])
            close(ob, clip)
    return {k: sorted(v) for k, v in reg.items()}

def export(coll, path):
    for o in bpy.data.objects: o.select_set(False)
    for o in coll.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=False, export_yup=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS')
    print('EXPORTED', os.path.basename(path), os.path.getsize(path), 'bytes', flush=True)

def glb_json(path):
    with open(path, 'rb') as f:
        f.read(12); n, _ = struct.unpack('<I4s', f.read(8)); return json.loads(f.read(n))

def tri_count(coll):
    return {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll.objects if o.type == 'MESH'}

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 24; sc.frame_start = 1; sc.frame_end = 36; sc.unit_settings.system = 'METRIC'
full, full_root, OBJ = build('')
clips = bake_clips(full_root, OBJ)
export(full, os.path.join(BUILD, 'suppressor-qd-556.glb'))

# ---- checks of the build output against the recipe
inv = geom.inventory(); g = glb_json(os.path.join(BUILD, 'suppressor-qd-556.glb'))
names = [n.get('name') for n in g['nodes']]; want = [p['name'] for p in inv['parts']] + list(inv['sockets']) + ['suppressor', 'can_body']
tris = tri_count(full)
par = {}
for i, n in enumerate(g['nodes']):
    for c in n.get('children', []): par[g['nodes'][c]['name']] = n['name']
exit_node = next(n for n in g['nodes'] if n.get('name') == 'socket_exit')
stats = dict(
    asset='suppressor-qd-556', blender=bpy.app.version_string, parts=len(tris), triangles=sum(tris.values()), by_part=tris,
    nodes=len(names), missing=[n for n in want if n not in names], unexpected=[n for n in names if n not in want],
    hierarchy_ok=all(par.get(c) == p for p, d in (('suppressor', ['can_body', 'lock_collar', 'jaw_1', 'jaw_2', 'jaw_3', 'socket_mount', 'socket_exit', 'socket_thermal']),
                                                   ('can_body', ['mount_body', 'tube', 'blast_sleeve', 'blast_baffle', 'baffle_2', 'baffle_6', 'end_cap', 'marking_panel']),
                                                   ('lock_collar', ['collar_index'])) for c in d),
    clips={a['name']: dict(channels=len(a['channels']), nodes=sorted({g['nodes'][c['target']['node']]['name'] for c in a['channels']})) for a in g.get('animations', [])},
    clips_baked=clips, socket_exit_gltf=exit_node.get('translation'), socket_exit_recipe=inv['sockets']['socket_exit']['pos'],
    materials=sorted(m['name'] for m in g['materials']), fit_checks_mm=inv['fit_checks_mm'], glb_bytes=os.path.getsize(os.path.join(BUILD, 'suppressor-qd-556.glb')))
stats['passed'] = (not stats['missing'] and not stats['unexpected'] and stats['hierarchy_ok'] and sorted(stats['clips']) == ['qd_attach', 'qd_detach']
                   and all(abs(a - b) < 1e-5 for a, b in zip(stats['socket_exit_gltf'], stats['socket_exit_recipe'])) and inv['fit_checks_mm']['passed'])
json.dump(stats, open(os.path.join(HERE, 'build_stats.json'), 'w'), indent=1)
print('BUILD parts %d, triangles %d, clips %s, passed %s' % (stats['parts'], stats['triangles'], sorted(stats['clips']), stats['passed']), flush=True)
if stats['missing'] or stats['unexpected']: print('  missing', stats['missing'], 'unexpected', stats['unexpected'], flush=True)
if FAST: sys.exit(0)

# ------------------------------------------------------------------ renders (Cycles, CPU). Variants are render-only.
cut, cut_root, _ = build('cutaway', 1.5 * math.pi, math.radians(180), with_rifle=True)      # the upper quarter on the rifle's right is removed
half, half_root, _ = build('half', math.pi, math.radians(-90), with_rifle=True)            # the right half is removed: a true section
expl, expl_root, _ = build('exploded', explode=30.0)
rifle_path = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'hk416', 'model', 'hk416.glb')
have_rifle = os.path.exists(rifle_path); muz = Vector((0, 0, 0)); eye = None
if have_rifle:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=rifle_path)
    rifle_objs = [o for o in bpy.data.objects if o not in before]
    m = bpy.data.objects['socket_muzzle'].matrix_world.translation.copy(); eye = bpy.data.objects['socket_ads_eye'].matrix_world.translation.copy() - m
    for o in rifle_objs:
        if o.parent is None: o.location = o.location - m                                    # bring the rifle's socket_muzzle to our origin
    print('rifle loaded; socket_muzzle at', tuple(round(v, 4) for v in m), flush=True)
else:
    rifle_objs = []; print('no local hk416.glb (build assets/hk416/model first): on-rifle renders skipped', flush=True)

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'Standard'; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
w = bpy.data.worlds.new('studio'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.78, 0.79, 0.80, 1); bg.inputs[1].default_value = 0.7
def light(name, loc, energy, size, target):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size; o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
T = Vector((0, -0.04, 0))
light('key', T + Vector((-1.0, -0.7, 1.2)), 110, 1.2, T); light('fill', T + Vector((1.2, 0.1, 0.6)), 55, 1.5, T)
light('rim', T + Vector((0.2, 1.3, 0.9)), 70, 1.0, T); light('under', T + Vector((0.0, -0.1, -1.0)), 14, 2.0, T)
light('rifle_key', Vector((-1.2, 0.1, 1.3)), 90, 1.4, Vector((0, 0.35, 0)))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
VAR = dict(full=full, cutaway=cut, half=half, exploded=expl)

def show(which, rifle):
    for nm, c in VAR.items():
        for o in c.objects: o.hide_render = nm != which
    for o in rifle_objs: o.hide_render = not rifle

def shot(name, which, loc, target, ortho=None, lens=50, aspect=16 / 9, px=None, rifle=False, frame=None, clip=None):
    if ONLY and name not in ONLY.split(','): return
    if rifle and not have_rifle: return
    show(which, rifle)
    sc.render.resolution_x = px or PXW; sc.render.resolution_y = int((px or PXW) / aspect)
    cam.location = loc; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO' if ortho else 'PERSP'; cam.data.clip_start = 0.005; cam.data.clip_end = 20
    if ortho: cam.data.ortho_scale = ortho
    else: cam.data.lens = lens
    if clip:                                                # pose the asset at one frame of a clip
        for o in full.objects:
            if o.animation_data:
                for tr in o.animation_data.nla_tracks: tr.mute = tr.name != clip
        sc.frame_set(frame)
    sc.render.filepath = os.path.join(RENDERS, name + '.jpg'); bpy.ops.render.render(write_still=True); print('RENDERED', name, flush=True)
    if clip:
        for o in full.objects:
            if o.animation_data:
                for tr in o.animation_data.nla_tracks: tr.mute = True
        sc.frame_set(1)

mid = Vector((0, -0.035, 0))                               # centre of the can: 87 mm from its rear face
shot('side', 'full', (-2, mid.y, 0), mid, ortho=0.26, aspect=2.4)
shot('three_quarter', 'full', (-0.26, -0.30, 0.13), mid, lens=85)
shot('three_quarter_rear', 'full', (-0.28, 0.26, 0.14), mid, lens=85)
shot('front', 'full', (0, -1.2, 0), mid, ortho=0.075, aspect=1.0, px=900)
shot('section', 'half', (-2, mid.y, 0), mid, ortho=0.26, aspect=2.4)
shot('cutaway', 'cutaway', (-0.25, -0.22, 0.17), mid, lens=85)
shot('exploded', 'exploded', (-1.3, -0.62, 0.62), Vector((0, -0.215, 0)), ortho=0.66, aspect=3.0)
shot('qd_attach_frame_01', 'full', (-0.34, -0.36, 0.17), Vector((0, -0.06, 0)), lens=85, rifle=True, clip='qd_attach', frame=1)
shot('qd_attach_frame_22', 'full', (-0.34, -0.36, 0.17), Vector((0, -0.06, 0)), lens=85, rifle=True, clip='qd_attach', frame=22)
shot('on_rifle_right', 'full', (-2, 0.34, -0.035), Vector((0, 0.34, -0.035)), ortho=1.06, aspect=2.6, rifle=True)
shot('on_rifle_three_quarter', 'full', (-0.50, -0.48, 0.24), mid + Vector((0, 0.10, 0)), lens=70, rifle=True)
if eye is not None: shot('first_person', 'full', eye, eye + Vector((0, -1, 0)), lens=24, rifle=True)

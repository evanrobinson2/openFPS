"""blender -b work/hk416_lod0.blend --python tools/checks.py
Inventory coverage, assembly (no floating parts), animation interpenetration, and the GLB reload check.
Writes work/checks.json.  Tolerances: parts 'touch' when the gap is <= 0.25 mm; a clip fails when a moving part
goes more than 0.2 mm inside a part it moves relative to."""
import bpy, json, os, sys, math, struct
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOUCH, PEN = 0.25e-3, 0.2e-3
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH']
res = {}

# ------------------------------------------------------------ inventory coverage
inv = json.load(open(os.path.join(HERE, 'inventory.json')))
names = {o.name for o in meshes}
missing = sorted({r['part_name'] for r in inv} - names)
res['inventory'] = dict(features=len(inv), parts_named=len({r['part_name'] for r in inv}), merged_features=sum(1 for r in inv if r.get('merged')),
                        missing_parts=missing, objects_not_in_inventory=sorted(names - {r['part_name'] for r in inv}),
                        coverage=round(1 - sum(1 for r in inv if r['part_name'] in missing) / len(inv), 4), passed=not missing)

# ------------------------------------------------------------ geometry helpers
def world(o):
    M = o.matrix_world; me = o.data; me.calc_loop_triangles()
    vs = [M @ v.co for v in me.vertices]; ts = [tuple(t.vertices) for t in me.loop_triangles]
    return vs, ts
def bbox(vs):
    a = np.array(vs); return a.min(0), a.max(0)
def near(b1, b2, pad):
    return bool(np.all(b1[0] - pad <= b2[1]) and np.all(b2[0] - pad <= b1[1]))
def inside_depth(p, bvh):
    """Depth of p below the nearest surface of a closed, outward-facing mesh (0 if outside)."""
    q, n, i, d = bvh.find_nearest(p)
    if q is None: return 0.0
    return d if (p - q).dot(n) < -1e-9 else 0.0

def snapshot():
    sc.view_layers[0].update(); out = {}
    for o in meshes:
        vs, ts = world(o); out[o.name] = dict(vs=vs, ts=ts, bb=bbox(vs), bvh=BVHTree.FromPolygons(vs, ts), M=o.matrix_world.copy())
    return out

# ------------------------------------------------------------ assembly
rest = snapshot(); floating = []; contact = {}
for a in meshes:
    A = rest[a.name]; best = (1e9, None)
    for b in meshes:
        if b is a: continue
        B = rest[b.name]
        if not near(A['bb'], B['bb'], TOUCH): continue
        if A['bvh'].overlap(B['bvh']): best = (0.0, b.name); break
        if best[0] <= TOUCH: continue
        d = min([x[3] for x in (B['bvh'].find_nearest(v, 0.002) for v in A['vs']) if x[0] is not None] +
                [x[3] for x in (A['bvh'].find_nearest(v, 0.002) for v in B['vs']) if x[0] is not None] + [1e9])
        if d > TOUCH and (inside_depth(A['vs'][0], B['bvh']) > 0 or inside_depth(B['vs'][0], A['bvh']) > 0): d = 0.0     # one sits inside the other
        if d < best[0]: best = (d, b.name)
    contact[a.name] = best
    if best[0] > TOUCH: floating.append(dict(part=a.name, nearest=best[1], gap_mm=None if best[1] is None else round(best[0] * 1000, 3)))
groups = json.loads(sc['hk416_groups'])
fast = [n for n in names if groups.get(n) == 'fasteners']
not_seated = [n for n in fast if contact[n][0] > 0.0]
res['assembly'] = dict(parts=len(meshes), floating=floating, fasteners=len(fast), fasteners_not_seated=not_seated, passed=not floating and not not_seated)

# ------------------------------------------------------------ animation
clips = json.loads(sc['hk416_clips']); anim = {}
def pose(clip, frame):
    for name, act in clips[clip].items():
        o = bpy.data.objects[name]; ad = o.animation_data; a = bpy.data.actions[act]; ad.action = a
        if getattr(ad, 'action_slot', None) is None and len(a.slots): ad.action_slot = a.slots[0]
    sc.frame_set(frame); sc.view_layers[0].update()
def unpose(clip, restloc):
    for name in clips[clip]:
        o = bpy.data.objects[name]; o.animation_data.action = None; o.location = restloc[name]; o.rotation_euler = (0, 0, 0)
    sc.view_layers[0].update()
restloc = {o.name: o.location.copy() for o in sc.objects}
for clip in clips:
    acts = [bpy.data.actions[a] for a in clips[clip].values()]
    f0 = int(min(a.frame_range[0] for a in acts)); f1 = int(max(a.frame_range[1] for a in acts))
    worst = dict(depth_mm=0.0); moved_any = set(); ends = []
    for f in range(f0, f1 + 1):
        pose(clip, f)
        cur = {o.name: o.matrix_world.copy() for o in meshes}
        moving = [o for o in meshes if (cur[o.name].inverted() @ rest[o.name]['M'] - Matrix.Identity(4)).to_3x3().median_scale > 1e-12 or (cur[o.name].translation - rest[o.name]['M'].translation).length > 1e-7
                  or any(abs(x) > 1e-7 for r in (cur[o.name].to_3x3() - rest[o.name]['M'].to_3x3()) for x in r)]
        moved_any |= {o.name for o in moving}
        if f in (f0, f1): ends.append({o.name: [round(x * 1000, 2) for x in (cur[o.name].translation - rest[o.name]['M'].translation)] for o in moving if o.name in clips[clip]})
        for m in moving:
            Mm = cur[m.name]; D = Mm @ rest[m.name]['M'].inverted()          # rest-world -> current-world for m
            mv = [D @ v for v in rest[m.name]['vs']]; mb = bbox(mv)
            mb_bvh = None
            for s in meshes:
                if s is m: continue
                Ds = cur[s.name] @ rest[s.name]['M'].inverted()
                rel = D.inverted() @ Ds
                if all(abs(rel[i][j] - (1.0 if i == j else 0.0)) < 1e-6 for i in range(4) for j in range(4)): continue     # rigid with m: same assembly
                S = rest[s.name]; sv = S['vs'] if s not in moving else [Ds @ v for v in S['vs']]
                sb = bbox(sv)
                if not near(mb, sb, 0.0): continue
                Dsi = Ds.inverted()
                d1 = max([inside_depth(Dsi @ p, S['bvh']) for p in mv if np.all(np.array(p) >= sb[0]) and np.all(np.array(p) <= sb[1])] + [0.0])
                Di = D.inverted()
                d2 = max([inside_depth(Di @ p, rest[m.name]['bvh']) for p in sv if np.all(np.array(p) >= mb[0]) and np.all(np.array(p) <= mb[1])] + [0.0])
                d = max(d1, d2)
                if d * 1000 > worst['depth_mm']: worst = dict(depth_mm=round(d * 1000, 3), frame=f, moving=m.name, into=s.name)
    unpose(clip, restloc)
    anim[clip] = dict(frames=[f0, f1], seconds=round((f1 - f0) / 24, 2), moving_parts=len(moved_any), animated=sorted(clips[clip]), offsets_mm_at_ends=ends,
                      worst_penetration=worst, passed=worst['depth_mm'] <= PEN * 1000)
res['animation'] = dict(clips=anim, passed=all(c['passed'] for c in anim.values()))

# ------------------------------------------------------------ export: reload the GLB and compare
glb = os.path.join(HERE, 'hk416.glb'); built = dict(objects=len(meshes), materials=len({o.data.materials[0].name for o in meshes}))
d = open(glb, 'rb').read(); n = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + n])
imgs = j.get('images', []); embedded = all('bufferView' in i for i in imgs)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
rm = [o for o in bpy.context.scene.objects if o.type == 'MESH']
b = bpy.data.objects['barrel']; bpy.context.view_layer.update()
ys = [(b.matrix_world @ v.co).y for v in b.data.vertices]; blen = (max(ys) - min(ys)) * 1000
tr = 0
for o in rm: o.data.calc_loop_triangles(); tr += len(o.data.loop_triangles)
res['export'] = dict(file_bytes=len(d), built=built, reloaded=dict(objects=len(rm), materials=len({o.data.materials[0].name.split('.')[0] for o in rm}), triangles=tr,
                     animations=sorted(a['name'] for a in j.get('animations', [])), empties=sorted(o.name for o in bpy.context.scene.objects if o.type == 'EMPTY' and o.name.startswith('socket_'))),
                     images=len(imgs), all_images_embedded=embedded, barrel_length_mm=round(blen, 2), barrel_length_in=round(blen / 25.4, 3),
                     passed=bool(len(rm) == built['objects'] and embedded and abs(blen - 368.3) < 0.5 and len(j.get('animations', [])) == len(clips)))
json.dump(res, open(os.path.join(HERE, 'work', 'checks.json'), 'w'), indent=1)
print('INVENTORY', res['inventory']['coverage'], res['inventory']['passed'])
print('ASSEMBLY floating', len(floating), floating[:40]); print('  fasteners not seated', not_seated)
for c, v in anim.items(): print('ANIM', c, v['frames'], v['moving_parts'], v['worst_penetration'], 'PASS' if v['passed'] else 'FAIL')
print('EXPORT', res['export'])

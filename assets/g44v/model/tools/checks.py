"""blender -b work/g44v.blend --python tools/checks.py      -> work/../checks.json (committed) and a printed summary
1 INVENTORY  every item of the manual's component list (p. 36) is a named object
2 DIMENSIONS the build against the maker's specification table (the table manual p. 9 points to)
3 MASS       model volumes x nominal densities against the published weights (an inference check, not a fit)
4 CLIPS      interpenetration: every clip, every frame, every pair of parts that are not declared attached
"""
import bpy, json, os, sys, math, itertools
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clipeval
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inv = json.load(open(os.path.join(HERE, 'inventory.json'))); sc = bpy.context.scene
res = {}
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
acc = {o.name for o in meshes if o.parent and o.parent.name == 'accessories'}
# ---------------------------------------------------------------- 1 inventory
LIST = {'1': 'Slide', '2': 'Barrel', '3': 'Recoil spring assembly', '4': 'Firing pin', '5': 'Spacer sleeve', '6': 'Firing pin spring', '7': 'Spring cups', '8': 'Firing pin safety',
        '9': 'Firing pin safety spring', '10': 'Extractor', '11': 'Extractor depressor plunger', '12': 'Extractor depressor plunger spring', '13': 'Spring-loaded bearing',
        '14': 'Slide cover plate', '15': 'Rear sight', '16a': 'Front sight', '16b': 'Front sight screw', '17': 'Frame', '17c': 'Beavertail backstrap M', '17d': 'Beavertail backstrap L',
        '18': 'Magazine catch spring', '19': 'Magazine catch', '20': 'Slide lock spring', '21': 'Slide lock', '22': 'Locking block', '23': 'Trigger mechanism housing with ejector',
        '24': 'Connector', '26': 'Trigger with trigger bar', '27': 'Slide stop lever', '28': 'Trigger pin', '29': 'Trigger housing pin (short)', '31': 'Magazine tube', '32': 'Follower',
        '33': 'Magazine spring', '34': 'Magazine insert', '35': 'Magazine floor plate', '48': 'Loading assist right', '49': 'Loading assist left'}
have = {}
for q in inv['parts']:
    if q['part_no']: have.setdefault(q['part_no'], []).append(q['name'])
missing = [k for k in LIST if k not in have]
res['inventory'] = dict(manual_items=len(LIST), modelled=len(LIST) - len(missing), missing=missing, objects={k: have.get(k, []) for k in LIST},
                        open_meshes=[q['name'] for q in inv['parts'] if not q['closed']], note='items 25 and 30 are blank in the manual list')
print(f"INVENTORY {len(LIST) - len(missing)}/{len(LIST)} manual items modelled; missing {missing}; open meshes {res['inventory']['open_meshes']}")
# ---------------------------------------------------------------- 2 dimensions
def ext(names=None, excl=()):
    lo = [1e9] * 3; hi = [-1e9] * 3
    for o in meshes:
        if o.name in acc or (names and not any(o.name.startswith(n) for n in names)) or any(o.name.startswith(n) for n in excl): continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co; q = (-w.y * 1e3, w.x * 1e3, w.z * 1e3)
            for i in range(3): lo[i] = min(lo[i], q[i]); hi[i] = max(hi[i], q[i])
    return lo, hi
def sock(n): w = bpy.data.objects[n].matrix_world.translation; return (-w.y * 1e3, w.x * 1e3, w.z * 1e3)
lo, hi = ext(); slo, shi = ext(['p01_slide']); blo, bhi = ext(['p02_barrel'])
O = json.load(open(os.path.join(HERE, 'outlines.json')))['mm']; zt = sock('socket_trigger_finger')
import bisect
fr = O['frame']
def rear_at(z):          # rear-most L of the traced frame outline at height z
    xs = []
    for (l0, z0), (l1, z1) in zip(fr, fr[1:] + fr[:1]):
        if (z0 - z) * (z1 - z) <= 0 and z0 != z1: xs.append(l0 + (l1 - l0) * (z - z0) / (z1 - z0))
    return min(xs)
dims = [('1 length overall', hi[0] - lo[0], 185.0), ('2 slide length', shi[0] - slo[0], 174.0), ('3 width overall', hi[1] - lo[1], 32.0), ('4 slide width', shi[1] - slo[1], 25.5),
        ('5 height incl. magazine', hi[2] - lo[2], 128.0), ('6 line of sight (adjustable polymer)', sock('socket_front_sight')[0] - sock('socket_rear_sight')[0], 158.0),
        ('7 trigger distance', zt[0] - rear_at(zt[2]), 70.0), ('barrel length', bhi[0] - blo[0], 102.0)]
res['dimensions'] = []
for n, v, ref in dims:
    res['dimensions'].append(dict(dim=n, model_mm=round(v, 2), published_mm=ref, diff_mm=round(v - ref, 2), diff_pct=round(100 * (v - ref) / ref, 2)))
    print(f'DIMENSION {n:38s} model {v:7.2f}  published {ref:6.1f}  diff {v - ref:+6.2f} mm ({100 * (v - ref) / ref:+.1f} %)')
res['dimensions_note'] = 'published = the maker\'s specification table for this model (the table manual p. 9 points to; values in notes/MANUAL_NOTES.md). "Technical data are rounded and do not reflect tolerances" (maker\'s note).'
# ---------------------------------------------------------------- 3 mass budget
grp = dict(slide=0.0, barrel_and_spring=0.0, frame=0.0, magazine=0.0)
def top(o):
    while o.parent and o.parent.name not in ('frame_group', 'slide_group', 'magazine_group', 'accessories', 'g44v'): o = o.parent
    return o
for q in inv['parts']:
    o = bpy.data.objects[q['name']]
    if o.name in acc: continue
    t = top(o); g = 'slide' if t.parent.name == 'slide_group' else 'magazine' if t.parent.name == 'magazine_group' else 'barrel_and_spring' if t.name[:3] in ('p02', 'p03') else 'frame'
    grp[g] += q['mass_g']
raw = grp['slide'] + grp['barrel_and_spring'] + grp['frame']; k = 358.0 / raw
res['mass'] = dict(raw_model_g={a: round(b, 1) for a, b in grp.items()}, raw_without_magazine_g=round(raw, 1), published_without_magazine_g=358.0, published_empty_magazine_g=57.0,
                   scale_to_published=round(k, 3), normalised_g={a: round(b * k, 1) for a, b in grp.items() if a != 'magazine'},
                   note='volumes of the modelled solids x nominal densities (steel 7.85, glass-filled polymer 1.38, slide body 2.6 as a steel-reinforced polymer guess). Internal '
                        'cavities of the real parts are not known, so the raw total is not expected to match; the split between slide, barrel and frame after scaling to 358 g is what the action simulation uses.')
print('MASS raw', res['mass']['raw_model_g'], 'total w/o magazine', round(raw, 1), 'published 358; normalised', res['mass']['normalised_g'], '; magazine raw', round(grp['magazine'], 1), 'published 57')
# ---------------------------------------------------------------- 4 clip interpenetration
att = {frozenset((a, b)) for a, b, _ in inv['attached']}
def set_clip(name): pass
def trees():
    dg = bpy.context.evaluated_depsgraph_get(); out = {}
    for o in meshes:
        if o.name in acc: continue
        M = o.matrix_world; vs = [M @ v.co for v in o.data.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        out[o.name] = (vs, lo, hi, M.copy())
    return out
polys = {o.name: [tuple(f.vertices) for f in o.data.polygons] for o in meshes}
def inside(vs, tree):
    """is a sample of these vertices inside the closed solid of the tree?  (ray parity, three samples, two of three)"""
    n = 0
    for v in (vs[0], vs[len(vs) // 2], vs[-1]):
        cnt = 0; o = v.copy(); d = Vector((0.5377, 0.6132, 0.5786))
        for _ in range(64):
            h = tree.ray_cast(o, d)
            if h[0] is None: break
            cnt += 1; o = h[0] + d * 1e-6
        n += cnt % 2
    return n >= 2
def pairs(cur, moved=None):
    hits = []; names = sorted(cur); bv = {}
    for a, b in itertools.combinations(names, 2):
        if frozenset((a, b)) in att: continue
        if moved is not None and a not in moved and b not in moved: continue
        va, la, ha, _ = cur[a]; vb, lb, hb, _ = cur[b]
        if any(la[i] > hb[i] or lb[i] > ha[i] for i in range(3)): continue
        for n, v in ((a, va), (b, vb)):
            if n not in bv: bv[n] = BVHTree.FromPolygons(v, polys[n], epsilon=0.0)
        ov = bv[a].overlap(bv[b])
        if ov: hits.append((a, b, len(ov)))
        elif inside(va, bv[b]) or inside(vb, bv[a]): hits.append((a, b, -1))      # no surface crossing, but one part sits inside the other's solid
    return hits
clipeval.pose('', 1); rest = trees()
rh = pairs(rest)
res['clips'] = dict(rest_pose=dict(pairs_tested='all', intersecting=[dict(a=a, b=b, triangle_pairs=n) for a, b, n in rh]))
print(f'CLIPS rest pose: {len(rh)} intersecting pairs', rh[:40])
total = len(rh)
for clip, info in inv['clips'].items():
    fmax = clipeval.clip_len(clip)
    bad = {}
    for f in range(1, fmax + 1):
        clipeval.pose(clip, f); cur = trees()
        moved = {n for n in cur if any(abs(cur[n][3][i][j] - rest[n][3][i][j]) > 1e-9 for i in range(3) for j in range(4))}
        for a, b, n in pairs(cur, moved):
            e = bad.setdefault((a, b), dict(a=a, b=b, frames=[], max_triangle_pairs=0)); e['frames'].append(f); e['max_triangle_pairs'] = max(e['max_triangle_pairs'], n)
    for e in bad.values(): e['frames'] = [e['frames'][0], e['frames'][-1], len(e['frames'])]
    res['clips'][clip] = dict(frames=fmax, moving_nodes=info['nodes'], intersecting=list(bad.values()))
    total += len(bad)
    print(f'CLIPS {clip:16s} {fmax:3d} frames: {len(bad)} intersecting pairs', [(e['a'], e['b'], e['frames']) for e in bad.values()][:30])
res['clips']['method'] = 'triangle-triangle overlap (mathutils BVHTree.overlap) of the world-space meshes at every frame at 30 fps; plus a ray-parity test for one part lying wholly inside the solid of another (reported with triangle_pairs -1); pairs declared in inventory.json "attached" are skipped; accessories (detached backstraps) excluded'
res['clips']['total_intersecting_pairs'] = total
clipeval.pose('', 1)
json.dump(res, open(os.path.join(HERE, 'checks.json'), 'w'), indent=1)
print('CHECKS written; total intersecting pairs', total)

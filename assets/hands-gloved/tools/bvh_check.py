"""blender -b --python tools/bvh_check.py -- frames.npz out.json
Exact interpenetration measurement between posed glove shells and the locally built rifle's triangles (called by
checks/penetration.py; uses Blender only for mathutils' BVH tree).

For each frame and hand:
  1. every glove vertex is tested against every rifle part whose box contains it (inside = odd crossings on at least 4
     of 6 axis rays); its depth is the distance to that part's surface;
  2. the glove's and the rifle's triangles are intersected (BVH overlap); every triangle in an intersecting pair is
     sampled at about 0.6 mm and the samples are tested the same way, glove samples against the rifle part and rifle
     samples against the glove shell;
  3. rifle vertices inside a glove shell's box are tested against that shell.
The frame's penetration is the largest depth found.  Depth into overlapping rifle parts is taken per part (the largest
single-part depth), which is exact unless the point is inside two overlapping parts at once."""
import sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]; Z = np.load(argv[0]); meta = json.loads(str(Z['meta'])); RZ = np.load(meta['rifle_npz']); RM = json.load(open(meta['rifle_json']))
AX = [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
def tree(V, F): return BVHTree.FromPolygons([tuple(map(float, v)) for v in V], [tuple(map(int, f)) for f in F], epsilon=0.0)
def inside(t, p):
    odd = 0
    for d in AX:
        o = Vector(p); n = 0
        for _ in range(64):
            loc, nrm, idx, dist = t.ray_cast(o, d)
            if loc is None: break
            n += 1; o = loc + d * 1e-4
        odd += n & 1
    return odd >= 4
def depth(t, p):
    r = t.find_nearest(Vector(p)); return r[3] if r[0] is not None else 0.0
def tri_samples(a, b, c, h=0.6):
    n = int(max(1, np.ceil(max(np.linalg.norm(b - a), np.linalg.norm(c - a), np.linalg.norm(c - b)) / h))); out = []
    for i in range(n + 1):
        for j in range(n + 1 - i): out.append(a + (b - a) * (i / n) + (c - a) * (j / n))
    return out
# ---- rifle: per part trees (rest), grouped by mover
parts = {}
for n, p in RM['parts'].items():
    if p['hi'][2] < -330 or p['lo'][2] > 300: continue
    V = RZ['V_' + n].astype(float); F = RZ['T_' + n]; parts[n] = dict(V=V, F=F, t=tree(V, F), lo=V.min(0), hi=V.max(0), mover=p['mover'] or 'static')
groups = {}
for n, p in parts.items(): groups.setdefault(p['mover'], []).append(n)
gtree = {}
for g, names in groups.items():
    Vs, Fs, own, off = [], [], [], 0
    for n in names: Vs.append(parts[n]['V']); Fs.append(parts[n]['F'] + off); own += [n] * len(parts[n]['F']); off += len(parts[n]['V'])
    V = np.vstack(Vs); F = np.vstack(Fs); gtree[g] = dict(t=tree(V, F), V=V, F=F, own=own, lo=V.min(0), hi=V.max(0))
shell_names = meta['shells']; res = []
for fi, fr in enumerate(meta['frames']):
    motion = {k: np.array(v) for k, v in fr.get('motion', {}).items()}; skip = set(fr.get('skip', ()))
    best = dict(depth=0.0)
    V = Z[f'V_{fi}'].astype(float); sid = Z['S']; Fh = Z['F']
    for g, G in gtree.items():
        if g in skip: continue
        M = motion.get(g); Vg = V if M is None else (V - M[:3, 3]) @ M[:3, :3]          # glove in the mover's rest frame
        if np.any(Vg.max(0) < G['lo'] - 0.5) or np.any(Vg.min(0) > G['hi'] + 0.5): continue
        def test_pt(p, shell):
            for n in groups[g]:
                P_ = parts[n]
                if np.all(p >= P_['lo']) and np.all(p <= P_['hi']) and inside(P_['t'], p):
                    d = depth(P_['t'], p)
                    if d > best['depth']: best.update(depth=float(d), part=n, shell=shell, kind='glove point in rifle part', at=[round(float(x), 1) for x in p])
        # 1. glove vertices
        cand = np.where(np.all(Vg >= G['lo'], 1) & np.all(Vg <= G['hi'], 1))[0]
        for i in cand: test_pt(Vg[i], shell_names[sid[i]])
        # 2. intersecting triangle pairs, per shell
        for s, sn in enumerate(shell_names):
            fm = np.where(sid[Fh[:, 0]] == s)[0]; vi = np.where(sid == s)[0]
            if not len(vi): continue
            lo, hi = Vg[vi].min(0), Vg[vi].max(0)
            if np.any(hi < G['lo']) or np.any(lo > G['hi']): continue
            Fs = Fh[fm] - vi[0]; ts = tree(Vg[vi], Fs); pairs = ts.overlap(G['t'])
            if pairs:
                for a in {a for a, b in pairs}:
                    for p in tri_samples(*Vg[vi][Fs[a]]): test_pt(p, sn)
                for b in {b for a, b in pairs}:
                    for p in tri_samples(*G['V'][G['F'][b]]):
                        if inside(ts, p):
                            d = depth(ts, p)
                            if d > best['depth']: best.update(depth=float(d), part=G['own'][b], shell=sn, kind='rifle point in glove shell', at=[round(float(x), 1) for x in p])
            # 3. rifle vertices inside the shell's box
            rc = np.where(np.all(G['V'] >= lo, 1) & np.all(G['V'] <= hi, 1))[0]
            for i in rc[:: max(1, len(rc) // 4000)]:
                if inside(ts, G['V'][i]):
                    d = depth(ts, G['V'][i])
                    if d > best['depth']: best.update(depth=float(d), part='(vertex of group %s)' % g, shell=sn, kind='rifle vertex in glove shell', at=[round(float(x), 1) for x in G['V'][i]])
    best['id'] = fr['id']; best['depth'] = round(best['depth'], 3); res.append(best)
    print('BVH', fr['id'], best['depth'], best.get('part', ''), best.get('shell', ''), flush=True)
json.dump(res, open(argv[1], 'w'), indent=1)

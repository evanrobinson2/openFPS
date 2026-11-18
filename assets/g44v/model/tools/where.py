"""blender -b ../../../build/g44v/g44v.blend --python tools/where.py -- <clip> <frame> <part a> <part b> : where two parts intersect (model mm), for debugging a clip."""
import bpy, sys, os
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import clipeval
clip, frame, a, b = sys.argv[sys.argv.index('--') + 1:]
clipeval.pose(clip, float(frame))
def tree(n):
    o = bpy.data.objects[n]; vs = [o.matrix_world @ v.co for v in o.data.vertices]; ps = [tuple(f.vertices) for f in o.data.polygons]
    return BVHTree.FromPolygons(vs, ps, epsilon=0.0), vs, ps
ta, va, pa = tree(a); tb, vb, pb = tree(b); ov = ta.overlap(tb); pts = []
for i, j in ov:
    for vs, ps, k in ((va, pa, i), (vb, pb, j)):
        c = sum((vs[q] for q in ps[k]), vs[0] * 0) / len(ps[k]); pts.append((-c.y * 1e3, c.x * 1e3, c.z * 1e3))
if pts:
    for ax, nm in enumerate('LSZ'): print('WHERE', nm, round(min(q[ax] for q in pts), 2), round(max(q[ax] for q in pts), 2))
print('WHERE pairs', len(ov))

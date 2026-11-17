"""blender -b work/hk416_lod0.blend --python tools/dump_tris.py : world triangles of every mesh as (L, S, Z) mm -> work/tris.npz"""
import bpy, numpy as np, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tris, owner, names = [], [], []
for o in bpy.context.scene.objects:
    if o.type != 'MESH': continue
    me = o.data; me.calc_loop_triangles(); M = o.matrix_world
    co = np.array([(M @ v.co)[:] for v in me.vertices])
    t = np.array([lt.vertices[:] for lt in me.loop_triangles])
    w = co[t]                                           # (n, 3, 3) Blender world X, Y, Z in metres
    tris.append(np.stack([-w[..., 1], w[..., 0], w[..., 2]], -1) * 1000.0)
    owner += [len(names)] * len(t); names.append(o.name)
np.savez(os.path.join(HERE, 'work', 'tris.npz'), tris=np.concatenate(tris), owner=np.array(owner), names=np.array(names))
print('dumped', sum(len(t) for t in tris), 'triangles from', len(names), 'parts')

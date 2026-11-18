"""blender -b refs-local/build/hk416/work/hk416_lod0.blend --python tools/extract_rifle.py
Dump the locally built HK416 (never committed) for the grip solver and the checks:
  refs-local/build/rifle.npz   triangles per part (rest pose, mm, asset frame) and, per clip frame, the 4x4 motion of each moving part
  refs-local/build/rifle.json  part -> mover, sockets, clip lengths
Asset frame (assets/hk416/USAGE.md): +X shooter's left, +Y up, +Z to the muzzle.  Blender frame of the recipe: X left, Y = -muzzle, Z up."""
import bpy, json, os, numpy as np
from mathutils import Matrix
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(HERE, 'refs-local', 'build')
C = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])            # blender -> asset axes
S = np.diag([1000.0, 1000.0, 1000.0, 1.0])
def conv(M): return (S @ C) @ np.array(M) @ np.linalg.inv(S @ C)                     # 4x4 in asset frame, mm
sc = bpy.context.scene; clips = json.loads(sc['hk416_clips']); groups = json.loads(sc['hk416_groups'])
movers = sorted({n for c in clips.values() for n in c})
def mover_of(o):
    while o is not None:
        if o.name in movers: return o.name
        o = o.parent
    return ''
arr = {}; meta = dict(parts={}, sockets={}, clips={}, fps=sc.render.fps, movers=movers)
dg = bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type == 'MESH':
        me = o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
        V = np.array([o.matrix_world @ v.co for v in me.vertices]); V = (np.c_[V, np.ones(len(V))] @ (S @ C).T)[:, :3]
        T = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int32)
        arr['V_' + o.name] = V.astype(np.float32); arr['T_' + o.name] = T
        meta['parts'][o.name] = dict(mover=mover_of(o), group=groups.get(o.name, ''), lo=V.min(0).round(2).tolist(), hi=V.max(0).round(2).tolist(), tris=len(T))
    elif o.type == 'EMPTY' and o.name.startswith('socket'):
        meta['sockets'][o.name] = [round(float(x), 3) for x in (conv(o.matrix_world)[:3, 3])]
rest = {n: np.array(bpy.data.objects[n].matrix_world) for n in movers}
for clip, objs in clips.items():
    acts = {n: bpy.data.actions[a] for n, a in objs.items()}
    f1 = int(max(a.frame_range[1] for a in acts.values()))
    for n, a in acts.items():
        ad = bpy.data.objects[n].animation_data; ad.action = a
        if hasattr(ad, 'action_slot') and len(getattr(a, 'slots', [])): ad.action_slot = a.slots[0]
    D = np.zeros((f1, len(movers), 4, 4))
    for f in range(1, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        for j, n in enumerate(movers):
            D[f - 1, j] = conv(np.array(bpy.data.objects[n].matrix_world) @ np.linalg.inv(rest[n])) if n in acts else np.eye(4)
    arr['clip_' + clip] = D; meta['clips'][clip] = dict(frames=f1, movers=sorted(acts))
    for n in acts:
        ad = bpy.data.objects[n].animation_data; ad.action = None
    sc.frame_set(1)
np.savez_compressed(os.path.join(OUT, 'rifle.npz'), **arr); json.dump(meta, open(os.path.join(OUT, 'rifle.json'), 'w'), indent=1)
print('EXTRACTED', len(meta['parts']), 'parts', meta['sockets'], {c: v['frames'] for c, v in meta['clips'].items()})

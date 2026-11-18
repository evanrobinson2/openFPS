"""Build render scenes (numpy) and call Blender.  Used by the comparison renders and the checks.  Asset frame, mm."""
import os, sys, json, subprocess, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl, glove
BUILD = os.path.join(HERE, 'refs-local', 'build'); BLENDER = '/opt/homebrew/bin/blender'
_hand = None
def hand():
    global _hand
    if _hand is None: _hand = hl.Hand(); _hand.mats = {n: glove.face_materials(s) for n, s in _hand.shells.items()}; _hand.details = glove.detail_parts(_hand)
    return _hand
def hand_meshes(side, q, H, F=None, prefix=''):
    """Posed meshes of one hand in the asset frame.  side 'L' or 'R'; q, H, F are in the canonical-left world (mirrored for R)."""
    h = hand(); Wd = h.fk(q, H, F); S = h.skin_mats(Wd); out = []
    for n, sh in h.shells.items():
        V = h.pose_shell(n, S); Fc = sh['F']
        if side == 'R': V = V * [-1, 1, 1]; Fc = Fc[:, ::-1]
        out.append(dict(name=f'{prefix}{side}_{n}', V=V, F=Fc, mats=glove.MATERIALS, M=h.mats[n]))
    for n, d in h.details.items():
        Sb = S[hl.BI[d['bone']]]; V = d['V'] @ Sb[:3, :3].T + Sb[:3, 3]; Fc = d['F']
        if side == 'R': V = V * [-1, 1, 1]; Fc = Fc[:, ::-1]
        out.append(dict(name=f'{prefix}{side}_{n}', V=V, F=Fc, mat=d['mat'], smooth=False))
    return out
def rifle_meshes(clip=None, frame=1, hide=()):
    z = np.load(os.path.join(BUILD, 'rifle.npz')); meta = json.load(open(os.path.join(BUILD, 'rifle.json'))); out = []
    D = z['clip_' + clip][frame - 1] if clip else None
    for n, p in meta['parts'].items():
        if any(n.startswith(hh) for hh in hide): continue
        V = z['V_' + n].astype(float)
        if D is not None and p['mover']: M = D[meta['movers'].index(p['mover'])]; V = V @ M[:3, :3].T + M[:3, 3]
        out.append(dict(name=n, V=V, F=z['T_' + n], mat='rifle_polymer' if p['group'] in ('grip', 'magazine', 'stock') else 'rifle', smooth=False))
    return out
def render(meshes, camera, out, size=(1280, 853), samples=24, **kw):
    arr = {}; mm = []
    for i, m in enumerate(meshes):
        arr[f'V_{i}'] = np.asarray(m['V'], np.float32); arr[f'F_{i}'] = np.asarray(m['F'], np.int32); e = {k: v for k, v in m.items() if k not in ('V', 'F', 'M')}
        if 'M' in m: arr[f'M_{i}'] = np.asarray(m['M'], np.int32)
        mm.append(e)
    arr['meta'] = json.dumps(dict(meshes=mm, camera=camera, size=list(size), samples=samples, **kw))
    tmp = os.path.join(BUILD, 'scene_tmp_%d.npz' % os.getpid()); np.savez(tmp, **arr)
    r = subprocess.run([BLENDER, '-b', '--python', os.path.join(HERE, 'tools', 'render.py'), '--', tmp, out], capture_output=True, text=True)
    os.remove(tmp)
    if 'RENDERED' not in r.stdout: print(r.stdout[-3000:], r.stderr[-2000:])
    return out
if __name__ == '__main__':
    # flat hand study views
    h = hand(); q = np.zeros(len(hl.ANGLES)); ms = hand_meshes('L', q, np.eye(4))
    os.makedirs(os.path.join(BUILD, 'r'), exist_ok=True)
    render(ms, dict(eye=[0, 60, 520], target=[-5, 40, 0], up=[0, 1, 0], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_dorsal.jpg'), size=(900, 1000))
    render(ms, dict(eye=[0, 60, -520], target=[-5, 40, 0], up=[0, 1, 0], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_palmar.jpg'), size=(900, 1000))
    render(ms, dict(eye=[520, 60, 0], target=[-5, 40, 0], up=[0, 0, 1], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_radial.jpg'), size=(1000, 500))

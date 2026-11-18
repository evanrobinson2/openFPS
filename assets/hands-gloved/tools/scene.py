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
        Sb = np.asarray(S)[hl.BI[d['bone']]]; V0 = d['V'] + (S.pads @ d['pad_shift'] if 'pad_shift' in d and getattr(S, 'pads', None) is not None else 0.0); V = V0 @ Sb[:3, :3].T + Sb[:3, 3]; Fc = d['F']
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
def hidden_by_sleeve(meshes, camera):
    """CR-2 (sleeve fix).  Share of each hand's glove (vertices of its fingers, thumb, palm and web) whose line of sight to
    the camera is cut by a forearm sleeve, either hand's.  camera: eye/target with ortho_mm (parallel rays) or fov_deg."""
    sl = [m for m in meshes if m['name'].endswith('_sleeve')]; T = np.concatenate([np.asarray(m['V'], float)[np.asarray(m['F'])] for m in sl]); A, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    eye = np.array(camera['eye'], float); tgt = np.array(camera['target'], float); out = {}
    for hand_ in sorted({m['name'].rsplit('_', 1)[0] for m in sl}):
        P = np.concatenate([np.asarray(m['V'], float) for m in meshes if m['name'].startswith(hand_ + '_') and m['name'][len(hand_) + 1:].split('_')[0] in ('finger', 'thumb', 'palm', 'web')])
        D = np.tile((eye - tgt) / np.linalg.norm(eye - tgt), (len(P), 1)) if 'ortho_mm' in camera else (eye - P) / np.linalg.norm(eye - P, axis=1)[:, None]
        tmax = np.full(len(P), 1e9) if 'ortho_mm' in camera else np.linalg.norm(eye - P, axis=1); hit = np.zeros(len(P), bool)
        for i in range(0, len(P), 400):          # Moller-Trumbore, in blocks
            o = P[i:i + 400, None, :]; d = D[i:i + 400, None, :]; pv = np.cross(d, e2[None]); det = (e1[None] * pv).sum(-1); ok = np.abs(det) > 1e-9; inv = 1.0 / np.where(ok, det, 1.0)
            tv = o - A[None]; u = (tv * pv).sum(-1) * inv; qv = np.cross(tv, e1[None]); v = (d * qv).sum(-1) * inv; t = (e2[None] * qv).sum(-1) * inv
            hit[i:i + 400] = (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.5) & (t < tmax[i:i + 400, None])).any(1)
        out[hand_] = round(float(hit.mean()), 3)
    return out
if __name__ == '__main__':
    # flat hand study views
    h = hand(); q = np.zeros(len(hl.ANGLES)); ms = hand_meshes('L', q, np.eye(4))
    os.makedirs(os.path.join(BUILD, 'r'), exist_ok=True)
    render(ms, dict(eye=[0, 60, 520], target=[-5, 40, 0], up=[0, 1, 0], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_dorsal.jpg'), size=(900, 1000))
    render(ms, dict(eye=[0, 60, -520], target=[-5, 40, 0], up=[0, 1, 0], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_palmar.jpg'), size=(900, 1000))
    render(ms, dict(eye=[520, 60, 0], target=[-5, 40, 0], up=[0, 0, 1], ortho_mm=330), os.path.join(BUILD, 'r', 'flat_radial.jpg'), size=(1000, 500))

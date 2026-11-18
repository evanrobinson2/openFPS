"""Measure interpenetration of the gloves with the rifle in every frame of every clip.  Writes checks/penetration.json.

    python3 checks/penetration.py            # needs the local rifle build and Blender (for its BVH tree only)

Every frame of every hand clip is posed (linear-blend skinning of the glove shells, the same as the runtime), the
rifle's moving parts are put where the rifle clip has them, and tools/bvh_check.py measures the deepest point of
either surface inside the other against the exact triangles.  Tolerance: TOL mm (see README.md)."""
import os, sys, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl
BUILD = os.path.join(HERE, 'refs-local', 'build'); TOL = 1.0
h = hl.Hand(); SH = [n for n in h.shells if n != 'sleeve']          # the sleeve is cloth, not part of the glove
E = dict(np.load(os.path.join(BUILD, 'frames.npz'), allow_pickle=True)['E'].item()); meta = json.loads(str(np.load(os.path.join(BUILD, 'frames.npz'), allow_pickle=True)['meta']))
z = np.load(os.path.join(BUILD, 'rifle.npz')); rm = json.load(open(os.path.join(BUILD, 'rifle.json')))
def posed(side, fr):
    q, H, F = fr['q'], fr['H'], fr['F']
    if side == 'R': H, F = hl.mirror_mats(H), hl.mirror_mats(F)
    S = h.skin_mats(h.fk(q, H, F)); V = np.vstack([h.pose_shell(n, S) for n in SH])
    return V * [-1, 1, 1] if side == 'R' else V
Fs, Sid, off = [], [], 0
for i, n in enumerate(SH): Fs.append(h.shells[n]['F'] + off); Sid += [i] * len(h.shells[n]['V']); off += len(h.shells[n]['V'])
arr = dict(F=np.vstack(Fs).astype(np.int32), S=np.array(Sid, np.int32)); frames = []; seen = {}
only = sys.argv[1:]
for clip, fl in E.items():
    if only and clip not in only: continue
    m = meta[clip]
    for f, fr in enumerate(fl):
        mot = {}
        if m['rifle']:
            D = z['clip_' + m['rifle']][int(fr['rifle_frame']) - 1]; mot = {mv: D[rm['movers'].index(mv)].tolist() for mv in rm['clips'][m['rifle']]['movers']}
        for s in 'RL':
            key = (s, fr[s]['q'].round(3).tobytes(), fr[s]['H'].round(4).tobytes(), json.dumps(mot))
            if key in seen: frames.append(dict(id=f'{clip}:{f + 1}:{s}', same_as=seen[key])); continue
            seen[key] = f'{clip}:{f + 1}:{s}'; arr[f'V_{len([x for x in frames if "same_as" not in x])}'] = posed(s, fr[s]).astype(np.float32)
            frames.append(dict(id=f'{clip}:{f + 1}:{s}', motion=mot))
uniq = [x for x in frames if 'same_as' not in x]
arr['meta'] = json.dumps(dict(frames=uniq, shells=SH, rifle_npz=os.path.join(BUILD, 'rifle.npz'), rifle_json=os.path.join(BUILD, 'rifle.json')))
tmp = os.path.join(BUILD, 'pen_frames.npz'); np.savez(tmp, **arr); out = os.path.join(BUILD, 'pen_out.json')
r = subprocess.run(['/opt/homebrew/bin/blender', '-b', '--python', os.path.join(HERE, 'tools', 'bvh_check.py'), '--', tmp, out], capture_output=True, text=True)
if not os.path.exists(out) or 'Traceback' in r.stderr: print(r.stdout[-2000:], r.stderr[-3000:]); sys.exit(1)
res = {x['id']: x for x in json.load(open(out))}; os.remove(tmp)
for x in frames:
    if 'same_as' in x: res[x['id']] = dict(res[x['same_as']], id=x['id'])
clips = {}
for clip in E:
    if only and clip not in only: continue
    rows = [res[f'{clip}:{f + 1}:{s}'] for f in range(len(E[clip])) for s in 'RL']; w = max(rows, key=lambda x: x['depth'])
    clips[clip] = dict(frames=len(E[clip]), max_depth_mm=w['depth'], worst=dict(frame=int(w['id'].split(':')[1]), hand=w['id'].split(':')[2], rifle_part=w.get('part'), glove_part=w.get('shell'), kind=w.get('kind')),
                       frames_over_tolerance=sorted({int(x['id'].split(':')[1]) for x in rows if x['depth'] > TOL}), per_frame_max_mm=[max(res[f'{clip}:{f + 1}:{s}']['depth'] for s in 'RL') for f in range(len(E[clip]))])
    print(f"{clip:20s} max {w['depth']:6.3f} mm  frame {clips[clip]['worst']['frame']:3d} {clips[clip]['worst']['hand']}  {w.get('part', '')} / {w.get('shell', '')}  over tolerance: {clips[clip]['frames_over_tolerance']}")
if not only:
    json.dump(dict(asset='hands-gloved', tolerance_mm=TOL, method='exact triangle test, see tools/bvh_check.py', unique_poses_measured=len(uniq), frames_measured=len(frames),
                   max_depth_mm=max(c['max_depth_mm'] for c in clips.values()), all_within_tolerance=all(not c['frames_over_tolerance'] for c in clips.values()), clips=clips),
              open(os.path.join(HERE, 'checks', 'penetration.json'), 'w'), indent=1)

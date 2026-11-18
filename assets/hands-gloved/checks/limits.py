"""Check every joint angle in every frame of every clip against the joint limits.  Writes checks/limits.json and
checks/fk_reference.json (fingertip positions per frame, for the JS parity test).

    python3 checks/limits.py

The 23 hand angles are read from the clips; the four arm angles (wrist flexion, wrist deviation, forearm pronation,
elbow flexion) are measured from the hand and forearm matrices and the assumed shoulder (grips/solve.py SHOULDER)."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model'))
import handlib as hl
z = np.load(os.path.join(HERE, 'refs-local', 'build', 'frames.npz'), allow_pickle=True); E = dict(z['E'].item()); h = hl.Hand()
ARM = ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'); TIPS = ('thumb_tip', 'index_tip', 'middle_tip', 'ring_tip', 'little_tip')
obs = {a: [1e9, -1e9] for a in hl.ANGLES + list(ARM)}; clips = {}; ref = {}; nbad = 0; nvals = 0
for clip, fl in E.items():
    worst = (1e9, None); ref[clip] = dict(R=[], L=[])
    for f, fr in enumerate(fl):
        for s in 'RL':
            q = fr[s]['q']; vals = dict(zip(hl.ANGLES, q)); vals.update({k: fr[s]['arm'][k] for k in ARM})
            for a, v in vals.items():
                lo, hi = hl.limit_of(a) if a in hl.ANGLES else hl.LIMITS[a][:2]; m = min(v - lo, hi - v); nvals += 1; nbad += m < -1e-6
                obs[a][0] = min(obs[a][0], float(v)); obs[a][1] = max(obs[a][1], float(v))
                if m < worst[0]: worst = (float(m), dict(frame=f + 1, hand=s, joint=a, value=round(float(v), 2), min=lo, max=hi))
            H, F = fr[s]['H'], fr[s]['F']
            if s == 'R': H, F = hl.mirror_mats(H), hl.mirror_mats(F)
            L = h.pose_landmarks(h.skin_mats(h.fk(q, H, F)))
            ref[clip][s].append([[round(float(x) * (-1 if (s == 'R' and i == 0) else 1) / 1000.0, 6) for i, x in enumerate(L[t])] for t in TIPS])
    clips[clip] = dict(frames=len(fl), smallest_margin_deg=round(worst[0], 2), at=worst[1], pass_=bool(worst[0] >= -1e-6))
joints = {a: dict(min_seen=round(v[0], 2), max_seen=round(v[1], 2), limit_min=(hl.limit_of(a) if a in hl.ANGLES else hl.LIMITS[a][:2])[0], limit_max=(hl.limit_of(a) if a in hl.ANGLES else hl.LIMITS[a][:2])[1],
                  source=hl.LIMITS[a if a in hl.LIMITS else a.split('_', 1)[1]][2]) for a, v in obs.items()}
out = dict(asset='hands-gloved', values_checked=int(nvals), outside_limits=int(nbad), all_within_limits=bool(nbad == 0), sources={k: hl.SRC[k] for k in ('BA', 'HU', 'CO', 'AA', 'K', 'I')},
           note='Arm angles depend on the assumed shoulder position (an inference) and on the elbow swivel chosen per frame.', clips=clips, joints=joints)
json.dump(out, open(os.path.join(HERE, 'checks', 'limits.json'), 'w'), indent=1)
json.dump(dict(tips=list(TIPS), units='metres, rifle frame', clips=ref), open(os.path.join(HERE, 'checks', 'fk_reference.json'), 'w'), separators=(',', ':'))
for c, v in clips.items(): print(f"{c:20s} {v['frames']:3d} frames  smallest margin {v['smallest_margin_deg']:6.2f} deg  at {v['at']['joint']} ({v['at']['hand']}, frame {v['at']['frame']}) = {v['at']['value']}")
print('values checked', nvals, 'outside limits', nbad)

"""Measure interpenetration of the gloves with the rifle in every frame of every clip.  Writes checks/penetration.json.

    python3 checks/penetration.py            # needs the local rifle build and Blender (for its BVH tree only)

Every frame of every hand clip is posed (linear-blend skinning of the glove shells, the same as the runtime), the
rifle's moving parts are put where the rifle clip has them, and tools/bvh_check.py measures the deepest point of
either surface inside the other against the exact triangles.  Tolerance: TOL mm (see README.md).

CR-2, soft pads.  The glove is measured as the pose has it, that is with each palm pad pressed in by the amount the
frame carries (handlib 'pad_*', mm).  That measurement is the interpenetration, and its tolerance is the same 1.0 mm
everywhere, pads included.  Compression is reported apart from it, per pad and per clip, three ways:
  commanded   the compression the frame carries at the pad's middle, against the pad's limit (handlib.LIMITS);
  overlap     how deep the pad's vertices would be inside the rifle with no compression at all (measured the same way,
              on the uncompressed glove): this is what the compression has to take up;
  beyond      overlap of a pad's vertices beyond what the limit could take up there (the limit times the vertex's share
              of the pad).  Anything above the tolerance here would be interpenetration that no allowed compression explains."""
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
    S = h.skin_mats(h.fk(q, H, F)); V = np.vstack([h.pose_shell(n, S) for n in SH]); U = np.vstack([h.pose_shell(n, S, pads=None) for n in SH])
    return (V * [-1, 1, 1], U * [-1, 1, 1]) if side == 'R' else (V, U)
PADW = np.concatenate([np.linalg.norm(h.shells[n]['D'], axis=2) for n in SH], axis=1)          # (pads, vertices): each vertex's share of each pad
PLIM = np.array([hl.limit_of('pad_' + k)[1] for k in hl.PADS])
Fs, Sid, off = [], [], 0
for i, n in enumerate(SH): Fs.append(h.shells[n]['F'] + off); Sid += [i] * len(h.shells[n]['V']); off += len(h.shells[n]['V'])
arr = dict(F=np.vstack(Fs).astype(np.int32), S=np.array(Sid, np.int32), PADW=PADW.astype(np.float32), PLIM=PLIM); frames = []; seen = {}
only = sys.argv[1:]; uidx = {}; pose_of = {}
for clip, fl in E.items():
    if only and clip not in only: continue
    m = meta[clip]
    for f, fr in enumerate(fl):
        mot = {}
        if m['rifle']:
            D = z['clip_' + m['rifle']][int(fr['rifle_frame']) - 1]; mot = {mv: D[rm['movers'].index(mv)].tolist() for mv in rm['clips'][m['rifle']]['movers']}
        for s in 'RL':
            key = (s, fr[s]['q'].round(3).tobytes(), fr[s]['H'].round(4).tobytes(), json.dumps(mot))
            if key in seen: frames.append(dict(id=f'{clip}:{f + 1}:{s}', same_as=seen[key])); pose_of[(clip, f, s)] = seen[key]; continue
            pose_of[(clip, f, s)] = f'{clip}:{f + 1}:{s}'
            seen[key] = f'{clip}:{f + 1}:{s}'; k_ = len([x for x in frames if "same_as" not in x]); V_, U_ = posed(s, fr[s]); arr[f'V_{k_}'] = V_.astype(np.float32); uidx[seen[key]] = k_
            if np.any(fr[s]['q'][hl.PAD_IDX] > 0): arr[f'U_{k_}'] = U_.astype(np.float32)
            frames.append(dict(id=f'{clip}:{f + 1}:{s}', motion=mot))
uniq = [x for x in frames if 'same_as' not in x]
# CR-2: hand against hand.  Every frame in which the two gloves' boxes come within 2 mm of each other is measured the same way
# (vertices of each glove inside the other's closed shells, and the reverse); the same pair of poses is measured once.
pairs = {}; pair_of = {}
for (clip, f, s), pid in pose_of.items():
    if s != 'R': continue
    a, b = uidx[pid], uidx[pose_of[(clip, f, 'L')]]; Va, Vb = arr[f'V_{a}'], arr[f'V_{b}']
    if np.all(Va.min(0) - 2.0 <= Vb.max(0)) and np.all(Vb.min(0) - 2.0 <= Va.max(0)): pairs.setdefault((a, b), len(pairs)); pair_of[(clip, f)] = pairs[(a, b)]
arr['meta'] = json.dumps(dict(frames=uniq, shells=SH, pairs=[list(k) for k in pairs], rifle_npz=os.path.join(BUILD, 'rifle.npz'), rifle_json=os.path.join(BUILD, 'rifle.json')))
tmp = os.path.join(BUILD, 'pen_frames.npz'); np.savez(tmp, **arr); out = os.path.join(BUILD, 'pen_out.json')
r = subprocess.run(['/opt/homebrew/bin/blender', '-b', '--python', os.path.join(HERE, 'tools', 'bvh_check.py'), '--', tmp, out], capture_output=True, text=True)
if not os.path.exists(out) or 'Traceback' in r.stderr: print(r.stdout[-2000:], r.stderr[-3000:]); sys.exit(1)
allres = json.load(open(out)); hh = sorted([x for x in allres if 'pair' in x], key=lambda x: x['pair']); res = {x['id']: x for x in allres if 'pair' not in x}; os.remove(tmp)
for x in frames:
    if 'same_as' in x: res[x['id']] = dict(res[x['same_as']], id=x['id'])
clips = {}
for clip in E:
    if only and clip not in only: continue
    rows = [res[f'{clip}:{f + 1}:{s}'] for f in range(len(E[clip])) for s in 'RL']; w = max(rows, key=lambda x: x['depth'])
    clips[clip] = dict(frames=len(E[clip]), max_depth_mm=w['depth'], worst=dict(frame=int(w['id'].split(':')[1]), hand=w['id'].split(':')[2], rifle_part=w.get('part'), glove_part=w.get('shell'), kind=w.get('kind')),
                       frames_over_tolerance=sorted({int(x['id'].split(':')[1]) for x in rows if x['depth'] > TOL}), per_frame_max_mm=[max(res[f'{clip}:{f + 1}:{s}']['depth'] for s in 'RL') for f in range(len(E[clip]))],
                       pads={k: dict(limit_mm=float(PLIM[i]), commanded_max_mm=round(float(max(fr[s]['q'][hl.PAD_IDX[i]] for fr in E[clip] for s in 'RL')), 2),
                                     overlap_uncompressed_max_mm=round(max(x.get('pad_overlap', [0] * 4)[i] for x in rows), 3), beyond_limit_max_mm=round(max(x.get('pad_beyond', [0] * 4)[i] for x in rows), 3)) for i, k in enumerate(hl.PADS)})
    print(f"{clip:20s} max {w['depth']:6.3f} mm  frame {clips[clip]['worst']['frame']:3d} {clips[clip]['worst']['hand']}  {w.get('part', '')} / {w.get('shell', '')}  over tolerance: {clips[clip]['frames_over_tolerance']}")
if not only:
    pads = {k: dict(limit_mm=float(PLIM[i]), tissue_mm=h.pad_info[k]['tissue_mm'], how=h.pad_info[k]['how'], commanded_max_mm=max(c['pads'][k]['commanded_max_mm'] for c in clips.values()),
                    strain_at_commanded_max=round((max(c['pads'][k]['commanded_max_mm'] for c in clips.values()) - min(hl.P['glove_give'], max(c['pads'][k]['commanded_max_mm'] for c in clips.values()))) / h.pad_info[k]['tissue_mm'], 3),
                    overlap_uncompressed_max_mm=max(c['pads'][k]['overlap_uncompressed_max_mm'] for c in clips.values()), beyond_limit_max_mm=max(c['pads'][k]['beyond_limit_max_mm'] for c in clips.values()),
                    within_limit=bool(max(c['pads'][k]['commanded_max_mm'] for c in clips.values()) <= PLIM[i] + 1e-6 and max(c['pads'][k]['beyond_limit_max_mm'] for c in clips.values()) <= TOL)) for i, k in enumerate(hl.PADS)}
    json.dump(dict(asset='hands-gloved', tolerance_mm=TOL, method='exact triangle test, see tools/bvh_check.py; the glove is measured with its pads compressed as each frame says, and compression is reported apart (see this script\'s docstring)',
                   unique_poses_measured=len(uniq), frames_measured=len(frames),
                   max_depth_mm=max(c['max_depth_mm'] for c in clips.values()), all_within_tolerance=all(not c['frames_over_tolerance'] for c in clips.values()),
                   hand_against_hand=dict(note='CR-2 goal 7. Frames in which the two gloves\' boxes come within 2 mm are measured: the deepest vertex of either glove inside a closed shell of the other. Same tolerance. The gloves are not checked against themselves (a finger against its own palm).',
                                          frames_with_hands_near=len(pair_of), pose_pairs_measured=len(pairs), max_depth_mm=max([x['depth'] for x in hh] or [0.0]),
                                          worst=(lambda w_: dict(clip_frame=next('%s:%d' % (c_, f_ + 1) for (c_, f_), i_ in pair_of.items() if i_ == w_['pair']), shell_entered=w_.get('shell'), by=w_.get('by')) if w_ else None)(max(hh, key=lambda x: x['depth']) if hh else None),
                                          frames_over_tolerance=sorted('%s:%d' % (c_, f_ + 1) for (c_, f_), i_ in pair_of.items() if hh[i_]['depth'] > TOL) if hh else [],
                                          max_depth_by_clip_mm={c_: max(hh[i_]['depth'] for (c2, f_), i_ in pair_of.items() if c2 == c_) for c_ in sorted({k_[0] for k_ in pair_of})} if hh else {},
                                          all_within_tolerance=all(x['depth'] <= TOL for x in hh)),
                   soft_pads=dict(note='Compression, reported apart from interpenetration. commanded: what the frames carry at each pad\'s middle. overlap_uncompressed: how deep the pad would sit in the rifle with no compression. beyond_limit: overlap that the pad\'s limit could not take up (must stay within the tolerance). strain: commanded compression less the glove\'s give, over the tissue thickness.',
                                  strain_limit=hl.P['strain_limit'], glove_give_mm=hl.P['glove_give'], pads=pads, all_within_limits=all(v['within_limit'] for v in pads.values())), clips=clips),
              open(os.path.join(HERE, 'checks', 'penetration.json'), 'w'), indent=1)

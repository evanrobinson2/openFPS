"""Does the digit touch the control?  Writes checks/contact.json.

    python3 checks/contact.py        # needs the frames from clips/make.py and the local rifle build

For every frame of the clips in which a digit works a control, the gap is the smallest distance from the vertices of
that digit's glove shell to the exact triangles of the control (moved by the rifle clip).  A gap of at most 1.0 mm
counts as contact (CR-1 item 4); the solver keeps 0.5 mm clear, so a touching digit reads about 0.5.  This says where
the glove is, not how hard it presses.  Interpenetration is measured separately (checks/penetration.py)."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ('model', 'grips'): sys.path.insert(0, os.path.join(HERE, d))
import handlib as hl
from rifle import Rifle, tri_dist
R = Rifle(); h = hl.Hand(); BUILD = os.path.join(HERE, 'refs-local', 'build'); z = np.load(os.path.join(BUILD, 'frames.npz'), allow_pickle=True); E = z['E'].item()
TOL = 1.0
JOBS = [  # clip, side, digit shell, control parts, what CR-1 asks
    ('trigger_pull', 'R', 'finger_index', ('trigger',), 'pad on the trigger face'),
    ('mag_release', 'R', 'finger_index', ('mag_release_button', 'mag_button_rib_1', 'mag_button_rib_2', 'mag_button_rib_3'), 'CR-1 item 4: index finger touches the magazine release'),
    ('mag_out', 'R', 'finger_index', ('mag_release_button', 'mag_button_rib_1', 'mag_button_rib_2', 'mag_button_rib_3'), 'CR-1 item 4: index finger touches the magazine release'),
    ('safety_to_fire', 'R', 'thumb', ('selector_lever_l',), 'CR-1 item 4: thumb touches the selector lever'),
    ('safety_to_safe', 'R', 'thumb', ('selector_lever_l',), 'CR-1 item 4: thumb touches the selector lever'),
    ('bolt_catch', 'L', 'thumb', ('bolt_catch', 'bolt_catch_ribs'), 'thumb on the bolt catch paddle'),
    ('charge', 'L', 'finger_index', ('charging_handle',), 'index finger hooks the charging handle')]
out = {}
for clip, side, shell, parts, what in JOBS:
    gaps = []
    for fr in E[clip]:
        rf = fr['rifle_frame']; mo = R.motion(clip, float(rf)) if rf else {}; T = []
        for n in parts:
            V = R.z['V_' + n].astype(float); mv = R.meta['parts'][n]['mover']
            if mv in mo: V = V @ mo[mv][:3, :3].T + mo[mv][:3, 3]
            T.append(V[R.z['T_' + n]])
        T = np.concatenate(T); s = fr[side]; M = hl.mirror_mats if side == 'R' else (lambda m: m)
        P = h.pose_shell(shell, h.skin_mats(h.fk(s['q'], M(s['H']), M(s['F']))))
        if side == 'R': P = P * [-1, 1, 1]
        gaps.append(float(tri_dist(P, T[:, 0][None], T[:, 1][None], T[:, 2][None]).min()))
    g = np.array(gaps); touch = [i for i, v in enumerate(gaps) if v <= TOL]
    out[clip] = dict(hand=side, digit=shell.replace('finger_', ''), control=parts[0], asks=what, smallest_gap_mm=round(float(g.min()), 2), frame_of_smallest_gap=int(g.argmin()), frames=len(gaps),
                     frames_in_contact=touch, contact=bool(len(touch) > 0), gap_mm_per_frame=[round(v, 2) for v in gaps])
    print(f"{clip:16s} {side} {shell:13s} -> {parts[0]:20s} smallest gap {g.min():6.2f} mm at frame {g.argmin():2d}; frames within {TOL} mm: {len(touch)} of {len(gaps)}")
json.dump(dict(asset='hands-gloved', tolerance_mm=TOL, method=__doc__.split('\n\n')[2].replace('\n', ' '), clips=out,
               cr1_item_4=dict(magazine_release=bool(out['mag_release']['contact'] and out['mag_out']['contact']), selector=bool(out['safety_to_fire']['contact'] and out['safety_to_safe']['contact']))),
          open(os.path.join(HERE, 'checks', 'contact.json'), 'w'), indent=1)

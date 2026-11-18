"""The firing hand's move to the selector, measured.  Writes checks/selector_move.json.

    python3 checks/selector_move.py        # after clips/make.py, checks/limits.py and checks/penetration.py

CR-3 asks, for safety_to_fire and safety_to_safe: the thumb's glove within 1.0 mm of the left selector lever through
the whole stroke of the lever (the frames of the rifle's clip), interpenetration at most 1.0 mm in every frame, joint
limits respected, no frame with the trigger finger inside the trigger guard, the hand back exactly on the firing grip
at the end, and the size of the move.  This check measures, per frame of each clip:
  gap        smallest distance from the thumb's glove (every vertex) to the lever's exact triangles;
  guard      vertices of each finger's glove inside the window of the trigger guard (grips/solve.py TRIGGER_GUARD);
             trigger_pull is measured the same way to show that the test sees a finger that is in the guard;
  trigger    smallest distance from the trigger finger's glove to the trigger, and the finger's bend (PIP + DIP);
  move       how far the hand is from the firing grip: the wrist joint's displacement, the hand's turn, the
             displacement of palm landmarks, of the elbow, and the elbow swivel;
  slip       how far the vertex of the thumb's glove that starts nearest the lever moves along the lever, and where on
             the lever the thumb bears (in the lever's own frame: along it from the pivot, and across it).
Interpenetration and joint limits are read from penetration.json and limits.json (the same measurements as for every
other clip), not measured again here."""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ('model', 'grips'): sys.path.insert(0, os.path.join(HERE, d))
import handlib as hl
from rifle import Rifle, tri_dist
import solve
R = Rifle(); h = hl.Hand(); BUILD = os.path.join(HERE, 'refs-local', 'build'); z = np.load(os.path.join(BUILD, 'frames.npz'), allow_pickle=True); E = z['E'].item(); META = json.loads(str(z['meta']))
TOL = 1.0; BOX = solve.TRIGGER_GUARD; MIRROR = np.array([-1.0, 1.0, 1.0]); DIG = ('thumb', 'finger_index', 'finger_middle', 'finger_ring', 'finger_little')
LM = ('wrist', 'index_meta_palmar', 'middle_mcp_palmar', 'little_mcp_palmar', 'thenar', 'hypothenar', 'index_tip'); A = hl.ANGLES.index
def load(name):
    p = os.path.join(HERE, 'checks', name); return json.load(open(p)) if os.path.exists(p) else None
PEN, LIM = load('penetration.json'), load('limits.json')
def posed(fr):
    s = fr['R']; Sk = h.skin_mats(h.fk(s['q'], hl.mirror_mats(s['H']), hl.mirror_mats(s['F']))); L = h.pose_landmarks(Sk)
    return {n: h.pose_shell(n, Sk) * MIRROR for n in DIG}, {n: np.asarray(L[n]) * MIRROR for n in LM if n in L}
def part_tris(names, mo):
    T = []
    for n in names:
        V = R.z['V_' + n].astype(float); mv = R.meta['parts'][n]['mover']
        if mv in mo: V = V @ mo[mv][:3, :3].T + mo[mv][:3, 3]
        T.append(V[R.z['T_' + n]])
    return np.concatenate(T)
def in_guard(P): return int(np.all((P > BOX[0]) & (P < BOX[1]), axis=1).sum())
def gap_to(P, T): return tri_dist(P, T[:, 0][None], T[:, 1][None], T[:, 2][None])
Vl = R.z['V_selector_lever_l'].astype(float); M90 = R.motion('safety_to_fire', 6.0)['selector_lever_l']
PIVOT = np.linalg.lstsq((np.eye(3) - M90[:3, :3])[1:, 1:], M90[1:3, 3], rcond=None)[0]      # the lever's axis (y, z): the point its quarter turn leaves in place
out = {}
for clip in ('safety_to_fire', 'safety_to_safe'):
    fl = E[clip]; m = META[clip]; n = len(fl); stroke = list(range(m['pre'], m['pre'] + m['n_rifle'])); rows = []; sh0, lm0 = posed(fl[0]); H0 = fl[0]['R']['H']; e0 = fl[0]['R']['F'][:3, 3]; j = None
    for f, fr in enumerate(fl):
        mo = R.motion(clip, float(fr['rifle_frame'])); sh, lm = posed(fr); Tl = part_tris(('selector_lever_l',), mo); Tt = part_tris(('trigger',), mo); d = gap_to(sh['thumb'], Tl); H = fr['R']['H']; q = fr['R']['q']
        row = dict(frame=f + 1, rifle_frame=int(fr['rifle_frame']), lever_stroke=f in stroke, thumb_to_lever_mm=round(float(d.min()), 2),
                   in_trigger_guard={k.replace('finger_', ''): in_guard(sh[k]) for k in DIG}, index_to_trigger_mm=round(float(gap_to(sh['finger_index'], Tt).min()), 1),
                   index_bend_deg=round(float(q[A('index_pip_flex')] + q[A('index_dip_flex')]), 1),
                   wrist_moved_mm=round(float(np.linalg.norm(H[:3, 3] - H0[:3, 3])), 1), hand_turned_deg=round(math.degrees(float(np.linalg.norm(hl.to_rotvec(H0[:3, :3].T @ H[:3, :3])))), 1),
                   landmarks_moved_mm={k: round(float(np.linalg.norm(lm[k] - lm0[k])), 1) for k in lm}, elbow_moved_mm=round(float(np.linalg.norm(fr['R']['F'][:3, 3] - e0)), 1), elbow_swivel_deg=round(float(fr['R']['arm']['swivel']), 1),
                   arm_deg={k: round(float(fr['R']['arm'][k]), 1) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')})
        if f in stroke:
            Ml = mo['selector_lever_l']; Mi = np.linalg.inv(Ml); k = int(d.argmin()); loc = Mi[:3, :3] @ sh['thumb'][k] + Mi[:3, 3]      # where the thumb bears, in the lever's own (rest) frame
            if j is None: j = k; p0 = loc
            pj = Mi[:3, :3] @ sh['thumb'][j] + Mi[:3, 3]
            row.update(thumb_bears_on_lever_mm=dict(along_from_pivot=round(float(PIVOT[1] - loc[2]), 1), across=round(float(loc[1] - PIVOT[0]), 1), out_from_wall=round(float(loc[0] - Vl[:, 0].min()), 1)), thumb_slip_on_lever_mm=round(float(np.linalg.norm(pj - p0)), 2))
        rows.append(row)
    st = [r for r in rows if r['lever_stroke']]; far = max(rows, key=lambda r: r['hand_turned_deg']); end = rows[-1]
    pen = PEN['clips'][clip]['per_frame_max_mm'] if PEN and clip in PEN['clips'] and len(PEN['clips'][clip]['per_frame_max_mm']) == n else None; lim = LIM['clips'].get(clip) if LIM else None
    res = dict(frames=n, lever_stroke_frames=[r['frame'] for r in st],
               thumb_to_lever_mm=dict(per_stroke_frame=[r['thumb_to_lever_mm'] for r in st], largest=max(r['thumb_to_lever_mm'] for r in st), tolerance=TOL, passes=bool(max(r['thumb_to_lever_mm'] for r in st) <= TOL)),
               thumb_slip_on_lever_mm=max(r['thumb_slip_on_lever_mm'] for r in st), thumb_bears_on_lever_mm=[r['thumb_bears_on_lever_mm'] for r in st],
               interpenetration_mm=dict(source='checks/penetration.json', largest=max(pen) if pen else None, frames_over_tolerance=[i + 1 for i, v in enumerate(pen) if v > TOL] if pen else None, tolerance=TOL, passes=bool(max(pen) <= TOL) if pen else None),
               joint_limits=dict(source='checks/limits.json', smallest_margin_deg=lim['smallest_margin_deg'] if lim and lim['frames'] == n else None, at=lim['at'] if lim and lim['frames'] == n else None, passes=bool(lim['pass_']) if lim and lim['frames'] == n else None),
               trigger_finger=dict(frames_in_trigger_guard=[r['frame'] for r in rows if r['in_trigger_guard']['index'] > 0], frames_with_any_finger_in_trigger_guard=[r['frame'] for r in rows if sum(r['in_trigger_guard'].values()) > 0],
                                   nearest_to_trigger_mm=min(r['index_to_trigger_mm'] for r in rows), bend_deg_at_firing_grip=rows[0]['index_bend_deg'], largest_bend_deg=max(r['index_bend_deg'] for r in rows),
                                   passes=bool(all(r['in_trigger_guard']['index'] == 0 for r in rows))),
               returns_to_firing_grip=dict(wrist_off_mm=end['wrist_moved_mm'], hand_off_deg=end['hand_turned_deg'], angles_off_deg=round(float(np.abs(fl[-1]['R']['q'] - fl[0]['R']['q']).max()), 3),
                                           passes=bool(end['wrist_moved_mm'] == 0 and end['hand_turned_deg'] == 0 and np.abs(fl[-1]['R']['q'] - fl[0]['R']['q']).max() < 1e-6)),
               hand_move=dict(at_the_lever=dict(wrist_moved_mm=st[0]['wrist_moved_mm'], hand_turned_deg=st[0]['hand_turned_deg'], landmarks_moved_mm=st[0]['landmarks_moved_mm'], elbow_moved_mm=st[0]['elbow_moved_mm'], elbow_swivel_deg=st[0]['elbow_swivel_deg'], arm_deg=st[0]['arm_deg']),
                              at_the_firing_grip=dict(elbow_swivel_deg=rows[0]['elbow_swivel_deg'], arm_deg=rows[0]['arm_deg']),
                              largest_in_clip=dict(wrist_moved_mm=max(r['wrist_moved_mm'] for r in rows), hand_turned_deg=far['hand_turned_deg'], elbow_moved_mm=max(r['elbow_moved_mm'] for r in rows)),
                              elbow_swivel_fastest_deg_per_frame=round(max(abs(a['elbow_swivel_deg'] - b['elbow_swivel_deg']) for a, b in zip(rows, rows[1:])), 1),
                              hand_turn_fastest_deg_per_frame=round(max(math.degrees(float(np.linalg.norm(hl.to_rotvec(a['R']['H'][:3, :3].T @ b['R']['H'][:3, :3])))) for a, b in zip(fl, fl[1:])), 1)),
               per_frame=rows)
    res['passes'] = bool(res['thumb_to_lever_mm']['passes'] and res['interpenetration_mm']['passes'] and res['joint_limits']['passes'] and res['trigger_finger']['passes'] and res['returns_to_firing_grip']['passes'])
    out[clip] = res; hm = res['hand_move']['at_the_lever']
    print(f"{clip}: thumb to lever, stroke frames {res['thumb_to_lever_mm']['per_stroke_frame']} (<= {TOL}: {res['thumb_to_lever_mm']['passes']}); interpenetration {res['interpenetration_mm']['largest']} mm ({res['interpenetration_mm']['passes']}); limits margin {res['joint_limits']['smallest_margin_deg']} ({res['joint_limits']['passes']}); "
          f"index in guard frames {res['trigger_finger']['frames_in_trigger_guard']}, any finger {res['trigger_finger']['frames_with_any_finger_in_trigger_guard']}; returns {res['returns_to_firing_grip']['passes']}; move at the lever: wrist {hm['wrist_moved_mm']} mm, turn {hm['hand_turned_deg']} deg, elbow {hm['elbow_moved_mm']} mm, swivel {res['hand_move']['at_the_firing_grip']['elbow_swivel_deg']} -> {hm['elbow_swivel_deg']}; slip {res['thumb_slip_on_lever_mm']} mm; PASS {res['passes']}")
tp = [in_guard(posed(fr)[0]['finger_index']) for fr in E['trigger_pull']]; idle = in_guard(posed(E['idle'][0])[0]['finger_index'])
json.dump(dict(asset='hands-gloved', asks='CR-3 goal 1: glove within 1.0 mm of the lever through the whole lever stroke, interpenetration at most 1.0 mm in every frame, joint limits respected, no frame with the trigger finger inside the trigger guard, the hand back exactly on the firing grip, and the size of the move',
               method=__doc__.split('This check measures, per frame of each clip:')[1].replace('\n', ' ').strip(), trigger_guard_window_mm=dict(lo=BOX[0].tolist(), hi=BOX[1].tolist()),
               guard_test_sees_a_finger=dict(trigger_pull_index_vertices_in_guard_min=int(min(tp)), idle_index_vertices_in_guard=idle), lever_pivot_yz_mm=[round(float(v), 2) for v in PIVOT],
               all_pass=bool(all(v['passes'] for v in out.values())), clips=out), open(os.path.join(HERE, 'checks', 'selector_move.json'), 'w'), indent=1)
print('guard test: trigger_pull has at least', min(tp), 'index vertices in the guard in every frame; idle has', idle)

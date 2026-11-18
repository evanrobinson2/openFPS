"""Can the firing thumb reach the selector lever?  Writes checks/selector_reach.json.

    python3 checks/selector_reach.py        # needs the solved grips and the local rifle build; about 2 minutes

CR-2 goal 4 asks for the thumb's glove within 1 mm of the left selector lever, or numbers showing why not.  This check
(1) searches the thumb's whole range from the firing grip for the smallest distance from its glove to the lever, with
nothing inside the rifle; (2) repeats that after moving the whole hand: 700 random small moves (up to 14 mm along each
axis and 16 degrees about each), keeping those that leave the palm clear of the rifle with its pads pressed to their
limits and the wrist inside its range, and polishing the six best; (3) gives the geometry behind the answer: where the
thumb's base joint is against where it would be with the web on its seat under the receiver's rear.
Distances are to points sampled on the lever's triangles (30 per triangle) in the search and to the exact triangles in
the reported numbers."""
import os, sys, json, math
import numpy as np
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ('model', 'grips'): sys.path.insert(0, os.path.join(HERE, d))
import handlib as hl, solve
from solve import DIGIT_IDX, SHOULDER, pole_of, es_min, tri_dist
S = solve.Solver(); h = S.h; R = S.r; g = solve.load_raw()['fire_indexed']; S.mir = True; H0 = g['H']; q0 = np.array(g['q'], float)
T = R.z['V_selector_lever_l'].astype(float)[R.z['T_selector_lever_l']] * [-1, 1, 1]
w = np.random.default_rng(0).dirichlet([1, 1, 1], size=(len(T), 30)); tree = cKDTree(np.einsum('tsk,tkj->tsj', w, T).reshape(-1, 3))
idx = np.array(DIGIT_IDX['thumb']); lo = hl.LO[idx] + 0.5; hi = hl.HI[idx] - 0.5; rng = np.random.default_rng(3)
qm = q0.copy(); qm[hl.PAD_IDX] = [hl.limit_of(hl.ANGLES[i])[1] for i in hl.PAD_IDX]
def shell(a, Hh): c = qm.copy(); c[idx] = a; S_ = S.skin(c, Hh); return h.pose_shell('thumb', S_), S_
def tf(a, Hh): P_, S_ = shell(a, Hh); return float(tree.query(P_)[0].min()) + 40.0 * S.pen('thumb', S_)
def best_thumb(Hh, TH, n=2, iters=400):
    o = np.argsort([tf(a, Hh) for a in TH])[:n]; best = None
    for i in o:
        a, fa = es_min(lambda a_: tf(a_, Hh), TH[i], np.full(5, 3.0), lo, hi, iters, np.random.default_rng(int(i)))
        if best is None or fa < best[1]: best = (a, fa)
    P_, S_ = shell(best[0], Hh); return best[0], float(tri_dist(P_, T[:, 0][None], T[:, 1][None], T[:, 2][None]).min()), float(S.pen('thumb', S_))
# 1. from the firing grip, the whole range of the thumb
a0, gap0, pen0 = best_thumb(H0, lo + (hi - lo) * rng.random((1500, 5)), n=5, iters=500)
print('from the firing grip: glove to lever %.2f mm (inside the rifle: %.2f)' % (gap0, pen0), flush=True)
# 2. after a small move of the whole hand
TH = lo + (hi - lo) * rng.random((80, 5)); res = []
for k in range(700):
    x = np.r_[rng.uniform(-14, 14, 3), rng.uniform(-16, 16, 3)]; Hh = H0 @ hl.M4(hl.rotvec(np.radians(x[3:]))); Hh[:3, 3] += x[:3]
    if S.pen('base', S.skin(qm, Hh)) > 0: continue
    F, ang = hl.forearm_and_wrist(Hh, S.world('R', SHOULDER['R']), pole_of(g['wrist']['swivel']))
    if not all(hl.LIMITS[kk][0] + 1.5 <= ang[kk] <= hl.LIMITS[kk][1] - 1.5 for kk in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')): continue
    res.append((min(tf(a, Hh) for a in TH), x, Hh))
res.sort(key=lambda r: r[0]); moved = []
for v, x, Hh in res[:6]:
    a, gp, pn = best_thumb(Hh, TH); moved.append(dict(glove_to_lever_mm=round(gp, 2), thumb_inside_rifle_mm=round(pn, 2), hand_moved_mm=round(float(np.linalg.norm(x[:3])), 1), hand_turned_deg=round(float(np.linalg.norm(x[3:])), 1)))
    print('after a move of %.1f mm and %.1f deg: %.2f mm' % (moved[-1]['hand_moved_mm'], moved[-1]['hand_turned_deg'], gp), flush=True)
# 3. why
Sk = S.skin(q0, H0); mirror = np.array([-1.0, 1, 1]); cmc = (H0 @ np.r_[hl.P['thumb_cmc'], 1])[:3] * mirror; web = S.lm(Sk, 'web_mid') * mirror; seat = np.array(solve.WEB_SEAT)
lever = T.reshape(-1, 3) * mirror; tip = lever[np.argmin(lever[:, 2])]; s = hl.seg('thumb'); L = s['mc'] + s['pp'] + s['dp'] + s['tip'] + hl.P['glove_tip'] + hl.P['glove']
out = dict(asset='hands-gloved', asks='CR-2 goal 4: the thumb\'s glove within 1.0 mm of the left selector lever in both safety clips, or numbers showing why not', tolerance_mm=1.0,
           from_the_firing_grip=dict(glove_to_lever_mm=round(gap0, 2), thumb_inside_rifle_mm=round(pen0, 2), thumb_angles_deg=[round(float(v), 1) for v in a0], searched='1,500 random thumb poses over the joint ranges, the five best polished'),
           after_a_small_move_of_the_hand=dict(tried=700, kept_clear_and_in_wrist_range=len(res), limits='up to 14 mm along each axis and 16 degrees about each', six_best=moved, smallest_gap_mm=min(m['glove_to_lever_mm'] for m in moved if m['thumb_inside_rifle_mm'] == 0) if any(m['thumb_inside_rifle_mm'] == 0 for m in moved) else None),
           geometry=dict(thumb_base_joint_mm=[round(float(v), 1) for v in cmc], lever_rear_tip_safe_mm=[round(float(v), 1) for v in tip], base_joint_to_lever_tip_mm=round(float(np.linalg.norm(tip - cmc)), 1), lever_above_base_joint_mm=round(float(tip[1] - cmc[1]), 1),
                         thumb_base_joint_to_glove_tip_straight_mm=round(L, 1), web_middle_mm=[round(float(v), 1) for v in web], web_seat_mm=list(solve.WEB_SEAT), web_from_seat_mm=dict(right=round(float(seat[0] - web[0]), 1), below=round(float(seat[1] - web[1]), 1), behind=round(float(seat[2] - web[2]), 1)),
                         base_joint_to_lever_tip_if_web_were_on_its_seat_mm=round(float(np.linalg.norm(tip - (cmc + seat - web))), 1),
                         note='The thumb has to cross behind the top of the grip, under the receiver\'s rear, and then lie along the left wall at the lever\'s height. The lever\'s rear tip is that far above the thumb\'s base joint; the thumb\'s first bone is %.1f mm long and its base joint turns %.1f degrees each way in flexion and %.1f in abduction, so the far end of that bone cannot rise to the lever\'s height while it also crosses to the left side. With the web on its seat the base joint would be higher and further left by the web\'s offset.' % (s['mc'], hl.LIMITS['thumb_cmc_flex'][1], hl.LIMITS['thumb_cmc_abd'][1])),
           reached=bool(gap0 <= 1.0 and pen0 == 0))
json.dump(out, open(os.path.join(HERE, 'checks', 'selector_reach.json'), 'w'), indent=1); print(json.dumps(out['geometry'], indent=1))

"""How far must the firing hand move for its thumb to reach the selector lever?  Writes checks/selector_scan.json.

    python3 checks/selector_scan.py [poses per worker = 6000] [workers = 4]     # about 25 minutes; needs the solved grips and the local rifle build

CR-3.  checks/selector_reach.py showed that no thumb pose reaches the lever from the firing grip (10.5 mm) or after a
small move of the hand (7.8 mm at best within 14 mm and 16 degrees).  This scan widens the move.  Each worker draws
hand poses as moves from fire_indexed (three ways: along the line toward a pose known to reach, with scatter; a wide
cloud round the middle of that line; and uniformly in a box) and keeps a pose if the arm fits it at some elbow swivel
(every arm angle 1.5 degrees inside its limit) and the palm, web, cuff and the straight trigger finger are clear of
the rifle with the pads pressed to their limits.  For every kept pose, 3,000 thumb poses drawn over the thumb's whole
range are tried at the lever's two end positions: those with nothing inside the rifle are ranked by the distance from
the thumb's glove to the lever.  The result is coarse (every third vertex of the thumb's shell, points sampled on the
lever, no polishing): it says where reaching poses are, and grips/solve.py (solve_select) polishes the one it starts
from.  For each kept pose the elbow swivels at which the arm fits are recorded too: that is what shows that the
poses that reach need the elbow under the rifle."""
import os, sys, json, time, math, warnings
import numpy as np
from scipy.spatial import cKDTree
warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ('model', 'grips'): sys.path.insert(0, os.path.join(HERE, d))
ARM = ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'); TOWARD = np.array([-32.6, 6.1, -8.3, 45.3, 50.8, -3.4])      # a move that reaches, from a first unstructured search (elbow under the rifle)
NT = 3000; SW = np.arange(-10.0, 100.1, 5.0)
def worker(args):
    seed, nh = args
    import handlib as hl, solve
    from solve import DIGIT_IDX, SHOULDER, pole_of
    S = solve.Solver(); h = S.h; R = S.r; g = solve.load_raw()['fire_indexed']; S.mir = True; H0 = g['H']; q0 = np.array(g['q'], float)
    K = [cKDTree(solve.lever_points(R, f)[0]) for f in (1, 6)]; MO = [R.motion('safety_to_fire', f) for f in (1, 6)]
    ti = np.array(DIGIT_IDX['thumb']); lo_t = hl.LO[ti] + 0.5; hi_t = hl.HI[ti] - 0.5; rng = np.random.default_rng(1000 + seed); TH = lo_t + (hi_t - lo_t) * np.random.default_rng(5).random((NT, 5))
    qm = q0.copy(); qm[hl.PAD_IDX] = [hl.limit_of(hl.ANGLES[i])[1] for i in hl.PAD_IDX]
    for f in ('middle', 'ring', 'little'): qm[DIGIT_IDX[f]] = (8, 0, 8, 5)
    LIB = []
    for a in TH: c = qm.copy(); c[ti] = a; LIB.append(h.pose_shell('thumb', S.skin(c, np.eye(4)))[::3])      # the thumb's shell in the hand's own frame, per thumb pose
    LIB = np.array(LIB); n = LIB.shape[1]; qn = qm.copy(); qn[ti] = (0, -10, 0, 5, 5); out = []; tried = dict(arm=0, rifle=0, kept=0)
    def margins(Hh): return np.array([solve.arm_margin(hl.forearm_and_wrist(Hh, S.world('R', SHOULDER['R']), pole_of(sw))[1]) for sw in SW])
    for i in range(nh):
        m = rng.integers(3)
        if m == 0: x = TOWARD * rng.uniform(0.1, 1.1) + np.r_[rng.normal(0, 6, 3), rng.normal(0, 8, 3)]
        elif m == 1: x = TOWARD * 0.5 + np.r_[rng.normal(0, 15, 3), rng.normal(0, 20, 3)]
        else: x = np.r_[rng.uniform(-45, 15), rng.uniform(-20, 25), rng.uniform(-30, 20), rng.uniform(-30, 60, 2), rng.uniform(-30, 30)]
        Hh = H0 @ hl.M4(hl.rotvec(np.radians(x[3:6]))); Hh[:3, 3] += x[:3]; mg = margins(Hh); fit = SW[mg >= 1.5]
        if not len(fit): tried['arm'] += 1; continue
        S.motion = None; Sk = S.skin(qn, Hh)
        if S.pen('base', Sk) > 0 or S.pen('index', Sk) > 0: tried['rifle'] += 1; continue
        tried['kept'] += 1; W = LIB.reshape(-1, 3) @ Hh[:3, :3].T + Hh[:3, 3]; res = []
        for Kk, M in zip(K, MO):
            d = R.sdf(W, motion=M, mirror=True).reshape(NT, n); idx = np.where(np.maximum(0.0, solve.MARGIN - d).sum(1) == 0)[0]
            res.append(float(Kk.query(W.reshape(NT, n, 3)[idx].reshape(-1, 3))[0].reshape(len(idx), n).min(1).min()) if len(idx) else 99.0)
        out.append(np.r_[x, res, fit.min(), fit.max()])
    return np.array(out), tried
if __name__ == '__main__':
    import multiprocessing as mp
    nh = int(sys.argv[1]) if len(sys.argv) > 1 else 6000; nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4; t0 = time.time()
    with mp.get_context('spawn').Pool(nw) as pool: parts = pool.map(worker, [(s, nh) for s in range(nw)])
    D = np.vstack([p[0] for p in parts]); tried = {k: int(sum(p[1][k] for p in parts)) for k in ('arm', 'rifle', 'kept')}
    np.save(os.path.join(HERE, 'refs-local', 'build', 'selector_scan.npy'), D)
    gap = np.maximum(D[:, 6], D[:, 7]); mv = np.linalg.norm(D[:, :3], axis=1); tn = np.linalg.norm(D[:, 3:6], axis=1); reach = gap < 1.0; hi_sw = D[:, 9]
    def best(m): return dict(poses=int(m.sum()), reach_both_ends=int((m & reach).sum()), smallest_gap_at_both_ends_mm=round(float(gap[m].min()), 2) if m.any() else None)
    o = [i for i in np.argsort(mv + tn) if reach[i]]
    out = dict(asset='hands-gloved', asks='CR-3: how far the firing hand has to leave the firing grip for the thumb to reach the selector lever at both ends of its travel',
               method=__doc__.split('\n\n')[2].replace('\n', ' '), reach_means='thumb glove under 1.0 mm from the lever at safe and at fire, nothing inside the rifle (coarse: see the method)',
               hand_poses_tried=int(nh * nw), arm_out_of_range=tried['arm'], palm_or_trigger_finger_inside_rifle=tried['rifle'], kept=tried['kept'], reach_both_ends=int(reach.sum()), thumb_poses_per_hand_pose=NT,
               by_hand_turn_deg={'%d to %d' % (a, b): best((tn >= a) & (tn < b)) for a, b in ((0, 15), (15, 25), (25, 35), (35, 45), (45, 55), (55, 70), (70, 120))},
               by_highest_elbow_swivel_the_arm_fits_deg={'%d or more' % a: best(hi_sw >= a) for a in (-10, 0, 10, 20, 30, 40, 50)},
               note_swivel='The firing grip fits the arm only with the elbow 50 to 90 degrees out (grips.json has 55). No kept pose that reaches fits an elbow more than %d degrees out: to reach the lever the elbow has to come in under the rifle.' % (int(hi_sw[reach].max()) if reach.any() else -99),
               smallest_moves_that_reach=[dict(wrist_moved_mm=round(float(mv[i]), 1), hand_turned_deg=round(float(tn[i]), 1), gap_safe_mm=round(float(D[i, 6]), 2), gap_fire_mm=round(float(D[i, 7]), 2),
                                               elbow_swivel_fits_deg=[float(D[i, 8]), float(D[i, 9])], move=[round(float(v), 1) for v in D[i, :6]]) for i in o[:8]],
               seconds=round(time.time() - t0))
    json.dump(out, open(os.path.join(HERE, 'checks', 'selector_scan.json'), 'w'), indent=1)
    print(json.dumps({k: out[k] for k in ('hand_poses_tried', 'kept', 'reach_both_ends', 'by_hand_turn_deg', 'by_highest_elbow_swivel_the_arm_fits_deg')}, indent=1)); print(out['smallest_moves_that_reach'][:3])

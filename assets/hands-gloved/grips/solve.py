"""Solve the grips against the locally built HK416 (grips/grips.json is written by clips/make.py from these).

    python3 grips/solve.py            # all grips
    python3 grips/solve.py support    # only that grip ('fire*' for every grip whose name starts with fire)

Method (a grasp planner, not a hand-set pose):
  1. Place the hand.  (a) Firing hand (fit_palm; version 3): a grid of orientations with one palm landmark held on its
     point, each scored whole; the best few are polished by a search over the hand's pose, the elbow swivel, the
     palm's own joints (metacarpals, thumb base) and the compression of the palm's four soft pads, for the pose in
     which the anchors sit on their points, nothing is inside the rifle beyond what the pads give, and the wrist is
     inside its range.  Afterwards each pad is cut back to the least compression that still clears the rifle (relax).  (b) Magazine, bolt-catch and charging grips: a stated frame or pad fit, backed off along a
     stated direction until nothing is inside the rifle.  (c) Support hand: an evolution-strategy search of the hand's
     pose in which each candidate is pushed against the rifle until it touches, pulled toward where R2 has the fingertips.
  2. Close the digits against the rifle's signed distance field: a wrapping finger searches its four joints for the
     pose whose three palmar pads are nearest the surface with nothing inside it; a digit with a job (trigger finger,
     thumb on a control) is placed on its target point by a search on its own joints.
  3. Choose the elbow swivel that keeps wrist, forearm and elbow inside their limits and furthest from any of them.
Joint angles never leave handlib.LIMITS (they are clipped to them).  A right hand is solved as the canonical left
hand in the x-mirrored world.  Everything is mm and degrees in the asset frame (+X left, +Y up, +Z muzzle)."""
import os, sys, json, math, time
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl
from rifle import Rifle, tri_dist

# ------------------------------------------------------------------ the shooter (I: standing, stock extended, torso bladed 30 degrees)
# CR-1 stance change.  Version 1 had the stock collapsed and the right shoulder 45 mm behind the buttpad.  With that, a level
# firing hand flat on the grip's side needs 95 degrees of wrist extension against a limit of 70, and the hand as solved here
# (rising 16 degrees) fits with 0.3 degrees to spare.  Version 2 solves the arms for the stock fully extended (the end of the
# rifle's stock_extend clip, 75 mm), which moves both shoulders back 75 mm and leaves the wrist about 10 degrees clear of its
# limits (notes/NOTES.md has the numbers); the torso is turned 30 degrees instead of 15 so that the support hand still
# reaches the handguard.  The rifle is still drawn and checked with its stock collapsed, as its clips have it.
STOCK_OUT = 75.0
SHOULDER = dict(R=np.array([-50.0, -62.0, -452.0 - STOCK_OUT]),   # I: right shoulder joint: 45 mm behind the buttpad face, 20 mm below its centre, 50 mm outboard
                L=np.array([262.0, -62.0, -347.0]))                 # I: left shoulder, 360 mm from the right (A: biacromial 415.7 less the acromion overhang), torso turned 30 deg
SWIVEL = (-10.0, 100.0)   # I: elbow swivel about the shoulder-wrist line, degrees outboard of straight down (90 = level with the shoulder)
def pole_of(phi): return np.array([math.sin(math.radians(phi)), -math.cos(math.radians(phi)), 0.0])    # canonical-left world: +x is outboard for both arms
MARGIN = 0.50             # mm kept between the glove and the rifle while solving
def A(i): return hl.ANGLES.index(i)
DIGIT_IDX = {f: [A(f + '_mcp_flex'), A(f + '_mcp_abd'), A(f + '_pip_flex'), A(f + '_dip_flex')] for f in hl.FING}
DIGIT_IDX['thumb'] = [A('thumb_cmc_flex'), A('thumb_cmc_abd'), A('thumb_cmc_rot'), A('thumb_mcp_flex'), A('thumb_ip_flex')]

def arm_margin(a):
    """How far the arm is from its nearest limit, in degrees (CR-1: of the elbow swivels that keep every angle in range,
    the one furthest from any limit is used; version 1 took the one with the least wrist bend, which ran the wrist to its stop)."""
    return min(min(a[k] - hl.LIMITS[k][0], hl.LIMITS[k][1] - a[k]) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'))
ELBOW_MARGIN = 4.0
def swivel_rank(side, sw, a):
    """Which elbow swivel to use among those inside the limits (smaller is better).  Support arm: the one furthest from any
    limit (CR-1).  Firing arm (CR-2, sleeve fix): the lowest elbow that keeps every angle ELBOW_MARGIN degrees inside its
    limit.  R1-F10 and R2-F01 show the firing forearm arriving from below with the wrist bent to the little-finger side;
    version 2's choice (furthest from any limit) put the elbow out at 60 to 65 degrees and pointed the forearm at R1's camera."""
    m = arm_margin(a)
    return -m if side == 'L' else ((0, sw) if m >= ELBOW_MARGIN else (1, -m))
def es_min(fun, x0, sigma, lo, hi, iters, rng, shrink=0.985, grow=1.25):
    """(1+1) evolution strategy with step-size adaptation, bounded.  Robust on the non-smooth contact objective."""
    x = np.clip(np.asarray(x0, float), lo, hi); fx = fun(x); s = 1.0
    for _ in range(iters):
        c = np.clip(x + rng.normal(size=len(x)) * sigma * s, lo, hi); fc = fun(c)
        if fc < fx: x, fx = c, fc; s = min(s * grow, 2.0)
        else: s = max(s * shrink, 0.02)
    return x, fx

class Solver:
    def __init__(self):
        self.h = hl.Hand(); self.r = Rifle(); h = self.h; self.lmi = {n: i for i, n in enumerate(h.lm_names)}
        self.grp = {}
        for g, shells, stride in (('base', ('palm', 'web', 'cuff'), 1), ('thumb', ('thumb',), 1)) + tuple((f, ('finger_' + f,), 1) for f in hl.FING):
            V = np.vstack([h.shells[s]['V'][::stride] for s in shells]); Wt = np.vstack([h.shells[s]['W'][::stride] for s in shells])
            self.grp[g] = (np.c_[V, np.ones(len(V))], Wt, np.concatenate([np.c_[h.shells[s]['D'][:, ::stride], np.zeros((len(hl.PADS), len(h.shells[s]['V'][::stride]), 1))] for s in shells], axis=1))
        self.rng = np.random.default_rng(416); self.motion = None; self.mir = False; self.skip = ()
    # ---- geometry helpers (canonical-left world)
    def world(self, side, p): p = np.asarray(p, float); return p * [-1, 1, 1] if side == 'R' else p
    def skin(self, q, H): return self.h.skin_mats(self.h.fk(q, H))
    def pts(self, g, S):
        Vh, Wt, D = self.grp[g]; c = getattr(S, 'pads', None)            # CR-2: the pads are compressed as the pose says
        if c is not None and np.any(c): Vh = Vh + np.einsum('k,kvj->vj', c, D)
        return np.einsum('vb,bij,vj->vi', Wt, np.asarray(S)[:, :3, :], Vh)
    def sdf(self, P_, skip=None): return self.r.sdf(P_, motion=self.motion, mirror=self.mir, skip=self.skip if skip is None else skip)
    def pen(self, g, S, skip=None):
        v = np.maximum(0.0, MARGIN - self.sdf(self.pts(g, S), skip)).sum()
        if g == 'thumb': v += np.maximum(0.0, MARGIN - self.sdf(self.pts('base', S), skip)).sum()      # CR-1: the thenar part of the palm moves with the thumb
        return v
    def lm(self, S, name):
        if name == 'web_mid':        # CR-1: the middle of the web between thumb and index; it moves with both, unlike the landmark 'web'
            sh = self.h.shells['web']; m = sh['ring'] == 4; return np.einsum('vb,bij,vj->vi', sh['W'][m], np.asarray(S)[:, :3, :], np.c_[sh['V'][m], np.ones(m.sum())]).mean(0)
        i = self.lmi[name]; c = getattr(S, 'pads', None); p = self.h.lm_pos[i:i + 1]
        if c is not None and np.any(c): p = p + np.einsum('k,kvj->vj', c, self.h.lm_D[:, i:i + 1])
        return self.h.pose_points(p, self.h.lm_bone[i:i + 1], S)[0]
    # ---- digits
    STARTS = ((8.0, 0.0, 8.0, 5.0), (45.0, 0.0, 60.0, 35.0), (70.0, 0.0, 92.0, 50.0), (20.0, 0.0, 85.0, 55.0))
    def wrap(self, f, q, H, iters=60, skip=None, w=(0.5, 1.0, 1.0), curl=0.0):
        """Close finger f round the rifle: a search on its four joints, from several starting curls, for the pose whose
        three palmar pads (proximal, middle, distal phalanx) are nearest the surface with nothing inside it.
        Returns q and whether the result is free of the rifle."""
        q = q.copy(); idx = np.array(DIGIT_IDX[f]); lo, hi = hl.LO[idx] + 0.5, hl.HI[idx] - 0.5; th = f == 'thumb'
        li = [self.lmi[f + s] for s in (('_pad_prox', '_pad') if th else ('_pad_prox', '_pad_mid', '_pad'))]; wv = np.array((0.6, 1.0) if th else w)
        def fun(a):
            c = q.copy(); c[idx] = a; S = self.skin(c, H); L = self.h.pose_points(self.h.lm_pos[li], self.h.lm_bone[li], S)
            return float(wv @ np.clip(self.sdf(L, skip), 0.0, 25.0)) + 25.0 * self.pen(f, S, skip) + (0.0 if th else 0.03 * abs(a[3] - 0.67 * a[2]) + 0.02 * abs(a[1]) + curl * max(0.0, 150.0 - a[0] - a[2]))
        best = None; starts = ((0, 0, 0, 10, 10), (10, -10, 0, 25, 30), (-10, 10, 0, 5, 5), (15, 5, 4, 30, 40)) if th else self.STARTS
        for k, st in enumerate(starts):
            a, fa = es_min(fun, np.array(st, float), np.array([8.0, 8.0, 4.0, 10.0, 10.0]) if th else np.array([12.0, 3.0, 12.0, 8.0]), lo, hi, iters, np.random.default_rng(7 + k))
            if best is None or fa < best[1]: best = (a, fa)
        q[idx] = best[0]; return self.clear(f, q, H, skip)
    def clear(self, d, q, H, skip=None):
        """If a digit still touches into the rifle, open it a little at a time until it does not.  Returns q and whether it is free."""
        idx = np.array(DIGIT_IDX[d]); fl = idx[[0, 3, 4]] if d == 'thumb' else idx[[0, 2, 3]]; q = q.copy()
        for _ in range(80):
            if self.pen(d, self.skin(q, H), skip) == 0: return q, True
            q[fl] = np.maximum(q[fl] - np.array([0.4, 0.8, 0.6]), hl.LO[fl] + 0.5)
        return q, False
    def ik(self, d, q, H, landmark, target, iters=220, w_touch=0.0, prior=None, skip=None, extra=None):
        """Place a digit's landmark on a target point without entering the rifle, by a search on that digit's own joints."""
        idx = np.array(DIGIT_IDX[d]); lo, hi = hl.LO[idx] + 0.5, hl.HI[idx] - 0.5; q = q.copy(); p0 = q[idx] if prior is None else np.asarray(prior, float)
        def fun(a):
            c = q.copy(); c[idx] = a; S = self.skin(c, H); L = self.lm(S, landmark); e = np.linalg.norm(L - target)
            v = e + 100.0 * self.pen(d, S, skip) + 0.01 * np.abs(a - p0).sum()
            if w_touch: v += w_touch * abs(float(self.sdf(L[None], skip)[0]))
            if d != 'thumb': v += 0.03 * abs(a[3] - 0.67 * a[2])
            if extra: v += extra(S)
            return v
        starts = [np.clip(p0, lo, hi)] + [np.array(s, float) for s in (((0, 0, 0, 10, 10), (10, -10, 0, 25, 30), (-10, 10, 0, 5, 5), (-15, -15, 0, 0, 0)) if d == 'thumb' else self.STARTS)]
        best = None
        for k, st in enumerate(starts):
            a, fa = es_min(fun, np.clip(st, lo, hi), np.full(len(idx), 6.0), lo, hi, iters if k == 0 else iters // 2, np.random.default_rng(11 + k))
            if best is None or fa < best[1]: best = (a, fa)
            if k == 0 and fa < 3.0: break            # the prior already reaches the target cleanly
        q[idx] = best[0]; q, _ = self.clear(d, q, H, skip)
        return q, float(np.linalg.norm(self.lm(self.skin(q, H), landmark) - target))
    def relax(self, q, H):
        """CR-2.  Cut each pad's compression back (bisection) to the least that still leaves the whole glove clear of the
        rifle: a pad is pressed in only as far as the rifle presses it."""
        q = q.copy(); free = lambda qq: (lambda Sk: sum(self.pen(g_, Sk) for g_ in self.grp) == 0)(self.skin(qq, H))      # every part: the distal pad also carries the fingers' bases
        if not np.any(q[hl.PAD_IDX] > 0) or not free(q): return q
        for i in hl.PAD_IDX:
            if q[i] <= 0: continue
            lo_, hi_ = 0.0, q[i]; q[i] = 0.0
            if free(q): continue
            for _ in range(7):
                m = (lo_ + hi_) / 2; q[i] = m
                if free(q): hi_ = m
                else: lo_ = m
            q[i] = hi_
        return q
    def pen_all(self, q, H):
        S = self.skin(q, H); return sum(self.pen(g, S) for g in self.grp)
    def seat(self, spec, H, fine=False):
        """Guarded moves: translate the open hand along each direction until it touches.  Returns H and whether the start was free."""
        q = spec['q_open']; side = spec['side']
        if self.pen_all(q, H) > 0: return H, False
        for rnd in range(spec.get('seat_rounds', 2)):
            for kind, d, dmax in spec.get('seat', ()):
                d = hl.unit(self.world(side, d)) if kind == 'world' else H[:3, :3] @ hl.unit(d)
                step = 4.0; moved = 0.0
                while step > (0.2 if fine else 0.5) and moved < dmax:
                    T = H.copy(); T[:3, 3] += d * step
                    if self.pen_all(q, T) > 0: step *= 0.5
                    else: H = T; moved += step
        return H, True
    def close(self, spec, H, q0, fine=False, do_ik=True):
        """Apply the spec's digit jobs to a hand pose.  Returns q and a dict of digit errors / free flags."""
        q = q0.copy(); side = spec['side']; out = {}
        for d, job in spec['digits'].items():
            if job[0] == 'wrap':
                q, free = self.wrap(d, q, H, iters=220 if fine else 40, **(job[1] if len(job) > 1 else {})); out[d] = 0.0 if free else 30.0
            elif job[0] == 'ik':
                kw = dict(job[3]) if len(job) > 3 else {}
                if do_ik: q, e = self.ik(d, q, H, job[1], self.world(side, job[2]), iters=320, **kw); out[d] = e
                else: q[DIGIT_IDX[d]] = spec['q_open'][DIGIT_IDX[d]]; out[d] = 0.0
            elif job[0] == 'pose': q[DIGIT_IDX[d]] = job[1]; q, free = self.clear(d, q, H); out[d] = 0.0 if free else 30.0
        return q, out
    # ---- a whole grip
    def frame0(self, spec):
        s = spec['H0']; return hl.frame(self.world(spec['side'], s['wrist']), self.world(spec['side'], s['distal']), self.world(spec['side'], s['dorsal']))
    def score(self, spec, H, swivel, q0, fine=False, detail=False):
        side = spec['side']; v = {}
        if spec.get('seat'): H, free = self.seat(spec, H, fine); v['start'] = 0.0 if free else 500.0 + 30.0 * self.pen_all(spec['q_open'], H)
        q, dig = self.close(spec, H, q0, fine, do_ik=fine); S = self.skin(q, H)
        v['pen'] = 30.0 * sum(self.pen(g, S) for g in self.grp)
        v['digits'] = sum(dig.values())
        v['anchors'] = sum(w * np.linalg.norm(self.lm(S, k) - self.world(side, p)) for k, (p, w) in spec.get('anchors', {}).items())
        gaps = {k: float(self.sdf(self.lm(S, k)[None], skip=())[0]) for k in spec.get('touch', {})}
        v['touch'] = sum(w * min(abs(gaps[k]), 20.0) for k, w in spec.get('touch', {}).items())
        F, ang = hl.forearm_and_wrist(H, self.world(side, SHOULDER[side]), pole_of(swivel)); ang['swivel'] = float(swivel)
        wm = spec.get('wrist_margin', 1.5)
        v['wrist'] = sum(spec.get('w_wrist', 3.0) * max(0.0, hl.LIMITS[k][0] + wm - ang[k], ang[k] - hl.LIMITS[k][1] + wm) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')) \
            + 0.04 * (abs(ang['wrist_flex']) + abs(ang['wrist_dev'])) + (50.0 if ang['reach_over'] else 0.0)
        tot = sum(v.values())
        if detail: return tot, dict(q=q, H=H, F=F, S=S, terms={k: round(float(x), 2) for k, x in v.items()}, digits={k: round(float(x), 2) for k, x in dig.items()}, gaps={k: round(g, 2) for k, g in gaps.items()}, wrist=ang)
        return tot
    def best_swivel(self, side, H):
        best = None
        for sw in np.arange(SWIVEL[0], SWIVEL[1] + 0.1, 2.5):
            F, a = hl.forearm_and_wrist(H, self.world(side, SHOULDER[side]), pole_of(sw))
            viol = sum(max(0.0, hl.LIMITS[k][0] - a[k], a[k] - hl.LIMITS[k][1]) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'))
            key = (round(viol, 3), swivel_rank(side, sw, a))
            if best is None or key < best[0]: a['swivel'] = float(sw); best = (key, F, a, viol)
        return best[1], best[2], best[3]
    def place(self, spec):
        """Rigid least-squares fit of palm landmarks to points on the rifle (Kabsch), optional pitch about a pivot, then back off until free."""
        side = spec['side']
        if 'frame' in spec:
            s = spec['frame']; H = hl.frame(self.world(side, s['wrist']), self.world(side, s['distal']), self.world(side, s['dorsal']))
            if spec.get('fit'): return H, 0.0, 0.0
            back = hl.unit(self.world(side, spec['retreat'])); q = spec['q_open']; moved = 0.0; free = lambda Hh: sum(self.pen(g_, self.skin(q, Hh)) for g_ in spec.get('backoff_groups', ('base',))) == 0
            while not free(H) and moved < 40.0: H = H.copy(); H[:3, 3] += back * 0.5; moved += 0.5
            return H, 0.0, moved
        names = list(spec['place']); P_ = np.array([self.h.landmarks[n][1] for n in names]); Q = np.array([self.world(side, spec['place'][n]) for n in names])
        pc, qc = P_.mean(0), Q.mean(0); U, s, Vt = np.linalg.svd((P_ - pc).T @ (Q - qc)); d = np.sign(np.linalg.det(Vt.T @ U.T)); R = Vt.T @ np.diag([1, 1, d]) @ U.T
        H = hl.M4(R, qc - R @ pc); fit = float(np.sqrt(((P_ @ R.T + H[:3, 3] - Q) ** 2).sum(1).mean()))
        if spec.get('pitch'):            # rotate about a lateral axis through a pivot on the rifle (degrees, + = fingers up)
            ang, piv = spec['pitch']; piv = self.world(side, piv); Rp = hl.rx(-math.radians(ang)); H = hl.M4(Rp, piv - Rp @ piv) @ H
        if spec.get('yaw'):              # rotate about a vertical axis through a pivot (degrees, + = wrist toward the rifle's centre plane)
            ang, piv = spec['yaw']; piv = self.world(side, piv); Ry = hl.ry(math.radians(ang) * (1 if side == 'R' else -1)); H = hl.M4(Ry, piv - Ry @ piv) @ H
        if spec.get('fit'): return H, fit, 0.0
        back = hl.unit(self.world(side, spec['retreat'])); q = spec['q_open']; moved = 0.0; free = lambda Hh: self.pen('base', self.skin(q, Hh)) == 0
        while not free(H) and moved < 40.0: H = H.copy(); H[:3, 3] += back * 0.5; moved += 0.5
        return H, fit, moved
    def fit_palm(self, spec, H0, iters=2500, verbose=True):
        """CR-1.  Seat a folding palm on the rifle: a search over the hand's pose (6), the elbow swivel and the palm's own
        joints (thumb carpometacarpal flexion, abduction and rotation, thumb MCP, ring and little carpometacarpal flexion)
        for the pose in which the named palm pads touch the surface, the anchors sit on their points, nothing of the palm,
        web, cuff or thumb is inside the rifle, and the wrist is inside its range.  Returns H, q0, swivel, terms."""
        side = spec['side']; f = spec['fit']; pi = np.array([A(k) for k in f['joints']]); q0 = spec['q_open'].copy()
        if 'seed_pose' in f: H0 = f['seed_pose'][0].copy(); H0[:3, 3] += self.world(side, f['seed_shift']); q0 = np.array(f['seed_pose'][1], float)
        edge = np.array([0.0 if k.startswith('pad_') else 0.5 for k in f['joints']])
        lo = np.r_[[-30.0] * 3, [-40.0] * 3, SWIVEL[0], hl.LO[pi] + edge]; hi = np.r_[[30.0] * 3, [40.0] * 3, SWIVEL[1], hl.HI[pi] - edge]
        tn = list(f['touch']); tw = np.array([f['touch'][k] for k in tn]); toff = np.array([f.get('touch_gap', {}).get(k, 0.0) for k in tn])
        anch = [(k, self.world(side, p), w) for k, (p, w) in f['anchors'].items()]; groups = f.get('groups', ('base', 'thumb'))
        pw = np.array([f.get('pad_cost', 0.25) if k.startswith('pad_') else 0.02 for k in f['joints']])      # CR-2: a pad is compressed only where that buys contact
        def unpack(x):
            Hh = H0 @ hl.M4(hl.rotvec(np.radians(x[3:6]))); Hh[:3, 3] += x[:3]; q = q0.copy(); q[pi] = x[7:]; return Hh, q
        def terms(x):
            Hh, q = unpack(x); S = self.skin(q, Hh); v = {}
            v['pen'] = 40.0 * sum(self.pen(g, S) for g in groups)
            L = np.array([self.lm(S, k) for k in tn]); v['touch'] = float(tw @ np.minimum(np.abs(self.sdf(L) - MARGIN - toff), 15.0))
            v['anchors'] = sum(w * np.linalg.norm(self.lm(S, k) - p) for k, p, w in anch)
            F, ang = hl.forearm_and_wrist(Hh, self.world(side, SHOULDER[side]), pole_of(x[6]))
            v['wrist'] = f.get('w_wrist', 1.0) * sum(3.0 * max(0.0, hl.LIMITS[k][0] + 1.5 - ang[k], ang[k] - hl.LIMITS[k][1] + 1.5) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')) + 0.03 * (abs(ang['wrist_flex']) + abs(ang['wrist_dev']))
            if 'level' in f:      # the hand's distal axis against a wanted elevation above the bore line (deg)
                el = math.degrees(math.asin(max(-1, min(1, Hh[1, 1])))); v['level'] = f['level'][1] * abs(el - f['level'][0])
            v['prior'] = float(pw @ np.abs(x[7:] - q0[pi]))
            if 'seed_pose' in f: v['stay'] = 0.4 * float(np.linalg.norm(x[:3])) + 0.4 * float(np.linalg.norm(x[3:6]))
            if 'extra' in f: v.update(f['extra'](self, S, Hh, q))
            return v
        # coarse scan (CR-1, reworked for CR-2): for each orientation of a grid about the first guess the hand is put with the
        # start landmark on its point, the pads fully compressed, and scored whole; the best few are polished by the search above.
        Hbase = H0; sl, sp = f.get('start', (None, np.zeros(3))); sp = self.world(side, sp); cand = []; nfail = 0
        if sl is None: cand.append((0.0, 0, 0, 0, np.r_[np.zeros(6), spec.get('swivel0', 40.0), q0[pi]]))
        def wrist_only(Hh, sw):
            F, ang = hl.forearm_and_wrist(Hh, self.world(side, SHOULDER[side]), pole_of(sw))
            return sum(max(0.0, hl.LIMITS[k][0] + 1.5 - ang[k], ang[k] - hl.LIMITS[k][1] + 1.5) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')) + 0.01 * (abs(ang['wrist_flex']) + abs(ang['wrist_dev']))
        for yaw in (f.get('yaws', (0.0,)) if sl else ()):
            for pitch in f.get('pitches', (0.0,)):
                for roll in f.get('rolls', (0.0,)):
                    Rs = hl.ry(math.radians(yaw)) @ hl.rx(-math.radians(pitch)) @ hl.rz(math.radians(roll)); Hh = hl.M4(Rs) @ Hbase; q = q0.copy()
                    q[hl.PAD_IDX] = [hl.limit_of(hl.ANGLES[i])[1] if hl.ANGLES[i] in f['joints'] else 0.0 for i in hl.PAD_IDX]
                    Hh[:3, 3] += sp - self.lm(self.skin(q, Hh), sl)
                    Rr = Hbase[:3, :3].T @ Hh[:3, :3]; xx = np.r_[Hh[:3, 3] - Hbase[:3, 3], np.degrees(hl.to_rotvec(Rr)), 0.0, q[pi]]
                    xx[6] = min(np.arange(SWIVEL[0], SWIVEL[1] + 0.1, 5.0), key=lambda w_: wrist_only(Hh, w_))
                    cand.append((sum(terms(xx).values()), yaw, pitch, roll, xx))
        if 'seed_pose' in f:      # CR-2: a hold that is another hold moved a little (fire_reach): start from that one and charge for leaving it
            cand = [(0.0, 0, 0, 0, np.r_[np.zeros(6), f['seed_pose'][2], q0[pi]])]
        cand.sort(key=lambda c: c[0]); best = None
        if verbose: print('    scan: %d candidates, %d starts inside the rifle' % (len(cand), nfail))
        if verbose:
            for c in cand[:6]: print('    scan', c[1:4], round(c[0], 1), {kk: round(float(v), 1) for kk, v in terms(c[4]).items()}, flush=True)
        lo[3:6] = -180.0; hi[3:6] = 180.0; lo[:3] = -80.0; hi[:3] = 80.0
        for k, c in enumerate(cand[:f.get('polish', 3)]):
            sg = np.array([0.5 if k_.startswith('pad_') else 2.5 for k_ in f['joints']])
            x, fx = es_min(lambda u: sum(terms(u).values()), c[4], np.r_[[1.0] * 3, [1.5] * 3, 5.0, sg], lo, hi, iters, np.random.default_rng(416 + k))
            x, fx = es_min(lambda u: sum(terms(u).values()), x, np.r_[[0.3] * 3, [0.4] * 3, 2.0, sg * 0.4], lo, hi, iters // 2, np.random.default_rng(516 + k))
            if verbose: print('    polished', c[1:4], round(fx, 2), {kk: round(float(v), 1) for kk, v in terms(x).items()}, flush=True)
            if best is None or fx < best[1]: best = (x, fx)
        x, fx = best
        Hh, q = unpack(x); t = {k: round(float(v), 2) for k, v in terms(x).items()}
        if verbose: print('   palm fit', round(fx, 2), t, 'x', np.round(x, 1), flush=True)
        return Hh, q, float(x[6]), t
    def solve(self, spec, motion=None, iters=500, x0=None, verbose=True, H_fixed=None, q_fixed=None):
        t0 = time.time(); self.motion = motion; self.mir = spec['side'] == 'R'; self.skip = tuple(spec.get('free', ())); self.rng = np.random.default_rng(416)
        q0 = spec['q0']; x = np.r_[np.zeros(6), spec.get('swivel0', 10.0)] if x0 is None else np.asarray(x0, float); extra = {}
        if H_fixed is not None:
            H = H_fixed
            if q_fixed is not None: q0 = np.array(q_fixed, float); spec = dict(spec); spec['digits'] = {d: j for d, j in spec['digits'].items() if d in spec.get('only', spec['digits'])}
        elif 'fit' in spec:
            H, fit, _ = self.place(spec); H, q0, sw, t = self.fit_palm(spec, H, iters=spec['fit'].get('iters', 2500), verbose=verbose); x[6] = sw; extra = dict(place_fit_rms=round(fit, 2), palm_fit=t)
        elif 'place' in spec or 'frame' in spec: H, fit, moved = self.place(spec); extra = dict(place_fit_rms=round(fit, 2), backed_off=moved)
        else:
            H0 = self.frame0(spec)
            def Hx(x): Hh = H0 @ hl.M4(hl.rotvec(np.radians(x[3:6]))); Hh[:3, 3] += x[:3]; return Hh
            lo = np.r_[[-40.0] * 3, [-50.0] * 3, SWIVEL[0]]; hi = np.r_[[40.0] * 3, [50.0] * 3, SWIVEL[1]]
            if iters > 0:
                x, fx = es_min(lambda u: self.score(spec, Hx(u), u[6], q0), x, np.r_[np.array(spec.get('sigma_t', [4.0] * 3)), [5.0] * 3, 8.0], lo, hi, iters, self.rng)
                if verbose: print('   search', round(fx, 1), round(time.time() - t0, 1), 's', flush=True)
            H, _ = self.seat(spec, Hx(x), True)
        sp2 = dict(spec); sp2['seat'] = ()
        tot, d = self.score(sp2, H, x[6], q0, fine=True, detail=True); d['q'] = self.relax(d['q'], d['H']); d['S'] = self.skin(d['q'], d['H']); d['x'] = x; d['side'] = spec['side']; d['attach'] = spec.get('attach'); d['score'] = float(tot); d.update(extra)
        d['F'], d['wrist'], d['limit_violation_deg'] = self.best_swivel(spec['side'], d['H'])
        mins = {g: float(self.sdf(self.pts(g, d['S'])).min()) for g in self.grp}; d['min_sdf'] = min(mins.values()); d['seconds'] = round(time.time() - t0, 1)
        if verbose: print(f"  score {tot:.1f} {d['terms']} {extra}  min sdf {d['min_sdf']:.2f}  wrist {d['wrist']['wrist_flex']:.0f}/{d['wrist']['wrist_dev']:.0f} pron {d['wrist']['pronation']:.0f} elbow {d['wrist']['elbow_flex']:.0f} swivel {d['wrist']['swivel']:.0f} viol {d['limit_violation_deg']:.1f}  {d['seconds']} s\n   digits {d['digits']}\n   gaps {d['gaps']}", flush=True)
        self.motion = None; return d

# ------------------------------------------------------------------ grip specifications (targets are points on the rifle, asset frame)
def base_q(**kw):
    q = np.zeros(len(hl.ANGLES))
    for k, v in kw.items(): q[A(k)] = v
    return q
WRAP = ('wrap',)
CURL = ('wrap', dict(curl=0.06))      # a finger that closes round a handle: of two poses that touch, the more closed one
def q_open(index=(8, 4, 12, 8), thumb=(-5, -14, 0, 5, 5), **kw):
    q = base_q(**kw)
    for f in hl.FING: q[DIGIT_IDX[f]] = (8, 0, 8, 5)
    q[DIGIT_IDX['index']] = index; q[DIGIT_IDX['thumb']] = thumb; return q
# where the firing hand's palm pads go on the right side of the grip.  Height: the middle finger's knuckle pad hard under the
# trigger guard (guard bottom y -83.4, half a gloved finger 12.2).  Along the grip: 15 mm behind the grip's front edge, the
# furthest forward at which this hand's middle finger still closes round the front under the trigger guard (12 mm further
# forward it cannot).  R1 has the index knuckle about 24 mm ahead of this and R3 about 5 mm ahead (checks/compare.py).
# The other two pads follow from the hand's own shape with the hand rising 12 degrees.
GRIP_PADS = {'middle_mcp_palmar': (-15.0, -95.5, -157.0), 'index_meta_palmar': (-15.0, -84.2, -180.9), 'little_mcp_palmar': (-15.0, -136.9, -164.3)}
R3_INDEX_TIP = (-17.5, -55.3, -80.5)   # R3: the straight index finger's tip lies 0.84 of a finger breadth below the magazine release's centre and 0.15 ahead of it
TRIGGER_FACE = (0.0, -62.0, -114.6)   # middle of the trigger blade's front face (the blade spans y -50 to -74 there; rifle geometry)
TANG = (0.0, -45.0, -178.5)      # the notch where the top of the grip's back meets the underside of the receiver's rear (rifle geometry)
WEB_SEAT = (0.0, -54.0, -187.0)  # CR-2: where the middle of the web goes: 9 mm below and 8.5 mm behind the notch, which is as near as a web 14.4 mm thick can lie to it
PALM_JOINTS = ('mc2_flex', 'mc3_flex', 'mc4_flex', 'mc5_flex', 'thumb_cmc_flex', 'thumb_cmc_abd', 'thumb_cmc_rot', 'thumb_mcp_flex', 'thumb_ip_flex', 'pad_thenar', 'pad_hypothenar', 'pad_midpalm', 'pad_distal')
def spec_fire_indexed(forward=0.0, **kw):
    """Firing hand on the pistol grip, trigger finger straight along the receiver (R3-F03).
    CR-2: the hand's pose, the elbow swivel, the four metacarpals, the thumb's base and the compression of the four palm
    pads are searched together.  The search starts from a grid of orientations with the middle finger's knuckle pad on the
    right face of the grip under the trigger guard, and pulls the middle of the web toward its seat under the receiver's
    rear while that pad stays put, nothing is inside the rifle beyond what the pads give, and the wrist stays in range.
    Then three fingers wrap the front of the grip, the index finger is laid along the receiver and the thumb lies on the
    left side.  notes/NOTES.md says how far the web gets and why."""
    b = dict(mc4_flex=10, mc5_flex=16, mc2_flex=4, mc3_flex=3); seat = (WEB_SEAT[0], WEB_SEAT[1], WEB_SEAT[2] + forward)
    pad = (-16.0, GRIP_PADS['middle_mcp_palmar'][1], GRIP_PADS['middle_mcp_palmar'][2] + forward)      # the middle finger's knuckle pad: on the right face, hard under the trigger guard
    return dict(side='R', attach='socket_hand_right', q0=base_q(**b), q_open=q_open(thumb=(15, -20, 0, 20, 20), **b), swivel0=0.0,
                frame=dict(distal=(0, 0, 1), dorsal=(-1, 0, 0), wrist=(-40.0, -100.0, -240.0)),
                fit=dict(joints=PALM_JOINTS, groups=('base', 'thumb'), start=('middle_mcp_palmar', pad), yaws=(-10, -2, 6, 14), pitches=(-12, -4, 4, 12), rolls=(0, 8, 16, 24),
                         touch=dict(thenar=0.4, hypothenar=0.3, palm_distal=0.3, palm_centre=0.2), anchors={'web_mid': (seat, 1.0), 'middle_mcp_palmar': (pad, 0.8)}, polish=4, iters=3000),
                digits=dict(middle=CURL, ring=CURL, little=CURL,
                            index=('ik', 'index_tip', R3_INDEX_TIP, dict(prior=(5, -10, 8, 5))),
                            thumb=('ik', 'thumb_pad', (17.0, -52.0, -160.0), dict(w_touch=0.5))),
                touch=dict(web=1.0, thenar=0.4, middle_pad_mid=1.0, ring_pad_mid=1.0, little_pad_mid=0.8, middle_pad=1.0, ring_pad=1.0, little_pad=0.6, middle_pad_prox=0.6, ring_pad_prox=0.6))
def spec_fire(**kw):
    """Firing hand, pad of the index finger on the trigger face (R1-F06).  Same hand placement as fire_indexed."""
    s = spec_fire_indexed(); s['digits']['index'] = ('ik', 'index_pad', TRIGGER_FACE, dict(w_touch=1.0, prior=(30, 0, 55, 30)))
    s['start'] = 'fire_indexed'; s['only'] = ('index',); return s
def spec_fire_reach(**kw):
    """Firing hand slid 9 mm forward along the grip, trigger finger straight: the hold from which the fingertip reaches
    the magazine release (inferred: no reference shows the press; a hand of this size cannot reach the button from
    the firing grip without moving)."""
    s = spec_fire_indexed(forward=9.0); s['fit']['seed'] = 'fire_indexed'; s['fit']['seed_shift'] = (0.0, 0.0, 9.0); s['fit']['polish'] = 1; s['fit']['iters'] = 1500; return s
# CR-1: where R2 has the support hand's fingertips (checks/compare.py: read off the photograph, scaled by the 68.0 mm height of
# the handguard; y above the bore, z ahead of the receiver).  x is set on the handguard's right side and, for the thumb, left of the top rail.
R2_TIPS = dict(little_tip=(-17.0, 32.9, 56.0), ring_tip=(-14.0, 45.9, 72.9), middle_tip=(-14.0, 42.0, 98.9), index_tip=(-25.0, 14.2, 130.0), thumb_tip=(14.0, 62.0, 97.6))
def spec_support(**kw):
    """Support hand under the handguard, fingers up the right side, thumb over the top (R2-S01..S06)."""
    b = dict(mc4_flex=3, mc5_flex=8)      # (CR-2: letting the handguard bed into the palm's pads was tried and gave a worse fit to R2: mean 23.3 mm against 18.4; not used)
    # CR-2: the wrist is kept 6 degrees inside every limit (version 2: 1.5).  With 1.5 this hand came out 1 degree from both its
    # ulnar and its pronation limit, and the frames in which it leaves the handguard (charge) ran up to 3.7 degrees past them.
    return dict(side='L', attach='socket_hand_left', q0=base_q(**b), q_open=q_open(index=(8, 0, 8, 5), **b), swivel0=15.0, wrist_margin=6.0,
                H0=dict(dorsal=(0.20, -0.96, -0.18), distal=(-0.90, 0.05, 0.42), wrist=(72.0, -82.0, 50.0)),
                seat=(('hand', (0, 0, -1), 70.0),), seat_rounds=1,
                digits=dict(index=WRAP, middle=WRAP, ring=WRAP, little=WRAP,
                            thumb=('ik', 'thumb_tip', R2_TIPS['thumb_tip'], dict(prior=(10, 5, 0, 15, 10)))),
                anchors={k: (R2_TIPS[k], w) for k, w in (('middle_tip', 0.5), ('ring_tip', 0.5), ('little_tip', 0.4), ('index_tip', 0.4))},
                touch=dict(palm_distal=1.0, thenar=0.4, middle_pad=0.6, index_pad=0.5, ring_pad=0.5, little_pad=0.3, middle_pad_prox=0.5, ring_pad_prox=0.3, index_pad_prox=0.3))
def spec_mag_grip(**kw):
    """Support hand round the magazine body below the magazine well (R3-S01, R3-S02, R1-S01): palm on the left face,
    fingers round the front onto the right face, thumb closed on the left and rear.  Moves with the magazine."""
    b = dict(mc4_flex=3, mc5_flex=8)
    return dict(side='L', attach='mag_body', q0=base_q(**b), q_open=q_open(index=(8, 0, 8, 5), **b),
                place={'middle_mcp_palmar': (12.6, -125.0, -8.0), 'little_mcp_palmar': (12.6, -164.0, -17.0), 'web': (12.6, -100.0, -47.0)}, retreat=(1.0, 0.0, 0.0),
                digits=dict(index=WRAP, middle=WRAP, ring=WRAP, little=WRAP,
                            thumb=('ik', 'thumb_pad', (14.6, -72.0, -58.0), dict(w_touch=0.5, prior=(-8, 16, 0, 5, 5)))),
                touch=dict(middle_pad=1.0, index_pad=1.0, ring_pad=1.0, little_pad=0.6, middle_pad_mid=0.6, ring_pad_mid=0.6, index_pad_mid=0.6))
def spec_catch_ready(**kw):
    """Support hand against the left of the magazine and magazine well, fingers up and forward along the receiver,
    thumb up beside the bolt catch paddle (no reference: inferred)."""
    b = dict(mc4_flex=2, mc5_flex=4)
    return dict(side='L', attach='socket_hand_left', q0=base_q(**b), q_open=q_open(index=(8, 0, 8, 5), thumb=(-5, 15, 0, 5, 5), **b),
                frame=dict(dorsal=(1.0, 0.0, 0.0), distal=(0.0, 0.8, 0.6), wrist=(35.5, -119.0, -75.0)), retreat=(1.0, 0.0, 0.0), backoff_groups=('base', 'thumb'),
                digits=dict(index=WRAP, middle=WRAP, ring=WRAP, little=WRAP,
                            thumb=('ik', 'thumb_pad', (25.5, -9.0, -80.0), dict(prior=(-5, 12, 0, 5, 5)))),
                touch=dict(middle_pad=0.6, index_pad=0.6, ring_pad=0.6, palm_centre=0.5))
def spec_charge_grip(**kw):
    """Support hand at the charging handle: palm toward the shooter, index fingertip hooked in front of the handle's
    left wing and latch, the other fingers curled (no reference: inferred).  Moves with the handle."""
    q = base_q(mc4_flex=2, mc5_flex=4)
    for f in ('middle', 'ring', 'little'): q[DIGIT_IDX[f]] = (80, 0, 95, 55)
    q[DIGIT_IDX['thumb']] = (5, -5, 0, 20, 30)
    return dict(side='L', attach='charging_handle', q0=q, q_open=q,
                frame=dict(dorsal=(0.28, 0.05, 0.96), distal=(-0.70, 0.71, 0.0), wrist=(111.9, -89.2, -153.2)), retreat=(1.0, 0.0, 0.4),
                digits=dict(middle=('pose', (80, 0, 95, 55)), ring=('pose', (80, 0, 95, 55)), little=('pose', (80, 0, 95, 55)), thumb=('pose', (5, -5, 0, 20, 30)),
                            index=('ik', 'index_pad', (25.5, 23.0, -169.6), dict(w_touch=1.0, prior=(25, -5, 60, 45)))),
                touch=dict(index_pad=2.0))
SPECS = dict(fire_indexed=spec_fire_indexed, fire=spec_fire, fire_reach=spec_fire_reach, support=spec_support, mag_grip=spec_mag_grip, catch_ready=spec_catch_ready, charge_grip=spec_charge_grip)

def real_matrix(side, M): return hl.mirror_mats(M) if side == 'R' else M
RAW = os.path.join(HERE, 'refs-local', 'build', 'grips_raw.npz')
def load_raw(): return dict(np.load(RAW, allow_pickle=True)['g'].item()) if os.path.exists(RAW) else {}
if __name__ == '__main__':
    S = Solver(); sel = [a for a in sys.argv[1:] if not a.startswith('--')]; res = load_raw()
    kw = {k: float(next((a.split('=')[1] for a in sys.argv if a.startswith('--' + k + '=')), 'nan')) for k in ('pitch', 'drop', 'yaw')}; kw = {k: v for k, v in kw.items() if v == v}
    IT = int(next((a[8:] for a in sys.argv if a.startswith('--iters=')), 400))
    for name, fn in SPECS.items():
        if sel and not any(name == s or (s.endswith('*') and name.startswith(s[:-1])) for s in sel): continue
        print(name, flush=True); spec = fn(**kw); st = spec.get('state'); motion = S.r.motion(*st) if st else None
        if 'fit' in spec and 'seed' in spec['fit']: sd = res[spec['fit']['seed']]; spec['fit']['seed_pose'] = (sd['H'], sd['q'], sd['wrist']['swivel'])
        st0 = res.get(spec.get('start')); g = S.solve(spec, iters=IT, motion=motion, H_fixed=st0['H'] if st0 else None, q_fixed=st0['q'] if st0 else None); g.pop('S'); g['state'] = st; res[name] = g
        np.savez(RAW, g=np.array(res, dtype=object))

"""Solve the grips against the locally built HK416 (grips/grips.json is written by clips/make.py from these).

    python3 grips/solve.py            # all grips
    python3 grips/solve.py support    # only grips whose name starts with 'support'

Method (a grasp planner, not a hand-set pose):
  1. Place the hand.  Either (a) by contact correspondences: three or more pads of the palm are matched to named
     points on the rifle (read off the references and the rifle's geometry, notes/STUDIES.md) with a least-squares
     rigid fit, optionally pitched about a pivot until the wrist is inside its range, then backed off along a stated
     direction until nothing is inside the rifle; or (b) by an evolution-strategy search of the hand's pose in which
     each candidate is pushed against the rifle until it touches.
  2. Close the digits against the rifle's signed distance field: a wrapping finger searches its four joints for the
     pose whose three palmar pads are nearest the surface with nothing inside it; a digit with a job (trigger finger,
     thumb on a control) is placed on its target point by a search on its own joints.
  3. Choose the elbow swivel that keeps wrist, forearm and elbow inside their limits with the least wrist bend.
Joint angles never leave handlib.LIMITS (they are clipped to them).  A right hand is solved as the canonical left
hand in the x-mirrored world.  Everything is mm and degrees in the asset frame (+X left, +Y up, +Z muzzle)."""
import os, sys, json, math, time
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl
from rifle import Rifle

# ------------------------------------------------------------------ the shooter (I: squared-up standing stance behind the sights, stock collapsed)
SHOULDER = dict(R=np.array([-50.0, -62.0, -452.0]),     # I: right shoulder joint: 45 mm behind the buttpad face (z -404), 20 mm below its centre, 50 mm outboard
                L=np.array([298.0, -62.0, -359.0]))     # I: left shoulder, 360 mm from the right (A: biacromial 415.7 less the acromion overhang), torso bladed 15 deg
SWIVEL = (-10.0, 75.0)    # I: elbow swivel about the shoulder-wrist line, degrees outboard of straight down
def pole_of(phi): return np.array([math.sin(math.radians(phi)), -math.cos(math.radians(phi)), 0.0])    # canonical-left world: +x is outboard for both arms
MARGIN = 0.50             # mm kept between the glove and the rifle while solving
def A(i): return hl.ANGLES.index(i)
DIGIT_IDX = {f: [A(f + '_mcp_flex'), A(f + '_mcp_abd'), A(f + '_pip_flex'), A(f + '_dip_flex')] for f in hl.FING}
DIGIT_IDX['thumb'] = [A('thumb_cmc_flex'), A('thumb_cmc_abd'), A('thumb_cmc_rot'), A('thumb_mcp_flex'), A('thumb_ip_flex')]

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
            self.grp[g] = (np.c_[V, np.ones(len(V))], Wt)
        self.rng = np.random.default_rng(416); self.motion = None; self.mir = False; self.skip = ()
    # ---- geometry helpers (canonical-left world)
    def world(self, side, p): p = np.asarray(p, float); return p * [-1, 1, 1] if side == 'R' else p
    def skin(self, q, H): return self.h.skin_mats(self.h.fk(q, H))
    def pts(self, g, S): Vh, Wt = self.grp[g]; return np.einsum('vb,bij,vj->vi', Wt, S[:, :3, :], Vh)
    def sdf(self, P_, skip=None): return self.r.sdf(P_, motion=self.motion, mirror=self.mir, skip=self.skip if skip is None else skip)
    def pen(self, g, S, skip=None): return np.maximum(0.0, MARGIN - self.sdf(self.pts(g, S), skip)).sum()
    def lm(self, S, name): i = self.lmi[name]; return self.h.pose_points(self.h.lm_pos[i:i + 1], self.h.lm_bone[i:i + 1], S)[0]
    # ---- digits
    STARTS = ((8.0, 0.0, 8.0, 5.0), (45.0, 0.0, 60.0, 35.0), (70.0, 0.0, 92.0, 50.0), (20.0, 0.0, 85.0, 55.0))
    def wrap(self, f, q, H, iters=60, skip=None, w=(0.5, 1.0, 1.0)):
        """Close finger f round the rifle: a search on its four joints, from several starting curls, for the pose whose
        three palmar pads (proximal, middle, distal phalanx) are nearest the surface with nothing inside it.
        Returns q and whether the result is free of the rifle."""
        q = q.copy(); idx = np.array(DIGIT_IDX[f]); lo, hi = hl.LO[idx] + 0.5, hl.HI[idx] - 0.5; th = f == 'thumb'
        li = [self.lmi[f + s] for s in (('_pad_prox', '_pad') if th else ('_pad_prox', '_pad_mid', '_pad'))]; wv = np.array((0.6, 1.0) if th else w)
        def fun(a):
            c = q.copy(); c[idx] = a; S = self.skin(c, H); L = self.h.pose_points(self.h.lm_pos[li], self.h.lm_bone[li], S)
            return float(wv @ np.clip(self.sdf(L, skip), 0.0, 25.0)) + 25.0 * self.pen(f, S, skip) + (0.0 if th else 0.03 * abs(a[3] - 0.67 * a[2]) + 0.02 * abs(a[1]))
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
        v['wrist'] = sum(3.0 * max(0.0, hl.LIMITS[k][0] + 1.5 - ang[k], ang[k] - hl.LIMITS[k][1] + 1.5) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex')) \
            + 0.04 * (abs(ang['wrist_flex']) + abs(ang['wrist_dev'])) + (50.0 if ang['reach_over'] else 0.0)
        tot = sum(v.values())
        if detail: return tot, dict(q=q, H=H, F=F, S=S, terms={k: round(float(x), 2) for k, x in v.items()}, digits={k: round(float(x), 2) for k, x in dig.items()}, gaps={k: round(g, 2) for k, g in gaps.items()}, wrist=ang)
        return tot
    def best_swivel(self, side, H):
        best = None
        for sw in np.arange(SWIVEL[0], SWIVEL[1] + 0.1, 2.5):
            F, a = hl.forearm_and_wrist(H, self.world(side, SHOULDER[side]), pole_of(sw))
            viol = sum(max(0.0, hl.LIMITS[k][0] - a[k], a[k] - hl.LIMITS[k][1]) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'))
            key = (round(viol, 3), abs(a['wrist_flex']) + abs(a['wrist_dev']))
            if best is None or key < best[0]: a['swivel'] = float(sw); best = (key, F, a, viol)
        return best[1], best[2], best[3]
    def place(self, spec):
        """Rigid least-squares fit of palm landmarks to points on the rifle (Kabsch), optional pitch about a pivot, then back off until free."""
        side = spec['side']
        if 'frame' in spec:
            s = spec['frame']; H = hl.frame(self.world(side, s['wrist']), self.world(side, s['distal']), self.world(side, s['dorsal']))
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
        back = hl.unit(self.world(side, spec['retreat'])); q = spec['q_open']; moved = 0.0; free = lambda Hh: self.pen('base', self.skin(q, Hh)) == 0
        while not free(H) and moved < 40.0: H = H.copy(); H[:3, 3] += back * 0.5; moved += 0.5
        return H, fit, moved
    def solve(self, spec, motion=None, iters=500, x0=None, verbose=True, H_fixed=None):
        t0 = time.time(); self.motion = motion; self.mir = spec['side'] == 'R'; self.skip = tuple(spec.get('free', ())); self.rng = np.random.default_rng(416)
        q0 = spec['q0']; x = np.r_[np.zeros(6), spec.get('swivel0', 10.0)] if x0 is None else np.asarray(x0, float); extra = {}
        if H_fixed is not None: H = H_fixed
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
        tot, d = self.score(sp2, H, x[6], q0, fine=True, detail=True); d['x'] = x; d['side'] = spec['side']; d['attach'] = spec.get('attach'); d['score'] = float(tot); d.update(extra)
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
def q_open(index=(8, 4, 12, 8), thumb=(-5, -14, 0, 5, 5), **kw):
    q = base_q(**kw)
    for f in hl.FING: q[DIGIT_IDX[f]] = (8, 0, 8, 5)
    q[DIGIT_IDX['index']] = index; q[DIGIT_IDX['thumb']] = thumb; return q
def spec_fire_indexed(pitch=0.0, drop=8.0, yaw=10.0):
    """Firing hand on the pistol grip, trigger finger straight along the receiver (R3-F03).
    Placed by contact: the middle and little knuckle pads on the right side of the grip at its front edge, one under
    the trigger guard and one 40 mm down the grip; the web between thumb and index under the rear of the receiver."""
    b = dict(mc4_flex=4, mc5_flex=10)
    return dict(side='R', attach='socket_hand_right', q0=base_q(**b), q_open=q_open(thumb=(-8, -19, 0, 0, 5), **b),
                place={'middle_mcp_palmar': (-15.5, -93.0 - drop, -152.0 - 0.27 * drop), 'little_mcp_palmar': (-15.5, -133.0 - drop, -163.0 - 0.27 * drop), 'web': (-14.0, -62.0 - drop, -193.0 - 0.27 * drop)},
                pitch=(pitch, (0.0, -93.0 - drop, -165.0)), yaw=(yaw, (-15.5, -93.0 - drop, -152.0)), retreat=(-1.0, 0.0, -0.15),
                digits=dict(middle=WRAP, ring=WRAP, little=WRAP,
                            index=('ik', 'index_pad', (-15.4, -41.0, -93.0), dict(w_touch=0.5, prior=(8, 4, 12, 8))),
                            thumb=('ik', 'thumb_pad', (15.3, -62.0, -172.0), dict(w_touch=0.5, prior=(8, -5, 0, 20, 25)))),
                anchors={'middle_pad_mid': ((1.0, -91.0, -143.0), 1.0)},
                touch=dict(thenar=0.4, middle_pad_mid=1.0, ring_pad_mid=1.0, little_pad_mid=0.8, middle_pad=1.0, ring_pad=1.0, little_pad=0.6, middle_pad_prox=0.6, ring_pad_prox=0.6))
def spec_fire(**kw):
    """Firing hand, pad of the index finger on the trigger face (R1-F06).  Same hand placement as fire_indexed."""
    s = spec_fire_indexed(); s['digits']['index'] = ('ik', 'index_pad', (-1.5, -58.0, -105.4), dict(w_touch=1.0, prior=(30, 0, 55, 30)))
    s['start'] = 'fire_indexed'; return s
def spec_support(**kw):
    """Support hand under the handguard, fingers up the right side, thumb over the top (R2-S01..S06)."""
    b = dict(mc4_flex=3, mc5_flex=8)
    return dict(side='L', attach='socket_hand_left', q0=base_q(**b), q_open=q_open(index=(8, 0, 8, 5), **b), swivel0=15.0,
                H0=dict(dorsal=(0.20, -0.96, -0.18), distal=(-0.90, 0.05, 0.42), wrist=(72.0, -82.0, 78.0)),
                seat=(('hand', (0, 0, -1), 70.0),), seat_rounds=1,
                digits=dict(index=WRAP, middle=WRAP, ring=WRAP, little=WRAP,
                            thumb=('ik', 'thumb_pad', (12.0, 37.2, 150.0), dict(w_touch=0.5, prior=(10, 5, 0, 25, 30)))),
                anchors={'palm_distal': ((-4.0, -32.0, 100.0), 0.8)},
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
SPECS = dict(fire_indexed=spec_fire_indexed, fire=spec_fire, support=spec_support, mag_grip=spec_mag_grip, catch_ready=spec_catch_ready, charge_grip=spec_charge_grip)

def real_matrix(side, M): return hl.mirror_mats(M) if side == 'R' else M
RAW = os.path.join(HERE, 'refs-local', 'build', 'grips_raw.npz')
def load_raw(): return dict(np.load(RAW, allow_pickle=True)['g'].item()) if os.path.exists(RAW) else {}
if __name__ == '__main__':
    S = Solver(); sel = [a for a in sys.argv[1:] if not a.startswith('--')]; res = load_raw()
    kw = {k: float(next((a.split('=')[1] for a in sys.argv if a.startswith('--' + k + '=')), 'nan')) for k in ('pitch', 'drop', 'yaw')}; kw = {k: v for k, v in kw.items() if v == v}
    IT = int(next((a[8:] for a in sys.argv if a.startswith('--iters=')), 400))
    for name, fn in SPECS.items():
        if sel and not any(name.startswith(s) for s in sel): continue
        print(name, flush=True); spec = fn(**kw); st = spec.get('state'); motion = S.r.motion(*st) if st else None
        g = S.solve(spec, iters=IT, motion=motion, H_fixed=res[spec['start']]['H'] if spec.get('start') in res else None); g.pop('S'); g['state'] = st; res[name] = g
        np.savez(RAW, g=np.array(res, dtype=object))

"""Solve the grips against the locally built HK416 (grips/grips.json is written by clips/make.py from these).

    python3 grips/solve.py            # all grips
    python3 grips/solve.py support    # only grips whose name starts with 'support'

Method (a grasp planner, not a hand-set pose):
  1. The hand's orientation and approach offset (6 numbers) and the elbow swivel (1) are searched with an evolution
     strategy.  Each candidate hand is first seated: with the digits open it is pushed along the spec's directions
     until it touches (up under the receiver, forward into the backstrap, palm onto the grip; or up under the handguard).
  2. For each seated candidate the digits are closed against the rifle's signed distance field: wrapping fingers sweep
     shut joint by joint until they touch (MCP + PIP + DIP together, then PIP + DIP, then DIP); a digit with a job
     (trigger finger, thumb on a control) is placed by a small inverse-kinematics search on its own joints.
  3. The candidate is scored: nothing inside the rifle, named pads touching, a few landmarks on named features of the
     rifle (read off the references, notes/STUDIES.md), wrist and elbow inside their limits.
Joint angles never leave handlib.LIMITS (they are clipped to them).  A right hand is solved as the canonical left
hand in the x-mirrored world.  Everything is mm and degrees in the asset frame (+X left, +Y up, +Z muzzle)."""
import os, sys, json, math, time
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl
from rifle import Rifle

# ------------------------------------------------------------------ the shooter (I: squared-up standing stance behind the sights, stock collapsed)
SHOULDER = dict(R=np.array([-50.0, -62.0, -452.0]),     # I: right shoulder joint: 45 mm behind the buttpad face (z -404), 20 mm below its centre, 50 mm outboard
                L=np.array([276.0, -62.0, -300.0]))     # I: left shoulder, 360 mm from the right (A: biacromial 415.7 less the acromion overhang), torso bladed 25 deg
SWIVEL = (-10.0, 75.0)    # I: elbow swivel about the shoulder-wrist line, degrees outboard of straight down
def pole_of(phi): return np.array([math.sin(math.radians(phi)), -math.cos(math.radians(phi)), 0.0])    # canonical-left world: +x is outboard for both arms
MARGIN = 0.30             # mm kept between the glove and the rifle while solving
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
        for g, shells, stride in (('base', ('palm', 'web', 'cuff'), 2), ('thumb', ('thumb',), 2)) + tuple((f, ('finger_' + f,), 2) for f in hl.FING):
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
    def wrap(self, f, q, H, iters=60, skip=None, start=(8.0, 0.0, 8.0, 5.0), w=(0.5, 1.0, 1.0)):
        """Close finger f round the rifle: a search on its four joints for the pose whose three palmar pads (proximal,
        middle, distal phalanx) are nearest the surface with nothing inside it.  Returns q and whether the open finger was free."""
        q = q.copy(); idx = np.array(DIGIT_IDX[f]); lo, hi = hl.LO[idx] + 0.5, hl.HI[idx] - 0.5; q[idx] = start
        if self.pen(f, self.skin(q, H), skip) > 0: return q, False
        li = [self.lmi[f + s] for s in ('_pad_prox', '_pad_mid', '_pad')]; wv = np.array(w)
        def fun(a):
            c = q.copy(); c[idx] = a; S = self.skin(c, H); L = self.h.pose_points(self.h.lm_pos[li], self.h.lm_bone[li], S)
            return float(wv @ np.clip(self.sdf(L, skip), 0.0, 25.0)) + 25.0 * self.pen(f, S, skip) + 0.03 * abs(a[3] - 0.67 * a[2]) + 0.02 * abs(a[1])
        a, fa = es_min(fun, q[idx], np.array([12.0, 3.0, 12.0, 8.0]), lo, hi, iters, np.random.default_rng(7)); q[idx] = a
        return q, True
    def ik(self, d, q, H, landmark, target, iters=220, w_touch=0.0, prior=None, skip=None, extra=None):
        """Place a digit's landmark on a target point without entering the rifle, by a search on that digit's own joints."""
        idx = np.array(DIGIT_IDX[d]); lo, hi = hl.LO[idx] + 0.5, hl.HI[idx] - 0.5; q = q.copy(); p0 = q[idx] if prior is None else np.asarray(prior, float)
        def fun(a):
            c = q.copy(); c[idx] = a; S = self.skin(c, H); L = self.lm(S, landmark); e = np.linalg.norm(L - target)
            v = e + 25.0 * self.pen(d, S, skip) + 0.01 * np.abs(a - p0).sum()
            if w_touch: v += w_touch * abs(float(self.sdf(L[None], skip)[0]))
            if d != 'thumb': v += 0.03 * abs(a[3] - 0.67 * a[2])
            if extra: v += extra(S)
            return v
        a, fa = es_min(fun, np.clip(p0, lo, hi), np.full(len(idx), 6.0), lo, hi, iters, np.random.default_rng(11)); q[idx] = a
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
                q, free = self.wrap(d, q, H, iters=260 if fine else 50, **(job[1] if len(job) > 1 else {})); out[d] = 0.0 if free else 30.0
            elif job[0] == 'ik':
                kw = dict(job[3]) if len(job) > 3 else {}
                if do_ik: q, e = self.ik(d, q, H, job[1], self.world(side, job[2]), iters=320, **kw); out[d] = e
                else: q[DIGIT_IDX[d]] = spec['q_open'][DIGIT_IDX[d]]; out[d] = 0.0
            elif job[0] == 'pose': q[DIGIT_IDX[d]] = job[1]; out[d] = 0.0
        return q, out
    # ---- a whole grip
    def frame0(self, spec):
        s = spec['H0']; return hl.frame(self.world(spec['side'], s['wrist']), self.world(spec['side'], s['distal']), self.world(spec['side'], s['dorsal']))
    def score(self, spec, H, swivel, q0, fine=False, detail=False):
        side = spec['side']; v = {}; H, free = self.seat(spec, H, fine); v['start'] = 0.0 if free else 500.0 + 30.0 * self.pen_all(spec['q_open'], H)
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
    def solve(self, spec, motion=None, iters=500, x0=None, verbose=True, H_fixed=None):
        t0 = time.time(); self.motion = motion; self.mir = spec['side'] == 'R'; self.skip = tuple(spec.get('free', ())); self.rng = np.random.default_rng(416)
        H0 = self.frame0(spec); q0 = spec['q0']
        def Hx(x): Hh = H0 @ hl.M4(hl.rotvec(np.radians(x[3:6]))); Hh[:3, 3] += x[:3]; return Hh
        lo = np.r_[[-40.0] * 3, [-50.0] * 3, SWIVEL[0]]; hi = np.r_[[40.0] * 3, [50.0] * 3, SWIVEL[1]]
        x = np.r_[np.zeros(6), spec.get('swivel0', 10.0)] if x0 is None else np.asarray(x0, float)
        if not spec.get('fixed_root') and iters > 0:
            x, fx = es_min(lambda u: self.score(spec, Hx(u), u[6], q0), x, np.r_[np.array(spec.get('sigma_t', [4.0] * 3)), [5.0] * 3, 8.0], lo, hi, iters, self.rng)
            if verbose: print('   search', round(fx, 1), round(time.time() - t0, 1), 's', flush=True)
        tot, d = self.score(spec, Hx(x) if H_fixed is None else H_fixed, x[6], q0, fine=True, detail=True); d['x'] = x; d['side'] = spec['side']; d['attach'] = spec.get('attach'); d['score'] = float(tot)
        mins = {g: float(self.sdf(self.pts(g, d['S'])).min()) for g in self.grp}; d['min_sdf'] = min(mins.values()); d['seconds'] = round(time.time() - t0, 1)
        if verbose: print(f"  score {tot:.1f} {d['terms']}  min sdf {d['min_sdf']:.2f}  wrist {d['wrist']['wrist_flex']:.0f}/{d['wrist']['wrist_dev']:.0f} pron {d['wrist']['pronation']:.0f} elbow {d['wrist']['elbow_flex']:.0f} swivel {x[6]:.0f}  {d['seconds']} s\n   digits {d['digits']}\n   gaps {d['gaps']}", flush=True)
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
def spec_fire_indexed():
    """Firing hand on the pistol grip, trigger finger straight along the receiver (R3-F03)."""
    b = dict(mc4_flex=4, mc5_flex=10)
    return dict(side='R', attach='socket_hand_right', q0=base_q(**b), q_open=q_open(thumb=(-8, -19, 0, 0, 5), **b),
                H0=dict(dorsal=(-0.90, 0.25, -0.35), distal=(-0.10, 0.57, 0.82), wrist=(-64.0, -145.0, -257.0)),
                seat=(('world', (0, 0, 1), 60.0), ('hand', (0, 0, -1), 60.0), ('world', (0, 1, 0), 70.0)), seat_rounds=3,
                digits=dict(middle=WRAP, ring=WRAP, little=WRAP,
                            index=('ik', 'index_pad', (-15.4, -41.0, -93.0), dict(w_touch=0.5, prior=(8, 4, 12, 8))),
                            thumb=('ik', 'thumb_pad', (15.3, -64.0, -160.0), dict(w_touch=0.5, prior=(8, -5, 0, 20, 25)))),
                anchors={'web': ((0.0, -56.0, -184.0), 0.3)},
                touch=dict(thenar=0.4, middle_pad_mid=1.0, ring_pad_mid=1.0, little_pad_mid=0.8, middle_pad=1.0, ring_pad=1.0, little_pad=0.6, middle_pad_prox=0.6, ring_pad_prox=0.6))
def spec_fire():
    """Firing hand, pad of the index finger on the trigger face (R1-F06)."""
    s = spec_fire_indexed(); s['digits']['index'] = ('ik', 'index_pad', (0.3, -58.0, -105.2), dict(w_touch=0.5, prior=(30, 0, 55, 30)))
    s['start'] = 'fire_indexed'; s['fixed_root'] = True; s['seat'] = (); return s
def spec_support():
    """Support hand under the handguard, fingers up the right side, thumb over the top (R2-S01..S06)."""
    b = dict(mc4_flex=3, mc5_flex=8)
    return dict(side='L', attach='socket_hand_left', q0=base_q(**b), q_open=q_open(index=(8, 0, 8, 5), **b), swivel0=15.0,
                H0=dict(dorsal=(0.20, -0.96, -0.18), distal=(-0.90, 0.05, 0.42), wrist=(72.0, -82.0, 78.0)),
                seat=(('hand', (0, 0, -1), 70.0),), seat_rounds=1,
                digits=dict(index=WRAP, middle=WRAP, ring=WRAP, little=WRAP,
                            thumb=('ik', 'thumb_pad', (12.0, 37.2, 150.0), dict(w_touch=0.5, prior=(10, 5, 0, 25, 30)))),
                anchors={'palm_distal': ((-4.0, -32.0, 112.0), 0.8)},
                touch=dict(palm_distal=1.0, thenar=0.4, middle_pad=0.6, index_pad=0.5, ring_pad=0.5, little_pad=0.3, middle_pad_prox=0.5, ring_pad_prox=0.3, index_pad_prox=0.3))
SPECS = dict(fire_indexed=spec_fire_indexed, fire=spec_fire, support=spec_support)

def real_matrix(side, M): return hl.mirror_mats(M) if side == 'R' else M
RAW = os.path.join(HERE, 'refs-local', 'build', 'grips_raw.npz')
def load_raw(): return dict(np.load(RAW, allow_pickle=True)['g'].item()) if os.path.exists(RAW) else {}
if __name__ == '__main__':
    S = Solver(); sel = [a for a in sys.argv[1:] if not a.startswith('--')]; res = load_raw(); IT = int(next((a[8:] for a in sys.argv if a.startswith('--iters=')), 500))
    for name, fn in SPECS.items():
        if sel and not any(name.startswith(s) for s in sel): continue
        print(name, flush=True); spec = fn(); x0 = res[spec['start']]['x'] if spec.get('start') in res else None
        g = S.solve(spec, x0=x0, iters=IT, H_fixed=res[spec['start']]['H'] if spec.get('start') in res else None); g.pop('S'); res[name] = g
        np.savez(RAW, g=np.array(res, dtype=object))

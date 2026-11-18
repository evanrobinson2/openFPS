"""Scratch: trace the seating moves of a grip spec (which part touches first).  python3 tools/trace_seat.py fire_indexed"""
import sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'grips')); sys.path.insert(0, os.path.join(HERE, 'model'))
import numpy as np, solve, handlib as hl
S = solve.Solver(); spec = solve.SPECS[sys.argv[1]](); side = spec['side']; S.mir = side == 'R'; m = [-1, 1, 1] if S.mir else [1, 1, 1]
H = S.frame0(spec); q = spec['q_open']
def report(tag, H):
    Sk = S.skin(q, H); out = {}
    for g in S.grp:
        P = S.pts(g, Sk); d = S.sdf(P); i = d.argmin(); out[g] = (round(float(d.min()), 1), np.round(P[i] * m, 0).tolist())
    print(tag, 'wrist', np.round(H[:3, 3] * m, 1), out)
report('start', H)
for rnd in range(spec.get('seat_rounds', 2)):
    for kind, d, dmax in spec['seat']:
        dd = hl.unit(S.world(side, d)) if kind == 'world' else H[:3, :3] @ hl.unit(d); step = 4.0; moved = 0
        while step > 0.2 and moved < dmax:
            T = H.copy(); T[:3, 3] += dd * step
            if S.pen_all(q, T) > 0: step *= 0.5
            else: H = T; moved += step
        report(f'r{rnd} {kind}{d} moved {moved:.1f}', H)
q2, dig = S.close(spec, H, spec['q0'], fine=True, do_ik=True); print('digits', dig)
F, ang = hl.forearm_and_wrist(H, S.world(side, solve.SHOULDER[side]), solve.pole_of(spec.get('swivel0', 10.0))); print({k: round(v, 1) for k, v in ang.items()})
res = solve.load_raw(); res['dbg'] = dict(side=side, q=q2, H=H, F=F); res['dbg_open'] = dict(side=side, q=q, H=H, F=F); np.savez(solve.RAW, g=np.array(res, dtype=object))

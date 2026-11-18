"""Build the hand clips that go with the rifle's clips, and write the runtime data.

    python3 clips/make.py

Inputs: the solved grips (refs-local/build/grips_raw.npz, from grips/solve.py) and the locally built rifle.
Outputs: grips/grips.json (the grips, for people), hands-gloved.json (skeleton, limits, grips and clips for the
runtime module) and refs-local/build/frames.npz (every frame's pose, for the checks).

A hand clip runs at the rifle's 24 frames per second.  It may start `pre_roll` frames before its rifle clip and run
on after it (`post_roll`): hand frame f plays with rifle frame f - pre_roll, the rifle holding its first frame before
that and its last frame after.  Within a clip a hand is either held in a grip, blended between grips through
backed-off waypoints, carried by a moving part of the rifle (magazine, charging handle), or has one digit placed
frame by frame on a moving control (trigger, magazine release, selector, bolt catch) by the same inverse-kinematics
search the grips use.  Angles are interpolated between poses that are inside the joint limits, so they stay inside."""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model')); sys.path.insert(0, os.path.join(HERE, 'grips'))
import handlib as hl, solve
from solve import DIGIT_IDX, A
S = solve.Solver(); R = S.r; G = solve.load_raw(); FPS = R.meta['fps']
MIR = hl.MIRROR
def real(side, M): return hl.mirror_mats(M) if side == 'R' else M
def canon(side, M): return hl.mirror_mats(M) if side == 'R' else M
def ease(u): return float(hl.smooth(u))
def slerp(Ra, Rb, u):
    return Ra @ hl.rotvec(hl.to_rotvec(Ra.T @ Rb) * u)
def mix(Ha, Hb, u):
    H = np.eye(4); H[:3, :3] = slerp(Ha[:3, :3], Hb[:3, :3], u); H[:3, 3] = Ha[:3, 3] * (1 - u) + Hb[:3, 3] * u; return H
def motion(clip, r): return R.motion(clip, float(r)) if clip else {}
def mover_mat(clip, r, mover):
    return motion(clip, r).get(mover, np.eye(4)) if mover in R.movers else np.eye(4)

# ------------------------------------------------------------------ poses: q (deg), H (real asset frame), carried-by
class Pose:
    def __init__(self, side, q, H_real, carrier='static', state=None):
        self.side = side; self.q = np.array(q, float); self.carrier = carrier
        M0 = mover_mat(state[0], state[1], carrier) if state else np.eye(4)
        self.Hrel = np.linalg.inv(M0) @ H_real                      # hand in the carrier's rest frame
    def H(self, clip=None, r=1): return mover_mat(clip, r, self.carrier) @ self.Hrel
def from_grip(name, carrier=None):
    g = G[name]; c = carrier or (g['attach'] if g.get('attach') in R.movers else 'static')
    return Pose(g['side'], g['q'], real(g['side'], g['H']), c, g.get('state'))
def opened(p, back, amount=0.45, clip=None, r=1):
    """A waypoint: the same pose backed off along `back` (mm, real frame) with the fingers and thumb part-opened."""
    q = p.q.copy()
    for d, idx in DIGIT_IDX.items():
        if d == 'thumb': q[idx[3:]] *= amount; q[idx[1]] = q[idx[1]] * amount - 8 * (1 - amount)
        else: q[[idx[0], idx[2], idx[3]]] *= amount
    H = p.H(clip, r).copy(); H[:3, 3] += np.asarray(back, float); return Pose(p.side, q, H, 'static')
P = {k: from_grip(k) for k in ('fire_indexed', 'fire', 'support', 'mag_grip', 'catch_ready', 'charge_grip')}
BACK = dict(support=(0, -32, 0), mag_grip=(34, -4, 0), catch_ready=(30, 0, 0), charge_grip=(26, 8, 10))

# ------------------------------------------------------------------ digit targets on moving controls (rest position, real frame)
CONTROL = dict(trigger=('trigger', (-1.5, -58.0, -105.4)), mag_button=('mag_release_button', (-16.3, -39.0, -86.5)),
               selector=('selector_lever_l', (15.6, -34.6, -157.0)), paddle=('bolt_catch', (19.8, -9.0, -80.0)))
def control_point(name, clip, r):
    mover, p = CONTROL[name]; M = mover_mat(clip, r, mover); return M[:3, :3] @ np.array(p) + M[:3, 3]
def place_digit(side, digit, q, H_real, landmark, target, clip, r, prior=None, touch=0.6, iters=260):
    S.motion = motion(clip, r) or None; S.mir = side == 'R'; S.skip = ()
    q2, err = S.ik(digit, q, canon(side, H_real), landmark, S.world(side, target), iters=iters, w_touch=touch, prior=prior if prior is not None else q[DIGIT_IDX[digit]])
    S.motion = None; return q2, err

# ------------------------------------------------------------------ clips
class Clip:
    def __init__(self, name, rifle_clip, pre=0, post=0, note=''):
        self.name = name; self.rifle = rifle_clip; self.pre = pre; self.post = post; self.note = note
        self.n_rifle = R.meta['clips'][rifle_clip]['frames'] if rifle_clip else 0; self.n = pre + self.n_rifle + post; self.fr = {s: [None] * self.n for s in 'RL'}; self.err = {}
    def r(self, f): return f - self.pre + 1 if self.rifle else 1            # rifle frame (1-based, may run outside 1..n and is clamped when sampled)
    def rc(self, f): return min(max(self.r(f), 1), max(self.n_rifle, 1))
    def set(self, side, f, q, H): self.fr[side][f] = (np.array(q, float), np.array(H, float))
    def hold(self, side, pose, f0=0, f1=None):
        for f in range(f0, self.n if f1 is None else f1): self.set(side, f, pose.q, pose.H(self.rifle, self.rc(f)))
    def move(self, side, pa, pb, f0, f1):
        """Blend from pose pa at frame f0 to pose pb at frame f1 (both evaluated on their carriers at each frame)."""
        for f in range(f0, f1 + 1):
            u = ease((f - f0) / max(f1 - f0, 1)); self.set(side, f, pa.q * (1 - u) + pb.q * u, mix(pa.H(self.rifle, self.rc(f)), pb.H(self.rifle, self.rc(f)), u))
    def via(self, side, pa, pb, f0, f1, back_a, back_b, n_a=3, n_b=3):
        """pa -> backed-off pa -> backed-off pb -> pb."""
        oa = opened(pa, back_a, clip=self.rifle, r=self.rc(f0)); ob = opened(pb, back_b, clip=self.rifle, r=self.rc(f1))
        self.move(side, pa, oa, f0, f0 + n_a); self.move(side, oa, ob, f0 + n_a, f1 - n_b); self.move(side, ob, pb, f1 - n_b, f1)
    def digit(self, side, digit, landmark, target_fn, f0, f1, touch=0.6):
        """Re-place one digit on target_fn(f) for frames f0..f1, keeping the rest of the frame."""
        prior = None
        for f in range(f0, f1 + 1):
            q, H = self.fr[side][f]; q2, e = place_digit(side, digit, q, H, landmark, target_fn(f), self.rifle, self.rc(f), prior=prior, touch=touch)
            prior = q2[DIGIT_IDX[digit]]; self.set(side, f, q2, H); self.err[(side, digit, f)] = e
    def blend_digit(self, side, digit, f0, f1, toward_end=True):
        """Ease one digit's joints between whatever frames f0 and f1 hold."""
        idx = DIGIT_IDX[digit]; a = self.fr[side][f0][0][idx].copy(); b = self.fr[side][f1][0][idx].copy()
        for f in range(f0, f1 + 1):
            u = ease((f - f0) / max(f1 - f0, 1)); q, H = self.fr[side][f]; q = q.copy(); q[idx] = a * (1 - u) + b * u; self.set(side, f, q, H)
def lerp_pt(a, b, u): return np.asarray(a, float) * (1 - u) + np.asarray(b, float) * u

def build():
    C = {}
    fi, fire, sup = P['fire_indexed'], P['fire'], P['support']
    # idle
    c = Clip('idle', None, post=1, note='Both hands at rest on the rifle: firing hand with the trigger finger straight, support hand under the handguard.'); c.hold('R', fi); c.hold('L', sup); C[c.name] = c
    # finger to / off the trigger: the pad travels round the outside of the trigger guard, then in
    pad_i = S.lm(S.skin(fi.q, canon('R', fi.H())), 'index_pad') * [-1, 1, 1]; pad_t = np.array(CONTROL['trigger'][1]); mid = np.array([-13.0, -57.0, -99.0])
    def path(u): return lerp_pt(pad_i, mid, u / 0.55) if u < 0.55 else lerp_pt(mid, pad_t, (u - 0.55) / 0.45)
    n = 6
    c = Clip('finger_to_trigger', None, post=n, note='Trigger finger from straight along the receiver onto the trigger. No rifle clip.'); c.hold('R', fi); c.hold('L', sup)
    c.digit('R', 'index', 'index_pad', lambda f: path(ease(f / (n - 1))), 1, n - 1, touch=0.0); c.set('R', n - 1, fire.q, fire.H()); C[c.name] = c
    c2 = Clip('finger_off_trigger', None, post=n, note='Trigger finger back to straight. No rifle clip.'); c2.hold('L', sup)
    for f in range(n): c2.set('R', f, *c.fr['R'][n - 1 - f])
    C[c2.name] = c2
    # trigger pull: the pad stays on the trigger face
    c = Clip('trigger_pull', 'trigger_pull', note='Starts and ends with the finger on the trigger (grip fire).'); c.hold('R', fire); c.hold('L', sup)
    c.digit('R', 'index', 'index_pad', lambda f: control_point('trigger', 'trigger_pull', c.rc(f)), 0, c.n - 1); C[c.name] = c
    # magazine release: the straight finger presses the button
    def press_release(c, f_touch, f_last, f_back):
        c.digit('R', 'index', 'index_tip', lambda f: control_point('mag_button', c.rifle, c.rc(f)) + (np.array([-2.5, 0, 0]) if f < f_touch else 0), f_touch - 1, f_last)
        c.blend_digit('R', 'index', 0, f_touch - 1); c.blend_digit('R', 'index', f_last, f_back)
    c = Clip('mag_release', 'mag_release', pre=3, post=3, note='Trigger finger presses the magazine release and returns.'); c.hold('R', fi); c.hold('L', sup); press_release(c, 3, 12, 15); C[c.name] = c
    # selector: the thumb rides the left lever
    for nm in ('safety_to_fire', 'safety_to_safe'):
        c = Clip(nm, nm, pre=4, post=4, note='Firing thumb goes up to the selector lever on the left side as the lever turns. With this hand and this grip the thumb tip stops short of the lever (see notes/NOTES.md, limits).'); c.hold('R', fi); c.hold('L', sup)
        mid = 4 + c.n_rifle // 2; q2, e = place_digit('R', 'thumb', fi.q, fi.H(), 'thumb_tip', control_point('selector', nm, c.rc(mid)), nm, c.rc(mid), touch=0.0, iters=400)
        for f in range(4, 4 + c.n_rifle): c.set('R', f, q2, fi.H())
        c.blend_digit('R', 'thumb', 0, 4); c.blend_digit('R', 'thumb', 4 + c.n_rifle - 1, c.n - 1); c.err[('R', 'thumb', mid)] = e; C[c.name] = c
    # bolt catch: support hand to the magazine well, thumb on the paddle
    c = Clip('bolt_catch', 'bolt_catch', pre=12, post=12, note='Support hand comes back to the magazine well, its thumb presses the bolt catch paddle, and it returns to the handguard.'); c.hold('R', fi)
    cr = P['catch_ready']; c.via('L', sup, cr, 0, 12, BACK['support'], BACK['catch_ready']); c.hold('L', cr, 12, 12 + c.n_rifle)
    c.via('L', cr, sup, 12 + c.n_rifle - 1, c.n - 1, BACK['catch_ready'], BACK['support'])
    c.digit('L', 'thumb', 'thumb_pad', lambda f: control_point('paddle', 'bolt_catch', c.rc(f)), 12, 22); c.blend_digit('L', 'thumb', 9, 12); c.blend_digit('L', 'thumb', 22, 25); C[c.name] = c
    # magazine out: finger on the release, support hand takes the magazine and goes with it
    mg = P['mag_grip']
    c = Clip('mag_out', 'mag_out', pre=12, note='Trigger finger holds the release; the support hand takes the magazine and draws it out. Ends holding the magazine below the rifle.'); c.hold('R', fi)
    c.via('L', sup, mg, 0, 13, BACK['support'], BACK['mag_grip']); c.hold('L', mg, 13); press_release(c, 12, 12 + 17, 12 + 21); C[c.name] = c
    # magazine in: the hand brings the magazine up, seats it and returns to the handguard
    c = Clip('mag_in', 'mag_in', post=13, note='Starts holding the magazine below the rifle (where mag_out ends); seats it and returns to the handguard.'); c.hold('R', fi)
    c.hold('L', mg, 0, c.n_rifle); c.via('L', mg, sup, c.n_rifle - 1, c.n - 1, BACK['mag_grip'], BACK['support']); C[c.name] = c
    # charge: index finger hooks the charging handle, rides it back, lets it go
    cg = P['charge_grip']
    c = Clip('charge', 'charge', pre=13, post=6, note='Support hand hooks the charging handle with the index finger, draws it back 75 mm, lets it fly forward and returns to the handguard.'); c.hold('R', fi)
    c.via('L', sup, cg, 0, 13, BACK['support'], BACK['charge_grip'], n_a=3, n_b=3); c.hold('L', cg, 13, 13 + 14)
    rel = opened(cg, BACK['charge_grip'], clip='charge', r=14); c.move('L', cg, rel, 13 + 13, 13 + 16)
    c.via('L', rel, sup, 13 + 16, c.n - 1, (0, 0, 0), BACK['support'], n_a=1, n_b=3); C[c.name] = c
    # dust cover: nothing to do with the hands
    c = Clip('dust_cover_open', 'dust_cover_open', note='The cover springs open by itself; the hands hold their grips.'); c.hold('R', fi); c.hold('L', sup); C[c.name] = c
    return C

# ------------------------------------------------------------------ keep every frame clear of the rifle
ESCAPE = dict(L=hl.unit([0.85, -0.5, 0.15]), R=hl.unit([-0.85, -0.5, -0.15]))        # I: a hand in the way of the rifle moves outboard and down
def sanitize(C):
    """In-between frames can cut through the rifle.  For each frame: if the palm is inside the rifle (signed distance
    field, 0.5 mm margin) the hand is moved along ESCAPE until it is not; the move is smoothed over neighbouring frames;
    then any digit still inside is opened until it is clear.  Returns the largest move per clip (mm)."""
    moved = {}
    for name, c in C.items():
        moved[name] = 0.0
        for s in 'RL':
            esc = ESCAPE[s]; d = np.zeros(c.n)
            def state(f): S.motion = motion(c.rifle, c.rc(f)) or None; S.mir = s == 'R'; S.skip = ()
            def ok(f, q, H):
                Sk = S.skin(q, canon(s, H))
                if S.pen('base', Sk) > 0: return None
                q2 = q
                for dg in DIGIT_IDX:
                    q2, free = S.clear(dg, q2, canon(s, H))
                    if not free: return None
                return q2
            for f in range(c.n):
                q, H = c.fr[s][f]; state(f)
                while d[f] < 120.0:
                    Ht = H.copy(); Ht[:3, 3] += esc * d[f]
                    if ok(f, q, Ht) is not None: break
                    d[f] += 1.5
            if d.max() > 0:              # spread each move over its neighbours so the hand does not twitch
                m = np.array([d[max(0, f - 2):f + 3].max() for f in range(c.n)]); d = np.maximum(d, np.convolve(np.r_[m[0], m[0], m, m[-1], m[-1]], np.ones(5) / 5, 'valid'))
            for f in range(c.n):
                q, H = c.fr[s][f]; state(f); Ht = H.copy(); Ht[:3, 3] += esc * d[f]; q2 = ok(f, q, Ht); k = 0
                while q2 is None and k < 60: Ht[:3, 3] += esc * 1.5; q2 = ok(f, q, Ht); k += 1
                c.set(s, f, q if q2 is None else q2, Ht); moved[name] = max(moved[name], float(np.linalg.norm(Ht[:3, 3] - H[:3, 3])))
            S.motion = None
    return moved

# ------------------------------------------------------------------ evaluation of every frame: forearm, wrist angles, approximate clearance
def evaluate(C):
    out = {}
    for name, c in C.items():
        frames = []; sw_prev = {s: None for s in 'RL'}
        for f in range(c.n):
            fr = dict(rifle_frame=c.rc(f) if c.rifle else None)
            for s in 'RL':
                q, H = c.fr[s][f]; Hc = canon(s, H); best = None
                for sw in np.arange(solve.SWIVEL[0], solve.SWIVEL[1] + 0.1, 2.5):
                    F, a = hl.forearm_and_wrist(Hc, S.world(s, solve.SHOULDER[s]), solve.pole_of(sw))
                    viol = sum(max(0.0, hl.LIMITS[k][0] - a[k], a[k] - hl.LIMITS[k][1]) for k in ('wrist_flex', 'wrist_dev', 'pronation', 'elbow_flex'))
                    key = (round(viol, 2), abs(sw - sw_prev[s]) if sw_prev[s] is not None else abs(a['wrist_flex']) + abs(a['wrist_dev']))
                    if best is None or key < best[0]: best = (key, F, dict(a, swivel=float(sw)))
                sw_prev[s] = best[2]['swivel']
                S.motion = motion(c.rifle, c.rc(f)) or None; S.mir = s == 'R'; S.skip = (); Sk = S.skin(q, Hc); d = min(float(S.sdf(S.pts(g, Sk)).min()) for g in S.grp); S.motion = None
                fr[s] = dict(q=q, H=H, F=real(s, best[1]), arm=best[2], sdf=d)
            frames.append(fr)
        out[name] = frames
    return out

def quat(Rm):
    t = np.trace(Rm)
    if t > 0: s = math.sqrt(t + 1) * 2; q = [(Rm[2, 1] - Rm[1, 2]) / s, (Rm[0, 2] - Rm[2, 0]) / s, (Rm[1, 0] - Rm[0, 1]) / s, s / 4]
    else:
        i = int(np.argmax(np.diag(Rm))); j, k = (i + 1) % 3, (i + 2) % 3; s = math.sqrt(1 + Rm[i, i] - Rm[j, j] - Rm[k, k]) * 2; q = [0, 0, 0, 0]
        q[i] = s / 4; q[j] = (Rm[j, i] + Rm[i, j]) / s; q[k] = (Rm[k, i] + Rm[i, k]) / s; q[3] = (Rm[k, j] - Rm[j, k]) / s
    return [round(float(x), 7) for x in q]
def pq(M): return [round(float(x) / 1000.0, 7) for x in M[:3, 3]] + quat(M[:3, :3])

if __name__ == '__main__':
    C = build(); MOVED = sanitize(C); E = evaluate(C); h = S.h
    for name, frames in E.items():
        c = C[name]; worst = min(min(fr[s]['sdf'] for s in 'RL') for fr in frames); e = max(c.err.values()) if c.err else 0.0
        print(f"{name:20s} {len(frames):3d} frames  pre {c.pre:2d}  approx. clearance min {worst:6.2f} mm  digit target error max {e:5.2f} mm  largest escape move {MOVED[name]:5.1f} mm", flush=True)
    # ---- frames for the checks
    np.savez(os.path.join(solve.HERE, 'refs-local', 'build', 'frames.npz'), E=np.array({n: [dict(rifle_frame=fr['rifle_frame'], **{s: dict(q=fr[s]['q'], H=fr[s]['H'], F=fr[s]['F'], arm=fr[s]['arm']) for s in 'RL'}) for fr in frames] for n, frames in E.items()}, dtype=object),
             meta=json.dumps({n: dict(rifle=C[n].rifle, pre=C[n].pre, post=C[n].post, n_rifle=C[n].n_rifle) for n in C}))
    # ---- grips.json
    sock = R.sockets; grips = {}
    for name, g in G.items():
        if name.startswith('dbg'): continue
        Fc, arm, viol = S.best_swivel(g['side'], g['H']); g['F'] = Fc; g['wrist'] = arm; g['limit_violation_deg'] = viol
        Hr = real(g['side'], g['H']); Fr = real(g['side'], g['F']); so = 'socket_hand_right' if g['side'] == 'R' else 'socket_hand_left'; Hs = Hr.copy(); Hs[:3, 3] -= sock[so]
        grips[name] = dict(side=g['side'], doc=(solve.SPECS[name].__doc__ or '').strip().replace('\n    ', ' '), carried_by=P[name].carrier if name in P else 'static', socket=so,
                           hand_in_socket=pq(Hs), hand=pq(Hr), forearm=pq(Fr), angles_deg={a: round(float(v), 2) for a, v in zip(hl.ANGLES, g['q'])},
                           arm_deg={k: round(float(v), 1) for k, v in g['wrist'].items() if k != 'reach_over'},
                           solver=dict(pads_gap_mm=g['gaps'], digit_target_error_mm=g['digits'], min_clearance_mm_approx=round(g['min_sdf'], 2), limit_violation_deg=round(float(g['limit_violation_deg']), 2),
                                       **{k: g[k] for k in ('place_fit_rms', 'backed_off') if k in g}))
    json.dump(dict(units='position metres + quaternion xyzw in the rifle frame (+X left, +Y up, +Z muzzle); angles degrees', sockets={k: [round(float(x) / 1000, 6) for x in v] for k, v in sock.items() if 'hand' in k}, grips=grips),
              open(os.path.join(solve.HERE, 'grips', 'grips.json'), 'w'), indent=1)
    # ---- runtime data
    bones = [dict(name=n, parent=(hl.ORDER[h.parent[i]] if h.parent[i] >= 0 else None), length=round(float(h.J[n][2]) / 1000, 6),
                  rest=[[round(float(v) / (1000.0 if j == 3 and i2 < 3 else 1.0), 6) for j, v in enumerate(row)] for i2, row in enumerate(h.rest[i])]) for i, n in enumerate(hl.ORDER)]
    rt = dict(asset='hands-gloved', credit='carpetshark', fps=FPS,
              frame='Rifle frame of assets/hk416: metres, +X shooter\'s left, +Y up, +Z to the muzzle, origin on the bore axis at the upper receiver\'s front face.',
              skeleton=dict(note='Canonical LEFT hand, rest pose: X radial, Y distal, Z dorsal, origin at the wrist joint centre. The right hand is its mirror image (x -> -x). rest = 4x4 row-major, translation in metres.', bones=bones),
              angles=hl.ANGLES, limits_deg={k: dict(min=v[0], max=v[1], source=hl.SRC[v[2]].split(';')[0].split(':')[0][:120], note=v[3]) for k, v in hl.LIMITS.items()},
              landmarks={n: dict(bone=hl.ORDER[h.lm_bone[i]], position=[round(float(x) / 1000, 6) for x in h.lm_pos[i]]) for i, n in enumerate(h.lm_names)},
              capsules=[dict(bone=n, radius=round(float(r) / 1000, 5)) for n, r in [(f + s, hl.breadth(f) / 2 * k + hl.P['glove']) for f in hl.FING for s, k in (('_01', 1.0), ('_02', 0.93), ('_03', 0.86))] + [('thumb_01', 15.0), ('thumb_02', 12.5), ('thumb_03', 11.8)]],
              sockets={k: [round(float(x) / 1000, 6) for x in v] for k, v in sock.items() if 'hand' in k}, shoulders={s: [round(float(x) / 1000, 4) for x in solve.SHOULDER[s]] for s in 'RL'},
              grips={k: dict(side=v['side'], hand=v['hand'], forearm=v['forearm'], angles=[round(float(x), 3) for x in G[k]['q']]) for k, v in grips.items()}, clips={})
    PROXY = ('handguard_body', 'upper_body', 'lower_body', 'grip_body', 'mag_body', 'barrel', 'buffer_tube', 'stock_body', 'charging_handle', 'trigger', 'trigger_guard', 'magwell_flare',
             'bolt_catch', 'selector_lever_l', 'mag_release_button', 'flash_hider', 'rear_sight_base', 'front_sight_base')
    rt['rifle_proxy'] = dict(note='Bounding boxes of a few parts of the locally built rifle and the motion of its moving parts in each clip, for drawing context in the sample page. Not a model of the rifle.',
                             boxes=[dict(name=n, mover=R.meta['parts'][n]['mover'] or None, lo=[round(v / 1000, 5) for v in R.meta['parts'][n]['lo']], hi=[round(v / 1000, 5) for v in R.meta['parts'][n]['hi']]) for n in PROXY if n in R.meta['parts']],
                             motion={cn: {mv: [pq(R.motion(cn, float(f))[mv]) for f in range(1, cm['frames'] + 1)] for mv in cm['movers'] if mv in ('mag_body', 'charging_handle', 'trigger', 'bolt_catch', 'selector_lever_l', 'mag_release_button')} for cn, cm in R.meta['clips'].items() if cn in {c.rifle for c in C.values()}})
    for name, frames in E.items():
        c = C[name]
        rt['clips'][name] = dict(rifle_clip=c.rifle, pre_roll=c.pre, post_roll=c.post, rifle_frames=c.n_rifle, frames=len(frames), note=c.note, digit_target_error_mm=round(max(c.err.values()) if c.err else 0.0, 2),
                                 R=[dict(hand=pq(fr['R']['H']), forearm=pq(fr['R']['F']), angles=[round(float(x), 3) for x in fr['R']['q']]) for fr in frames],
                                 L=[dict(hand=pq(fr['L']['H']), forearm=pq(fr['L']['F']), angles=[round(float(x), 3) for x in fr['L']['q']]) for fr in frames])
    json.dump(rt, open(os.path.join(solve.HERE, 'hands-gloved.json'), 'w'), separators=(',', ':'))
    print('wrote grips/grips.json, hands-gloved.json (%.0f kB), frames.npz' % (os.path.getsize(os.path.join(solve.HERE, 'hands-gloved.json')) / 1000))

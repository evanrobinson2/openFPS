#!/usr/bin/env python3
"""Grenade sounds, synthesised from the simulation. No recording is used anywhere.

    python3 sound/sim.py            # stage A: physics and published levels -> params.json (recipes)
    python3 sound/verify_js.py      # stage B parity: the browser synthesiser against this file's renderer, under node

Stage A writes one recipe per sound: Friedlander pulses, decaying modes and filtered noise bursts, each number with
its source. Stage B (render) turns a recipe into samples; grenades-sound.js is the same renderer in the browser.
Loudness comes only from published effect figures (the stun grenade's 170..180 dB at 5 ft) or labelled game tuning,
never from an energetic quantity. PUB = published, PX = measured on the model, EST = estimate, GAME = game tuning.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
P0 = 20e-6
E_STEEL, RHO_STEEL = 200e9, 7850.0            # PUB: textbook values for carbon steel
C_BAR = math.sqrt(E_STEEL / RHO_STEEL)
FT5 = 1.524
MODEL = {s: json.load(open(os.path.join(HERE, '..', 'model', 'work', f'stats_grenade_{s}.json'))) for s in ('frag', 'flash', 'smoke-green')}

def pa(db): return P0 * 10 ** (db / 20)
def db(p): return 20 * math.log10(max(p, 1e-12) / P0)

# ---------------------------------------------------------------- stage B: the renderer (mirrored in grenades-sound.js)
def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF; t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd

def biquad(x, kind, fc, q):
    w = 2 * math.pi * fc / SR; cs, al = math.cos(w), math.sin(w) / (2 * q)
    if kind == 'lp': b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0
    else: b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0
    a0 = 1 + al; a1 = -2 * cs; a2 = 1 - al
    b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0
    y = [0.0] * len(x); x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xi, y1, yi; y[i] = yi
    return y

def env_at(env, t):
    if env['type'] == 'exp': return (t / env['a'] if t < env['a'] else math.exp(-(t - env['a']) / env['tau']))
    pts = env['points']
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return pts[-1][1]

def render(rec):
    n = int(round(rec['dur'] * SR)); out = [0.0] * n
    for c in rec['components']:
        i0 = int(round(c['t0'] * SR))
        if c['type'] == 'pulse':
            T = c['T']
            for i in range(i0, n):
                tau = (i - i0) / SR
                if tau > 12 * T: break
                out[i] += c['peak'] * (1 - tau / T) * math.exp(-tau / T)
        elif c['type'] == 'modes':
            for f, td, amp, ph in c['modes']:
                m = min(n, i0 + int(8 * td * SR) + 1)
                for i in range(i0, m):
                    tau = (i - i0) / SR; out[i] += amp * math.exp(-tau / td) * math.sin(2 * math.pi * f * tau + ph)
        elif c['type'] == 'noise':
            m = min(n - i0, int(round(c['dur'] * SR))); rnd = mulberry32(c['seed']); x = [rnd() * 2 - 1 for _ in range(m)]
            if c.get('hp'): x = biquad(x, 'hp', c['hp'][0], c['hp'][1])
            if c.get('lp'): x = biquad(x, 'lp', c['lp'][0], c['lp'][1])
            for i in range(m): out[i0 + i] += c['amp'] * x[i] * env_at(c['env'], i / SR)
    return out

# ---------------------------------------------------------------- stage A: physics -> recipes
def ring_modes(d_ring, d_wire):
    """In-plane bending modes of a free circular ring of round wire: f_n = n (n^2 - 1) / sqrt(n^2 + 1) * sqrt(E I / (rho A R^4)) / 2 pi."""
    R = (d_ring - d_wire) / 2; k = C_BAR * (d_wire / 4) / R ** 2
    return [n * (n * n - 1) / math.sqrt(n * n + 1) * k / (2 * math.pi) for n in (2, 3)]

def beam_modes(L, t):
    """Free-free bending modes of a flat strip: f_i = lambda_i^2 / (2 pi L^2) * sqrt(E / rho) * t / sqrt(12)."""
    return [lam * lam / (2 * math.pi * L * L) * C_BAR * t / math.sqrt(12) for lam in (4.730, 7.853, 10.996)]

# model-derived sizes (PX: from model/build.py's numbers)
RING = dict(d_ring=0.0295, d_wire=0.002)
LEVER = dict(frag=dict(L=0.095, t=0.0012), flash=dict(L=0.135, t=0.0012), smoke=dict(L=0.120, t=0.0012))   # developed length of the lever path
HOLE_D = 0.009                                   # the four top emission holes (inferred size, see model notes)
# EST: contact stiffness E* of a steel body on each ground (Pa), and how much loose material the hit throws
GROUND = dict(concrete=dict(Estar=27e9, scatter=0.0), steel_plate=dict(Estar=110e9, scatter=0.0), wood_floor=dict(Estar=9.5e9, scatter=0.0),
              packed_dirt=dict(Estar=1.0e8, scatter=0.5), grass=dict(Estar=2.0e7, scatter=0.7), sand=dict(Estar=1.0e7, scatter=1.0), mud=dict(Estar=3.0e6, scatter=0.3))
# EST: what the body itself adds. Each grenade is a solid placeholder, so these are short, damped knocks of the outer shell only.
BODY = dict(frag=dict(mass=0.3969, radius=0.03175, modes=[[9000.0, 0.004, 0.25]]),
            impact=dict(mass=0.3969, radius=0.03175, modes=[[9000.0, 0.004, 0.25]]),
            flash=dict(mass=0.3770, radius=0.022, modes=[[3500.0, 0.025, 0.6], [6200.0, 0.015, 0.35]]),
            smoke=dict(mass=0.5386, radius=0.03175, modes=[[1900.0, 0.015, 0.7], [3100.0, 0.010, 0.4], [4700.0, 0.008, 0.2]]),
            **{'smoke-white': dict(mass=0.6804, radius=0.03175, modes=[[1700.0, 0.015, 0.7], [2900.0, 0.010, 0.4], [4400.0, 0.008, 0.2]])})
BOUNCE = dict(ref_db_at_1m=85.0, ref_speed=5.0, ref_surface='concrete')     # GAME: a 5 m/s hit on concrete peaks at 85 dB at 1 m

def contact_time(body, surface, v):
    """Hertz: t_c = 2.87 (m^2 / (R E*^2 v))^(1/5)."""
    b, g = BODY[body], GROUND[surface]; return 2.87 * (b['mass'] ** 2 / (b['radius'] * g['Estar'] ** 2 * max(v, 0.05))) ** 0.2

def bounce_recipe(body, surface, v):
    b, g = BODY[body], GROUND[surface]; tc = contact_time(body, surface, v); tref = contact_time('frag', BOUNCE['ref_surface'], BOUNCE['ref_speed'])
    # Hertz peak force goes as m v / t_c; the level is pinned to the reference hit
    amp = pa(BOUNCE['ref_db_at_1m']) * (b['mass'] * v / tc) / (BODY['frag']['mass'] * BOUNCE['ref_speed'] / tref)
    fc = min(1.0 / (2 * tc), 12000.0); hard = min(1.0, fc / 1500.0)
    # 0.733 = peak of sin(pi x) exp(-x / 1.5): dividing by it makes the contact knock itself peak at amp
    comps = [dict(type='modes', t0=0.002, modes=[[fc, 1.5 * tc, amp / 0.733, 0.0]] + [[f, td, amp * a * hard, 0.0] for f, td, a in b['modes']])]
    if g['scatter'] > 0:
        comps.append(dict(type='noise', t0=0.002, dur=0.12, seed=7 + int(v * 10), amp=amp * 0.6 * g['scatter'], hp=[600.0, 0.7], lp=[5000.0, 0.7], env=dict(type='exp', a=0.004, tau=0.03)))
    return dict(dur=0.25, ref_distance_m=1.0, components=comps, contact_time_ms=tc * 1e3)

def recipes():
    R = {}
    rm = ring_modes(**RING); a_pin = pa(62)                                        # GAME: 62 dB at 0.3 m, a small metallic handling sound
    R['pin_pull'] = dict(dur=0.45, ref_distance_m=0.3, note='wire pin dragged out of its hole, the ring ringing, the pin clearing',
        components=[dict(type='noise', t0=0.01, dur=0.11, seed=11, amp=a_pin * 0.8, hp=[2500.0, 0.8], lp=[9000.0, 0.8], env=dict(type='table', points=[[0, 0], [0.01, 1], [0.08, 0.7], [0.11, 0]])),
                    dict(type='modes', t0=0.115, modes=[[rm[0], 0.045, a_pin, 0.0], [rm[0] * 0.95, 0.040, a_pin * 0.6, 1.0], [rm[1], 0.020, a_pin * 0.35, 0.5]]),
                    dict(type='noise', t0=0.115, dur=0.012, seed=12, amp=a_pin * 1.5, hp=[1500.0, 0.7], lp=[12000.0, 0.7], env=dict(type='exp', a=0.0005, tau=0.003))])
    for k, lv in LEVER.items():
        bm = beam_modes(**lv); a = pa(70)                                          # GAME: 70 dB at 0.3 m
        R[f'lever_release_{k}'] = dict(dur=0.5, ref_distance_m=0.3, note='the lever springs off the hinge and flies: a click and the free strip ringing',
            components=[dict(type='noise', t0=0.01, dur=0.01, seed=21, amp=a * 1.6, hp=[1200.0, 0.7], lp=[10000.0, 0.7], env=dict(type='exp', a=0.0004, tau=0.002)),
                        dict(type='modes', t0=0.011, modes=[[bm[0], 0.090, a, 0.0], [bm[1], 0.060, a * 0.6, 0.7], [bm[2], 0.035, a * 0.35, 1.3]])])
        R[f'lever_land_{k}'] = dict(dur=0.3, ref_distance_m=1.0, note='the lever landing on hard ground about 0.8 s later',
            components=[dict(type='noise', t0=0.005, dur=0.008, seed=22, amp=pa(60), hp=[1500.0, 0.7], lp=[9000.0, 0.7], env=dict(type='exp', a=0.0004, tau=0.002)),
                        dict(type='modes', t0=0.006, modes=[[bm[0], 0.030, pa(58), 0.0], [bm[1], 0.022, pa(56), 0.4], [bm[2], 0.015, pa(52), 1.1]]),
                        dict(type='modes', t0=0.075, modes=[[bm[0], 0.020, pa(50), 0.0], [bm[1], 0.015, pa(49), 0.9]])])
    # detonations: a Friedlander pulse p(t) = P (1 - t/T) exp(-t/T). Free field at the reference distance.
    pk = pa(175.0)
    R['detonation_frag'] = dict(dur=1.6, ref_distance_m=FT5, peak_db=175.0, note='GAME level (the FM gives none for the frag): 175 dB at 5 ft, borrowed from the stun grenade. GAME positive phase 1.2 ms. Rumble and falling dirt are game dressing.',
        components=[dict(type='pulse', t0=0.005, peak=pk, T=0.0012),
                    dict(type='noise', t0=0.006, dur=0.9, seed=31, amp=pk * 0.05, lp=[160.0, 0.7], env=dict(type='exp', a=0.01, tau=0.22)),
                    dict(type='noise', t0=0.35, dur=1.1, seed=32, amp=pk * 0.0012, hp=[1800.0, 0.7], lp=[7000.0, 0.7], env=dict(type='table', points=[[0, 0], [0.15, 1], [0.5, 0.6], [1.1, 0]]))])
    R['detonation_flash'] = dict(dur=0.7, ref_distance_m=FT5, peak_db=175.0, note='PUB level: middle of the 170..180 dB at 5 ft in FM Table A-5. GAME positive phase 0.6 ms. The body is not destroyed: its tube rings briefly.',
        components=[dict(type='pulse', t0=0.005, peak=pk, T=0.0006),
                    dict(type='noise', t0=0.005, dur=0.03, seed=41, amp=pk * 0.08, hp=[2500.0, 0.7], lp=[14000.0, 0.7], env=dict(type='exp', a=0.0005, tau=0.006)),
                    dict(type='modes', t0=0.006, modes=[[3500.0, 0.060, pk * 0.004, 0.0], [6200.0, 0.040, pk * 0.003, 0.9]]),
                    dict(type='noise', t0=0.006, dur=0.5, seed=42, amp=pk * 0.02, lp=[220.0, 0.7], env=dict(type='exp', a=0.008, tau=0.10))])
    R['smoke_ignite'] = dict(dur=0.5, ref_distance_m=1.0, peak_db=118.0, note='GAME: a small pop (118 dB at 1 m) and the first rush of smoke',
        components=[dict(type='pulse', t0=0.005, peak=pa(118.0), T=0.0004),
                    dict(type='noise', t0=0.006, dur=0.45, seed=51, amp=pa(84.0), hp=[700.0, 0.7], lp=[7000.0, 0.7], env=dict(type='table', points=[[0, 0], [0.02, 1], [0.15, 0.5], [0.45, 0.35]]))])
    # burn hiss: jets from the four top holes. Peak frequency from the jet Strouhal number, St = f d / U ~ 0.2 (PUB, round jets)
    U = 60.0; f_pk = 0.2 * U / HOLE_D                                              # GAME: jet speed 60 m/s
    R['smoke_hiss_loop'] = dict(dur=2.0, loop=True, ref_distance_m=1.0, peak_db=78.0, strouhal_peak_hz=f_pk, note='GAME level: about 72 dB rms at 1 m at full emission; the runtime scales it with the plume emission rate. Loopable.',
        components=[dict(type='noise', t0=0.0, dur=2.0, seed=61, amp=pa(72.0) * 2.2, hp=[f_pk * 0.5, 0.6], lp=[f_pk * 4.0, 0.6], env=dict(type='table', points=[[0, 1], [2.0, 1]])),
                    dict(type='noise', t0=0.0, dur=2.0, seed=62, amp=pa(72.0) * 0.5, hp=[5000.0, 0.7], lp=[14000.0, 0.7], env=dict(type='table', points=[[0, 1], [2.0, 1]]))])
    return R

PLAYBACK = dict(full_scale_db=175.0, compression=3.0, floor=0.004, air_lp=dict(fc0=18000.0, r_half=60.0), speed_of_sound=343.0,
                note='GAME: playback mapping, not physics. A sound of level L dB at the listener plays at gain 10^((L - 175) / (20 * 3)), so a 175 dB bang is full scale and an 85 dB bounce is about 0.03. Distance: level falls 20 log10(r / ref), delay r / 343 s, and a low-pass at 18000 / (1 + r / 60) Hz stands in for air absorption (EST).')

def main():
    R = recipes(); info = {}
    for name, rec in R.items():
        y = render(rec); peak = max(abs(v) for v in y); rec['peak_pa'] = peak; rec['peak_db_at_ref'] = db(peak); info[name] = (rec['dur'], db(peak))
    examples = {f'{b}|{s}|{v}': bounce_recipe(b, s, v) for b, s, v in (('frag', 'concrete', 5.0), ('frag', 'packed_dirt', 8.0), ('smoke', 'concrete', 6.0), ('flash', 'wood_floor', 4.0), ('smoke-white', 'grass', 9.0))}
    checks = []
    def chk(text, value, ok): checks.append(dict(check=text, value=value, passed=bool(ok)))
    chk('detonation_flash: rendered peak at 5 ft is inside the published 170..180 dB', R['detonation_flash']['peak_db_at_ref'], 170 <= R['detonation_flash']['peak_db_at_ref'] <= 180)
    chk('detonation_frag: rendered peak equals its labelled game level (175 dB at 5 ft) within 1 dB', R['detonation_frag']['peak_db_at_ref'], abs(R['detonation_frag']['peak_db_at_ref'] - 175) < 1)
    yb = render(examples['frag|concrete|5.0']); chk('bounce: the reference hit (frag, concrete, 5 m/s) peaks at its labelled 85 dB at 1 m within 2 dB', db(max(abs(v) for v in yb)), abs(db(max(abs(v) for v in yb)) - 85) < 2)
    chk('bounce: Hertz contact time, frag on concrete at 5 m/s (ms)', contact_time('frag', 'concrete', 5.0) * 1e3, 0.1 < contact_time('frag', 'concrete', 5.0) * 1e3 < 0.4)
    chk('bounce: softer ground gives a longer, duller contact (concrete < wood < dirt < grass < sand)', [contact_time('frag', s, 5.0) * 1e3 for s in ('concrete', 'wood_floor', 'packed_dirt', 'grass', 'sand')],
        all(contact_time('frag', a, 5.0) < contact_time('frag', b, 5.0) for a, b in zip(('concrete', 'wood_floor', 'packed_dirt', 'grass'), ('wood_floor', 'packed_dirt', 'grass', 'sand'))))
    chk('pull ring: first bending mode of a 29.5 mm ring of 2 mm steel wire (Hz)', ring_modes(**RING)[0], 4000 < ring_modes(**RING)[0] < 8000)
    chk('lever: first free-free mode of the frag lever strip (Hz)', beam_modes(**LEVER['frag'])[0], 400 < beam_modes(**LEVER['frag'])[0] < 1200)
    out = dict(_doc='Written by sound/sim.py. Recipes for grenades-sound.js. Pressures in pascals at ref_distance_m. See sound/README.md.',
               sample_rate=SR, playback=PLAYBACK, ground=GROUND, body=BODY, bounce=BOUNCE, ring=RING, lever=LEVER, recipes=R, bounce_examples=examples, checks=checks, all_passed=all(c['passed'] for c in checks))
    json.dump(out, open(os.path.join(HERE, 'params.json'), 'w'), indent=1)
    for name, (d, l) in info.items(): print(f'{name:24s} {d:4.2f} s  peak {l:6.1f} dB at {R[name]["ref_distance_m"]} m')
    for c in checks: print('ok  ' if c['passed'] else 'FAIL', c['check'], '->', c['value'])

if __name__ == '__main__':
    main()

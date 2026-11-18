#!/usr/bin/env python3
"""Synthesised sound for the shotgun-590 asset. No recordings are used anywhere.

    python3 sound/sim.py          # writes params.json, compare/levels.json and compare/waveforms.png
    python3 sound/verify_js.py    # renders every sound in node with shotgun590-sound.js and compares sample by sample

Each sound is a list of components (blast pulses, decaying modes, filtered noise bursts) whose times and strengths
come from the action simulation (action/action.json) and the model (model/inventory.json). The browser module
renders the same list with the same arithmetic. Sources and guesses are in SRC below and in README.md.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ACT = json.load(open(os.path.join(HERE, '..', 'action', 'action.json'))); INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
FS = 48000; P0 = 101325.0; C = 340.294; PREF = 20e-6
SRC = dict(
    blast_coefficient=dict(value=0.25, basis='guess', source='far-field peak overpressure of a point energy release, dp = 0.25 p0 R0 / r with R0 = (E / p0)^(1/3): an order-of-magnitude coefficient'),
    front_to_back_db=dict(value=15.0, basis='guess', source='muzzle blast is louder in front than behind; 15 dB front to back, a generic figure'),
    positive_phase=dict(value=0.5, basis='guess', source='positive phase lasts 0.5 R0 / c'),
    ground_reflection=dict(value=0.5, basis='guess', source='one reflection off the ground, half amplitude; muzzle 1.4 m and ears 1.6 m above it'),
    published_level=dict(value=[151.5, 161.5], basis='published', source='peak level at the shooter\'s ear for 12 gauge shotguns: 151.5 dB with a 28 in barrel, 161.5 dB with an 18.5 in barrel (W. Krammer, Ball State University, as reproduced in E.A.R. Inc.\'s "Gunfire Noise Level Reference Chart"). Recreational firearms measure about 150 to 165 dB peak at the shooter\'s ear (Meinke et al., 2017, review, PMC5634813)'),
    mechanical_levels=dict(value='see MECH', basis='guess', source='peak levels of the mechanical sounds are tuning: a hard rack is set near 100 dB peak at the shooter\'s ear'),
    modes=dict(basis='derived', source='bending modes of the barrel and magazine tube as free steel tubes, from the model\'s lengths and diameters (E = 200 GPa, 7850 kg/m^3); contact clicks at 3.1, 5.2 and 7.4 kHz are a guess'),
)
PERSPECTIVES = dict(shooter=dict(note='at the shooter\'s ear, behind the muzzle'), bystander=dict(r=5.0, angle_deg=90.0, note='5 m to the side of the muzzle'))

def tube_modes(length, r_out, r_in):
    k = math.sqrt((r_out ** 2 + r_in ** 2) / 4.0); c_bar = math.sqrt(200e9 / 7850.0)
    return [round(b ** 2 / (2 * math.pi * length ** 2) * c_bar * k, 1) for b in (4.730, 7.853, 10.996)]
p = INV['params']
BARREL = tube_modes((p['muzzle'] - p['breech']) * 1e-3, p['barrel_r'] * 1e-3, p['bore_r'] * 1e-3)
TUBE = tube_modes((p['tube_z'][1] - p['tube_z'][0]) * 1e-3, p['tube_r'] * 1e-3, (p['tube_r'] - p['tube_wall']) * 1e-3)
CLICK = [3100.0, 5200.0, 7400.0]
MECH = dict(impact_pa_per_mps=1.8, friction_pa_per_mps=0.25, hammer_pa=1.2, insert_click_pa=0.5, safety_pa=0.15, lever_pa=0.1, hull_pa=0.2)

# ----------------------------------------------------------------------------- components
def fried(t0, amp, tpos): return dict(kind='friedlander', t0=round(t0, 6), amp=round(amp, 6), tpos=round(tpos, 7))
def mode(t0, f, decay, amp, phase=0.0): return dict(kind='mode', t0=round(t0, 6), f=f, decay=decay, amp=round(amp, 6), phase=phase)
def noise(t0, amp, fc, q, attack, decay, seed, hold=0.0): return dict(kind='noise', t0=round(t0, 6), amp=round(amp, 6), fc=fc, q=q, attack=attack, hold=hold, decay=decay, seed=seed)

def impact(t, pa, seed, heavy=True):
    """metal parts meeting: a contact click, the tubes ringing, and for a heavy stop the polymer forend's thud"""
    c = [mode(t, f, d, pa * a) for f, d, a in zip(CLICK, (0.004, 0.003, 0.002), (0.5, 0.35, 0.2))]
    c += [noise(t, pa * 0.6, 4200.0, 0.8, 0.0003, 0.004, seed)]
    if heavy:
        c += [mode(t, f, d, pa * a) for f, d, a in zip(TUBE, (0.060, 0.035, 0.020), (0.30, 0.18, 0.10))]
        c += [mode(t, f, d, pa * a) for f, d, a in zip(BARREL, (0.080, 0.045, 0.025), (0.22, 0.14, 0.08))]
        c += [mode(t, 190.0, 0.018, pa * 0.5), noise(t, pa * 0.3, 900.0, 0.7, 0.001, 0.02, seed + 1)]
    return c

def directivity(angle_deg): return 10 ** (-(SRC['front_to_back_db']['value'] * (1 - math.cos(math.radians(angle_deg))) / 2) / 20)

def shot(load, persp):
    s = ACT['shots'][load]; E = s['gas_energy_at_exit_J']; R0 = (E / P0) ** (1 / 3)
    if persp == 'shooter':
        ear = ACT['sockets']['socket_ads_eye']; mz = ACT['sockets']['socket_muzzle']; r = math.hypot(mz[2] - ear[2] + 0.08, 0.08); ang = 172.0
    else:
        r, ang = PERSPECTIVES[persp]['r'], PERSPECTIVES[persp]['angle_deg']
    peak = SRC['blast_coefficient']['value'] * P0 * R0 / r * directivity(ang); tpos = SRC['positive_phase']['value'] * R0 / C
    t_exit = s['t0'] + s['barrel_time_ms'] * 1e-3; t_arr = t_exit + r / C
    r_ref = math.sqrt(r * r + 4 * 1.4 * 1.6); refl = SRC['ground_reflection']['value'] * peak * r / r_ref
    comps = [fried(t_arr, peak, tpos), fried(t_exit + r_ref / C, refl, tpos * 1.3)]
    comps += [noise(t_arr, peak * 0.10, 650.0, 0.6, 0.002, 0.060, 11), noise(t_arr, peak * 0.05, 2400.0, 0.7, 0.001, 0.025, 12), mode(t_arr, 95.0, 0.045, peak * 0.12)]     # the gas tail and the low thump (guessed shares)
    near = 1.0 if persp == 'shooter' else 0.9 / PERSPECTIVES[persp]['r']
    comps += [c for c in impact(s['t0'], MECH['hammer_pa'] * near, 21, heavy=False)]                                 # the hammer, just before the blast
    comps += [mode(t_exit, f, d, 2.0 * near * a) for f, d, a in zip(BARREL, (0.10, 0.06, 0.03), (0.5, 0.3, 0.15))]  # the barrel rings after the shot (guessed strength)
    return dict(duration=0.45, components=comps, peak_pa_design=round(peak, 2), distance_m=round(r, 3), angle_deg=ang, blast_energy_J=E, scaled_radius_m=round(R0, 4))

def pump(which):
    ev = ACT['cycle']['events']; prof = ACT['cycle']['profile']; comps = []; t_shift = 0.0 if which != 'pump_forward' else -(prof['back_s'] + prof['dwell_s'])
    k_i, k_f = MECH['impact_pa_per_mps'], MECH['friction_pa_per_mps']; vmax_b = prof['exponent'] * ACT['cycle']['stroke_mm'] * 1e-3 / prof['back_s']; vmax_f = prof['exponent'] * ACT['cycle']['stroke_mm'] * 1e-3 / prof['forward_s']
    for i, e in enumerate(ev):
        if which == 'pump_back' and e['direction'] != 'back': continue
        if which == 'pump_forward' and e['direction'] != 'forward': continue
        t = e['t'] + t_shift + 0.01
        if e['name'] == 'unlock': comps += impact(t, k_i * e['slide_speed'] * 0.5, 30 + i, heavy=False)
        if e['name'] == 'eject': comps += [mode(t, 1750.0, 0.006, MECH['hull_pa']), noise(t, MECH['hull_pa'], 2600.0, 1.2, 0.0005, 0.006, 40 + i)]
        if e['name'] == 'rear_stop': comps += impact(t, k_i * e['slide_speed'], 50 + i)
        if e['name'] == 'feed': comps += [mode(t, 420.0, 0.010, 0.25), noise(t, 0.2, 1500.0, 0.9, 0.001, 0.010, 60 + i)]
        if e['name'] == 'chambered': comps += impact(t, k_i * e['slide_speed'] * 0.6, 70 + i, heavy=False)
        if e['name'] == 'locked': comps += impact(t, k_i * e['slide_speed'], 80 + i)
    if which != 'pump_forward': comps += [noise(0.01, k_f * vmax_b, 2800.0, 0.6, prof['back_s'], 0.006, 91)]            # the slide's hiss grows with its speed
    if which != 'pump_back': comps += [noise(0.01 + prof['back_s'] + prof['dwell_s'] + t_shift, k_f * vmax_f, 2800.0, 0.6, prof['forward_s'], 0.006, 92)]
    dur = (ACT['cycle']['duration'] if which == 'pump' else (prof['back_s'] if which == 'pump_back' else prof['forward_s'])) + 0.22
    return dict(duration=round(dur, 3), components=comps)

def simple(name):
    if name == 'dry_fire': return dict(duration=0.12, components=impact(ACT['params']['lock_time']['value'], MECH['hammer_pa'], 101, heavy=False) + [mode(ACT['params']['lock_time']['value'], BARREL[1], 0.03, 0.08)])
    if name == 'shell_insert':
        c = [noise(0.005, 0.12, 1800.0, 0.6, 0.09, 0.01, 111), mode(0.10, 240.0, 0.012, 0.2)] + impact(0.10, MECH['insert_click_pa'], 112, heavy=False) + [mode(0.10, TUBE[0], 0.03, 0.06)]
        return dict(duration=0.26, components=c)
    if name == 'safety': return dict(duration=0.08, components=impact(0.005, MECH['safety_pa'], 121, heavy=False))
    if name == 'action_release': return dict(duration=0.08, components=impact(0.005, MECH['lever_pa'], 131, heavy=False))

def build():
    snd = {}
    for load in ACT['shots']:
        for persp in PERSPECTIVES: snd[f'shot_{load}_{persp}'] = shot(load, persp)
    for w in ('pump', 'pump_back', 'pump_forward'): snd[w] = pump(w)
    for n in ('dry_fire', 'shell_insert', 'safety', 'action_release'): snd[n] = simple(n)
    return dict(fs=FS, units='pascals at the listener; times in seconds from the trigger break (shots, dry_fire) or from the start of the motion', sources=SRC, perspectives=PERSPECTIVES,
                modes_hz=dict(barrel=BARREL, magazine_tube=TUBE, contact=CLICK), mechanical=MECH, sounds=snd)

# ----------------------------------------------------------------------------- rendering (the same arithmetic as the JavaScript module)
def rng(seed):
    s = seed & 0xFFFFFFFF
    def r():
        nonlocal s
        s = (s + 0x6D2B79F5) & 0xFFFFFFFF; z = s
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z = (z ^ ((z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return r

def render(snd, fs=FS):
    n = int(round(snd['duration'] * fs)); y = [0.0] * n
    for c in snd['components']:
        i0 = max(0, int(math.ceil(c['t0'] * fs)))
        if c['kind'] == 'friedlander':
            for i in range(i0, min(n, i0 + int(c['tpos'] * fs * 8) + 1)):
                u = (i / fs - c['t0']) / c['tpos']; y[i] += c['amp'] * (1 - u) * math.exp(-u)
        elif c['kind'] == 'mode':
            w = 2 * math.pi * c['f']
            for i in range(i0, min(n, i0 + int(c['decay'] * fs * 9) + 1)):
                t = i / fs - c['t0']; y[i] += c['amp'] * math.exp(-t / c['decay']) * math.sin(w * t + c['phase'])
        else:
            r = rng(c['seed']); w0 = 2 * math.pi * c['fc'] / fs; al = math.sin(w0) / (2 * c['q']); a0 = 1 + al
            b0, b2, a1, a2 = al / a0, -al / a0, -2 * math.cos(w0) / a0, (1 - al) / a0; x1 = x2 = y1 = y2 = 0.0
            for i in range(i0, min(n, i0 + int((c['attack'] + c['hold'] + c['decay'] * 9) * fs) + 1)):
                t = i / fs - c['t0']; x = 2 * r() - 1; v = b0 * x + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = v
                env = (t / c['attack'] if t < c['attack'] else 1.0) if c['attack'] > 0 else 1.0
                if t > c['attack'] + c['hold']: env = math.exp(-(t - c['attack'] - c['hold']) / c['decay'])
                y[i] += c['amp'] * 3.0 * env * v
    return np.array(y)

def main():
    P = build(); levels = {}
    for name, s in P['sounds'].items():
        y = render(s); pk = float(np.max(np.abs(y))); s['peak_pa'] = round(pk, 4); s['peak_db'] = round(20 * math.log10(pk / PREF), 1)
        levels[name] = dict(peak_pa=s['peak_pa'], peak_db=s['peak_db'], duration=s['duration'], components=len(s['components']))
    json.dump(P, open(os.path.join(HERE, 'params.json'), 'w'), separators=(',', ':'))
    lo, hi = SRC['published_level']['value']; chk = {}
    for load in ACT['shots']:
        db = levels[f'shot_{load}_shooter']['peak_db']; chk[load] = dict(peak_db_at_shooter=db, published_range_db=[lo, hi], passed=lo - 2 <= db <= hi + 2)
    json.dump(dict(note='peak levels of every synthesised sound, dB re 20 uPa, at the listener of that sound', levels=levels, shot_level_check=dict(source=SRC['published_level']['source'],
              method='the blast coefficient and the front-to-back figure are generic guesses set once; this compares the result with the published range for 12 gauge shotguns (a 20 in barrel sits between the two published barrels)', rows=chk)),
              open(os.path.join(HERE, 'compare', 'levels.json'), 'w'), indent=1)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    names = ['shot_buck00_shooter', 'shot_slug_bystander', 'pump', 'shell_insert', 'dry_fire', 'safety']; fig, ax = plt.subplots(2, len(names), figsize=(3.2 * len(names), 5))
    for i, nm in enumerate(names):
        y = render(P['sounds'][nm]); t = np.arange(len(y)) / FS * 1e3; ax[0, i].plot(t, y, lw=0.6); ax[0, i].set(title=nm, xlabel='ms', ylabel='Pa' if i == 0 else '')
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))); f = np.fft.rfftfreq(len(y), 1 / FS); ax[1, i].semilogx(f[1:], 20 * np.log10(sp[1:] / sp.max() + 1e-9), lw=0.6); ax[1, i].set(xlim=(30, 20000), ylim=(-80, 3), xlabel='Hz', ylabel='dB re peak bin' if i == 0 else '')
    fig.suptitle('Synthesised waveforms and spectra (simulation only)'); fig.tight_layout(); fig.savefig(os.path.join(HERE, 'compare', 'waveforms.png'), dpi=80); plt.close(fig)
    for k, v in levels.items(): print(f'{k:28s} {v["peak_db"]:6.1f} dB  {v["peak_pa"]:10.3f} Pa  {v["duration"]:.2f} s  {v["components"]} components')
    print('modes', BARREL, TUBE); print({k: (v['passed'], v['peak_db_at_shooter']) for k, v in chk.items()})

if __name__ == '__main__':
    main()

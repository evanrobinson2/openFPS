#!/usr/bin/env python3
"""G44 V simulated sound.  Everything is synthesised from the action simulation and stated physics; nothing is a recording.

    python3 sim.py            # stage A: params.json (every derived table) + check.json (levels against published figures)
    python3 verify_js.py      # parity of g44v-sound.js (stage B in the browser) against stage B here

Stage A turns ../action/action.json and ../model/inventory.json into tables: blast pulse sizes per load, propagation paths per
perspective, modal tables of the mechanical sounds, room recipes.  Stage B (synth_dry, synth_mech, build_ir) turns tables into
waveforms in pascals; g44v-sound.js is a port of stage B with the same arithmetic and the same named random streams.
"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ACT = json.load(open(os.path.join(HERE, '..', 'action', 'action.json')))
INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
FS = 48000; C0 = 343.0; RHO_C = 413.0; P_REF = 20e-6
def db(p): return 20 * math.log10(max(abs(p), 1e-30) / P_REF)

# ------------------------------------------------------------------ inputs with their sources
SRC = dict(
    anchor_rifle_db=(140.0, 'published', 'about 140 dB peak for a .22 calibre rifle (cited in a firearm suppressor study, PMC8588962). Its measuring position is not stated; taken here as the shooter\'s ear'),
    bracket_1m_left_db=((149.0, 167.0), 'published', 'Flamme et al.: instantaneous peak levels 1 m to the shooter\'s left ranged from 149 to 167 dB across 15 recreational firearms (as summarised in CDC stacks 211059)'),
    efflux_exponent=(0.55, 'inferred', 'peak overpressure ~ (muzzle energy efflux rate)^0.55, from the blast scaling length ~ sqrt(efflux) and peak ~ length^1.1 (Fansler and Schmidt muzzle blast scaling, recalled, not re-read)'),
    decay_exponent=(1.1, 'inferred', 'peak ~ r^-1.1: weak-shock decay, same scaling'),
    directivity_db=(6.0, 'inferred', 'level(theta) = level(90 deg) + 6 cos(theta) dB: louder ahead of the muzzle, quieter behind. Typical of small arms, not measured for this pistol'),
    t_pos_ref=(0.25e-3, 'inferred', 'positive phase of the standard-velocity blast at 1 m; small-arms values are 0.2 to 0.5 ms'),
    friedlander_b=(1.5, 'inferred', 'decay constant of the Friedlander wave'), rise_time=(40e-6, 'inferred', 'shock rise seen through a 48 kHz system'),
    ground_reflection=(0.75, 'inferred', 'pressure reflection coefficient of range ground (grass over soil), broadband'),
    air_lp=(3.0e5, 'inferred', 'air absorption as a one-pole low-pass with corner 3e5 / r Hz (a rough fit to ISO 9613-1 at 20 C, 50 % RH)'),
    radiation_efficiency=(2.0e-3, 'inferred', 'share of a mechanical impact\'s lost energy that leaves as sound'),
    rifle_ear=((0.75, 170.0), 'inferred', 'ear of a rifle shooter: 0.75 m from the muzzle of a 24 in barrel, 170 deg off the line of fire'),
)
sv = lambda k: SRC[k][0]
MODES = dict(   # inferred modal tables: (frequency Hz, decay time s, share of the radiated energy); polymer frame damps quickly
    slide_frame=[(1900.0, 0.0030, 0.30), (3300.0, 0.0022, 0.30), (5100.0, 0.0014, 0.22), (7900.0, 0.0009, 0.18)],
    slide_barrel=[(2600.0, 0.0035, 0.30), (4300.0, 0.0024, 0.30), (6800.0, 0.0015, 0.25), (9800.0, 0.0008, 0.15)],
    striker=[(4200.0, 0.0012, 0.4), (7100.0, 0.0008, 0.35), (11500.0, 0.0005, 0.25)],
    trigger=[(3100.0, 0.0010, 0.5), (6400.0, 0.0006, 0.5)],
    magazine=[(900.0, 0.0050, 0.35), (1700.0, 0.0035, 0.35), (3900.0, 0.0015, 0.30)],
    case_ground=[(6200.0, 0.0060, 0.5), (9800.0, 0.0035, 0.5)],
)
def impact(t, energy_J, table, noise=0.3):
    """an impact that loses energy_J: modes at 1 m (pressure amplitudes from the radiated energy) plus a short noise click"""
    Eac = sv('radiation_efficiency') * energy_J
    modes = [dict(f=f, tau=tau, a=round(math.sqrt(w * (1 - noise) * Eac * RHO_C / (math.pi * tau)), 6)) for f, tau, w in MODES[table]]
    tn = 0.0006; return dict(t=round(t, 6), modes=modes, noise=dict(a=round(math.sqrt(noise * Eac * RHO_C / (2 * math.pi * tn)), 6), tau=tn, lp=0.35))

# ------------------------------------------------------------------ stage A
def stage_a():
    A = ACT['params']; g = A['gamma']['value']; bore = A['bore_area']['value']; V0 = A['chamber_vol']['value']; eta = A['covolume']['value']
    def efflux(p_exit, travel, charge):
        V = V0 + bore * travel; RT = p_exit * (V - eta * charge) / charge; a = math.sqrt(g * RT)
        ps = p_exit * (2 / (g + 1)) ** (g / (g - 1)); us = a * math.sqrt(2 / (g + 1))
        return g * ps * us * bore / (g - 1) * (1 + (g - 1) / 2)          # W, sonic exit
    ref = ACT['loads']['cci_standard_velocity']
    q_rifle = efflux(ref['test_barrel']['muzzle_pressure_MPa'] * 1e6, A['bullet_travel_test']['value'], ref['guessed']['charge_kg'])
    r_e, th_e = sv('rifle_ear')
    L_rifle_1m90 = sv('anchor_rifle_db') - sv('directivity_db') * math.cos(math.radians(th_e)) - 20 * sv('decay_exponent') * math.log10(1.0 / r_e)
    loads = {}; q_sv = None
    for k, L in ACT['loads'].items():
        q = efflux(L['pistol']['muzzle_pressure_MPa'] * 1e6, A['bullet_travel']['value'], L['guessed']['charge_kg'])
        if k == 'cci_standard_velocity': q_sv = q
        lvl = L_rifle_1m90 + 20 * sv('efflux_exponent') * math.log10(q / q_rifle)
        ev = L['events']; ms = A['m_slide']['value']; mg = 0.358 + 0.057 + 0.5; mu = ms * mg / (ms + mg); e_r, e_f = A['e_rear']['value'], A['e_front']['value']
        mech = [impact(ev['striker_hits'], ACT['firing']['energy_J'], 'striker')]
        if 'rear_stop' in ev: mech.append(impact(ev['rear_stop'], 0.5 * mu * ev['rear_stop_speed'] ** 2 * (1 - e_r ** 2), 'slide_frame'))
        if 'in_battery' in ev: mech.append(impact(ev['in_battery'], 0.5 * mu * ev['closing_speed'] ** 2 * (1 - e_f ** 2), 'slide_barrel'))
        loads[k] = dict(label=L['label'], t_blast=round(ev['bullet_exit'], 6), efflux_W=round(q), peak_pa_1m_90=round(P_REF * 10 ** (lvl / 20), 3), peak_db_1m_90=round(lvl, 2),
                        supersonic=bool(L['pistol']['muzzle_velocity_mps'] > C0), mech=mech)
    for k, L in loads.items(): L['t_pos'] = round(sv('t_pos_ref') * math.sqrt(L['efflux_W'] / q_sv), 7)
    # perspectives: source = the muzzle, 1.5 m above the ground; +Z downrange, +X left
    sock = {s['name']: s['pos_m_export'] for s in INV['sockets']}; mz = sock['socket_muzzle']; eye = sock['socket_ads_eye']
    listeners = dict(shooter=(0.08 - mz[0], eye[1] - mz[1], eye[2] - mz[2]), bystander=(3.0, 0.1, -0.3), downrange=(2.0, 0.0, 25.0))
    notes = dict(shooter='the shooter\'s right ear: at the eye socket of the model, 8 cm to the side', bystander='3 m to the shooter\'s left, level with the pistol', downrange='25 m downrange, 2 m beside the line of fire')
    persp = {}
    for name, (x, y, z) in listeners.items():
        r = math.sqrt(x * x + y * y + z * z); th = math.degrees(math.acos(z / r)); hs = 1.5; hl = 1.5 + y
        horiz = math.sqrt(x * x + z * z); rg = math.sqrt(horiz ** 2 + (hs + hl) ** 2); thg = math.degrees(math.acos(z / rg))
        def path(rr, tt, extra): return dict(delay=round(rr / C0, 7), gain=round((1.0 / rr) ** sv('decay_exponent') * 10 ** (sv('directivity_db') * math.cos(math.radians(tt)) / 20) * extra, 6),
                                             mech_gain=round(extra / rr, 6), lp=round(min(0.999, 1 - math.exp(-2 * math.pi * min(20000.0, sv('air_lp') / rr) / FS)), 6))
        persp[name] = dict(r=round(r, 4), theta_deg=round(th, 2), note=notes[name], direct=path(r, th, 1.0), ground=path(rg, thg, sv('ground_reflection')))
    # mechanical clips that are not part of a shot (hand operated): energies from spring loads and inferred hand speeds
    F0, F1, U = A['spring_F0']['value'], A['spring_F1']['value'], A['travel']['value']; ms = A['m_slide']['value']
    Esp = (F0 + F1) / 2 * U; v_close = math.sqrt(2 * (Esp - 0.3) / ms); UL = A['lock_open']['value']; v_rel = math.sqrt(2 * ((F0 + F0 + (F1 - F0) * UL / U) / 2 * UL - 0.3) / ms)
    clips = dict(
        trigger=[impact(0.0, 0.004, 'trigger')],
        dry_fire=[impact(0.0, 0.004, 'trigger'), impact(ACT['firing']['lock_time_s'], ACT['firing']['energy_J'], 'striker')],
        slide_rack=[impact(0.0, 0.5 * ms * 1.5 ** 2, 'slide_frame'), impact(0.06 + 2 * U / v_close, 0.5 * ms * v_close ** 2 * 0.9, 'slide_barrel')],
        slide_lock_open=[impact(0.0, 0.5 * ms * 1.5 ** 2, 'slide_frame'), impact(0.05, 0.02, 'slide_frame')],
        slide_release=[impact(0.0, 0.01, 'trigger'), impact(2 * UL / v_rel, 0.5 * ms * v_rel ** 2 * 0.9, 'slide_barrel')],
        magazine_out=[impact(0.0, 0.01, 'trigger'), impact(0.03, 0.02, 'magazine')],
        magazine_in=[impact(0.0, 0.05, 'magazine'), impact(0.012, 0.01, 'trigger')],
        case_ground=[impact(0.0, 0.6e-3 * 9.81 * 1.4 * 0.5, 'case_ground'), impact(0.11, 0.6e-3 * 9.81 * 1.4 * 0.06, 'case_ground')])
    clip_notes = 'hand speeds (1.5 m/s rack) and small click energies are inferred; closing speeds follow from the recoil spring loads in action.json'
    # rooms
    def shoebox(dims, src, lis, alpha, order=2):
        Lx, Ly, Lz = dims; taps = []; d0 = math.dist(src, lis)
        for nx in range(-order, order + 1):
            for ny in range(-order, order + 1):
                for nz in range(-order, order + 1):
                    n = abs(nx) + abs(ny) + abs(nz)
                    if n == 0 or n > order: continue
                    img = [(nx * L_ + (src_ if nx_ % 2 == 0 else L_ - src_)) for nx_, L_, src_ in ((nx, Lx, src[0]), (ny, Ly, src[1]), (nz, Lz, src[2]))]
                    d = math.dist(img, lis); taps.append(dict(delay=round((d - d0) / C0, 6), gain=round(d0 / d * (1 - alpha) ** (n / 2), 5)))
        V = Lx * Ly * Lz; S = 2 * (Lx * Ly + Ly * Lz + Lx * Lz); rt = 0.161 * V / (S * alpha)
        return sorted(taps, key=lambda q: q['delay']), rt
    taps, rt = shoebox((6.0, 3.0, 28.0), (3.0, 1.5, 2.0), (3.08, 1.57, 1.4), 0.35)
    overlays = dict(
        outdoor_berm=dict(note='open range, earth berm 25 m downrange: ground reflection and one diffuse return from the berm', taps=[dict(delay=round(2 * 1.5 ** 2 / 0.63 / C0 * 0.5, 6), gain=0.5), dict(delay=round(50.0 / C0, 6), gain=0.012)],
                          tail=dict(t0=round(50.0 / C0, 6), rt60=0.35, level=0.006, lp=0.25)),
        indoor_range=dict(note='indoor range lane hall 6 x 3 x 28 m, mean absorption 0.35 (baffles and backstop): image sources to second order, then a Sabine tail', taps=taps,
                          tail=dict(t0=0.030, rt60=round(rt, 3), level=0.05, lp=0.4)))
    return dict(meta=dict(title='G44 V simulated sound', credit='carpetshark', generator='sim.py', units='pascals at the listener; times in seconds from the trigger break'),
                fs=FS, c0=C0, sources={k: dict(value=v_[0], status=v_[1], source=v_[2]) for k, v_ in SRC.items()}, friedlander_b=sv('friedlander_b'), rise=sv('rise_time'),
                loads=loads, perspectives=persp, clips=clips, clip_notes=clip_notes, overlays=overlays, dur_shot=0.20, dur_clip=0.30)

# ------------------------------------------------------------------ stage B (ported line for line in g44v-sound.js)
def fnv1a(s):
    h = 0x811c9dc5
    for c in s.encode():
        h ^= c; h = (h * 0x01000193) & 0xFFFFFFFF
    return h
class Rng:      # mulberry32, the same stream as the JS
    def __init__(self, name): self.a = fnv1a(name)
    def next(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF; t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    def gauss(self):
        a = self.next(); b = self.next(); return math.sqrt(-2 * math.log(a + 1e-12)) * math.cos(2 * math.pi * b)
def add_blast(buf, P, pk, T, t0, lp):
    fs = P['fs']; b = P['friedlander_b']; rise = P['rise']; n0 = max(0, int(math.floor(t0 * fs))); n1 = min(len(buf), int(math.ceil((t0 + rise + 8 * T) * fs)) + 1); y = 0.0
    for n in range(n0, n1):
        t = n / fs - t0; x = 0.0
        if t >= 0:
            if t < rise: x = pk * t / rise
            else: u = (t - rise) / T; x = pk * (1 - u) * math.exp(-b * u)
        y += lp * (x - y); buf[n] += y
def add_impact(buf, P, ev, t0, gain, lp, seed):
    fs = P['fs']; n0 = max(0, int(math.floor((t0 + ev['t']) * fs))); tmax = max(m['tau'] for m in ev['modes']) * 7; n1 = min(len(buf), n0 + int(tmax * fs) + 2)
    rng = Rng(seed); nz = ev['noise']; y = 0.0; z = 0.0
    for n in range(n0, n1):
        t = n / fs - (t0 + ev['t']); x = 0.0
        if t >= 0:
            for m in ev['modes']: x += m['a'] * math.exp(-t / m['tau']) * math.sin(2 * math.pi * m['f'] * t)
            z += nz['lp'] * (rng.gauss() - z); x += nz['a'] * math.exp(-t / nz['tau']) * z
        y += lp * (x * gain - y); buf[n] += y
def synth_dry(P, load, persp='shooter', field=False):
    """one shot in pascals at the listener, free field (direct sound only) or over open ground (field)"""
    L = P['loads'][load]; ps = P['perspectives'][persp]; buf = [0.0] * int(P['dur_shot'] * P['fs'])
    for i, pth in enumerate([ps['direct']] + ([ps['ground']] if field else [])):
        add_blast(buf, P, L['peak_pa_1m_90'] * pth['gain'], L['t_pos'], L['t_blast'] + pth['delay'], pth['lp'])
        for j, ev in enumerate(L['mech']): add_impact(buf, P, ev, pth['delay'], pth['mech_gain'], pth['lp'], 'mech|%s|%d|%d' % (load, j, i))
    return np.array(buf)
def synth_mech(P, clip, persp='shooter'):
    ps = P['perspectives'][persp]; buf = [0.0] * int(P['dur_clip'] * P['fs']); pth = ps['direct']
    for j, ev in enumerate(P['clips'][clip]): add_impact(buf, P, ev, 0.002, pth['mech_gain'], pth['lp'], 'clip|%s|%d' % (clip, j))
    return np.array(buf)
def build_ir(P, overlay):
    """impulse response of the surroundings: the direct path is the first sample, value 1"""
    O = P['overlays'][overlay]; fs = P['fs']; tl = O['tail']; n = int((tl['t0'] + tl['rt60'] * 1.1) * fs) + 1; h = [0.0] * n; h[0] = 1.0
    for tp in O['taps']:
        k = int(math.floor(tp['delay'] * fs + 0.5))
        if 0 < k < n: h[k] += tp['gain']
    rng = Rng('ir|' + overlay); z = 0.0; k0 = int(tl['t0'] * fs)
    for k in range(k0, n):
        t = (k - k0) / fs; z += tl['lp'] * (rng.gauss() - z); h[k] += tl['level'] * z * math.exp(-6.907755 * t / tl['rt60'])
    return np.array(h)
JOBS = lambda P: [['dry_%s_%s_%s' % (l, p, 'field' if f else 'free'), 'dry', l, p, f] for l in P['loads'] for p in P['perspectives'] for f in (False, True)] + \
                 [['mech_%s' % c, 'mech', c, 'shooter'] for c in P['clips']] + [['ir_%s' % o, 'ir', o] for o in P['overlays']]

def main():
    P = stage_a(); json.dump(P, open(os.path.join(HERE, 'params.json'), 'w'), indent=1)
    rows = {}
    for l in P['loads']:
        rows[l] = {}
        for p in P['perspectives']:
            x = synth_dry(P, l, p, False); xf = synth_dry(P, l, p, True); pk = float(np.max(np.abs(x)))
            rows[l][p] = dict(peak_pa=round(pk, 3), peak_db=round(db(pk), 2), peak_db_over_ground=round(db(float(np.max(np.abs(xf)))), 2), sel_db=round(10 * math.log10(float(np.sum(x * x)) / FS / P_REF ** 2), 2))
    lo, hi = sv('bracket_1m_left_db'); L90 = {l: P['loads'][l]['peak_db_1m_90'] for l in P['loads']}
    chk = dict(note='levels of the synthesised shots, and the two published figures used. One constant is calibrated (the rifle anchor); the pistol levels follow from the simulated muzzle conditions.',
               calibration=dict(anchor=SRC['anchor_rifle_db'][2], rifle_level_at_ear_db=sv('anchor_rifle_db')),
               prediction_1m_90deg_db=L90,
               bracket_check=dict(published=SRC['bracket_1m_left_db'][2], bracket_db=[lo, hi], inside={l: bool(lo <= v_ <= hi) for l, v_ in L90.items()},
                                  comment='a .22 pistol should sit near the bottom of the bracket; CCI Quiet-22 falls just below or near its lower edge, as a reduced load should'),
               subsonic=dict(note='all three loads leave the 102 mm barrel below the speed of sound (ballistics.json), so there is no ballistic crack in any shot', supersonic={l: P['loads'][l]['supersonic'] for l in P['loads']}),
               mechanical_peak_db_at_ear={c: round(db(float(np.max(np.abs(synth_mech(P, c))))), 1) for c in P['clips']}, levels=rows)
    os.makedirs(os.path.join(HERE, 'compare'), exist_ok=True); json.dump(chk, open(os.path.join(HERE, 'compare', 'check.json'), 'w'), indent=1)
    for l in rows: print('%-22s 1 m side %.1f dB | ear %.1f dB (over ground %.1f) | bystander %.1f | 25 m downrange %.1f | T+ %.2f ms' % (
        l, L90[l], rows[l]['shooter']['peak_db'], rows[l]['shooter']['peak_db_over_ground'], rows[l]['bystander']['peak_db'], rows[l]['downrange']['peak_db'], P['loads'][l]['t_pos'] * 1e3))
    print('bracket', chk['bracket_check']['inside'], '| mech', chk['mechanical_peak_db_at_ear'])
    if '--noplots' not in sys.argv:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 4)); col = dict(cci_standard_velocity='#1f6fb4', cci_mini_mag='#c0392b', cci_quiet_22='#2e8b57')
        for l in P['loads']:
            x = synth_dry(P, l, 'shooter', True); t = np.arange(len(x)) / FS * 1e3; ax[0].plot(t, x, color=col[l], lw=0.8, label=l); ax[1].plot(t, 20 * np.log10(np.maximum(np.abs(x), 1e-3) / P_REF), color=col[l], lw=0.6)
        ax[0].set_xlim(0, 12); ax[0].set_xlabel('time after the trigger break, ms'); ax[0].set_ylabel('pressure at the shooter\'s ear, Pa'); ax[0].legend(fontsize=7); ax[0].set_title('Simulated shot over open ground (blast and ground reflection)')
        ax[1].set_xlim(0, 60); ax[1].set_ylim(60, 160); ax[1].set_xlabel('time after the trigger break, ms'); ax[1].set_ylabel('level, dB re 20 uPa'); ax[1].set_title('Striker, blast, slide on the frame, slide closing')
        fig.tight_layout(); fig.savefig(os.path.join(HERE, 'compare', 'sim_shots.png'), dpi=110); plt.close(fig)
if __name__ == '__main__':
    main()

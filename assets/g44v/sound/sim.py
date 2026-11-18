#!/usr/bin/env python3
"""G44 V simulated sound, version 2.  Everything is synthesised from the action simulation and stated physics; nothing is a recording.

    python3 sim.py            # stage A: params.json (every derived table) + compare/check.json (levels against published figures)
    python3 sim.py render     # also writes listening WAVs into audio/ (ignored by git)
    python3 diagnose.py       # before and after: energy in time, band envelopes, playback mapping -> compare/before_after.json
    python3 verify_js.py      # parity of g44v-sound.js (stage B in the browser) against stage B here

Stage A turns ../action/action.json and ../model/inventory.json into tables: the blast waveform of each load, propagation paths per
perspective (delay, gain and a short filter for the ground and the air), modal tables of the mechanical sounds, room recipes.
Stage B (source_blast, source_mech, synth_dry, synth_mech, build_ir) turns tables into waveforms in pascals; g44v-sound.js is a port
of stage B with the same arithmetic and the same named random streams.
"""
import importlib.util, json, math, os, sys
import numpy as np
from scipy.special import wofz
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import metrics as M
ACT = json.load(open(os.path.join(HERE, '..', 'action', 'action.json')))
INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
FS = 48000; C0 = 343.2; RHO0 = 1.204; RHO_C = RHO0 * C0; P0 = 101325.0; P_REF = 20e-6; NFIR = 64; FIR_C = 20
db = M.db

# ------------------------------------------------------------------ inputs with their sources
SRC = dict(
    # --- published measurements (the calibration and the checks)
    meinke_pistol_ear=(dict(peak_db=157.5, sd=0.3, laeq8_db=78.1, barrel_in=4.5, mic_to_trigger_m=0.47, mic_height_m=1.10), 'published',
        'Meinke, Murphy, Finan, Lankford, Flamme, Stewart, Soendergaard, Jerome 2014, Int J Audiol 53 S2 (CDC stacks 36705), table 4: a .22 LR semi-automatic pistol with a 4.5 in barrel, 40 gr high-velocity lead round nose, '
        'fired outdoors standing with two hands; 1/8 in microphone at the left ear position, 47 cm from the trigger, 110 cm above the ground; mean of 5 shots'),
    meinke_rifles_ear=(dict(peak_db=[139.6, 143.0, 143.4, 143.8], barrel_in=[24, 18, 18, 18.5], laeq8_db=[63.8, 65.6, 66.5, 66.3]), 'published', 'same paper, table 2: four .22 rifles, same ammunition, same ear position'),
    murphy_pistol=(dict(muzzle_mic_db=160, ear_db=152, instructor_db=135, laeq8_muzzle_db=71, laeq8_ear_db=63, barrel_in=10, mic_left_of_muzzle_m=0.6, ear_mic_off_axis_m=0.35, mic_height_m=1.63, muzzle_height_m=1.53, lw_hv_db=150, lw_lv_db=145), 'published',
        'Murphy, Flamme, Campbell, Zechmann, Tasko, Lankford, Meinke, Finan, Stewart 2018, Int J Audiol 57 S1 S28-S41 (CDC stacks 211059), tables 2 to 4: a .22 LR semi-automatic pistol with a 10 in barrel, 40 gr rated 1280 ft/s, unsuppressed; '
        'pressure microphones 0.6 m left of the muzzle, 0.35 m either side of the firearm centre line at the ears, 1 m behind the head; LAeq8 over a 100 ms window; sound power by a 3 m hemisphere, 18 ms window'),
    murphy_rifle=(dict(muzzle_mic_hv_db=152, ear_hv_db=141, muzzle_mic_lv_db=149, ear_lv_db=140, barrel_in=20.75), 'published', 'same paper, table 2: a .22 LR bolt-action rifle, 1280 ft/s and 1050 ft/s ammunition. The barrel length (about 21 in) is the catalogue figure for that model, recalled, not from the paper'),
    murphy_a_duration=(0.2e-3, 'published', 'same paper, note 1: all of the unsuppressed A-durations were less than 0.2 ms'),
    murphy_suppressed_pistol_ear=(dict(peak_db=[128, 133], laeq8_db=[48, 49]), 'published', 'same paper: the suppressed pistol at the left and right ear. Everything that is not muzzle blast (action, port) is inside this, so it bounds the mechanical sound from above'),
    flamme_bracket=((149.0, 167.0), 'published', 'Flamme, Wong, Liebe, Lynd 2009, Noise Health 11:231: peak levels 1 m left of 15 recreational firearms ranged from 149 to 167 dB (as summarised in the 2018 paper)'),
    # --- blast physics
    efflux_exponent=(0.55, 'inferred', 'peak overpressure ~ (muzzle energy efflux rate)^0.55: blast scaling length ~ sqrt(efflux), peak ~ length^1.1 (Fansler and Schmidt muzzle blast scaling; recalled, not re-read). Tested here against five published barrel lengths'),
    decay_exponent=(1.1, 'inferred', 'peak ~ r^-1.1: weak-shock decay, same scaling'),
    directivity_db=(6.0, 'inferred', 'level(theta) = level(90 deg) + 6 cos(theta) dB. Tested against the published muzzle-to-ear difference of the 10 in pistol'),
    kinney_graham=('t+/W^(1/3) = 980 [1 + (Z/0.54)^10] / ([1 + (Z/0.02)^3] [1 + (Z/0.74)^6] sqrt(1 + (Z/6.9)^2)) ms; dp/p0 = 808 [1 + (Z/4.5)^2] / (sqrt(1 + (Z/0.048)^2) sqrt(1 + (Z/0.32)^2) sqrt(1 + (Z/1.35)^2))', 'published',
        'Kinney and Graham 1985, Explosive Shocks in Air: positive phase and peak of a free-air burst of W kg TNT (4.184 MJ/kg) at scaled distance Z = r / W^(1/3). Recalled, not re-read. Used with W = the internal energy of the propellant gas at bullet exit, p V / (gamma - 1)'),
    volume_source=('p(r, t) = rho0 / (4 pi r) d2V/dt2', 'published', 'far field of a compact volume source (Pierce, Acoustics, simple source). The gas leaving the muzzle displaces air at a rate that follows the energy efflux, so the pressure is positive while the flow builds, negative while it dies, and the two impulses cancel'),
    jet_efficiency=(0.005, 'inferred', 'share of the mechanical power of a supersonic jet radiated as sound: 0.2 to 1 % (Lighthill 1954; NASA SP-8072 uses about 0.5 % for rocket exhausts; recalled). A 0.3 ms blow-down is not an established jet, so this is an upper estimate'),
    jet_strouhal=(0.2, 'published', 'jet mixing noise peaks near f D_j / U_j = 0.2 (Tam 1995, Supersonic jet noise, Annu Rev Fluid Mech)'),
    rise_note=('band-limited to 20 kHz', 'numerical', 'the shock is built at 16 x 48 kHz and low-passed; a 48 kHz system shows a lower peak than the 200 to 800 kHz systems of the published measurements (see check.json, sampled_peak_loss_db)'),
    # --- propagation
    ground_sigma=(200e3, 'inferred', 'flow resistivity of range ground, Pa s/m2: mown grass over soil is 150 to 300 kPa s/m2 (Embleton, Piercy, Daigle 1983). Impedance by Delany and Bazley 1970; spherical-wave reflection by Chien and Soroka 1975'),
    ground_scatter=(0.2, 'inferred', 'share of the energy striking rough grassy ground that is scattered diffusely (Lambert law) rather than reflected like a mirror. Not measured'),
    source_height=(1.5, 'published', 'muzzle 1.53 m above the ground for a standing shooter (Murphy 2018)'),
    atmosphere=((20.0, 50.0), 'stated', '20 C, 50 % relative humidity, 101.325 kPa; air absorption by ISO 9613-1'),
    # --- mechanical sound
    radiation_efficiency=(3.2e-4, 'calibrated', 'share of an impact\'s lost energy that leaves as sound. Set so the mechanical sound of the high-velocity load at the ear has the exposure by which the port-side ear exceeds the other ear on the published suppressed pistol (LAE 93.6 against 92.6 dB: 86.7 dB for the action alone, if the asymmetry is the action). That pistol has a different bolt, so this is an estimate'),
    polymer=(dict(E=3.0e9, rho=1380.0, nu=0.39, eta=0.04), 'inferred', 'frame and magazine: polyamide 6, conditioned (handbook 2 to 3.5 GPa, loss factor 0.02 to 0.06); density as in model/build.py'),
    slide_material=(dict(E=2.0e10, rho=2600.0, eta=0.03), 'inferred', 'the slide is steel rails and breech in polymer; effective bending stiffness is a guess, density is the model\'s'),
    steel=(dict(E=2.05e11, rho=7850.0, eta=0.01), 'published', 'handbook steel; the loss factor is for a part held in an assembly, inferred'),
    hand_damping=(2.0, 'inferred', 'a gripped pistol: loss factors of the frame and magazine doubled'),
    wall_mm=(dict(grip=2.5, magazine=1.5, slide=2.5), 'inferred', 'wall thicknesses; not measured'),
    contact_radius=(0.005, 'inferred', 'radius of the contact patches for the Hertz contact time'),
    friction_efficiency=(1.0e-3, 'inferred', 'share of the rail friction power (2 N x slide speed, action.json) radiated as sound'),
    trigger_reset_time=(0.13, 'inferred', 'the shooter lets the trigger forward about 0.1 s after the shot; shooter cadence, not physics. action/ does not simulate the release'),
)
sv = lambda k: SRC[k][0]

# ------------------------------------------------------------------ gas dynamics of the muzzle (same lumped blow-down as action/sim.py)
AP = {k: v['value'] for k, v in ACT['params'].items()}
G = AP['gamma']; BORE = AP['bore_area']
def exit_state(p_exit, travel, charge):
    V = AP['chamber_vol'] + BORE * travel - AP['covolume'] * charge
    return dict(p=p_exit, V=V, m=charge, RT=p_exit * V / charge, E_gas=p_exit * V / (G - 1))
def blowdown(st, dt=1e-6, t_end=4e-3):
    """isentropic emptying of the bore through a sonic muzzle: time, energy efflux (W), mechanical power of the fully expanded jet (W), its speed and diameter"""
    cf = math.sqrt(G) * (2 / (G + 1)) ** ((G + 1) / (2 * (G - 1))); m = st['m']; out = []
    pcrit = P0 * ((G + 1) / 2) ** (G / (G - 1)); t = 0.0
    while t < t_end:
        r = m / st['m']; p = st['p'] * r ** G; RT = st['RT'] * r ** (G - 1)
        if p <= pcrit: break
        md = BORE * p / math.sqrt(RT) * cf
        uj = math.sqrt(2 * G / (G - 1) * RT * (1 - (P0 / p) ** ((G - 1) / G))); mj = uj / math.sqrt(G * RT * (P0 / p) ** ((G - 1) / G))
        ar = (1 / mj) * ((2 / (G + 1)) * (1 + (G - 1) / 2 * mj * mj)) ** ((G + 1) / (2 * (G - 1)))
        out.append((t, md * G / (G - 1) * RT, 0.5 * md * uj * uj, uj, math.sqrt(4 * BORE * max(ar, 1.0) / math.pi)))
        m -= md * dt; t += dt
    return np.array(out).T
def kg_duration(E, r):
    W3 = (E / 4.184e6) ** (1 / 3); Z = r / W3
    return W3 * 980 * (1 + (Z / 0.54) ** 10) / ((1 + (Z / 0.02) ** 3) * (1 + (Z / 0.74) ** 6) * math.sqrt(1 + (Z / 6.9) ** 2)) * 1e-3
def kg_peak(E, r):
    Z = r / (E / 4.184e6) ** (1 / 3)
    return P0 * 808 * (1 + (Z / 4.5) ** 2) / (math.sqrt(1 + (Z / 0.048) ** 2) * math.sqrt(1 + (Z / 0.32) ** 2) * math.sqrt(1 + (Z / 1.35) ** 2))
def fnv1a(s):
    h = 0x811c9dc5
    for c in s.encode():
        h ^= c; h = (h * 0x01000193) & 0xFFFFFFFF
    return h
UP = 16
def blast_table(st, peak_pa, t_exit, name):
    """the blast at 1 m, 90 degrees, in pascals, sampled at FS from sample floor(t_exit FS):
    Friedlander positive phase (duration from Kinney and Graham with the exit gas energy), a negative phase that follows the decay of the
    blow-down (volume source: equal and opposite impulse), and the jet noise of the blow-down."""
    T = kg_duration(st['E_gas'], 1.0); bd = blowdown(st); dt = 1.0 / (FS * UP); n = int(6e-3 / dt); t = np.arange(n) * dt
    pos = np.where(t < T, (1 - t / T) * np.exp(-t / T), 0.0); imp = np.trapezoid(pos, dx=dt)
    edot = np.interp(t, bd[0], bd[1], right=0.0); g = -np.gradient(edot, dt); g[g < 0] = 0; g /= np.trapezoid(g, dx=dt)
    ks = np.exp(-t[:int(4 * T / dt)] / (T / 2)); ks /= ks.sum(); h = np.convolve(g, ks)[:n]; h /= np.trapezoid(h, dx=dt)
    neg = np.zeros(n); k0 = int(round(T / dt)); neg[k0:] = -imp * h[:n - k0]
    blast = peak_pa * (pos + neg)
    # jet noise: white noise shaped to the Strouhal spectrum, with the rms that the jet's acoustic power gives at 1 m
    wj = np.interp(t, bd[0], bd[2], right=0.0); prms = np.sqrt(sv('jet_efficiency') * wj * RHO_C / (4 * math.pi))
    fp = float(np.sum(bd[2] * sv('jet_strouhal') * bd[3] / bd[4]) / np.sum(bd[2]))
    rng = np.random.Generator(np.random.PCG64(fnv1a('jet|' + name))); w = rng.standard_normal(n); f = np.fft.rfftfreq(n, dt)
    shape = (f / fp) ** 2 / (1 + (f / fp) ** 2) ** 2.5; W = np.fft.irfft(np.fft.rfft(w) * np.sqrt(shape), n); W /= np.sqrt(np.mean(W * W)); jet = prms * W
    # band-limit to 20 kHz and sample at FS with the right sub-sample offset
    off = (t_exit * FS - math.floor(t_exit * FS)) / FS; m = 12 * UP; kk = np.arange(-m, m + 1); fc = 20000.0 / (FS * UP / 2)
    lp = fc * np.sinc(fc * kk) * np.kaiser(2 * m + 1, 9.0); lp /= lp.sum()
    def samp(x):
        y = np.convolve(np.concatenate([np.zeros(int(round(off / dt)) + m), x]), lp)[m:]       # y[k]: time k dt - m dt, the waveform starting at off
        return y[::UP][:int(5.5e-3 * FS)]
    tb = samp(blast + jet); only = samp(blast)
    return dict(T=T, fp=fp, table=tb, pre=m // UP, sampled_peak=float(np.max(np.abs(only))), neg_depth=float(neg.min() * peak_pa / peak_pa), jet_energy_ratio=float(np.sum(jet ** 2) / np.sum(blast ** 2)),
                e_free_1m=float(np.sum(blast ** 2) * dt / RHO_C), tau_blowdown=float(np.trapezoid(edot, dx=dt) / edot[0]))

# ------------------------------------------------------------------ propagation: filters for the air and the ground
def air_db_per_m(f, T=293.15, hr=50.0):
    T0 = 293.15; psat = 10 ** (-6.8346 * (273.16 / T) ** 1.261 + 4.6151); h = hr * psat
    fo = 24 + 4.04e4 * h * (0.02 + h) / (0.391 + h); fn = (T / T0) ** -0.5 * (9 + 280 * h * math.exp(-4.170 * ((T / T0) ** (-1 / 3) - 1)))
    return 8.686 * f * f * (1.84e-11 * (T / T0) ** 0.5 + (T / T0) ** -2.5 * (0.01275 * math.exp(-2239.1 / T) / (fo + f * f / fo) + 0.1068 * math.exp(-3352.0 / T) / (fn + f * f / fn)))
FGRID = np.fft.rfftfreq(512, 1.0 / FS)
def ground_q(r2, psi):
    """spherical-wave reflection coefficient of the ground along a path of length r2 at grazing angle psi (exp(-i w t) convention)"""
    f = np.maximum(FGRID, 20.0); X = RHO0 * f / sv('ground_sigma'); Z = 1 + 0.0571 * X ** -0.754 + 1j * 0.087 * X ** -0.732
    Rp = (Z * math.sin(psi) - 1) / (Z * math.sin(psi) + 1); k = 2 * math.pi * f / C0; w = np.sqrt(0.5j * k * r2) * (math.sin(psi) + 1 / Z)
    return Rp + (1 - Rp) * (1 + 1j * math.sqrt(math.pi) * w * wofz(w))
def fir_design(H, frac):
    """NFIR taps whose response is H (given on FGRID, exp(-i w t) convention) delayed by FIR_C + frac samples"""
    Hn = np.conj(H) * np.exp(-2j * math.pi * FGRID / FS * (FIR_C + frac)); Hn = Hn * np.clip((23500.0 - FGRID) / 3500.0, 0.0, 1.0)
    h = np.fft.irfft(Hn, 512)[:NFIR]; w = np.ones(NFIR); n = np.arange(NFIR); w[:8] = np.sin(0.5 * math.pi * (n[:8] + 0.5) / 8) ** 2; w[-16:] = np.cos(0.5 * math.pi * (n[:16] + 0.5) / 16) ** 2
    return h * w
def one_path(r, extra_gain, Q=None):
    A = 10 ** (-np.array([air_db_per_m(f) for f in FGRID]) * r / 20); H = A if Q is None else A * Q
    d = r / C0 * FS - FIR_C; n = int(math.floor(d))
    return dict(n=n, gain=round(extra_gain, 6), fir=[round(float(v), 7) for v in fir_design(H, d - n)])
def paths(src, lis, hs, hl, directive):
    """direct and ground-reflected path from a source to a listener (positions in the gun frame: +Z downrange, +X left, +Y up; heights above the ground)"""
    x, y, z = (lis[i] - src[i] for i in range(3)); r = math.sqrt(x * x + y * y + z * z); horiz = math.sqrt(x * x + z * z); rg = math.sqrt(horiz ** 2 + (hs + hl) ** 2)
    def lvl(rr, zz): return (1.0 / rr) ** sv('decay_exponent') * 10 ** (sv('directivity_db') * (zz / rr) / 20) if directive else 1.0 / rr
    return dict(r=round(r, 4), theta_deg=round(math.degrees(math.acos(z / r)), 2), direct=one_path(r, lvl(r, z)), ground=one_path(rg, lvl(rg, z), ground_q(rg, math.atan2(hs + hl, horiz))))
def scatter(src, lis, hs, hl):
    """diffuse (Lambert) scatter from rough ground: energy arriving per 0.5 ms, relative to a unit source at 1 m, as an amplitude envelope"""
    d = sv('ground_scatter'); step = 0.05; half = 9.0; xs = np.arange(-half, half, step) + step / 2; X, Zg = np.meshgrid(xs, xs)
    sx, sz = src[0], src[2]; d1 = np.sqrt((X - sx) ** 2 + (Zg - sz) ** 2 + hs ** 2); d2 = np.sqrt((X - lis[0]) ** 2 + (Zg - lis[2]) ** 2 + hl ** 2)
    dirg = 10 ** (sv('directivity_db') * ((Zg - sz) / d1) / 10)
    e = d / math.pi * (hs / d1) * (hl / d2) / (d1 ** 2.2 * d2 ** 2) * dirg * step * step; tt = (d1 + d2) / C0; bin_s = 0.0005
    t0 = math.floor(tt.min() / bin_s); idx = (tt / bin_s).astype(int) - t0; nb = 60; env = np.bincount(idx[idx < nb], weights=e[idx < nb], minlength=nb)[:nb]
    return dict(n0=int(t0 * bin_s * FS), bin=int(bin_s * FS), amp=[round(float(math.sqrt(v / (bin_s * FS))), 7) for v in env], energy_ratio_1m=float(env.sum()))

# ------------------------------------------------------------------ mechanical sound: structure, impacts
def geometry():
    p = {k: v['value'] for k, v in INV['params'].items()}; parts = {q['name']: q for q in INV['parts']}
    def box(n, ax): b = parts[n]['bbox_mm'][ax]; return (b[1] - b[0]) * 1e-3
    return dict(slide_len=p.get('slide_len', 174.0) * 1e-3, slide_h=(p.get('slide_top', 11.75) - p.get('slide_bot', -9.2)) * 1e-3, slide_w=2 * p.get('slide_half_w', 12.75) * 1e-3,
                barrel_od=p.get('barrel_od', 13.0) * 1e-3, bore_d=p.get('bore_groove_d', 5.6) * 1e-3, barrel_free=(p.get('muzzle', 174.3) - 98.6) * 1e-3,
                frame_len=box('p17_frame', 'L'), frame_w=box('p17_frame', 'S'), grip_h=0.080, grip_d=0.050, dust_cover_h=0.020,
                mag_len=box('p31_magazine_tube', 'Z'), mag_d=0.030, spring_mass=parts['p03_recoil_spring']['mass_g'] * 1e-3, mag_spring_mass=parts['p33_magazine_spring']['mass_g'] * 1e-3)
def structure():
    """modes of the parts that ring: frequency (Hz), loss factor, body.  Beam and plate theory (Blevins, Formulas for Natural Frequency and Mode Shape) on the dimensions of model/inventory.json."""
    g = geometry(); pm = sv('polymer'); st = sv('steel'); sl = sv('slide_material'); wl = sv('wall_mm'); hd = sv('hand_damping'); modes = []
    FF = (22.373, 61.673, 120.903); CL = (3.516, 22.034, 61.697)
    def beam(body, lams, L, E, rho, rg, eta, n): modes.extend(dict(body=body, f=lam / (2 * math.pi * L * L) * math.sqrt(E / rho) * rg, eta=eta) for lam in lams[:n])
    def plate(body, a, b, h, m_, eta):
        D = m_['E'] * h ** 3 / (12 * (1 - m_['nu'] ** 2))
        modes.extend(dict(body=body, f=math.pi / 2 * math.sqrt(D / (m_['rho'] * h)) * (i * i / a ** 2 + j * j / b ** 2), eta=eta) for i, j in ((1, 1), (2, 1), (1, 2)))
    def rg_channel(h, w, t): return math.sqrt((w * h ** 3 - (w - 2 * t) * (h - 2 * t) ** 3) / 12 / (w * h - (w - 2 * t) * (h - 2 * t)))
    plate('grip', g['grip_h'], g['grip_d'], wl['grip'] * 1e-3, pm, pm['eta'] * hd)                                                           # side panels of the hollow grip
    beam('frame', FF, g['frame_len'], pm['E'], pm['rho'], rg_channel(g['dust_cover_h'], g['frame_w'], wl['grip'] * 1e-3), pm['eta'] * hd, 3)  # frame bending, free-free
    beam('slide', FF, g['slide_len'], sl['E'], sl['rho'], rg_channel(g['slide_h'], g['slide_w'], wl['slide'] * 1e-3), sl['eta'], 3)           # slide bending, free-free
    beam('barrel', CL, g['barrel_free'], st['E'], st['rho'], 0.25 * math.hypot(g['barrel_od'], g['bore_d']), st['eta'], 2)                    # barrel ahead of the locking block, clamped-free
    plate('magazine', g['mag_len'], g['mag_d'], wl['magazine'] * 1e-3, pm, 0.1)                                                               # magazine wall; rounds and spring damp it (inferred 0.1)
    k = (AP['spring_F1'] - AP['spring_F0']) / AP['travel']
    modes.extend(dict(body='spring', f=n / 2.0 * math.sqrt(k / g['spring_mass']), eta=0.02) for n in (1, 2, 3))                               # surge waves of the recoil spring
    modes.extend(dict(body='case', f=f, eta=0.004) for f in (9000.0, 15000.0))                                                                # ovalling of the thin brass case (inferred)
    return [dict(body=m['body'], f=round(m['f'], 1), eta=m['eta']) for m in modes if m['f'] < 20000]
STRUCT = structure()
def hertz_time(m_red, v, E1, E2, nu=0.3):
    """contact time of a Hertz impact (Johnson, Contact Mechanics): 2.87 (m^2 / (R E*^2 v))^(1/5)"""
    Es = 1 / ((1 - nu ** 2) / E1 + (1 - nu ** 2) / E2); return 2.87 * (m_red ** 2 / (sv('contact_radius') * Es ** 2 * max(v, 0.05))) ** 0.2
def impact(t, energy_J, tau_c, bodies, noise=0.15):
    """an impact that loses energy_J with contact time tau_c, exciting `bodies` ({body: coupling}).
    Modal weights: force spectrum of a half-sine contact x radiation efficiency of a small source x coupling / (f eta).  Amplitudes are pascals at 1 m."""
    Eac = sv('radiation_efficiency') * energy_J; ws = []
    for m in STRUCT:
        if m['body'] not in bodies: continue
        x = 2 * m['f'] * tau_c; F2 = (math.cos(math.pi * m['f'] * tau_c) / (1 - x * x)) ** 2 if abs(x - 1) > 1e-3 else (math.pi / 4) ** 2
        ka = 2 * math.pi * m['f'] / C0 * 0.06; ws.append((m, bodies[m['body']] * F2 * ka * ka / (1 + ka * ka) / (m['f'] * m['eta'])))
    tot = sum(w for _, w in ws) or 1.0; modes = []
    for m, w in ws:
        tau = 1 / (math.pi * m['f'] * m['eta']); a = math.sqrt(w / tot * (1 - noise) * Eac * RHO_C / (math.pi * tau))
        if a > 1e-4: modes.append(dict(f=m['f'], tau=round(tau, 6), a=round(a, 6)))
    tn = max(tau_c, 0.0003); fc = min(0.45 * FS, 1.0 / tau_c)
    return dict(t=round(t, 6), modes=modes, noise=dict(a=round(math.sqrt(noise * Eac * RHO_C / (2 * math.pi * tn)), 6), tau=round(tn, 6), lp=round(1 - math.exp(-2 * math.pi * fc / FS), 6)))
ALL = dict(grip=1.0, frame=1.0, slide=1.0, barrel=0.5, magazine=0.5, spring=0.05)
def shot_mech(L):
    """the mechanical events of one shot, timed and sized from action.json"""
    ev = L['events']; ms = AP['m_slide']; mg = AP['m_pistol'] + AP['m_magazine'] + 0.5; mu = ms * mg / (ms + mg); st = sv('steel')['E']; pm = sv('polymer')['E']; cy = L['cycle']
    v_at = lambda t: abs(float(np.interp(t, np.arange(len(cy['slide_mps'])) * cy['dt'], cy['slide_mps'])))
    out = [('firing pin on the rim', impact(ev['striker_hits'], ACT['firing']['energy_J'], 2 * AP['rim_crush'] / ACT['firing']['impact_speed_mps'], dict(slide=1.0, barrel=1.0, frame=0.3)))]
    v = ev['eject_slide_speed']; out.append(('case on the ejector', impact(ev['eject'], 0.5 * AP['m_case'] * v * v, hertz_time(AP['m_case'], v, 1.1e11, st), dict(case=1.0, slide=0.3, frame=0.3))))
    if 'rear_stop' in ev:
        v = ev['rear_stop_speed']; out.append(('slide on the frame', impact(ev['rear_stop'], 0.5 * mu * v * v * (1 - AP['e_rear'] ** 2), hertz_time(mu, v, st, pm), ALL)))
    v = v_at(ev['feed_pick_up']); mr = AP['m_cartridge'] * ms / (AP['m_cartridge'] + ms)
    out.append(('breech picks up the next round', impact(ev['feed_pick_up'], 0.5 * mr * v * v, hertz_time(mr, v, 1.1e11, st), dict(magazine=1.0, slide=0.5, grip=0.5, case=0.2))))
    v = v_at(ev['firing_pin_caught']); out.append(('firing pin caught by the trigger bar', impact(ev['firing_pin_caught'], 0.3 * 0.5 * AP['m_striker'] * v * v, hertz_time(AP['m_striker'], v, st, st), dict(slide=1.0, frame=0.5))))
    v = ev['closing_speed']; out.append(('slide closes on the barrel', impact(ev['in_battery'], 0.5 * mu * v * v * (1 - AP['e_front'] ** 2), hertz_time(mu, v, st, st), dict(ALL, barrel=1.0))))
    out.append(('magazine stack rises', impact(ev['in_battery'] + 0.008, 0.04, 0.0004, dict(magazine=1.0, grip=0.5))))
    out.append(('trigger reset', impact(sv('trigger_reset_time'), 0.004, hertz_time(0.004, 0.5, st, st), dict(frame=1.0, grip=0.5))))
    # rail friction: noise whose rms follows sqrt(friction power), 1 ms steps
    n = int(ev['in_battery'] / 0.001) + 1; env = [round(math.sqrt(sv('friction_efficiency') * AP['slide_friction'] * v_at(i * 0.001) * RHO_C / (4 * math.pi)), 5) for i in range(n)]
    return [dict(e, name=nm) for nm, e in out], dict(t=0.0, step=int(0.001 * FS), env=env, lp=0.45, hp=0.12)
def hand_clips():
    """hand-operated clips, with the same impact builder; hand speeds and small energies are inferred"""
    F0, F1, U, UL, ms = AP['spring_F0'], AP['spring_F1'], AP['travel'], AP['lock_open'], AP['m_slide']; st = sv('steel')['E']; pm = sv('polymer')['E']
    Esp = (F0 + F1) / 2 * U; v_close = math.sqrt(2 * (Esp - 0.3) / ms); v_rel = math.sqrt(2 * ((F0 + F0 + (F1 - F0) * UL / U) / 2 * UL - 0.3) / ms)
    vh = 1.5; t_pull = U / (2 / math.pi * vh); t_rel = t_pull + 0.03; t_home = t_rel + 2 * U / v_close; v_feed = v_close * math.sqrt((U - AP['u_feed']) / U)
    fr = lambda n, f: [round(math.sqrt(sv('friction_efficiency') * AP['slide_friction'] * f(i * 0.001) * RHO_C / (4 * math.pi)), 5) for i in range(n)]
    pull = lambda t: vh * math.sin(math.pi * t / t_pull) if t < t_pull else (v_close * (t - t_rel) / (t_home - t_rel) if t_rel < t < t_home else 0.0)
    click = lambda t, e: impact(t, e, hertz_time(0.004, 0.5, st, st), dict(frame=1.0, grip=0.5))
    rear = lambda t: impact(t, 0.5 * ms * 1.0 ** 2, hertz_time(ms, 1.0, st, pm), ALL)
    home = lambda t, v: impact(t, 0.5 * ms * v * v * (1 - AP['e_front'] ** 2), hertz_time(ms, v, st, st), dict(ALL, barrel=1.0))
    feed = lambda t, v: impact(t, 0.5 * AP['m_cartridge'] * v * v, hertz_time(AP['m_cartridge'], v, 1.1e11, st), dict(magazine=1.0, slide=0.5, grip=0.5, case=0.2))
    mag = lambda t, e: impact(t, e, 0.0004, dict(magazine=1.0, grip=1.0, frame=0.3))
    case = lambda t, e: impact(t, e, 0.00005, dict(case=1.0))
    t_feed = t_rel + (t_home - t_rel) * math.sqrt((U - AP['u_feed']) / U)
    return dict(
        trigger=dict(events=[click(0.0, 0.004)]),
        dry_fire=dict(events=[click(0.0, 0.004), impact(ACT['firing']['lock_time_s'], ACT['firing']['energy_J'], 0.00005, dict(slide=1.0, barrel=1.0, frame=0.3))]),
        slide_rack=dict(events=[rear(t_pull), feed(t_feed, v_feed), home(t_home, v_close), mag(t_home + 0.008, 0.04)], friction=dict(t=0.0, step=int(0.001 * FS), env=fr(int(t_home * 1000) + 1, pull), lp=0.45, hp=0.12)),
        slide_lock_open=dict(events=[rear(t_pull), click(t_pull + 0.05, 0.02)], friction=dict(t=0.0, step=int(0.001 * FS), env=fr(int(t_pull * 1000) + 1, pull), lp=0.45, hp=0.12)),
        slide_release=dict(events=[click(0.0, 0.01), feed(2 * UL / v_rel * 0.5, v_rel * 0.6), home(2 * UL / v_rel, v_rel), mag(2 * UL / v_rel + 0.008, 0.04)]),
        magazine_out=dict(events=[click(0.0, 0.01), mag(0.03, 0.02)]),
        magazine_in=dict(events=[mag(0.0, 0.05), click(0.012, 0.01)]),
        case_ground=dict(events=[case(0.0, 0.6e-3 * 9.81 * 1.4 * 0.5), case(0.11, 0.6e-3 * 9.81 * 1.4 * 0.06)])), 'hand speeds (1.5 m/s rack) and small click energies are inferred; closing speeds follow from the recoil spring loads in action.json'

# ------------------------------------------------------------------ stage A
def action_sim():
    spec = importlib.util.spec_from_file_location('g44v_action_sim', os.path.join(HERE, '..', 'action', 'sim.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def efflux(st): return float(blowdown(st, t_end=2e-6)[1][0])
def reference_guns():
    """exit states of the published firearms: the same interior ballistics as the pistol (action/sim.py), other barrel lengths.  The nearest simulated load stands in for each published one."""
    A = action_sim(); out = {}
    for key, barrel_in, load in (('meinke_pistol_4.5in', 4.5, 'cci_mini_mag'), ('murphy_pistol_10in', 10.0, 'cci_mini_mag'), ('murphy_rifle_hv', 20.75, 'cci_mini_mag'), ('murphy_rifle_lv', 20.75, 'cci_standard_velocity'),
                                 ('meinke_rifle_18in', 18.0, 'cci_mini_mag'), ('meinke_rifle_24in', 24.0, 'cci_mini_mag')):
        c = ACT['loads'][load]['calibrated']; travel = barrel_in * 0.0254 - AP['case_len']
        ib = A.interior(dict(charge=ACT['loads'][load]['guessed']['charge_kg']), travel, c['burn_coeff'], c['loss_factor'], dt=1e-6, post=0)
        out[key] = dict(state=exit_state(ib['p_exit'], travel, ACT['loads'][load]['guessed']['charge_kg']), v_exit=ib['v_exit'], load=load, barrel_in=barrel_in)
    return out
HS = sv('source_height')
EAR_SIDE = 0.08
def stage_a():
    refs = reference_guns()
    # --- one calibration: the published 4.5 in pistol at the ear fixes the level constant
    mk = sv('meinke_pistol_ear'); d_ax = math.sqrt(mk['mic_to_trigger_m'] ** 2 - EAR_SIDE ** 2) + 0.13; r_mk = math.hypot(d_ax, EAR_SIDE); cos_mk = -d_ax / r_mk
    q_ref = efflux(refs['meinke_pistol_4.5in']['state'])
    L_ref_1m90 = mk['peak_db'] - sv('directivity_db') * cos_mk - 20 * sv('decay_exponent') * math.log10(1.0 / r_mk)
    peak_1m90 = lambda st: P_REF * 10 ** ((L_ref_1m90 + 20 * sv('efflux_exponent') * math.log10(efflux(st) / q_ref)) / 20)
    loads = {}; aux = {}
    for k, L in ACT['loads'].items():
        st = exit_state(L['pistol']['muzzle_pressure_MPa'] * 1e6, AP['bullet_travel'], L['guessed']['charge_kg']); pk = peak_1m90(st); tx = L['events']['bullet_exit']; bt = blast_table(st, pk, tx, k)
        mech, fric = shot_mech(L)
        loads[k] = dict(label=L['label'], t_blast=round(tx, 6), n_blast=int(math.floor(tx * FS)) - bt['pre'], efflux_W=round(efflux(st)), gas_energy_J=round(st['E_gas'], 1), peak_pa_1m_90=round(pk, 3), peak_db_1m_90=round(db(pk), 2),
                        t_pos=round(bt['T'], 7), jet_peak_hz=round(bt['fp']), supersonic=bool(L['pistol']['muzzle_velocity_mps'] > C0), blast=[round(float(v), 4) for v in bt['table']], mech=mech, friction=fric)
        aux[k] = dict(bt, state=st)
    # --- perspectives: sources are the muzzle (blast) and the middle of the slide (mechanical), HS above the ground
    sock = {s['name']: s['pos_m_export'] for s in INV['sockets']}; mz = sock['socket_muzzle']; eye = sock['socket_ads_eye']; ch = sock['socket_chamber']
    listeners = dict(shooter=(mz[0] - EAR_SIDE, eye[1], eye[2]), bystander=(mz[0] + 3.0, mz[1] + 0.1, mz[2] - 0.3), downrange=(mz[0] + 2.0, mz[1], mz[2] + 25.0))
    notes = dict(shooter='the shooter\'s right ear: at the eye socket of the model, 8 cm to the side', bystander='3 m to the shooter\'s left, level with the pistol', downrange='25 m downrange, 2 m beside the line of fire')
    persp = {}
    for name, lis in listeners.items():
        hl = HS + lis[1] - mz[1]; b = paths(mz, lis, HS, hl, True); m = paths(ch, lis, HS + ch[1] - mz[1], hl, False); sc = scatter(mz, lis, HS, hl)
        persp[name] = dict(r=b['r'], theta_deg=b['theta_deg'], note=notes[name], blast=dict(direct=b['direct'], ground=b['ground']), mech=dict(direct=m['direct'], ground=m['ground']),
                           scatter=dict(n0=sc['n0'], bin=sc['bin'], amp=sc['amp']), scatter_energy_ratio_1m=round(sc['energy_ratio_1m'], 6))
    clips, clip_notes = hand_clips()
    # --- surroundings as impulse responses for the shooter (the dry free-field shot is the convolver input, so the ground is part of each)
    sh = persp['shooter']['blast']; gd = sh['direct']['gain']
    def shoebox(dims, src, lis, alpha, order=2):
        Lx, Ly, Lz = dims; taps = []; d0 = math.dist(src, lis)
        for nx in range(-order, order + 1):
            for ny in range(-order, order + 1):
                for nz in range(-order, order + 1):
                    n = abs(nx) + abs(ny) + abs(nz)
                    if n == 0 or n > order: continue
                    img = [(n_ * L_ + (s_ if n_ % 2 == 0 else L_ - s_)) for n_, L_, s_ in ((nx, Lx, src[0]), (ny, Ly, src[1]), (nz, Lz, src[2]))]
                    d = math.dist(img, lis); taps.append(dict(delay=round((d - d0) / C0, 6), gain=round(d0 / d * (1 - alpha) ** (n / 2), 5)))
        V = Lx * Ly * Lz; S = 2 * (Lx * Ly + Ly * Lz + Lx * Lz); return sorted(taps, key=lambda q: q['delay']), 0.161 * V / (S * alpha)
    taps, rt = shoebox((6.0, 3.0, 28.0), (3.0, 1.5, 2.0), (3.08, 1.57, 1.4), 0.35)
    g_rel = dict(n=sh['ground']['n'] - sh['direct']['n'] - FIR_C, gain=round(sh['ground']['gain'] / gd, 6), fir=sh['ground']['fir'])
    berm = (1 / 50.6) ** sv('decay_exponent') * 10 ** (sv('directivity_db') / 20) * 0.3 / gd
    overlays = dict(
        outdoor_berm=dict(note='open range, earth berm 25 m downrange: the ground (same reflection and scatter as the open-air shot) and a diffuse return from the berm (reflecting 0.3 of the pressure, inferred)', ground=g_rel, scatter=True,
                          taps=[dict(delay=round(50.0 / C0, 6), gain=round(berm, 5))], tail=dict(t0=round(50.0 / C0, 6), rt60=0.35, level=round(berm / 2, 5), lp=0.25)),
        indoor_range=dict(note='indoor range lane hall 6 x 3 x 28 m, mean absorption 0.35 (baffles and backstop): image sources to second order, then a Sabine tail', taps=taps,
                          tail=dict(t0=0.030, rt60=round(rt, 3), level=0.05, lp=0.4)))
    P = dict(meta=dict(title='G44 V simulated sound', version=2, credit='carpetshark', generator='sim.py', units='pascals at the listener; times in seconds from the trigger break'),
             fs=FS, c0=C0, fir_centre=FIR_C, sources={k: dict(value=v_[0], status=v_[1], source=v_[2]) for k, v_ in SRC.items()}, structure=STRUCT,
             calibration=dict(level_1m_90deg_of_reference_db=round(L_ref_1m90, 2), reference_efflux_W=round(q_ref), reference_ear=dict(r_m=round(r_mk, 3), theta_deg=round(math.degrees(math.acos(cos_mk)), 1))),
             loads=loads, perspectives=persp, clips=clips, clip_notes=clip_notes, overlays=overlays, dur_shot=0.20, dur_clip=0.30, ear_map_k=30.0)
    return P, dict(refs=refs, loads=aux, peak_1m90=peak_1m90, L_ref=L_ref_1m90, q_ref=q_ref)

# ------------------------------------------------------------------ stage B (ported in g44v-sound.js)
class Rng:      # mulberry32, the same stream as the JS
    def __init__(self, name): self.a = fnv1a(name)
    def next(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF; t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    def gauss(self):
        a = self.next(); b = self.next(); return math.sqrt(-2 * math.log(a + 1e-12)) * math.cos(2 * math.pi * b)
def add_impact(buf, fs, ev, t0, seed):
    te = t0 + ev['t']; n0 = max(0, int(math.floor(te * fs))); tmax = max([m['tau'] for m in ev['modes']] + [ev['noise']['tau']]) * 7; n1 = min(len(buf), n0 + int(tmax * fs) + 2)
    rng = Rng(seed); nz = ev['noise']; z = 0.0
    for n in range(n0, n1):
        t = n / fs - te
        if t < 0: continue
        x = 0.0
        for m in ev['modes']: x += m['a'] * math.exp(-t / m['tau']) * math.sin(2 * math.pi * m['f'] * t)
        z += nz['lp'] * (rng.gauss() - z); buf[n] += x + nz['a'] * math.exp(-t / nz['tau']) * z
def add_friction(buf, fs, fr, t0, seed):
    rng = Rng(seed); n0 = int(math.floor((t0 + fr['t']) * fs)); z = 0.0; y = 0.0; N = len(fr['env'])
    for i in range((N - 1) * fr['step']):
        k = i // fr['step']; u = (i - k * fr['step']) / fr['step']; e = fr['env'][k] + (fr['env'][k + 1] - fr['env'][k]) * u
        g = rng.gauss(); z += fr['lp'] * (g - z); y += fr['hp'] * (z - y)
        if 0 <= n0 + i < len(buf): buf[n0 + i] += e * (z - y) * 2.0
def source_blast(P, L, n):
    buf = [0.0] * n; tb = L['blast']
    for i in range(len(tb)):
        if 0 <= L['n_blast'] + i < n: buf[L['n_blast'] + i] += tb[i]
    return buf
def source_mech(P, events, friction, n, t0, seed):
    buf = [0.0] * n
    for j, ev in enumerate(events): add_impact(buf, P['fs'], ev, t0, '%s|%d' % (seed, j))
    if friction: add_friction(buf, P['fs'], friction, t0, seed + '|friction')
    return buf
def add_path(out, src, pth, extra=1.0):
    """out += gain * (src filtered by the path's FIR), delayed by the path's whole samples"""
    fir = pth['fir']; g = pth['gain'] * extra; N = len(out); nd = pth['n']
    y = np.convolve(np.asarray(src), np.asarray(fir))
    lo = max(0, -nd); hi = min(len(y), N - nd)
    if hi > lo: out[nd + lo:nd + hi] += g * y[lo:hi]
def scatter_kernel(sc, seed):
    rng = Rng(seed); k = [0.0] * (len(sc['amp']) * sc['bin']); z = 0.0
    for i in range(len(k)):
        g = rng.gauss(); z += 0.2 * (g - z); k[i] = sc['amp'][i // sc['bin']] * (g - z) * 1.118      # first-order high-pass (roughness scatters short waves); 1.118 restores unit power
    return k
def synth_parts(P, L, ps, field, seed):
    n = int(P['dur_shot'] * P['fs']); out = np.zeros(n); sb = source_blast(P, L, n); sm = source_mech(P, L.get('mech', []), L.get('friction'), n, 0.0, 'mech|' + seed)
    add_path(out, sb, ps['blast']['direct']); add_path(out, sm, ps['mech']['direct'])
    if field:
        add_path(out, sb, ps['blast']['ground']); add_path(out, sm, ps['mech']['ground'])
        if 'scatter' in ps:
            y = np.convolve(np.asarray(sb), np.asarray(scatter_kernel(ps['scatter'], 'scatter|' + seed))); n0 = ps['scatter']['n0']; hi = min(len(y), n - n0)
            if hi > 0: out[n0:n0 + hi] += y[:hi]
    return out
def synth_dry(P, load, persp='shooter', field=False):
    """one shot in pascals at the listener: free field (direct sound only), or over open ground (field: reflection and diffuse scatter)"""
    return synth_parts(P, P['loads'][load], P['perspectives'][persp], field, load)
def synth_mech(P, clip, persp='shooter'):
    C = P['clips'][clip]; n = int(P['dur_clip'] * P['fs']); out = np.zeros(n)
    add_path(out, source_mech(P, C['events'], C.get('friction'), n, 0.002, 'clip|' + clip), P['perspectives'][persp]['mech']['direct']); return out
def build_ir(P, overlay):
    """impulse response of the surroundings for the shooter: the direct path is the first sample, value 1"""
    O = P['overlays'][overlay]; fs = P['fs']; tl = O['tail']; n = int((tl['t0'] + tl['rt60'] * 1.1) * fs) + 1; h = [0.0] * n; h[0] = 1.0
    if 'ground' in O:
        g = O['ground']
        for i, v in enumerate(g['fir']):
            if 0 < g['n'] + i < n: h[g['n'] + i] += g['gain'] * v
    if O.get('scatter'):
        sc = P['perspectives']['shooter']['scatter']; k = scatter_kernel(sc, 'scatter|ir'); gd = P['perspectives']['shooter']['blast']['direct']; n0 = sc['n0'] - gd['n'] - P['fir_centre']
        for i, v in enumerate(k):
            if 0 < n0 + i < n: h[n0 + i] += v / gd['gain']
    for tp in O['taps']:
        k = int(math.floor(tp['delay'] * fs + 0.5))
        if 0 < k < n: h[k] += tp['gain']
    rng = Rng('ir|' + overlay); z = 0.0; k0 = int(tl['t0'] * fs)
    for k in range(k0, n):
        t = (k - k0) / fs; z += tl['lp'] * (rng.gauss() - z); h[k] += tl['level'] * z * math.exp(-6.907755 * t / tl['rt60'])
    return np.array(h)
def ear_map(x, k, peak=None):
    """the playback mapping of chain({ear: true}): normalise to -1 dBFS, low shelf +10 dB at 150 Hz (equal-loudness compensation, the Web Audio
    biquad), then asinh(k x) / asinh(k), times 0.85.  Not physics."""
    from scipy.signal import lfilter
    pk = float(np.max(np.abs(x))) if peak is None else peak; A = 10 ** (10 / 40.0); w0 = 2 * math.pi * 150.0 / FS; al = math.sin(w0) / 2 * math.sqrt(2.0); c = math.cos(w0); sq = 2 * math.sqrt(A) * al
    b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]; a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return 0.85 * np.arcsinh(k * lfilter(b, a, x * 10 ** (-1 / 20) / pk)) / math.asinh(k)
JOBS = lambda P: [['dry_%s_%s_%s' % (l, p, 'field' if f else 'free'), 'dry', l, p, f] for l in P['loads'] for p in P['perspectives'] for f in (False, True)] + \
                 [['mech_%s' % c, 'mech', c, 'shooter'] for c in P['clips']] + [['ir_%s' % o, 'ir', o] for o in P['overlays']]

# ------------------------------------------------------------------ checks against published figures
def checks(P, X):
    refs = X['refs']; res = {}
    def gun(key, lis, hl, hs=HS, field=True):
        st = refs[key]['state']; pk = X['peak_1m90'](st); bt = blast_table(st, pk, 0.003, key); L = dict(blast=[float(v) for v in bt['table']], n_blast=int(0.003 * FS) - bt['pre'])
        b = paths((0, 0, 0), lis, hs, hl, True); x = synth_parts(P, L, dict(blast=b, mech=b), field, key); r = math.sqrt(sum(v * v for v in lis))
        model_pk = db(pk * b['direct']['gain']); s = M.summary(x, FS)
        return dict(model_peak_db=round(model_pk, 1), sampled_48k_peak_db=s['peak_db'], a_duration_ms=s['a_duration_ms'], lae_db=s['lae_db'], laeq8_db=s['laeq8_db'], peak_minus_lae_db=round(model_pk - s['lae_db'], 1),
                    r_m=round(r, 3), theta_deg=b['theta_deg'], efflux_W=round(efflux(st)), exit_velocity_mps=round(refs[key]['v_exit']), stand_in_load=refs[key]['load'], barrel_in=refs[key]['barrel_in'])
    mp = sv('murphy_pistol'); mr = sv('murphy_rifle'); mk = sv('meinke_pistol_ear'); mrf = sv('meinke_rifles_ear'); dh = mp['mic_height_m'] - mp['muzzle_height_m']
    rows = []
    def row(name, pub, g, role, note=''): rows.append(dict(what=name, role=role, published_db=pub, model_db=g['model_peak_db'], error_db=round(g['model_peak_db'] - pub, 1), geometry=dict(r_m=g['r_m'], theta_deg=g['theta_deg']), barrel_in=g['barrel_in'], stand_in_load=g['stand_in_load'], note=note)); return g
    d_ax = math.sqrt(mk['mic_to_trigger_m'] ** 2 - EAR_SIDE ** 2) + 0.13
    g_mk = row('Meinke 2014: 4.5 in pistol, left ear', mk['peak_db'], gun('meinke_pistol_4.5in', (EAR_SIDE, 0, -d_ax), mk['mic_height_m'], hs=mk['mic_height_m']), 'calibration', 'muzzle taken 0.13 m ahead of the trigger (inferred)')
    g_pm = row('Murphy 2018: 10 in pistol, 0.6 m left of the muzzle', mp['muzzle_mic_db'], gun('murphy_pistol_10in', (0.6, dh, 0), mp['mic_height_m'], hs=mp['muzzle_height_m']), 'check')
    g_pe = row('Murphy 2018: 10 in pistol, at the ear', mp['ear_db'], gun('murphy_pistol_10in', (0.35, dh, -0.70), mp['mic_height_m'], hs=mp['muzzle_height_m']), 'check', 'ear taken 0.70 m behind the muzzle (inferred; the paper gives only the 0.35 m offset)')
    row('Murphy 2018: 21 in rifle, 1280 ft/s, 0.6 m left of the muzzle', mr['muzzle_mic_hv_db'], gun('murphy_rifle_hv', (0.6, dh, 0), mp['mic_height_m'], hs=mp['muzzle_height_m']), 'check')
    row('Murphy 2018: 21 in rifle, 1050 ft/s, 0.6 m left of the muzzle', mr['muzzle_mic_lv_db'], gun('murphy_rifle_lv', (0.6, dh, 0), mp['mic_height_m'], hs=mp['muzzle_height_m']), 'check')
    row('Murphy 2018: 21 in rifle, 1280 ft/s, at the ear', mr['ear_hv_db'], gun('murphy_rifle_hv', (0.35, dh, -0.85), mp['mic_height_m'], hs=mp['muzzle_height_m']), 'check', 'ear taken 0.85 m behind the muzzle (inferred)')
    row('Meinke 2014: 18 in rifles, left ear (143.0 to 143.8)', 143.4, gun('meinke_rifle_18in', (EAR_SIDE, 0, -0.76), 1.10, hs=1.10), 'check', 'ear taken 0.30 m behind the chamber (inferred)')
    row('Meinke 2014: 24 in rifle, left ear', mrf['peak_db'][0], gun('meinke_rifle_24in', (EAR_SIDE, 0, -0.91), 1.10, hs=1.10), 'check', 'ear taken 0.30 m behind the chamber (inferred)')
    errs = [r['error_db'] for r in rows if r['role'] == 'check']
    res['peak_levels'] = dict(note='one constant is calibrated (first row). Every other row is a prediction: the same interior ballistics run at the published barrel length, the same scaling and directivity. Published loads are replaced by the nearest simulated load.',
                              rows=rows, check_rms_error_db=round(float(np.sqrt(np.mean(np.square(errs)))), 2), check_worst_error_db=max(errs, key=abs))
    # --- the pistol itself
    lo, hi = sv('flamme_bracket'); L90 = {l: P['loads'][l]['peak_db_1m_90'] for l in P['loads']}
    res['pistol_1m_left'] = dict(published=SRC['flamme_bracket'][2], bracket_db=[lo, hi], model_db=L90, inside={l: bool(lo <= v <= hi) for l, v in L90.items()})
    # --- A-duration and exposure
    lim = sv('murphy_a_duration') * 1e3; ad = {}
    for l in P['loads']:
        st = X['loads'][l]['state']; b = paths((0, 0, 0), (0.6, dh, 0), mp['muzzle_height_m'], mp['mic_height_m'], True); x = synth_parts(P, dict(blast=P['loads'][l]['blast'], n_blast=P['loads'][l]['n_blast']), dict(blast=b, mech=b), True, l)
        s = M.summary(x, FS); ad[l] = dict(model_t_pos_ms=round(P['loads'][l]['t_pos'] * 1e3, 3), a_duration_through_48k_ms=s['a_duration_ms'], negative_phase=s['negative_phase'], peak_minus_lae_db=round(db(P['loads'][l]['peak_pa_1m_90'] * b['direct']['gain']) - s['lae_db'], 1),
                                       kinney_graham_free_burst_peak_db_1m=round(db(kg_peak(st['E_gas'], 1.0)), 1), model_peak_db_1m_90=P['loads'][l]['peak_db_1m_90'], blowdown_time_ms=round(X['loads'][l]['tau_blowdown'] * 1e3, 3),
                                       jet_noise_energy_re_blast_db_in_band=round(10 * math.log10(max(float(np.sum((np.array(P['loads'][l]['blast']) - 0) ** 2)) * 0 + X['loads'][l]['jet_energy_ratio'], 1e-9)), 1))
    res['a_duration'] = dict(published=SRC['murphy_a_duration'][2], limit_ms=lim, at='0.6 m left of the muzzle, over ground', by_load=ad, passes={l: bool(v['model_t_pos_ms'] < lim) for l, v in ad.items()},
                             note='model_t_pos is the positive phase of the model; the value seen through a 48 kHz system is longer because the shock is band-limited to 20 kHz. The Kinney-Graham peak of a free burst of all the exit gas energy must lie above the model peak (a muzzle puts only part of that energy into the blast): it does.')
    res['exposure'] = dict(note='peak minus A-weighted exposure level (LAE = LAeq8 + 44.6 dB). The two published studies differ by 10 dB; the model is compared with both and is not fitted to either.',
                           murphy_10in_pistol=dict(published_muzzle_mic=round(mp['muzzle_mic_db'] - (mp['laeq8_muzzle_db'] + 44.6), 1), published_ear=round(mp['ear_db'] - (mp['laeq8_ear_db'] + 44.6), 1), model_muzzle_mic=g_pm['peak_minus_lae_db'], model_ear=g_pe['peak_minus_lae_db']),
                           meinke_4p5in_pistol=dict(published_ear=round(mk['peak_db'] - (mk['laeq8_db'] + 44.6), 1), model_ear=g_mk['peak_minus_lae_db']),
                           sampled_peak_loss_db=round(g_pm['model_peak_db'] - g_pm['sampled_48k_peak_db'], 2))
    # --- sound power of the 10 in pistol (hemisphere over ground, 18 ms window)
    st = refs['murphy_pistol_10in']['state']; bt = blast_table(st, X['peak_1m90'](st), 0.003, 'lw'); a = sv('directivity_db') * math.log(10) / 10; dirm = math.sinh(a) / a
    E = bt['e_free_1m'] * (1 + bt['jet_energy_ratio']) * 4 * math.pi * dirm * 0.75
    res['sound_power'] = dict(published_db=mp['lw_hv_db'], model_db=round(10 * math.log10(E / 0.018 / 1e-12), 1), radiated_energy_J=round(E, 3),
                              note='model: blast and jet energy at 1 m, 90 degrees x the mean of the directivity over the sphere x 0.75 (half of it meets soft ground), over 18 ms. The model does not reproduce the published figure. '
                                   'The published 150 dB is 18 J of sound in 18 ms; the same paper\'s 160 dB peak and LAeq8 71 dB at 0.6 m give about 1.6 J for a uniform source. The low-frequency and forward content of the real blast may be larger than modelled; not resolved.')
    # --- mechanical sound against the suppressed-pistol bound
    sup = sv('murphy_suppressed_pistol_ear'); mech = {}
    for l in P['loads']:
        L = P['loads'][l]; x = synth_parts(P, dict(blast=[], n_blast=0, mech=L['mech'], friction=L['friction']), P['perspectives']['shooter'], True, l); mech[l] = dict(peak_db=round(db(np.max(np.abs(x))), 1), lae_db=round(M.sel(x, FS, True), 1))
    res['mechanical'] = dict(published=SRC['murphy_suppressed_pistol_ear'][2], bound_peak_db=max(sup['peak_db']), bound_lae_db=round(max(sup['laeq8_db']) + 44.6, 1), model_at_ear=mech,
                             below_bound={l: bool(v['peak_db'] < max(sup['peak_db']) and v['lae_db'] < max(sup['laeq8_db']) + 44.6) for l, v in mech.items()},
                             clips_peak_db_at_ear={c: round(db(float(np.max(np.abs(synth_mech(P, c))))), 1) for c in P['clips']})
    res['subsonic'] = dict(note='all three loads leave the 102 mm barrel below the speed of sound (ballistics.json), so there is no ballistic crack in any shot', supersonic={l: P['loads'][l]['supersonic'] for l in P['loads']})
    lv = {}
    for l in P['loads']:
        lv[l] = {}
        for p in P['perspectives']:
            x = synth_dry(P, l, p, False); xf = synth_dry(P, l, p, True); ps = P['perspectives'][p]
            lv[l][p] = dict(model_peak_db=round(db(P['loads'][l]['peak_pa_1m_90'] * ps['blast']['direct']['gain']), 2), sampled_48k_peak_db=round(db(np.max(np.abs(x))), 2), lae_db=round(M.sel(x, FS, True), 2), lae_over_ground_db=round(M.sel(xf, FS, True), 2))
    res['levels'] = lv
    return res

def write_wav(path, x, fs=FS):
    import wave
    y = np.clip(np.asarray(x), -1, 1); b = (y * 8388607).astype('<i4'); raw = b''.join(int(v).to_bytes(4, 'little', signed=True)[:3] for v in b)
    with wave.open(path, 'wb') as w: w.setnchannels(1); w.setsampwidth(3); w.setframerate(fs); w.writeframes(raw)
def render(P):
    """listening renders for the owner; audio/ is ignored by git"""
    out = os.path.join(HERE, 'audio'); os.makedirs(out, exist_ok=True); k = P['ear_map_k']; norm = lambda x: x * 10 ** (-1 / 20) / np.max(np.abs(x)); files = []
    pad = lambda x: np.concatenate([np.zeros(int(0.05 * FS)), x, np.zeros(int(0.3 * FS))])
    for l in P['loads']:
        dry = synth_dry(P, l, 'shooter', False); fld = synth_dry(P, l, 'shooter', True)
        for name, x in (('dry_free_field', dry), ('default_open_air', fld), ('outdoor_berm', np.convolve(dry, build_ir(P, 'outdoor_berm'))), ('indoor_range', np.convolve(dry, build_ir(P, 'indoor_range')))):
            write_wav(os.path.join(out, 'g44v_%s_%s_linear.wav' % (l, name)), pad(norm(x))); write_wav(os.path.join(out, 'g44v_%s_%s_as_played.wav' % (l, name)), pad(ear_map(x, k, float(np.max(np.abs(dry)))) if name != 'indoor_range' else ear_map(x, k)))
            files += ['g44v_%s_%s_linear.wav' % (l, name), 'g44v_%s_%s_as_played.wav' % (l, name)]
    for c in P['clips']: write_wav(os.path.join(out, 'g44v_clip_%s_as_played.wav' % c), pad(ear_map(synth_mech(P, c), k))); files.append('g44v_clip_%s_as_played.wav' % c)
    print('wrote %d WAV files to %s' % (len(files), out))
def main():
    P, X = stage_a(); json.dump(P, open(os.path.join(HERE, 'params.json'), 'w'), indent=None, separators=(',', ':'))
    chk = checks(P, X); os.makedirs(os.path.join(HERE, 'compare'), exist_ok=True); json.dump(chk, open(os.path.join(HERE, 'compare', 'check.json'), 'w'), indent=1)
    for r in chk['peak_levels']['rows']: print('%-62s published %6.1f  model %6.1f  %+5.1f  (%s)' % (r['what'], r['published_db'], r['model_db'], r['error_db'], r['role']))
    print('check rms error %.2f dB, worst %+.1f dB' % (chk['peak_levels']['check_rms_error_db'], chk['peak_levels']['check_worst_error_db']))
    for l, v in chk['a_duration']['by_load'].items(): print('%-22s 1 m side %.1f dB | T+ %.3f ms (48k: %.3f) | neg %s | peak-LAE %.1f | K-G bound %.1f dB | ear %s' % (l, P['loads'][l]['peak_db_1m_90'], v['model_t_pos_ms'], v['a_duration_through_48k_ms'], v['negative_phase'], v['peak_minus_lae_db'], v['kinney_graham_free_burst_peak_db_1m'], chk['levels'][l]['shooter']))
    print('exposure', chk['exposure']); print('sound power', chk['sound_power']['model_db'], 'published', chk['sound_power']['published_db']); print('mechanical', chk['mechanical'])
    print('structure', [(m['body'], m['f']) for m in STRUCT])
    if '--noplots' not in sys.argv:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(15, 4)); col = dict(cci_standard_velocity='#1f6fb4', cci_mini_mag='#c0392b', cci_quiet_22='#2e8b57')
        for l in P['loads']:
            x = synth_dry(P, l, 'shooter', True); t = np.arange(len(x)) / FS * 1e3; ax[0].plot(t, x, color=col[l], lw=0.8, label=l); ax[1].plot(t, 20 * np.log10(np.maximum(np.abs(x), 1e-3) / P_REF), color=col[l], lw=0.5)
            f = np.fft.rfftfreq(len(x), 1 / FS); ax[2].semilogx(f[1:], 10 * np.log10(np.abs(np.fft.rfft(x))[1:] ** 2 / FS ** 2 / P_REF ** 2 + 1e-30), color=col[l], lw=0.6)
        ax[0].set_xlim(4.5, 8); ax[0].set_xlabel('time after the trigger break, ms'); ax[0].set_ylabel('pressure at the shooter\'s ear, Pa'); ax[0].legend(fontsize=7); ax[0].set_title('Simulated blast: shock, negative phase, jet noise')
        ax[1].set_xlim(0, 60); ax[1].set_ylim(60, 165); ax[1].set_xlabel('time after the trigger break, ms'); ax[1].set_ylabel('level, dB re 20 uPa'); ax[1].set_title('Blast, ground, slide on the frame, slide closing (simulation)')
        ax[2].set_xlim(50, 24000); ax[2].set_ylim(40, 100); ax[2].set_xlabel('frequency, Hz'); ax[2].set_ylabel('energy spectral density, dB re (20 uPa)^2 s/Hz'); ax[2].set_title('Spectrum of the simulated shot over ground')
        fig.tight_layout(); fig.savefig(os.path.join(HERE, 'compare', 'sim_shots.png'), dpi=110); plt.close(fig)
    if 'render' in sys.argv: render(P)
if __name__ == '__main__':
    main()

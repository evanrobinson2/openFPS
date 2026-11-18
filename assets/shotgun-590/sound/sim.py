#!/usr/bin/env python3
"""Synthesised sound for the shotgun-590 asset, version 2. No recording is used anywhere: not as a sample, not as a
filter, not as something to fit. The only outside numbers are published measurements, each named in SRC.

    python3 sound/sim.py          # writes params.json and compare/{levels,checks,bands}.json, compare/waveforms.png
    python3 sound/verify_js.py    # renders every sound in node with shotgun590-sound.js and compares sample by sample
    python3 sound/sim.py wav      # also writes listening WAVs into sound/audio/ (ignored by git, never committed)

Each sound is a list of components whose times and strengths come from the action simulation (action/action.json)
and the model (model/inventory.json):
  friedlander  a blast wave, optionally through a short filter (the ground's reflection)
  jet          the noise of the gas emptying from the bore: filtered noise under the blow-down envelope
  mode         one decaying structural mode
  noise        filtered noise with an attack and a decay (friction, scattered sound)
The browser module renders the same list with the same arithmetic. README.md explains the physics and the checks.
"""
import json, math, os, sys
import numpy as np
try:
    from scipy.signal import lfilter
except Exception:                                                          # scipy is optional: a plain loop gives the same samples
    lfilter = None
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import measure as M

ACT = json.load(open(os.path.join(HERE, '..', 'action', 'action.json'))); INV = json.load(open(os.path.join(HERE, '..', 'model', 'inventory.json')))
FS = 48000; P0 = 101325.0; C = 340.294; RHO = 1.225; PREF = 20e-6; GAMMA = ACT['params']['gamma']['value']

# ----------------------------------------------------------------------------- sources of every number that is not derived
SRC = dict(
    maher_shaw_2010=dict(basis='published', value=dict(on_axis_rms9_db=145.0, behind_rms9_db=129.0, front_to_back_db=15.0),
        source='R. C. Maher and S. R. Shaw, "Directional aspects of forensic gunshot recordings", AES 39th Int. Conf., 2010. Remington 870, 18 in barrel, Federal 2 3/4 in 00 buck. Microphones 3 m from the muzzle, gun and microphones 3 m above frozen grass so the ground reflection arrives about 10 ms late. Unweighted rms level of a 9 ms window (400 samples at 44.1 kHz from 50 samples before the blast): near 145 dB on axis, about 15 dB less behind the shooter, lowest value 129 dB (read from the text; the figure was not digitised)'),
    murphy_tubbs_2007=dict(basis='published', value=dict(peak_db=[159.0, 161.5], third_octave_max_hz=[500, 800], ground_reflection_ms=6.24, window_ms=42.67),
        source='W. J. Murphy and R. L. Tubbs, "Assessment of noise exposure for indoor and outdoor firing ranges", J. Occup. Environ. Hyg. 4:688-697, 2007 (NIOSH). Remington 870 12 gauge, 45.72 cm barrel, outdoor range. B&K 4136 microphone 1 m to the left of the shooter at the height of the shooter\'s ear. Peak levels of the weapons other than the two loudest, the 870 among them: 159.0 to 161.5 dB. One-third-octave spectra over 42.67 ms: the maximum falls between 500 and 800 Hz for most of the weapons. Reflections seen after the direct wave: tent and shooter at 3.58 and 4.23 ms, ground at 6.24 ms'),
    kardous_willson_2004=dict(basis='published', value=dict(peak_db=163.0, duration_us=456.0),
        source='C. A. Kardous and R. D. Willson, "Limitations of using dosimeters in impulse noise environments", J. Occup. Environ. Hyg. 1:456-462, 2004 (NIOSH). Remington 870 at an indoor range, B&K 4136 just outside the shooter\'s ear: peak 163 dB, impulse duration 456 microseconds'),
    krammer=dict(basis='published', value=dict(barrel_18p5_in_db=161.5, barrel_28_in_db=151.5),
        source='peak level at the shooter\'s ear for 12 gauge shotguns, 161.5 dB with an 18.5 in barrel and 151.5 dB with 28 in (W. Krammer, Ball State University, as reproduced in E.A.R. Inc.\'s "Gunfire Noise Level Reference Chart"; a secondary source)'),
    meinke_2017=dict(basis='published', value=dict(shotgun_peak_db=[152.0, 170.0], outdoor_duration_ms=10.0, spectral_peak_hz=[400, 2000]),
        source='D. K. Meinke et al., "Prevention of noise-induced hearing loss from recreational firearms", Semin. Hear. 38:267-281, 2017 (PMC5634813). Shotguns 152 to 170 dB peak at the left ear of a right-handed shooter; outdoor impulses typically shorter than 10 ms; spectral peaks between 400 and 2000 Hz'),
    niosh_hhe_2013=dict(basis='published', value=dict(doorway_peak_db=[166.9, 171.8], doorway_b_duration_ms=[30, 62], walkway_peak_db=[150.5, 154.7], walkway_b_duration_ms=[172, 185]),
        source='NIOSH Health Hazard Evaluation Report 2013-0124-3208, Table B3: Remington 870 fired inside a shoothouse, microphones at instructor positions. Indoors, so it bounds the B-duration from above; it is not a target for an outdoor model'),
    routh_maher_2016=dict(basis='published', source='T. Routh and R. C. Maher, "Determining the muzzle blast duration and acoustical energy of quasi-anechoic gunshot recordings", AES 141st Conv., 2016. Remington 870 with 3 in shells among ten firearms, 3 m, 500 kHz sampling: muzzle blast durations (93 % of energy) are of the order of 1 ms, longest for the shotgun, whose energy also accumulates most slowly. The values are in figures only, so this is used as a qualitative check'),
    directivity_form=dict(basis='published form, coefficient fitted', source='peak overpressure proportional to mu cos(theta) + sqrt(1 - mu^2 sin^2(theta)): the form of K. Fansler and E. Schmidt, "The prediction of gun muzzle blast properties utilizing scaling" (BRL, 1983) and Fansler, ARL-TR-1434 (1997). Recalled: DTIC refused automated requests, so the report was not re-read. mu is fitted here to the published shotgun levels, see calibration'),
    blast_scaling=dict(basis='derived form, coefficient fitted', source='a release of energy E in air at pressure p0 has the scale radius R0 = (E / p0)^(1/3); weak-shock peak overpressure k p0 R0 / r and positive phase c_T R0 / c. E is the gas energy in the bore when the payload leaves, from the action simulation. k is fitted to the published levels (calibration); c_T is set so the buckshot load has the published 456 microsecond duration'),
    friedlander=dict(basis='published', source='muzzle blast as a Friedlander wave, p = P (1 - t/T) exp(-t/T): R. P. Hamernik and K. D. Hsueh, "Impulse noise: some definitions, physical acoustics and other considerations", J. Acoust. Soc. Am. 90:189-196, 1991, as used by Routh and Maher (2016). Its negative phase is fixed by its form: -0.135 P at t = 2 T, zero net impulse'),
    blowdown=dict(basis='derived', source='quasi-steady isentropic emptying of the bore through the choked muzzle: p = p_e (1 + t/theta)^(-2 gamma/(gamma-1)), theta = 2/(gamma-1) * V/(A c0) * ((gamma+1)/2)^((gamma+1)/(2(gamma-1))); textbook gas dynamics (the gun-emptying problem of J. Corner, "Theory of the Interior Ballistics of Guns", 1950). Gas temperature from p V = m R T with the charge mass of the action simulation'),
    jet_efficiency=dict(value=0.005, basis='published, recalled', source='acoustic efficiency of a supersonic exhaust jet, sound power / mechanical jet power, about 0.5 % (NASA SP-8072, "Acoustic loads generated by the propulsion system", 1971; recalled, not re-read)'),
    jet_strouhal=dict(value=0.2, basis='published, recalled', source='jet mixing noise peaks near a Strouhal number of 0.2 on the fully expanded jet diameter and velocity (Lighthill; Tam, Annu. Rev. Fluid Mech. 27, 1995)'),
    jet_source=dict(value=8.0, basis='inferred', source='the loudest part of a supersonic jet lies some diameters downstream of the nozzle, near the end of its core: 8 fully expanded diameters used. Behind the gun its noise therefore arrives later than the blast'),
    jet_directivity=dict(value=dict(front_db=5.0, back_db=-8.0), basis='inferred', source='jet noise is strongest forward of the muzzle: +5 dB on the axis to -8 dB behind, relative to the mean over a sphere, as a + b cos(theta)'),
    ground=dict(value=200e3, basis='published', source='grass: effective flow resistivity 150 to 300 kPa s/m^2 (T. F. W. Embleton, J. E. Piercy and G. A. Daigle, J. Acoust. Soc. Am. 74:1239-1244, 1983), 200 used, in the one-parameter impedance model of M. E. Delany and E. N. Bazley, Appl. Acoust. 3:105-116, 1970; plane-wave reflection coefficient at the angle of the reflected ray'),
    stance=dict(value=dict(eye_height=1.62, ear_from_eye=[0.04, -0.01, -0.10]), basis='inferred', source='standing shooter, eye 1.62 m above the ground, bore level; the ear 0.10 m behind, 0.04 m beside and 0.01 m below the aiming eye (the same figures as the hk416 asset)'),
    covered_line=dict(basis='chosen', value=dict(roof_height=2.7, back_wall_behind_ear=3.0, roof_front_ahead_of_ear=2.5, alpha_floor=0.02, alpha_roof=0.10, alpha_wall=0.05, scatter_roof=0.30, scatter_wall=0.10, scatter_floor=0.05, scattered_kept=0.5, berm_distance=50.0, berm_width=60.0, berm_height=6.0, alpha_berm=0.40),
        source='a covered firing point on an outdoor range. A concrete pad, a plywood roof on rafters 2.7 m up, a painted block wall 3 m behind the shooter, open at the front and the sides, an earth backstop 50 m downrange. The layout is a choice, not a measurement of any range. Absorption coefficients are handbook values near 500 Hz to 1 kHz (concrete 0.02, plywood panel 0.10, painted block 0.05); the scattering coefficients, the half of the scattered sound taken to stay under the roof rather than leave through the open sides, and the berm (0.40, Lambert) are inferred. Murphy and Tubbs (2007) saw the same kind of early reflections under a fabric tent at an outdoor range'),
    room=dict(basis='chosen', value=dict(width=8.5, height=2.7, length=10.0, left_of_muzzle=6.5, behind_ear=2.0, mixing_ms=40.0, bands_hz=[350, 1000, 2800], alpha_walls_ceiling=[0.20, 0.09, 0.10], alpha_floor=[0.01, 0.02, 0.02], air_m_per_m=[0.0003, 0.001, 0.004]),
        source='the default surroundings: an empty training room, 8.5 x 2.7 x 10 m: plywood-lined walls and ceiling on a concrete floor, the shooter 2 m from the back wall. The layout is a choice. Absorption: handbook values for a 3/8 in plywood panel (0.28, 0.22, 0.17, 0.09, 0.10, 0.11 from 125 Hz to 4 kHz) and smooth concrete, read at the three tail bands. Early reflections are image sources (J. B. Allen and D. A. Berkley, J. Acoust. Soc. Am. 65:943-950, 1979) out to 40 ms; after that a statistical tail with the Eyring decay time of each band (C. F. Eyring, 1930), whose energy rate is that of the image lattice for a source with the blast\'s directivity, 4 pi c <D^2> r_d^2 / (V D_d^2) per second relative to the direct wave: the method of the hk416 asset'),
    mechanical_scale=dict(value=3.5, basis='guess', source='pascals at the shooter\'s ear per kg m/s of impact momentum, before the force spectrum and radiation weights. Set so that a brisk rack peaks near 105 dB at the ear. No published level for a pump action was found'),
    hertz=dict(basis='derived', source='contact time of an impact from Hertz\'s theory, t_c = 2.87 (m^2 / (R E*^2 v))^(1/5), with the moving mass from the model and the speed from the action simulation; contact radius 5 mm (guess). The force is a half sine of that length, so modes above about 1 / t_c are barely excited (K. L. Johnson, "Contact Mechanics", 1985)'),
    structure=dict(basis='derived from inferred dimensions', source='barrel, magazine tube: free-free bending of steel tubes of the model\'s size. Receiver walls: simply supported aluminium plates, 3 mm (notes/NOTES.md). Action bars: free-free steel strips 2.8 mm thick. Stock and forend shells: simply supported polymer plates 3 mm thick, E = 3 GPa, 1150 kg/m^3 (guess: a glass-filled polymer). Loss factors: steel tubes 0.008 to 0.01, receiver and bars 0.02, polymer 0.06 (inferred: a gun held in two hands). Radiation: (ka)^2 / (1 + (ka)^2) for plates, (ka)^3 / (1 + (ka)^3) for tubes in bending; a mode\'s share of the sound is the square root of that. How strongly each event drives each part is a guess (PART_WEIGHT, EVENTS)'),
    hammer=dict(value=dict(mass=0.03, speed=4.5), basis='guess', source='hammer 30 g arriving at 4.5 m/s (about 0.3 J)'),
)
PERSPECTIVES = dict(shooter=dict(note='at the shooter\'s ear, behind the muzzle'), bystander=dict(offset=[5.0, 0.016, 0.0], note='5 m to the side of the muzzle, at ear height'))
ENVIRONMENTS = dict(room='the default: a plywood-lined training room, 8.5 x 2.7 x 10 m, the only kind of place with a published B-duration for this gun', covered='a covered firing point on an outdoor range (roof, back wall, concrete pad, backstop berm)', field='open grass, ground reflection only', free='free field, no reflection at all: the dry shot')

# ----------------------------------------------------------------------------- components
def fried(t0, amp, tpos, fir=None):
    c = dict(kind='friedlander', t0=round(t0, 7), amp=round(amp, 6), tpos=round(tpos, 7))
    if fir: c['fir'] = fir
    return c
def mode(t0, f, decay, amp, phase=0.0): return dict(kind='mode', t0=round(t0, 6), f=round(f, 1), decay=round(decay, 5), amp=round(amp, 6), phase=phase)
def noise(t0, amp, fc, q, attack, decay, seed, hold=0.0): return dict(kind='noise', t0=round(t0, 6), amp=round(amp, 6), fc=fc, q=q, attack=round(attack, 5), hold=round(hold, 5), decay=round(decay, 5), seed=seed)
def jet(t0, amp, theta, n, fc, q, seed, attack=0.0002, dur=0.03): return dict(kind='jet', t0=round(t0, 7), amp=round(amp, 6), theta=round(theta, 7), n=n, fc=round(fc, 1), q=q, attack=attack, dur=dur, seed=seed)

# ----------------------------------------------------------------------------- rendering (the same arithmetic as the JavaScript module)
def rng_block(seed, n):
    """n values of the generator in shotgun590-sound.js (its state advances by a constant, so it vectorises)"""
    s = (np.uint64(seed & 0xFFFFFFFF) + np.arange(1, n + 1, dtype=np.uint64) * np.uint64(0x6D2B79F5)) & np.uint64(0xFFFFFFFF); m = np.uint64(0xFFFFFFFF)
    z = ((s ^ (s >> np.uint64(15))) * (s | np.uint64(1))) & m
    z = (z ^ ((z + (((z ^ (z >> np.uint64(7))) * (z | np.uint64(61))) & m)) & m)) & m
    return ((z ^ (z >> np.uint64(14))) & m).astype(np.float64) / 4294967296.0

def bandpass(fc, q, x, fs):
    w0 = 2 * math.pi * fc / fs; al = math.sin(w0) / (2 * q); a0 = 1 + al; b0, b2, a1, a2 = al / a0, -al / a0, -2 * math.cos(w0) / a0, (1 - al) / a0
    if lfilter is not None: return lfilter([b0, 0.0, b2], [1.0, a1, a2], x)
    v = np.zeros(len(x)); x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        v[i] = b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x[i]; y2 = y1; y1 = v[i]
    return v

def render(snd, fs=FS, filters=None):
    n = int(round(snd['duration'] * fs)); y = np.zeros(n)
    for c in snd['components']:
        i0 = max(0, int(math.ceil(c['t0'] * fs))); k = c['kind']
        if i0 >= n: continue
        if k == 'friedlander':
            i = np.arange(i0, i0 + int(c['tpos'] * fs * 8) + 1); u = (i / fs - c['t0']) / c['tpos']; w = c['amp'] * (1 - u) * np.exp(-u)
            if c.get('fir'):
                f = filters[c['fir']]; w = np.convolve(w, np.array(f['taps'])); i = np.arange(i0 - f['lag'], i0 - f['lag'] + len(w))
            ok = (i >= 0) & (i < n); y[i[ok]] += w[ok]
        elif k == 'mode':
            i = np.arange(i0, min(n, i0 + int(c['decay'] * fs * 9) + 1)); t = i / fs - c['t0']; y[i] += c['amp'] * np.exp(-t / c['decay']) * np.sin(2 * math.pi * c['f'] * t + c['phase'])
        elif k == 'noise':
            i = np.arange(i0, min(n, i0 + int((c['attack'] + c['hold'] + c['decay'] * 9) * fs) + 1)); t = i / fs - c['t0']; v = bandpass(c['fc'], c['q'], 2 * rng_block(c['seed'], len(i)) - 1, fs)
            env = np.where(t < c['attack'], t / c['attack'], 1.0) if c['attack'] > 0 else np.ones(len(i)); late = t > c['attack'] + c['hold']
            env = np.where(late, np.exp(-(t - c['attack'] - c['hold']) / c['decay']), env); y[i] += c['amp'] * 3.0 * env * v
        elif k == 'jet':
            i = np.arange(i0, min(n, i0 + int(c['dur'] * fs) + 1)); t = i / fs - c['t0']; v = bandpass(c['fc'], c['q'], 2 * rng_block(c['seed'], len(i)) - 1, fs)
            env = np.where(t < c['attack'], t / c['attack'], 1.0) * np.power(1 + t / c['theta'], -c['n']); y[i] += c['amp'] * 3.0 * env * v
        else: raise ValueError(k)
    return y

_GAIN = {}
def noise_rms(fc, q):
    """rms of the unit filtered noise that 'noise' and 'jet' components multiply (3 x band-passed uniform noise)"""
    if (fc, q) not in _GAIN: _GAIN[(fc, q)] = float(np.sqrt(np.mean((3.0 * bandpass(fc, q, 2 * rng_block(7, 24000) - 1, FS))[2000:] ** 2)))
    return _GAIN[(fc, q)]

# ----------------------------------------------------------------------------- the shot: source
def source(load):
    """what the action simulation says about the gas at the muzzle, and what follows from it"""
    s = ACT['shots'][load]; g = GAMMA; E = s['gas_energy_at_exit_J']; pe = s['muzzle_pressure_MPa'] * 1e6; A = math.pi * ACT['params']['bore_d']['value'] ** 2 / 4; V = E * (g - 1) / pe
    mc = ACT['loads'][load]['charge']; RT = pe * V / mc; ce = math.sqrt(g * RT); Me = s['muzzle_velocity'] / ce; st = 1 + (g - 1) / 2 * Me ** 2; c0 = ce * math.sqrt(st); p0 = pe * st ** (g / (g - 1)); rho0 = mc / V * st ** (1 / (g - 1))
    theta = 2 / (g - 1) * V / (A * c0) * ((g + 1) / 2) ** ((g + 1) / (2 * (g - 1))); pcrit = P0 * ((g + 1) / 2) ** (g / (g - 1)); t_unchoke = ((p0 / pcrit) ** ((g - 1) / (2 * g)) - 1) * theta
    mdot = rho0 * (2 / (g + 1)) ** (1 / (g - 1)) * c0 * math.sqrt(2 / (g + 1)) * A                              # choked mass flow at the start
    Mj = math.sqrt(2 / (g - 1) * ((p0 / P0) ** ((g - 1) / g) - 1)); sj = 1 + (g - 1) / 2 * Mj ** 2; uj = Mj * c0 / math.sqrt(sj)      # fully expanded jet
    Dj = ACT['params']['bore_d']['value'] * math.sqrt(1 / Mj * (2 / (g + 1) * sj) ** ((g + 1) / (2 * (g - 1)))); Wj = 0.5 * mdot * uj ** 2
    R0 = (E / P0) ** (1 / 3)
    return dict(load=load, gas_energy_J=E, muzzle_pressure_MPa=round(pe / 1e6, 3), gas_volume_m3=round(V, 7), charge_kg=mc, gas_temperature_K_if_M24=round(RT / (8314.0 / 24), 0), sound_speed_gas=round(ce, 1), exit_mach=round(Me, 3),
                stagnation_pressure_MPa=round(p0 / 1e6, 3), blowdown_theta_ms=round(theta * 1e3, 3), choked_for_ms=round(t_unchoke * 1e3, 3), mass_flow_kg_s=round(mdot, 3), jet_mach=round(Mj, 3), jet_velocity=round(uj, 1), jet_diameter_mm=round(Dj * 1e3, 2),
                jet_power_MW=round(Wj / 1e6, 3), jet_peak_hz=round(SRC['jet_strouhal']['value'] * uj / Dj, 0), scale_radius_m=round(R0, 4), t_exit=s['t0'] + s['barrel_time_ms'] * 1e-3,
                _theta=theta, _Wj=Wj, _R0=R0, _Dj=Dj, _uj=uj, _fjet=SRC['jet_strouhal']['value'] * uj / Dj)

CAL = dict(k=0.25, mu=0.78, c_T=0.45)                                         # replaced by calibrate()
def directivity(th, mu=None):
    mu = CAL['mu'] if mu is None else mu
    return (mu * math.cos(th) + math.sqrt(1 - mu ** 2 * math.sin(th) ** 2)) / (1 + mu)
def blast_peak(src, r, th): return CAL['k'] * P0 * src['_R0'] / r * directivity(th)
def blast_tpos(src): return CAL['c_T'] * src['_R0'] / C
def jet_rms(src, r, th):
    d = SRC['jet_directivity']['value']; di = (d['front_db'] + d['back_db']) / 2 + (d['front_db'] - d['back_db']) / 2 * math.cos(th)
    return math.sqrt(RHO * C * SRC['jet_efficiency']['value'] * src['_Wj'] * 10 ** (di / 10) / (4 * math.pi * r * r))

# ----------------------------------------------------------------------------- the shot: geometry and surroundings
# Range frame, metres: x to the shooter's left, y up from the ground, z downrange; the muzzle is at (0, h, 0).
def stance():
    st = SRC['stance']['value']; eye = ACT['sockets']['socket_ads_eye']; mz = ACT['sockets']['socket_muzzle']; h = st['eye_height'] - eye[1]
    ear = [st['ear_from_eye'][0], st['eye_height'] + st['ear_from_eye'][1], eye[2] - mz[2] + st['ear_from_eye'][2]]
    return h, ear
def listener(persp):
    h, ear = stance()
    if persp == 'shooter': return h, ear
    o = PERSPECTIVES[persp]['offset']; return h, [o[0], h + o[1], o[2]]
def ray(S, L):
    d = [L[i] - S[i] for i in range(3)]; r = math.sqrt(sum(v * v for v in d)); return r, math.acos(max(-1.0, min(1.0, d[2] / r)))

def ground_fir(psi, sigma, ntap=96, lag=24, nfft=2048):
    """plane-wave reflection coefficient of a Delany-Bazley ground at grazing angle psi, as a short filter"""
    f = np.fft.rfftfreq(nfft, 1 / FS); X = np.maximum(f, 20.0) * RHO / sigma; Z = 1 + 0.0571 * X ** -0.754 + 1j * 0.087 * X ** -0.732      # e^{-i w t} convention
    R = (Z * math.sin(psi) - 1) / (Z * math.sin(psi) + 1); h = np.fft.irfft(np.conj(R), nfft); h = np.roll(h, lag)[:ntap]                # conj: numpy's transform is e^{+i w t}
    w = np.ones(ntap); w[:lag] = np.hanning(2 * lag)[:lag]; w[lag:] = np.hanning(2 * (ntap - lag))[ntap - lag:]
    return dict(lag=lag, taps=[round(float(v), 8) for v in h * w], grazing_deg=round(math.degrees(psi), 1), mean_abs_R_250_4k=round(float(np.mean(np.abs(R[(f >= 250) & (f <= 4000)]))), 3))

def band_weights(tpos, bands):
    """how a Friedlander pulse's energy divides between the tail's noise bands"""
    f = np.fft.rfftfreq(8192, 1 / FS); w = 2 * math.pi * f; a = 1 / tpos; S = w ** 2 / (w ** 2 + a ** 2) ** 2; out = []
    for fc, q in bands: out.append(float(np.sum(S / (1 + q * q * (f / fc - fc / np.maximum(f, 1e-9)) ** 2))))
    return [v / sum(out) for v in out]
TAIL_BANDS = [(350.0, 0.7), (1000.0, 0.7), (2800.0, 0.7)]

def diffuse(t0, energy, attack, decay, tpos, seed):
    """scattered sound: noise bursts carrying a given energy (Pa^2 s), shared between bands like the pulse that made them.
    energy and decay may be lists, one value per band"""
    out = []
    for j, ((fc, q), wgt) in enumerate(zip(TAIL_BANDS, band_weights(tpos, TAIL_BANDS))):
        e = energy[j] if isinstance(energy, list) else energy; d = decay[j] if isinstance(decay, list) else decay
        amp = math.sqrt(wgt * e / (attack / 3 + d / 2)) / noise_rms(fc, q); out.append(noise(t0, amp, fc, q, attack, d, seed + j))
    return out

def _axis_images(a0, a1, x, n_max):
    """images of a point between two parallel walls: (coordinate, reflections off the wall at a0, off the wall at a1)"""
    D = a1 - a0; out = []
    for n in range(-n_max, n_max + 1):
        out.append((2 * n * D + x, abs(n), abs(n))); out.append((2 * n * D + 2 * a0 - x, abs(n) + 1 if n <= 0 else n - 1, abs(n) if n <= 0 else n))
    return out

def room(src, h, L, t_exit, tpos, seed):
    """a closed room: image sources until the mixing time, then a statistical tail (Eyring) in three bands"""
    rm = SRC['room']['value']; _, ear = stance(); S = [0.0, h, 0.0]; W, H, Ln = rm['width'], rm['height'], rm['length']; x1 = rm['left_of_muzzle']; x0 = x1 - W; z0 = ear[2] - rm['behind_ear']; z1 = z0 + Ln
    V = W * H * Ln; Sw = 2 * (W * H + Ln * H) + W * Ln; Sf = W * Ln; aw = rm['alpha_walls_ceiling']; af = rm['alpha_floor']; gw = math.sqrt(1 - aw[1]); gf = math.sqrt(1 - af[1])
    rd, thd = ray(S, L); pd = blast_peak(src, rd, thd); tmix = rm['mixing_ms'] * 1e-3; comps = []; kept = []
    for xi, nx0, nx1 in _axis_images(x0, x1, L[0], 3):
        for yi, ny0, ny1 in _axis_images(0.0, H, L[1], 8):
            for zi, nz0, nz1 in _axis_images(z0, z1, L[2], 3):
                if nx0 + nx1 + ny0 + ny1 + nz0 + nz1 == 0: continue
                r, th = ray(S, [xi, yi, zi])
                if (r - rd) / C > tmix: continue
                kept.append((r, blast_peak(src, r, th) * gf ** ny0 * gw ** (nx0 + nx1 + ny1 + nz0 + nz1)))
    kept.sort()
    for r, a in kept: comps.append(fried(t_exit + r / C, a, tpos))
    n = 4000; mu = (np.arange(n) + 0.5) / n * 2 - 1; d2 = float(np.mean([directivity(math.acos(m)) ** 2 for m in mu])) / directivity(thd) ** 2     # mean-square directivity over the sphere, relative to the direct ray
    e_dir = pd * pd * 0.25 * tpos; t60 = []; e_tail = []
    for b in range(3):
        abar = (Sw * aw[b] + Sf * af[b]) / (Sw + Sf); T = 0.161 * V / (-(Sw + Sf) * math.log(1 - abar) + 4 * rm['air_m_per_m'][b] * V); t60.append(T)
        e_tail.append(e_dir * 4 * math.pi * C * d2 * rd * rd / V * (T / 13.8) * math.exp(-13.8 * tmix / T))
    w = band_weights(tpos, TAIL_BANDS); tot = sum(wi * ei for wi, ei in zip(w, e_tail))
    comps += diffuse(t_exit + rd / C + tmix, e_tail, 0.003, [T / 6.9 for T in t60], tpos, seed)                                                    # amplitude decay time of a band: T60 / 6.9
    doc = dict(volume_m3=round(V, 1), t60_s=[round(T, 2) for T in t60], image_sources=len(kept), first_reflection_ms=round((kept[0][0] - rd) / C * 1e3, 2), strongest_reflection_db_re_direct=round(20 * math.log10(max(a for _, a in kept) / pd), 1),
               early_energy_db_re_direct=round(10 * math.log10(sum(a * a for _, a in kept) / pd ** 2), 1), tail_energy_db_re_direct=round(10 * math.log10(tot / e_dir), 1), mean_square_directivity_re_direct=round(d2, 2))
    return comps, doc

def surroundings(src, h, L, env, tag, filters, t_exit, seed=300):
    """reflections and scattered sound of the muzzle blast for one listener. Returns components and a record."""
    S = [0.0, h, 0.0]; tpos = blast_tpos(src); comps = []; doc = dict(environment=env)
    if env == 'free': return comps, doc
    if env == 'room':
        comps, d = room(src, h, L, t_exit, tpos, seed); doc.update(d); return comps, doc
    if env == 'field':
        Li = [L[0], -L[1], L[2]]; r, th = ray(S, Li); psi = math.atan2(S[1] + L[1], math.hypot(L[0], L[2])); key = 'ground_' + tag
        filters[key] = ground_fir(psi, SRC['ground']['value']); comps.append(fried(t_exit + r / C, blast_peak(src, r, th), tpos, key))
        rd, _ = ray(S, L); doc.update(ground_delay_ms=round((r - rd) / C * 1e3, 2), ground_path_m=round(r, 3), ground_emission_deg=round(math.degrees(th), 1), ground_peak_pa_before_filter=round(blast_peak(src, r, th), 1), filter=key)
        return comps, doc
    cv = SRC['covered_line']['value']; _, ear = stance(); H = cv['roof_height']; zw = ear[2] - cv['back_wall_behind_ear']; zf = ear[2] + cv['roof_front_ahead_of_ear']
    gf = math.sqrt(1 - cv['alpha_floor']); gr = math.sqrt(1 - cv['alpha_roof']); gw = math.sqrt(1 - cv['alpha_wall'])
    sf = math.sqrt(1 - cv['scatter_floor']); sr = math.sqrt(1 - cv['scatter_roof']); sw = math.sqrt(1 - cv['scatter_wall'])
    rd, thd = ray(S, L); pd = blast_peak(src, rd, thd); paths = []; scat = []
    for wall in (0, 1):
        for j in range(-40, 41):
            for odd in (0, 1):
                if wall == 0 and j == 0 and odd == 0: continue                       # the direct path
                yi = 2 * j * H + (-L[1] if odd else L[1]); zi = 2 * zw - L[2] if wall else L[2]; Li = [L[0], yi, zi]; r, th = ray(S, Li)
                n_roof = abs(j); n_floor = abs(j) if not odd else (j - 1 if j >= 1 else -j + 1); ok = True
                for m in range(min(0, math.floor(yi / H)) - 1, max(1, math.ceil(yi / H)) + 2):   # roof crossings must land on the roof
                    if m % 2 == 0: continue
                    sx = (m * H - S[1]) / (yi - S[1]) if yi != S[1] else -1
                    if 0 < sx < 1:
                        zu = S[2] + sx * (zi - S[2]); za = zu if zu >= zw else 2 * zw - zu
                        if not (zw <= za <= zf): ok = False
                if not ok: continue
                full = blast_peak(src, r, th) * gf ** n_floor * gr ** n_roof * gw ** wall; spec = full * sf ** n_floor * sr ** n_roof * sw ** wall
                if full < pd * 10 ** (-70 / 20): continue
                paths.append((r, spec, n_floor, n_roof, wall, th)); scat.append((r, full * full - spec * spec))
    paths.sort(); kept = [p for p in paths if p[1] >= pd * 10 ** (-56 / 20)]
    for r, a, nf, nr, wl, th in kept: comps.append(fried(t_exit + r / C, a, tpos))
    e_s = cv['scattered_kept'] * sum(e for _, e in scat) * 0.25 * tpos; e_lost = sum(p[1] ** 2 for p in paths if p not in kept) * 0.25 * tpos                 # energy of a Friedlander pulse: P^2 T / 4
    t_mean = sum(r / C * e for r, e in scat) / sum(e for _, e in scat); t_first = min(r for r, _ in scat) / C
    comps += diffuse(t_exit + t_first, e_s + e_lost, 0.004, max(0.01, t_mean - t_first), tpos, seed)
    # the backstop: Lambert scattering from the berm's face, patch by patch
    bz = cv['berm_distance']; nx, ny = 30, 6; dA = (cv['berm_width'] / nx) * (cv['berm_height'] / ny); eb = 0.0; tb = []
    for ix in range(nx):
        for iy in range(ny):
            Pp = [(ix + 0.5) * cv['berm_width'] / nx - cv['berm_width'] / 2, (iy + 0.5) * cv['berm_height'] / ny, bz]; r1, th1 = ray(S, Pp); r2, _ = ray(Pp, L)
            e = blast_peak(src, r1, th1) ** 2 * (1 - cv['alpha_berm']) * (bz / r1) * ((bz - L[2]) / r2) * dA / (math.pi * r2 * r2); eb += e; tb.append(((r1 + r2) / C, e))
    tb0 = min(t for t, _ in tb); tbm = sum(t * e for t, e in tb) / eb; comps += diffuse(t_exit + tb0, eb * 0.25 * tpos, max(0.003, tbm - tb0), max(0.005, 1.5 * (tbm - tb0)), tpos, seed + 10)
    e_dir = pd * pd * 0.25 * tpos
    doc.update(direct_peak_pa=round(pd, 1), reflections=len(kept), first_reflection_ms=round((kept[0][0] - rd) / C * 1e3, 2), strongest_reflection_db_re_direct=round(20 * math.log10(max(p[1] for p in kept) / pd), 1),
               specular_energy_db_re_direct=round(10 * math.log10(sum(p[1] ** 2 for p in kept) / pd ** 2), 1), scattered_energy_db_re_direct=round(10 * math.log10((e_s + e_lost) / e_dir), 1), scattered_decay_ms=round(max(0.01, t_mean - t_first) * 1e3, 1),
               flutter_period_ms=round(2 * H / C * 1e3, 2), berm_energy_db_re_direct=round(10 * math.log10(eb * 0.25 * tpos / e_dir), 1), berm_arrives_ms=round(tb0 * 1e3, 1),
               earliest=[dict(delay_ms=round((r - rd) / C * 1e3, 2), db_re_direct=round(20 * math.log10(a / pd), 1), floor=nf, roof=nr, wall=wl, emission_deg=round(math.degrees(th), 1)) for r, a, nf, nr, wl, th in kept[:8]])
    return comps, doc

def shot_at(load, h, L, env='free', tag='x', filters=None, mech=True, near=1.0, src=None):
    """the shot heard at L (range frame) with the muzzle h above the ground"""
    src = src or source(load); filters = {} if filters is None else filters; r, th = ray([0.0, h, 0.0], L); t_exit = src['t_exit']; t_arr = t_exit + r / C
    t_arr = math.ceil(t_arr * FS) / FS - 1e-7                                    # the direct wave starts on a sample, so the rendered peak is the design peak (a shift of under 21 microseconds)
    peak = blast_peak(src, r, th); tpos = blast_tpos(src); comps = [fried(t_arr, peak, tpos)]
    zj = SRC['jet_source']['value'] * src['_Dj']; rj, thj = ray([0.0, h, zj], L); t_jet = t_exit + zj / src['_uj'] + rj / C     # the jet's noise comes from downstream of the muzzle
    fj = min(src['_fjet'], 9000.0); comps.append(jet(t_jet, jet_rms(src, rj, thj) / noise_rms(fj, 0.5), src['_theta'], (GAMMA + 1) / (2 * (GAMMA - 1)), fj, 0.5, 11, attack=0.0005))
    env_comps, doc = surroundings(src, h, L, env, tag, filters, t_exit); comps += env_comps
    if mech:
        hm = SRC['hammer']['value']; comps += impact(ACT['shots'][load]['t0'], 'hammer', hm['mass'], hm['speed'], 21, scale=near)          # the hammer, before the blast
        comps += ring(t_exit, 'barrel', 0.25 * near) + ring(t_exit, 'receiver', 0.08 * near)                                                     # the gun rings after the shot (guessed strength, pascals)
    return dict(duration=dict(covered=0.6, room=2.0).get(env, 0.3), components=comps, environment=env, peak_pa_design=round(peak, 2), positive_phase_ms=round(tpos * 1e3, 4), distance_m=round(r, 3), angle_deg=round(math.degrees(th), 1),
                jet_rms_pa_at_start=round(jet_rms(src, rj, thj), 1), jet_arrives_after_blast_ms=round((t_jet - t_arr) * 1e3, 2), surroundings=doc)

# ----------------------------------------------------------------------------- structure: modes of the parts, from the model
def tube_modes(length, r_out, r_in, n=5):
    k = math.sqrt((r_out ** 2 + r_in ** 2) / 4.0); c_bar = math.sqrt(200e9 / 7850.0)
    return [b ** 2 / (2 * math.pi * length ** 2) * c_bar * k for b in (4.730, 7.853, 10.996, 14.137, 17.279)[:n]]
def strip_modes(length, h, n=4): return [b ** 2 / (2 * math.pi * length ** 2) * h * math.sqrt(200e9 / (12 * 7850.0)) for b in (4.730, 7.853, 10.996, 14.137)[:n]]
def plate_modes(a, b, h, E, rho, nu, orders): return [math.pi / 2 * h * math.sqrt(E / (12 * rho * (1 - nu * nu))) * ((m / a) ** 2 + (n / b) ** 2) for m, n in orders]
def _size(name): b = INV['parts'][name]['bbox_mm']; return [(b[a][1] - b[a][0]) * 1e-3 for a in 'xyz']
p = INV['params']; _rc = _size('receiver'); _st = _size('stock'); _fe = _size('forend'); _bar = _size('action_bar_right')
PARTS = dict(   # frequencies (Hz), loss factor, radiating size a (m), kind of radiator
    barrel=dict(f=tube_modes((p['muzzle'] - p['breech']) * 1e-3, p['barrel_r'] * 1e-3, p['bore_r'] * 1e-3), eta=0.008, a=p['barrel_r'] * 1e-3, kind='tube'),
    magazine_tube=dict(f=tube_modes((p['tube_z'][1] - p['tube_z'][0]) * 1e-3, p['tube_r'] * 1e-3, (p['tube_r'] - p['tube_wall']) * 1e-3), eta=0.01, a=p['tube_r'] * 1e-3, kind='tube'),
    receiver=dict(f=plate_modes(_rc[2], _rc[1], 0.003, 69e9, 2700.0, 0.33, [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]), eta=0.02, a=math.sqrt(_rc[2] * _rc[1] / math.pi), kind='plate'),
    action_bars=dict(f=strip_modes(_bar[2], (p['bar'][3] - p['bar'][2]) * 1e-3), eta=0.02, a=math.sqrt(_bar[2] * _bar[1] / math.pi), kind='plate'),
    stock=dict(f=plate_modes(_st[2], 0.75 * _st[1], 0.003, 3e9, 1150.0, 0.38, [(1, 1), (2, 1), (3, 1), (1, 2)]), eta=0.06, a=math.sqrt(_st[2] * 0.75 * _st[1] / math.pi), kind='plate'),
    forend=dict(f=plate_modes(_fe[2], math.pi * p['forend_r'] * 1e-3, 0.003, 3e9, 1150.0, 0.38, [(1, 1), (2, 1), (3, 1), (4, 1)]), eta=0.06, a=math.sqrt(_fe[2] * math.pi * p['forend_r'] * 1e-3 / math.pi), kind='plate'),
    hull=dict(f=[1750.0, 3900.0], eta=0.08, a=0.012, kind='plate'),               # a fired plastic hull: a guess
)
PART_WEIGHT = dict(barrel=0.8, magazine_tube=0.8, receiver=1.0, action_bars=0.6, stock=0.9, forend=0.9, hull=0.5)   # guess: surface per unit mass and how well the part is coupled
def radiation(part, f):
    ka = 2 * math.pi * f / C * PARTS[part]['a']; n = 3 if PARTS[part]['kind'] == 'tube' else 2
    return math.sqrt(ka ** n / (1 + ka ** n))
def ring(t, part, pa, tc=0.0):
    """one part ringing: every mode, weighted by the force spectrum of a half-sine contact tc long and by how well it radiates"""
    P = PARTS[part]; out = []
    for i, f in enumerate(P['f']):
        if f > 0.42 * FS: continue
        x = f * tc; force = abs(math.cos(math.pi * x) / (1 - 4 * x * x)) if abs(x - 0.5) > 1e-6 else math.pi / 4
        a = pa * PART_WEIGHT[part] * force * radiation(part, f) / math.sqrt(len(P['f']))
        if a > 1e-4: out.append(mode(t, f, 1 / (math.pi * f * P['eta']), a, phase=0.0))
    return out

_MASS = {k: v['mass_g'] * 1e-3 * ACT['mass']['scale_to_published'] for k, v in INV['parts'].items()}
SLIDE_MASS = sum(_MASS[k] for k in ('forend', 'action_slide_tube', 'action_bar_right', 'action_bar_left', 'bolt_slide', 'bolt', 'bolt_lock'))
ESTAR = dict(steel_steel=115e9, steel_alu=58e9, steel_brass=62e9, steel_polymer=3.3e9)     # 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2
EVENTS = dict(   # what moves (kg), onto what, which parts answer and how strongly (guess), share of the slide's speed
    hammer=dict(pair='steel_steel', parts=dict(receiver=1.0, barrel=0.4, stock=0.3)),
    unlock=dict(mass=_MASS['bolt_lock'] + _MASS['bolt'], pair='steel_steel', parts=dict(receiver=1.0, barrel=0.5, action_bars=0.5)),
    sear=dict(mass=0.02, pair='steel_steel', v=2.0, parts=dict(receiver=0.8, stock=0.3)),
    eject=dict(mass=0.009, pair='steel_polymer', parts=dict(hull=1.0, receiver=0.5)),
    shell_released=dict(mass=ACT['params']['shell_mass']['value'], pair='steel_polymer', parts=dict(magazine_tube=1.0, receiver=0.6, forend=0.4)),
    rear_stop=dict(mass=SLIDE_MASS, pair='steel_alu', parts=dict(receiver=1.0, stock=1.0, action_bars=0.8, magazine_tube=0.6, forend=0.8, barrel=0.3)),
    lift_done=dict(mass=_MASS['elevator'] + ACT['params']['shell_mass']['value'], pair='steel_alu', parts=dict(receiver=1.0, stock=0.4)),
    feed=dict(mass=ACT['params']['shell_mass']['value'], pair='steel_brass', parts=dict(receiver=0.7, hull=0.6, action_bars=0.4)),
    chambered=dict(mass=_MASS['bolt'] + _MASS['bolt_slide'] + ACT['params']['shell_mass']['value'], pair='steel_steel', parts=dict(barrel=1.0, receiver=0.8, magazine_tube=0.4)),
    locked=dict(mass=SLIDE_MASS, pair='steel_steel', parts=dict(barrel=0.9, receiver=1.0, magazine_tube=0.7, forend=0.8, action_bars=0.7, stock=0.6)),
    rattle=dict(mass=2 * _MASS['action_bar_right'], pair='steel_alu', parts=dict(action_bars=1.0, receiver=0.7, forend=0.5)),
    rim_click=dict(mass=0.006, pair='steel_brass', v=3.0, parts=dict(receiver=0.8, magazine_tube=0.8)),
    button=dict(mass=0.008, pair='steel_polymer', v=2.0, parts=dict(receiver=0.7)),
    lever=dict(mass=0.006, pair='steel_steel', v=1.5, parts=dict(receiver=0.6)),
)
def contact_time(mass, v, pair): return 2.87 * (mass ** 2 / (0.005 * ESTAR[pair] ** 2 * max(v, 0.05))) ** 0.2
def impact(t, name, mass, v, seed, scale=1.0):
    """two parts meeting: momentum m v sets the strength, Hertz's contact time sets how bright it is; plus the contact's own short noise"""
    ev = EVENTS[name]; tc = contact_time(mass, v, ev['pair']); pa = SRC['mechanical_scale']['value'] * mass * v * scale; out = []
    for part, wgt in ev['parts'].items(): out += ring(t, part, pa * wgt, tc)
    fc = min(0.6 / tc, 9000.0); out.append(noise(t, 0.25 * pa / noise_rms(fc, 0.7), fc, 0.7, 0.0002, max(0.002, 2 * tc), seed))        # the contact itself: a quarter of the impact's scale (guess)
    return out

def _uniform(seed, n): return rng_block(seed, n)
def pump(which):
    ev = ACT['cycle']['events']; prof = ACT['cycle']['profile']; comps = []; S = ACT['cycle']['stroke_mm'] * 1e-3; ex = prof['exponent']
    t_fwd = prof['back_s'] + prof['dwell_s']; t_shift = 0.0 if which != 'pump_forward' else -t_fwd; lead = 0.01; doc = []
    def add(t, name, v, seed, mass=None):
        e = EVENTS[name]; m = mass if mass is not None else e['mass']; vv = e.get('v', v); comps.extend(impact(t, name, m, vv, seed)); doc.append(dict(t=round(t, 4), event=name, mass_kg=round(m, 4), speed=round(vv, 3), contact_ms=round(contact_time(m, vv, e['pair']) * 1e3, 3)))
    for i, e in enumerate(ev):
        if which == 'pump_back' and e['direction'] != 'back': continue
        if which == 'pump_forward' and e['direction'] != 'forward': continue
        t = e['t'] + t_shift + lead; v = e['slide_speed']; nm = e['name']
        if nm == 'unlock': add(t, 'unlock', v, 30 + i)
        if nm == 'hammer_cocked': add(t, 'sear', v, 35 + i)
        if nm == 'eject': add(t, 'eject', v, 40 + i)
        if nm == 'shell_released':
            add(t + 0.004, 'shell_released', 1.5, 45 + i)                                    # the magazine spring throws the shell onto the elevator (speed: guess)
            comps.append(noise(t, 0.08, PARTS['magazine_tube']['f'][2], 2.0, 0.002, 0.030, 46 + i))    # the spring rattling in its tube (guess)
        if nm == 'rear_stop': add(t, 'rear_stop', v, 50 + i)
        if nm == 'lift_done': add(t, 'lift_done', 0.6, 55 + i)
        if nm == 'feed': add(t, 'feed', v, 60 + i)
        if nm == 'chambered': add(t, 'chambered', v, 70 + i)
        if nm == 'locked': add(t, 'locked', v, 80 + i)
    k_f = 0.30                                                                             # rms pascals of sliding noise per m/s of slide speed, at the ear (guess)
    for stroke, T, t0, seed in (('back', prof['back_s'], 0.0, 91), ('forward', prof['forward_s'], t_fwd, 95)):
        if which == 'pump_back' and stroke != 'back' or which == 'pump_forward' and stroke != 'forward': continue
        vmax = ex * S / T; ts = t0 + t_shift + lead
        for fc, q, sh in ((PARTS['receiver']['f'][1], 0.7, 1.0), (PARTS['forend']['f'][1], 0.8, 0.8), (PARTS['action_bars']['f'][1], 1.0, 0.5)):   # sliding noise through the receiver, the forend shell and the bars
            comps.append(noise(ts, k_f * vmax * sh / noise_rms(fc, q), fc, q, T, 0.008, seed)); seed += 1
        u = _uniform(seed + 7, 9)                                                         # the action bars chattering in their slots: nine small knocks, evenly spread along the travel
        for j, uj in enumerate(sorted(u)):
            frac = (0.08 + 0.88 * uj); tj = T * frac ** (1 / ex); vj = ex * S / T * frac ** ((ex - 1) / ex)
            comps.extend(impact(ts + tj, 'rattle', EVENTS['rattle']['mass'], 0.12 * vj + 0.02, seed + 20 + j))
    dur = (ACT['cycle']['duration'] if which == 'pump' else (prof['back_s'] if which == 'pump_back' else prof['forward_s'])) + 0.25
    return dict(duration=round(dur, 3), components=comps, events=doc)

def simple(name):
    hm = SRC['hammer']['value']; lt = ACT['params']['lock_time']['value']
    if name == 'dry_fire': return dict(duration=0.2, components=impact(lt, 'hammer', hm['mass'], hm['speed'], 101))
    if name == 'shell_insert':
        fc = PARTS['magazine_tube']['f'][2]; c = [noise(0.005, 0.10 / noise_rms(fc, 1.0) * 0.5, fc, 1.0, 0.09, 0.012, 111), noise(0.005, 0.06 / noise_rms(900.0, 0.8) * 0.5, 900.0, 0.8, 0.09, 0.012, 113)]   # the shell sliding in against the spring
        return dict(duration=0.32, components=c + impact(0.10, 'rim_click', EVENTS['rim_click']['mass'], EVENTS['rim_click']['v'], 112) + impact(0.108, 'shell_released', ACT['params']['shell_mass']['value'], 0.5, 114))
    if name == 'safety': return dict(duration=0.12, components=impact(0.005, 'button', EVENTS['button']['mass'], EVENTS['button']['v'], 121))
    if name == 'action_release': return dict(duration=0.12, components=impact(0.005, 'lever', EVENTS['lever']['mass'], EVENTS['lever']['v'], 131))

# ----------------------------------------------------------------------------- calibration against published levels
def _targets():
    h, ear = stance(); mt = SRC['murphy_tubbs_2007']['value']['peak_db']; kr = SRC['krammer']['value']; mh = SRC['maher_shaw_2010']['value']
    bl = ACT['params']['barrel_length']['value'] / 0.0254; ear_db = kr['barrel_18p5_in_db'] + (kr['barrel_28_in_db'] - kr['barrel_18p5_in_db']) * (bl - 18.5) / (28 - 18.5)
    a5 = math.radians(5.0)
    return [dict(name='rms9 at 3 m, on axis (Maher and Shaw 2010)', kind='rms9', h=3.0, L=[3 * math.sin(a5), 3.0, 3 * math.cos(a5)], target=mh['on_axis_rms9_db']),
            dict(name='rms9 at 3 m, behind (Maher and Shaw 2010)', kind='rms9', h=3.0, L=[0.0, 3.0, -3.0], target=mh['behind_rms9_db']),
            dict(name='peak 1 m left of the shooter (Murphy and Tubbs 2007, middle of 159.0 to 161.5)', kind='peak', h=h, L=[ear[0] + 1.0, ear[1], ear[2]], target=sum(mt) / 2),
            dict(name=f'peak at the shooter\'s ear (Krammer, 18.5 and 28 in interpolated to {bl:.0f} in)', kind='peak', h=h, L=ear, target=round(ear_db, 2))]
def _measure(t, src):
    s = shot_at('buck00', t['h'], t['L'], 'free', mech=False, src=src); s['duration'] = 0.03; y = render(s)
    return M.rms9(y, FS) if t['kind'] == 'rms9' else M.db(float(np.max(np.abs(y))))
def calibrate():
    """k and mu by least squares on four published levels for 12 gauge guns with 18 to 20 in barrels; c_T from the published duration"""
    src = source('buck00'); CAL['c_T'] = SRC['kardous_willson_2004']['value']['duration_us'] * 1e-6 / (src['_R0'] / C); T = _targets(); best = None
    for mu in np.arange(0.50, 0.901, 0.01):
        CAL['mu'] = float(mu); CAL['k'] = 0.25
        for _ in range(3): CAL['k'] *= 10 ** (float(np.mean([t['target'] - _measure(t, src) for t in T])) / 20)
        err = float(np.sum([(t['target'] - _measure(t, src)) ** 2 for t in T]))
        if best is None or err < best[0]: best = (err, float(mu), CAL['k'])
    CAL['mu'], CAL['k'] = round(best[1], 2), round(best[2], 4); CAL['c_T'] = round(CAL['c_T'], 4)
    rows = [dict(name=t['name'], published_db=t['target'], model_db=round(_measure(t, src), 1)) for t in T]
    for r in rows: r['difference_db'] = round(r['model_db'] - r['published_db'], 1)
    return dict(k=CAL['k'], mu=CAL['mu'], c_T=CAL['c_T'], front_to_back_peak_db=round(20 * math.log10((1 + CAL['mu']) / (1 - CAL['mu'])), 1), rms_error_db=round(math.sqrt(best[0] / len(T)), 2), rows=rows,
                method='k (level) and mu (directivity) minimise the squared differences of these four levels, rendered in free field for the 00 buck load; c_T makes its positive phase the published 456 microseconds. Three numbers fitted to five published ones. The published guns have 18 and 18.5 in barrels, this one 20 in: the model has almost no barrel-length term, so the difference is ignored')

# ----------------------------------------------------------------------------- build
def build():
    cal = calibrate(); snd = {}; filters = {}; srcs = {}
    for load in ACT['shots']:
        src = source(load); srcs[load] = {k: v for k, v in src.items() if not k.startswith('_')}
        for persp in PERSPECTIVES:
            h, L = listener(persp); near = 1.0 if persp == 'shooter' else 0.3 / ray([0.0, h, 0.0], L)[0]
            for env, suffix in (('room', ''), ('covered', '_covered'), ('field', '_field'), ('free', '_free')):
                snd[f'shot_{load}_{persp}{suffix}'] = shot_at(load, h, L, env, f'{persp}', filters, near=near, src=src)
    for w in ('pump', 'pump_back', 'pump_forward'): snd[w] = pump(w)
    for n in ('dry_fire', 'shell_insert', 'safety', 'action_release'): snd[n] = simple(n)
    modes = {k: [round(f, 1) for f in v['f']] for k, v in PARTS.items()}
    return dict(version=2, fs=FS, units='pascals at the listener; times in seconds from the trigger break (shots, dry_fire) or from the start of the motion', sources=SRC, perspectives=PERSPECTIVES, environments=ENVIRONMENTS,
                calibration=cal, shot_source=srcs, modes_hz=modes, slide_mass_kg=round(SLIDE_MASS, 4), filters=filters, sounds=snd)

def checks(P):
    """the model against the published figures; everything here is a number computed from the simulation"""
    Y = lambda n: render(P['sounds'][n], FS, P['filters']); out = dict(calibration=P['calibration']); h, ear = stance(); src = source('buck00')
    free = Y('shot_buck00_shooter_free'); fld = Y('shot_buck00_shooter_field'); cov = Y('shot_buck00_shooter_covered'); rom = Y('shot_buck00_shooter')
    kw = SRC['kardous_willson_2004']['value']; mt = SRC['murphy_tubbs_2007']['value']; mk = SRC['meinke_2017']['value']; hh = SRC['niosh_hhe_2013']['value']
    a = M.a_duration(free, FS); a_blast = M.a_duration(render(dict(duration=0.05, components=[c for c in P['sounds']['shot_buck00_shooter_free']['components'] if c['kind'] == 'friedlander']), FS), FS); neg = M.negative_phase(render(dict(duration=0.05, components=[c for c in P['sounds']['shot_buck00_shooter_free']['components'] if c['kind'] == 'friedlander']), FS), FS)
    out['peak'] = dict(model_db_at_ear=dict(buck00=round(M.db(np.max(np.abs(free))), 1), slug=round(M.db(np.max(np.abs(Y('shot_slug_shooter_free')))), 1)), published=dict(kardous_willson_indoor_ear=kw['peak_db'], krammer_18p5_in=SRC['krammer']['value']['barrel_18p5_in_db'], krammer_28_in=SRC['krammer']['value']['barrel_28_in_db'], meinke_shotguns_left_ear=mk['shotgun_peak_db']),
                       passed=bool(mk['shotgun_peak_db'][0] <= M.db(np.max(np.abs(free))) <= mk['shotgun_peak_db'][1]))
    out['a_duration'] = dict(model_ms=round(a * 1e3, 3), blast_wave_alone_ms=round(a_blast * 1e3, 3), design_positive_phase_ms=P['sounds']['shot_buck00_shooter_free']['positive_phase_ms'], published_ms=kw['duration_us'] / 1e3, note='c_T is set from this figure, so agreement is by construction; the independent check is the spectrum below', slug_ms=round(M.a_duration(Y('shot_slug_shooter_free'), FS) * 1e3, 3))
    out['negative_phase'] = dict(blast_wave_alone=neg, note='fixed by the Friedlander form: no published negative-phase figure for a 12 gauge was found')
    # the spectrum at Murphy and Tubbs's microphone, over their window, on open ground
    filt = {}; mic = [ear[0] + 1.0, ear[1], ear[2]]; s = shot_at('buck00', h, mic, 'field', 'mt', filt, src=src); to = M.third_octave_max(render(s, FS, filt), FS); tod = M.third_octave_max(render(shot_at('buck00', h, mic, 'free', src=src)), FS); tof = M.third_octave_max(free, FS)
    flat = [k for k, v in to['bands'].items() if v >= to['level_db'] - 3]; win = mt['window_ms'] * 1e-3; tot = lambda b: round(10 * math.log10(sum(10 ** (v / 10) for v in b.values())), 1)
    out['spectrum'] = dict(position='1 m left of the shooter at ear height, 42.67 ms window', direct_wave_max_band_hz=tod['band_hz'], direct_wave_max_band_level_db=tod['level_db'], published_max_band_hz=mt['third_octave_max_hz'],
                           passed=bool(mt['third_octave_max_hz'][0] * 0.89 <= tod['band_hz'] <= mt['third_octave_max_hz'][1] * 1.12), with_ground_max_band_hz=to['band_hz'], with_ground_max_band_level_db=to['level_db'], with_ground_bands_within_3db_hz=[min(flat), max(flat)],
                           total_level_over_window_db=dict(direct=tot(tod['bands']), with_ground=tot(to['bands'])), at_ear_free_field_max_band_hz=tof['band_hz'], third_octave_bands_with_ground_db=to['bands'],
                           note='the paper also says the maximum band exceeded 130 dB for most weapons. The model does not reach that: its whole level over the window is about 133 dB, and Maher and Shaw\'s energy figure scaled to this microphone gives about 131 dB, so no single band of an impulse can hold 130 dB. Not reconciled')
    out['ground_reflection'] = dict(position='the same microphone', model_delay_ms=s['surroundings']['ground_delay_ms'], published_delay_ms=mt['ground_reflection_ms'], passed=bool(abs(s['surroundings']['ground_delay_ms'] - mt['ground_reflection_ms']) < 0.6), at_ear_delay_ms=P['sounds']['shot_buck00_shooter_field']['surroundings']['ground_delay_ms'])
    b = {k: round(M.b_duration(v, FS) * 1e3, 2) for k, v in (('free_field', free), ('open_grass', fld), ('covered_firing_point', cov), ('room', rom), ('room_bystander', Y('shot_buck00_bystander')))}
    out['b_duration'] = dict(model_ms=b, published=dict(outdoor_typical_under_ms=mk['outdoor_duration_ms'], indoor_shoothouse_doorway_ms=hh['doorway_b_duration_ms'], indoor_shoothouse_walkway_ms=hh['walkway_b_duration_ms']),
                             passed=bool(b['open_grass'] < mk['outdoor_duration_ms'] and b['open_grass'] < b['covered_firing_point'] < hh['doorway_b_duration_ms'][1] and hh['doorway_b_duration_ms'][0] <= b['room'] <= hh['walkway_b_duration_ms'][1]), note='open ground must be under the published outdoor figure; the covered firing point must sit between open ground and the indoor values; the room, at the shooter, must fall inside the published indoor range, 30 to 185 ms. Nothing in the room was adjusted to make it so. The published microphones were at instructor positions in rooms whose size is not given')
    out['directivity'] = dict(model_front_to_back_rms9_db=round(P['calibration']['rows'][0]['model_db'] - P['calibration']['rows'][1]['model_db'], 1), published_db=[SRC['maher_shaw_2010']['value']['front_to_back_db'], 16.0], note='about 15 dB in the text; 145 on axis against a lowest value of 129 gives 16')
    out['blowdown'] = dict(theta_ms=src['blowdown_theta_ms'], jet_choked_for_ms=src['choked_for_ms'], jet_rms_db_re_blast_peak_at_ear=round(20 * math.log10(P['sounds']['shot_buck00_shooter_free']['jet_rms_pa_at_start'] / P['sounds']['shot_buck00_shooter_free']['peak_pa_design']), 1), note='no published jet-noise level for a shotgun was found: unvalidated')
    def click(y):
        s = M.summary(y, FS); return dict(energy_in_first_2ms_percent=round(100 * (1 - 10 ** (s['energy_after_2ms_db'] / 10)), 1), energy_in_first_10ms_percent=round(100 * (1 - 10 ** (s['energy_after_10ms_db'] / 10)), 1), band_stays_20db_down_after_ms={k: v['stays_20db_down_after_ms'] for k, v in s['bands'].items()}, b_duration_ms=s['b_duration_ms'])
    out['click_measures'] = dict(note='how much of the shot is over within 2 ms, and how long each octave band takes to stay 20 dB under its own maximum (2 ms rms envelope). Buckshot at the shooter\'s ear. Version 1 is in bands_v1.json',
                                 default_room=click(rom), covered_firing_point=click(cov), open_grass=click(fld), free_field=click(free))
    out['all_passed'] = bool(all(v.get('passed', True) for v in out.values() if isinstance(v, dict)))
    return out

def write_wavs(P):
    import wave
    d = os.path.join(HERE, 'audio'); os.makedirs(d, exist_ok=True)
    def wav(name, y, peak):
        w = wave.open(os.path.join(d, name + '.wav'), 'wb'); w.setnchannels(1); w.setsampwidth(3); w.setframerate(FS)
        q = np.clip(np.round(y / peak * 0.89 * 8388607), -8388607, 8388607).astype('<i4'); w.writeframes(b''.join(int(v).to_bytes(4, 'little', signed=True)[:3] for v in q)); w.close()
    for name, s in P['sounds'].items():
        y = render(s, FS, P['filters']); wav(name, np.concatenate([np.zeros(2400), y, np.zeros(4800)]), float(np.max(np.abs(y))))
    def listen(y, ratio=3.0, release=0.06, max_boost_db=30.0):
        """playback mapping for listening, not physics: a peak follower (instant attack, 60 ms release) and 3:1 upward compression, so the
        part of the sound 30 dB under the peak plays 10 dB under it, as a recording chain or an ear at 160 dB would give"""
        a = np.abs(y) / np.max(np.abs(y)); env = np.zeros(len(y)); e = 0.0; k = math.exp(-1 / (release * FS))
        for i in range(len(y)): e = max(a[i], e * k); env[i] = e
        g = np.minimum(max_boost_db, -20 * np.log10(np.maximum(env, 1e-6)) * (1 - 1 / ratio)); g[env < 1e-5] = 0.0
        return y * 10 ** (g / 20)
    os.makedirs(os.path.join(d, 'listen'), exist_ok=True)
    for name in ('shot_buck00_shooter', 'shot_buck00_shooter_covered', 'shot_buck00_shooter_field', 'shot_buck00_shooter_free', 'shot_slug_shooter', 'shot_buck00_bystander', 'pump', 'dry_fire', 'shell_insert'):
        z = listen(np.concatenate([np.zeros(2400), render(P['sounds'][name], FS, P['filters']), np.zeros(4800)])); wav(os.path.join('listen', name + '_listen'), z, float(np.max(np.abs(z))))
    seq = np.zeros(int(3.2 * FS)); a = render(P['sounds']['shot_buck00_shooter'], FS, P['filters']); b = render(P['sounds']['pump'], FS, P['filters'])     # a shot, then a rack, at a listening mix (not the true 55 dB apart)
    seq[2400:2400 + len(a)] += a / np.max(np.abs(a)); i = int(1.0 * FS); seq[i:i + len(b)] += 0.25 * b / np.max(np.abs(b)); wav('demo_shot_then_pump_mixed', seq, float(np.max(np.abs(seq))))
    z = listen(seq); wav(os.path.join('listen', 'demo_shot_then_pump_listen'), z, float(np.max(np.abs(z))))
    print('WAVs written to', d)

def main():
    P = build(); levels = {}
    for name, s in P['sounds'].items():
        y = render(s, FS, P['filters']); pk = float(np.max(np.abs(y))); s['peak_pa'] = round(pk, 4); s['peak_db'] = round(20 * math.log10(pk / PREF), 1)
        levels[name] = dict(peak_pa=s['peak_pa'], peak_db=s['peak_db'], duration=s['duration'], components=len(s['components']))
    json.dump(P, open(os.path.join(HERE, 'params.json'), 'w'), separators=(',', ':'))
    json.dump(dict(note='peak levels of every synthesised sound, dB re 20 uPa, at the listener of that sound', levels=levels), open(os.path.join(HERE, 'compare', 'levels.json'), 'w'), indent=1)
    chk = checks(P); json.dump(chk, open(os.path.join(HERE, 'compare', 'checks.json'), 'w'), indent=1)
    bands = {n: M.summary(render(s, FS, P['filters']), FS) for n, s in P['sounds'].items()}
    json.dump(dict(note='band envelopes and summary measures of every sound in params.json, version 2 (see measure.py for the definitions); simulation only. bands_v1.json holds the same measures of version 1', sounds=bands), open(os.path.join(HERE, 'compare', 'bands.json'), 'w'), indent=1)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    names = ['shot_buck00_shooter_free', 'shot_buck00_shooter_field', 'shot_buck00_shooter_covered', 'shot_buck00_shooter', 'pump', 'dry_fire']; fig, ax = plt.subplots(3, len(names), figsize=(3.3 * len(names), 7.5))
    for i, nm in enumerate(names):
        y = render(P['sounds'][nm], FS, P['filters']); t = np.arange(len(y)) / FS * 1e3; ax[0, i].plot(t, y, lw=0.6); ax[0, i].set(title=nm, xlabel='ms', ylabel='Pa' if i == 0 else '')
        w = int(0.001 * FS); env = np.sqrt(np.convolve(y ** 2, np.ones(w) / w, 'same')); ax[1, i].plot(t, 20 * np.log10(env / np.max(np.abs(y)) + 1e-9), lw=0.6); ax[1, i].set(ylim=(-80, 3), xlabel='ms', ylabel='1 ms rms, dB re peak' if i == 0 else '')
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))); f = np.fft.rfftfreq(len(y), 1 / FS); ax[2, i].semilogx(f[1:], 20 * np.log10(sp[1:] / sp.max() + 1e-9), lw=0.6); ax[2, i].set(xlim=(30, 20000), ylim=(-80, 3), xlabel='Hz', ylabel='dB re peak bin' if i == 0 else '')
    fig.suptitle('Synthesised waveforms, level against time, and spectra (simulation only)'); fig.tight_layout(); fig.savefig(os.path.join(HERE, 'compare', 'waveforms.png'), dpi=80); plt.close(fig)
    for k, v in levels.items(): print(f'{k:30s} {v["peak_db"]:6.1f} dB  {v["peak_pa"]:10.3f} Pa  {v["duration"]:.2f} s  {v["components"]} components')
    print(json.dumps(P['calibration'], indent=1)); print('checks passed:', chk['all_passed'], {k: v.get('passed') for k, v in chk.items() if isinstance(v, dict) and 'passed' in v})
    if len(sys.argv) > 1 and sys.argv[1] == 'wav': write_wavs(P)

if __name__ == '__main__':
    main()

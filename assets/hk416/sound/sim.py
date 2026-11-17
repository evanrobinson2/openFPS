#!/usr/bin/env python3
"""HK416 D14.5RS discharge sound simulator (physics + published numbers, no recordings).

Two stages:
  A. make_params(): physics -> tables (params.json). Geometry, blast scaling, Mach cone, ground
     impedance, atmospheric absorption, modal tables, room recipes.
  B. synth_*(P, ...): tables -> waveforms. Stage B is ported 1:1 in hk416-sound.js, which reads
     the same params.json, so the browser synthesises the same sounds.

Usage (from the hk416 folder):
  python3 sound/sim.py all        # params + every render + compare
  python3 sound/sim.py params     # write sound/params.json only
  python3 sound/sim.py dry        # dry shots, mechanical, steel (masters + listening copies)
  python3 sound/sim.py overlays   # environment impulse responses + hearing protection
  python3 sound/sim.py compare    # matched comparison against the local reference recordings
See README.md for every parameter and its source.
"""
import base64, json, math, os, subprocess, sys
import warnings
import numpy as np
warnings.filterwarnings('ignore', message='.*encountered in matmul')   # spurious on macOS Accelerate; build_ir asserts finiteness
from scipy import signal, special

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, 'audio'); MASTERS = os.path.join(HERE, 'masters'); COMPARE = os.path.join(HERE, 'compare')
REFDIR = os.environ.get('OPENFPS_REF_AUDIO', os.path.join(HERE, 'refs-local'))

# ------------------------------------------------------------------ constants (see README parameter table)
FS, OS = 48000, 4
FSO = FS * OS
T_C, RH, P_ATM = 20.0, 50.0, 101325.0            # stated atmosphere
C0 = 343.2                                        # speed of sound at 20 C
RHO0 = 1.204
GAMMA = 1.4
BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
P_REF = 20e-6

# rifle geometry, range frame: x right, y up, z downrange, metres. From hk416.glb sockets.
EYE_H = 1.62                                      # range page camera height
MUZZLE_FROM_EYE = (0.0, -0.0655, 0.6586)          # socket_muzzle - socket_ads_eye
RECV_FROM_EYE = (0.0, -0.0655, 0.2076)            # socket_eject z (ejection port / bolt)
BUF_FROM_EYE = (0.0, -0.0655, 0.01)               # buffer tube, under the cheek
EAR_FROM_EYE = (0.04, -0.01, -0.10)               # right ear of a right-handed shooter (inferred anthropometry)
CASE_LAND_FROM_EYE = (2.1, -EYE_H + 0.005, 0.2)   # ballistic flight of the case from socket_eject (see README)

# muzzle blast
V0 = 850.0                # m/s, HK maintenance manual p.7 (14.5 in)
P90_DB = 164.0            # dB peak at 1 m, 90 deg (Larson Davis / Dater briefing: M4, 1 m left of muzzle)
T90 = 0.30e-3             # s, positive phase at 1 m 90 deg (inferred from published 5.56 A-durations 0.2-0.4 ms)
MU = 0.78                 # Fansler & Schmidt momentum index (recalled value, see README)
T_DIR_EXP = 0.5           # positive-phase duration scales with (l'/l'90)^0.5 (inferred)
RISE = 10e-6              # s shock rise used for synthesis (below the 48 kHz band)
SEC_DB, SEC_T, SEC_DELAY, SEC_MU = -10.0, 0.45e-3, 0.7e-3, 0.3    # secondary (afterburn) pulse, inferred
JET_DB, JET_TAU = -22.0, 1.2e-3                    # propellant jet noise, inferred
SHOT_SD_DB = 0.7          # shot-to-shot level spread (inferred)

# bullet (M855)
BUL_D, BUL_L, BUL_M = 5.70e-3, 23.0e-3, 4.02e-3
DRAG_K = 1.0e-3           # 1/m, v(x)=V0 exp(-k x) (fit to ~10 % loss per 100 m, inferred from M855 tables)

RPM = 850.0               # range page; manual gives 700-900
GROUND_SIGMA = 300.0      # kPa s/m^2, Delany-Bazley flow resistivity, packed dirt / sparse grass

# ------------------------------------------------------------------ deterministic RNG shared with JS
M32 = 0xFFFFFFFF


def fnv1a(s):
    h = 0x811C9DC5
    for ch in s.encode():
        h ^= ch; h = (h * 0x01000193) & M32
    return h


class Rng:
    """mulberry32 (counter based), identical stream in hk416-sound.js."""

    def __init__(self, name):
        self.seed = fnv1a(name); self.i = 0

    def u(self, n):
        i = np.arange(self.i + 1, self.i + n + 1, dtype=np.uint64); self.i += n
        a = (np.uint64(self.seed) + np.uint64(0x6D2B79F5) * i) & np.uint64(M32)
        t = a
        t = ((t ^ (t >> np.uint64(15))) * (t | np.uint64(1))) & np.uint64(M32)
        t = t ^ ((t + (((t ^ (t >> np.uint64(7))) * (t | np.uint64(61))) & np.uint64(M32))) & np.uint64(M32))
        t = (t ^ (t >> np.uint64(14))) & np.uint64(M32)
        return t.astype(np.float64) / 4294967296.0

    def g(self, n):
        u = self.u(2 * n)
        return np.sqrt(-2.0 * np.log(u[0::2] + 1e-12)) * np.cos(2 * np.pi * u[1::2])


def rnd(x):
    return int(math.floor(x + 0.5))


# ------------------------------------------------------------------ stage A physics helpers
def iso9613_alpha(f, T=T_C + 273.15, hr=RH, pa=1.0):
    """Atmospheric absorption, dB/m (ISO 9613-1)."""
    f = np.asarray(f, float); T0, T01 = 293.15, 273.16
    psat = 10 ** (-6.8346 * (T01 / T) ** 1.261 + 4.6151)
    h = hr * psat / pa
    frO = pa * (24 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    frN = pa * (T / T0) ** -0.5 * (9 + 280 * h * np.exp(-4.170 * ((T / T0) ** (-1 / 3) - 1)))
    return 8.686 * f ** 2 * (1.84e-11 / pa * (T / T0) ** 0.5 + (T / T0) ** -2.5 * (
        0.01275 * np.exp(-2239.1 / T) / (frO + f ** 2 / frO) + 0.1068 * np.exp(-3352.0 / T) / (frN + f ** 2 / frN)))


def dirfac(cos_t, mu=MU):
    """Fansler-Schmidt scaling-length ratio l'(theta)/l'(90 deg): amplitude directivity of the blast."""
    sin2 = 1 - cos_t * cos_t
    return (mu * cos_t + np.sqrt(1 - mu * mu * sin2)) / math.sqrt(1 - mu * mu)


def ground_Q(f, R2, cos_inc, sigma=GROUND_SIGMA):
    """Spherical-wave reflection coefficient over a Delany-Bazley impedance plane (exp(-iwt) convention)."""
    f = np.maximum(f, 1.0); X = f / sigma
    Z = 1 + 9.08 * X ** -0.75 + 1j * 11.9 * X ** -0.73
    beta = 1 / Z; k = 2 * np.pi * f / C0
    Rp = (cos_inc - beta) / (cos_inc + beta)
    w = (1 + 1j) / 2 * np.sqrt(k * R2) * (cos_inc + beta)
    F = 1 + 1j * np.sqrt(np.pi) * w * special.wofz(w)
    return Rp + (1 - Rp) * F


NFIR, LAT = 1024, 128


def path_fir(r, ground=None):
    """48 kHz FIR for a path: air absorption over r, times ground reflection Q if ground=(R2, cos_inc)."""
    f = np.fft.rfftfreq(NFIR, 1 / FS)
    H = 10 ** (-iso9613_alpha(f) * r / 20) + 0j
    if ground: H = H * np.conj(ground_Q(f, *ground))      # numpy uses exp(+iwt)
    h = np.roll(np.fft.irfft(H, NFIR), LAT)
    win = np.ones(NFIR); n = 64; ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)
    win[:n] = ramp; win[-n:] = ramp[::-1]
    return (h * win).astype(np.float32)


def whitham(M, b):
    """N-wave peak overpressure (Pa) and duration (s) at miss distance b (Whitham 1952)."""
    dp = 0.53 * P_ATM * (M * M - 1) ** 0.125 * BUL_D / (b ** 0.75 * BUL_L ** 0.25)
    T = 1.82 * M * b ** 0.25 * BUL_D / (C0 * (M * M - 1) ** 0.375 * BUL_L ** 0.25)
    return dp, T


def b64(a):
    return base64.b64encode(np.asarray(a, np.float32).tobytes()).decode()


def unb64(s):
    return np.frombuffer(base64.b64decode(s), np.float32).astype(np.float64)


V3 = lambda *a: np.array(a, float)
EYE = V3(0, EYE_H, 0)
AXIS = V3(0, 0, 1)
PERSP_LIS = {
    'shooter': EYE + V3(*EAR_FROM_EYE),
    'bystander': EYE + V3(5.0, -0.02, 0.0),
    'downrange': EYE + V3(2.0, -0.02, 50.0),          # 50 m downrange, 2 m beside the line of fire
    'ongun': EYE + V3(*MUZZLE_FROM_EYE) + V3(0.0, 0.06, -0.40),   # comparison mic on the handguard (inferred position)
    'side1m': EYE + V3(*MUZZLE_FROM_EYE) + V3(-1.0, 0.0, 0.0),    # comparison mic 1 m left of the muzzle
}
SRC = {'muzzle': EYE + V3(*MUZZLE_FROM_EYE), 'recv': EYE + V3(*RECV_FROM_EYE), 'buf': EYE + V3(*BUF_FROM_EYE),
       'case': EYE + V3(*CASE_LAND_FROM_EYE)}

# ---- absorption coefficients by octave band 63..16k (handbook values 125-4k; 63, 8k, 16k extrapolated)
MAT = {
    'concrete': [.01, .01, .01, .02, .02, .02, .03, .03, .04],
    'block_painted': [.08, .10, .05, .06, .07, .09, .08, .08, .09],
    'gypsum': [.30, .29, .10, .05, .04, .07, .09, .09, .10],
    'plaster': [.14, .14, .10, .06, .05, .04, .03, .03, .04],
    'carpet_furnished': [.08, .15, .30, .45, .60, .65, .65, .65, .65],
    'vinyl': [.02, .02, .03, .03, .03, .03, .02, .02, .03],
    'wood_door': [.15, .14, .10, .06, .08, .10, .10, .10, .10],
    'acoustic_panel': [.15, .25, .60, .90, .95, .90, .85, .85, .85],
    'panel_block_mix': [.12, .18, .33, .48, .51, .50, .47, .47, .47],
    'baffles': [.20, .35, .60, .80, .85, .85, .80, .80, .80],
    'rubber_berm': [.20, .30, .50, .70, .80, .85, .90, .90, .90],
    'metal_roof': [.30, .30, .25, .20, .15, .10, .10, .10, .12],
    'metal_wall': [.20, .15, .12, .10, .08, .08, .08, .08, .10],
    'facade': [.05, .04, .03, .03, .04, .05, .06, .07, .08],
    'asphalt': [.02, .02, .03, .03, .03, .04, .05, .06, .07],
    'soil_berm': [.15, .15, .25, .40, .55, .60, .60, .60, .60],
    'rock': [.02, .02, .03, .04, .05, .05, .06, .07, .08],
    'forest_slope': [.20, .30, .40, .50, .60, .70, .70, .70, .70],
    'wood_bench': [1, 1, 1, .10, .10, .10, .10, .10, .10],     # too small to reflect below ~300 Hz
    'partition': [1, 1, .6, .3, .3, .3, .3, .3, .3],
    'open': [1] * 9,
}
FOLIAGE_DB_M = [.02, .03, .04, .05, .06, .08, .09, .12, .12]     # ISO 9613-2 Table A.1 dense foliage


def mech_tables():
    """Modal tables for the action. f Hz, T60 s, relative amplitude; click = broadband contact noise.
    p1m = peak level at 1 m in dB (inferred). Frequencies: barrel free-free bending 631/1740/3410 Hz
    (steel tube 368 mm, OD 18, bore 5.56), carrier longitudinal ~15 kHz, case ovalling 8.2 kHz."""
    spring = [[41.8 * n, 0.16, 1.0 / n ** 0.5] for n in range(6, 30)]       # buffer spring standing waves
    case = [[8180, .006, 1], [8900, .005, .7], [12400, .004, .45], [15300, .003, .35]]
    return {
        'hammer': dict(p1m=92, modes=[[2900, .012, 1], [5200, .008, .7], [8100, .006, .5]], click=[.6, .00012]),
        'piston': dict(p1m=100, modes=[[631, .030, .5], [1740, .025, .8], [3410, .020, 1], [6300, .010, .6], [11000, .005, .4]], click=[.7, .00015]),
        'deflector': dict(p1m=88, modes=case, click=[.4, .0001]),
        'buffer': dict(p1m=101, modes=[[240, .025, 1], [1150, .012, .6], [2600, .008, .4], [4300, .005, .25]], click=[.5, .0004]),   # tungsten-granule buffer: damped thud
        'spring': dict(p1m=82, modes=spring, click=[0, .001]),
        'feed': dict(p1m=90, modes=[[1900, .010, 1], [4100, .008, .6]], click=[1.2, .0015]),
        'battery': dict(p1m=104, modes=[[631, .030, .4], [1740, .025, .7], [3410, .020, 1], [5600, .012, .8], [9200, .008, .5], [15000, .004, .3]], click=[.7, .00015]),
        'reset': dict(p1m=80, modes=[[3300, .008, 1], [6100, .005, .6]], click=[.5, .0001]),
        'catch': dict(p1m=97, modes=[[1150, .015, 1], [2600, .012, .8], [5600, .008, .5]], click=[.7, .0002]),
        'handle': dict(p1m=86, modes=[[2100, .010, 1], [4700, .006, .6]], click=[1.0, .001]),
        'case1': dict(p1m=78, modes=[[m[0], m[1] * 3, m[2]] for m in case], click=[.8, .0003]),
        'case2': dict(p1m=72, modes=[[m[0] * 1.012, m[1] * 3, m[2]] for m in case], click=[.6, .0003]),
        'case3': dict(p1m=66, modes=[[m[0] * 0.991, m[1] * 3, m[2]] for m in case], click=[.5, .0003]),
    }


CYCLE_S = 60.0 / RPM
# event, time after the bullet leaves the muzzle (s), source position
CYCLE = [['hammer', -1.3e-3, 'recv'], ['piston', 0.4e-3, 'recv'], ['deflector', 11e-3, 'recv'], ['buffer', 21e-3, 'buf'],
         ['spring', 21e-3, 'buf'], ['feed', 46e-3, 'recv'], ['battery', 62e-3, 'recv'],
         ['case1', 0.789, 'case'], ['case2', 1.266, 'case'], ['case3', 1.433, 'case']]
MECH_CLIPS = {      # standalone mechanical sounds (shooter perspective unless asked otherwise)
    'cycle': [e for e in CYCLE if not e[0].startswith('case')],
    'case_drop': [['deflector', 11e-3, 'recv']] + [e for e in CYCLE if e[0].startswith('case')],
    'trigger': [['hammer', 0.0, 'recv']],
    'trigger_reset': [['reset', 0.0, 'recv']],
    'charge': [['handle', 0.02, 'recv'], ['buffer', 0.375, 'buf'], ['spring', 0.375, 'buf'], ['feed', 0.70, 'recv'], ['battery', 0.75, 'recv']],  # times follow the glTF 'charge' clip
    'bolt_lock_back': [['piston', 0.4e-3, 'recv'], ['deflector', 11e-3, 'recv'], ['buffer', 21e-3, 'buf'], ['spring', 21e-3, 'buf'], ['catch', 30e-3, 'recv']],
    'bolt_release': [['catch', 0.0, 'recv'], ['feed', 0.022, 'recv'], ['battery', 0.038, 'recv'], ['spring', 0.0, 'buf']],
}
VARIANTS = {'single': dict(times=[0.0], reset=0.16, len=1.9),
            'semi3': dict(times=[0.0, 0.25, 0.5], reset=0.12, len=2.4),
            'auto1s': dict(times=[round(k * CYCLE_S, 6) for k in range(15)], reset=None, len=2.9)}


def steel_tables():
    """Free circular AR500 plate, 10 mm. Modes from Leissa's free-plate eigenvalues, extended asymptotically."""
    E, rho, nu, h = 207e9, 7850.0, 0.29, 0.010
    lam2 = {(2, 0): 5.253, (0, 1): 9.084, (3, 0): 12.23, (1, 1): 20.52, (4, 0): 21.6, (5, 0): 33.1, (2, 1): 35.25, (0, 2): 38.55,
            (6, 0): 46.2, (3, 1): 52.91, (1, 2): 59.86, (7, 0): 61.3, (4, 1): 73.1, (2, 2): 84.6, (0, 3): 87.80}
    cp = h * math.sqrt(E / (12 * rho * (1 - nu * nu)))
    fc = C0 ** 2 / (2 * np.pi) * math.sqrt(12 * rho * (1 - nu * nu) / (E * h * h))     # coincidence frequency
    out = {}
    for r_cm, dist in [(18, 20), (20, 30), (22, 35), (25, 45), (30, 55)]:
        a = r_cm / 100; S = np.pi * a * a; Mp = S * h * rho
        v_imp = V0 * math.exp(-DRAG_K * dist); J = BUL_M * v_imp; tau_c = BUL_L / v_imp
        rng = Rng('steel%d' % r_cm); rho0 = 0.15 + 0.45 * rng.u(1)[0]                  # hit radius / plate radius
        modes = []
        for n in range(0, 40):
            for s in range(0, 14):
                if n < 2 and s == 0: continue
                l2 = lam2.get((n, s), (np.pi / 2 * (n + 2 * s)) ** 2 * (1 if (n, s) in lam2 else 0.97))
                f = l2 / (2 * np.pi * a * a) * cp
                if f > 16000: continue
                lam = math.sqrt(l2)
                rr = np.linspace(0, 1, 400)
                msq = np.trapezoid(special.jv(n, lam * rr) ** 2 * rr, rr) * 2 * (1 if n == 0 else 0.5)   # mean square of the mode shape
                g = special.jv(n, lam * rho0) / math.sqrt(msq)                         # shape at the hit point / rms
                Fhat = abs(math.cos(np.pi * f * tau_c) / (1 - (2 * f * tau_c) ** 2 + 1e-9))   # half-sine contact spectrum
                v_rms = J * Fhat * abs(g) / Mp                                         # spatial rms velocity of the mode
                sig = min(1.0, (f / fc) ** 2) if f < fc else 1.0                       # radiation efficiency (unbaffled plate, crude)
                W = RHO0 * C0 * 2 * S * sig * v_rms ** 2 / 2                           # both faces, time-mean
                p1 = math.sqrt(2 * W * RHO0 * C0 / (4 * np.pi))                        # peak pressure at 1 m
                eta = 0.004 + RHO0 * C0 * sig / (np.pi * f * rho * h) * 2              # mount + radiation loss
                modes.append([round(f, 2), round(2.2 / (eta * f), 4), float('%.4g' % p1), float('%.3g' % iso9613_alpha(f))])
        modes.sort()
        out['r%d' % r_cm] = dict(radius=a, dist=dist, v_impact=round(v_imp, 1), hit_radius_frac=round(float(rho0), 3), fc=round(fc, 1),
                                 modes=modes, splash=dict(p1m=round(0.25 * math.sqrt(sum(m[2] ** 2 for m in modes)), 3), tau=0.0006))
    return out


def hpd_table():
    """Passive earmuff, NRR ~30 class: mean attenuation by octave band (typical published values, see README)."""
    att = [15.0, 21.3, 28.4, 39.6, 42.3, 37.1, 40.4, 40.2, 40.0]
    f = np.fft.rfftfreq(1024, 1 / FS); lf = np.log2(np.maximum(f, 20) / 63.0)
    mag_db = -np.interp(lf, np.arange(9), att)
    # minimum phase by the real cepstrum
    logm = np.log(10 ** (mag_db / 20)); full = np.concatenate([logm, logm[-2:0:-1]])
    cep = np.fft.ifft(full).real; n = len(full); w = np.zeros(n); w[0] = 1; w[1:n // 2] = 2; w[n // 2] = 1
    hmin = np.fft.ifft(np.exp(np.fft.fft(cep * w))).real[:256]
    return dict(bands=BANDS, att_db=att, fir=b64(hmin), note='apply after the room, at the ear')


def make_persp(name, firs):
    """Per-listener path tables for the dry sound."""
    L = PERSP_LIS[name]; M = SRC['muzzle']
    def fir_id(r, ground=None):
        if ground is None and r < 3.0: return -1
        firs.append(b64(path_fir(r, ground))); return len(firs) - 1
    def rays(S):   # direct and ground-reflected ray: (r, unit direction leaving the source, ground geometry or None)
        d = L - S; r1 = np.linalg.norm(d)
        Li = L * V3(1, -1, 1); d2 = Li - S; r2 = np.linalg.norm(d2)
        return [(r1, d / r1, None), (r2, d2 / r2, (r2, abs(d2[1]) / r2))]
    out = dict(lis=[round(float(v), 4) for v in L])
    P90 = P_REF * 10 ** (P90_DB / 20)
    blast = {'free': [], 'field': []}; sec = {'free': [], 'field': []}; jet = {'free': [], 'field': []}
    for i, (r, u, gr) in enumerate(rays(M)):
        D = float(dirfac(u @ AXIS)); P1 = P90 * D; T1 = T90 * D ** T_DIR_EXP
        k = (GAMMA + 1) / (2 * GAMMA) * P1 / (P_ATM * C0 * T1)             # weak-shock (Landau) lengthening, r0 = 1 m
        s = math.sqrt(max(0.25, 1 + k * math.log(r)))
        fid = fir_id(r, gr)
        e = dict(P=P1 / r / s, T=T1 * s, t=r / C0, fir=fid, r=round(r, 4), theta=round(math.degrees(math.acos(u @ AXIS)), 2))
        e2 = dict(P=P90 * 10 ** (SEC_DB / 20) * float(dirfac(u @ AXIS, SEC_MU)) / r, T=SEC_T, t=r / C0 + SEC_DELAY, fir=fid)
        e3 = dict(rms=P90 * 10 ** (JET_DB / 20) * D / r, tau=JET_TAU, t=r / C0, fir=fid)
        for v in (['free', 'field'] if i == 0 else ['field']): blast[v].append(e); sec[v].append(e2); jet[v].append(e3)
    out.update(blast=blast, sec=sec, jet=jet)
    # ballistic shock: ray leaves the trajectory at acos(1/M) to it
    nw = {'free': [], 'field': []}
    for i, Lx in enumerate([L, L * V3(1, -1, 1)]):
        d = Lx - M; zL = d[2]; b = math.hypot(d[0], d[1]); xe = 0.0
        for _ in range(30):
            Mx = V0 * math.exp(-DRAG_K * xe) / C0
            xe = zL - b / math.sqrt(Mx * Mx - 1)
        if xe <= 0: continue                                                # the cone launched at the muzzle never reaches this listener
        Mx = V0 * math.exp(-DRAG_K * xe) / C0; ray = math.hypot(b, zL - xe)
        dp, T = whitham(Mx, b)
        tb = (math.exp(DRAG_K * xe) - 1) / (DRAG_K * V0)
        e = dict(dp=dp, T=T, t=tb + ray / C0, fir=fir_id(ray, (ray, abs(d[1]) / ray) if i else None),
                 mach=round(Mx, 3), miss=round(b, 3), x_emit=round(xe, 2))
        for v in (['free', 'field'] if i == 0 else ['field']): nw[v].append(e)
    out['nwave'] = nw
    src = {}
    for tag in ['recv', 'buf', 'case']:
        S = SRC[tag]; rs = rays(S); src[tag] = {'free': [], 'field': []}
        if tag == 'case':   # source on the ground: direct and reflected coincide, (1+Q) in one FIR
            r, u, _ = rs[0]; f = np.fft.rfftfreq(NFIR, 1 / FS)
            H = 10 ** (-iso9613_alpha(f) * r / 20) * (1 + np.conj(ground_Q(f, r, max(0.02, abs(u[1])))))
            firs.append(b64(np.roll(np.fft.irfft(H, NFIR), LAT))); e = dict(g=1 / r, t=r / C0, fir=len(firs) - 1)
            src[tag]['free'].append(dict(g=1 / r, t=r / C0, fir=fir_id(r))); src[tag]['field'].append(e); continue
        for i, (r, u, gr) in enumerate(rs):
            e = dict(g=1 / r, t=r / C0, fir=fir_id(r, gr))
            for v in (['free', 'field'] if i == 0 else ['field']): src[tag][v].append(e)
    out['src'] = src
    first = min([blast['free'][0]['t']] + [e['t'] for e in nw['free']])
    out['t_first'] = first; out['t0'] = 0.010 - first
    return out


# ------------------------------------------------------------------ overlay recipes (geometry -> recipe)
def air_band():
    return [float(a) for a in iso9613_alpha(np.array(BANDS, float))]


def mean_sq_dir():
    th = np.linspace(0, np.pi, 2001)
    return float(np.trapezoid(dirfac(np.cos(th)) ** 2 * np.sin(th), th) / 2)


def eyring(Lr, alphas):
    Lx, Ly, Lz = Lr; V = Lx * Ly * Lz; areas = [Ly * Lz, Ly * Lz, Lx * Lz, Lx * Lz, Lx * Ly, Lx * Ly]; S = sum(areas)
    A = np.array([sum(areas[i] * alphas[i][b] for i in range(6)) for b in range(9)]); m = np.array(air_band()) / 4.343
    abar = np.minimum(A / S, 0.99)
    return V, S, (0.161 * V / (-S * np.log(1 - abar) + 4 * m * V)).tolist(), (0.161 * V / (A + 4 * m * V)).tolist()


def recipe_common(persp, eye):
    off = eye - EYE
    src = SRC['muzzle'] + off; lis = PERSP_LIS[persp] + off
    d = lis - src; rd = float(np.linalg.norm(d)); Dd = float(dirfac(d @ AXIS / rd))
    return dict(src=src.tolist(), lis=lis.tolist(), axis=AXIS.tolist(), rd=rd, Dd=Dd)


def room_recipe(persp, Lr, eye, surf, tmix, scat, length, extra=None, note=''):
    rc = recipe_common(persp, V3(*eye)); alphas = [MAT[s] for s in surf]
    V, S, t_ey, t_sab = eyring(Lr, alphas)
    Qd = mean_sq_dir() * (rc['rd'] / rc['Dd']) ** 2
    rc.update(len=length, seed='ir', elements=[
        dict(type='shoebox', L=Lr, alpha=alphas, tmax=tmix, scat=scat, mmax=None, bursts=0),
        dict(type='stat', T60=t_ey, var0=Qd * 4 * np.pi * C0 / V / FS, te0=rc['rd'] / C0, tmix=tmix, scat=scat, nrate=C0 * S / (4 * V))] + (extra or []),
        doc=dict(kind='shoebox image sources to %.0f ms + Eyring tail' % (tmix * 1e3), dims_m=Lr, surfaces=dict(zip(['x0', 'x1', 'floor', 'ceiling', 'z0_behind', 'z1_ahead'], surf)),
                 shooter_eye=eye, volume_m3=V, surface_m2=S, T60_eyring_s=[round(t, 2) for t in t_ey], T60_sabine_s=[round(t, 2) for t in t_sab], scattering=scat, note=note))
    return rc


def ground_element(persp):
    """The muzzle->listener ground bounce relative to the direct path (outdoor recipes)."""
    L = PERSP_LIS[persp]; M = SRC['muzzle']; d = L - M; r1 = np.linalg.norm(d)
    d2 = L * V3(1, -1, 1) - M; r2 = np.linalg.norm(d2)
    D1 = dirfac(d @ AXIS / r1); D2 = dirfac(d2 @ AXIS / r2)
    f = np.fft.rfftfreq(NFIR, 1 / FS)
    H = 10 ** (-iso9613_alpha(f) * (r2 - r1) / 20) * np.conj(ground_Q(f, r2, abs(d2[1]) / r2))
    return dict(type='fir', gain=float(D2 / r2 / (D1 / r1)), delay=float((r2 - r1) / C0), fir=b64(np.roll(np.fft.irfft(H, NFIR), LAT)))


def face(origin, eu, ev, nu, nv, mat, seed):
    return dict(type='patches', o=origin, eu=eu, ev=ev, nu=nu, nv=nv, alpha=MAT[mat], seed=seed)


def make_overlays():
    out = {}
    def add(name, title, persps, fn):
        out[name] = dict(title=title, persp={p: fn(p) for p in persps})
    add('concrete_room', 'Small concrete room 4 x 5 x 3 m', ['shooter'], lambda p: room_recipe(
        p, [4.0, 3.0, 5.0], [2.3, EYE_H, 1.2], ['block_painted', 'block_painted', 'concrete', 'concrete', 'block_painted', 'block_painted'], 0.08, 0.05, 2.6))
    add('furnished_room', 'Furnished room / house interior 4.5 x 6 x 2.5 m', ['shooter'], lambda p: room_recipe(
        p, [4.5, 2.5, 6.0], [1.9, EYE_H, 1.3], ['gypsum', 'gypsum', 'carpet_furnished', 'plaster', 'gypsum', 'gypsum'], 0.06, 0.35, 0.8,
        note='floor coefficient is carpet with the room furniture folded in'))
    add('hallway', 'Long hallway 1.8 x 30 x 2.6 m', ['shooter'], lambda p: room_recipe(
        p, [1.8, 2.6, 30.0], [0.8, EYE_H, 3.0], ['gypsum', 'gypsum', 'vinyl', 'gypsum', 'wood_door', 'wood_door'], 0.30, 0.10, 1.6))
    def lane(p):
        eye = [5.4, EYE_H, 3.0]; rc0 = recipe_common(p, V3(*eye)); taps = []
        for side in (-1, 1):   # stall partitions 0.6 m either side of the bore, first-order image
            src = np.array(rc0['src']); lis = np.array(rc0['lis']); img = src.copy(); img[0] = 2 * (src[0] + side * 0.6) - src[0]
            d = lis - img; r = np.linalg.norm(d); dd = d.copy(); dd[0] = -dd[0]
            g = float(dirfac(dd @ AXIS / r) / r / (rc0['Dd'] / rc0['rd']))
            taps.append([float((r - rc0['rd']) / C0), [g * math.sqrt(1 - a) for a in MAT['partition']]])
        return room_recipe(p, [12.0, 3.0, 28.0], eye, ['panel_block_mix', 'panel_block_mix', 'concrete', 'baffles', 'acoustic_panel', 'rubber_berm'], 0.12, 0.2, 1.2,
                           extra=[dict(type='taps', taps=taps)], note='25 m lane; stall partitions 0.6 m either side added as first-order images')
    add('indoor_range', 'Indoor range lane (baffles, rubber backstop)', ['shooter'], lane)
    add('warehouse', 'Warehouse / hangar 40 x 60 x 10 m', ['shooter', 'bystander', 'downrange'], lambda p: room_recipe(
        p, [40.0, 10.0, 60.0], [18.0, EYE_H, 6.0], ['metal_wall', 'metal_wall', 'concrete', 'metal_roof', 'metal_wall', 'metal_wall'], 0.25, 0.2, 4.0))

    def outdoor(p, length, elements, doc):
        rc = recipe_common(p, EYE); rc.update(len=length, seed='ir', elements=[ground_element(p)] + elements, doc=doc); return rc
    gdoc = 'Delany-Bazley ground, sigma %.0f kPa s/m^2, spherical-wave reflection' % GROUND_SIGMA
    add('open_field', 'Outdoor flat open field (ground reflection only)', ['shooter', 'bystander', 'downrange'],
        lambda p: outdoor(p, 0.12, [], dict(kind='direct + ground reflection', ground=gdoc)))
    def berm(p):
        rc0 = recipe_common(p, EYE); el = [face([-30, 0, 59], [60, 0, 0], [0, 6, 0], 60, 6, 'soil_berm', 'berm')]
        if p == 'shooter':   # the wooden bench under the muzzle (range page: top at y=0.99)
            src = np.array(rc0['src']); lis = np.array(rc0['lis']); img = src.copy(); img[1] = 2 * 0.99 - src[1]
            d = lis - img; r = np.linalg.norm(d); dd = d.copy(); dd[1] = -dd[1]
            g = float(dirfac(dd @ AXIS / r) / r / (rc0['Dd'] / rc0['rd']))
            el.append(dict(type='taps', taps=[[float((r - rc0['rd']) / C0), [g * math.sqrt(1 - a) for a in MAT['wood_bench']]]]))
        return outdoor(p, 0.75, el, dict(kind='ground + Lambert-scattering berm face + bench top', berm='face 60 x 6 m at z = 59 m (range page berm centred z = -62, 6 m deep)', ground=gdoc))
    add('range_berm', 'Outdoor range with an earth berm at about 60 m', ['shooter', 'bystander', 'downrange'], berm)
    add('forest_edge', 'Forest edge (tree line 80 m ahead)', ['shooter', 'bystander', 'downrange'], lambda p: outdoor(p, 1.8, [
        dict(type='trees', x0=-150, x1=150, z0=80, z1=200, density=0.04, radius=0.12, heff=3.0, foliage=FOLIAGE_DB_M, seed='trees')],
        dict(kind='ground + single scattering from tree trunks', trees='0.04 trunks/m^2, radius 0.12 m, 300 x 120 m stand starting 80 m ahead', foliage='ISO 9613-2 Table A.1 dB/m inside the stand', ground=gdoc)))
    def urban(p):
        eye = [6.0, EYE_H, 0.0]; rc = recipe_common(p, V3(*eye))
        rc.update(len=2.0, seed='ir', elements=[
            dict(type='shoebox', L=[18.0, 1000.0, 1000.0], alpha=[MAT['facade'], MAT['facade'], MAT['asphalt'], MAT['open'], MAT['open'], MAT['open']],
                 tmax=1.9, scat=0.3, mmax=[20, 0, 0], bursts=0.025),
            face([0, 0, 150 + eye[2]], [18, 0, 0], [0, 20, 0], 18, 20, 'facade', 'tjunction')],
            doc=dict(kind='image sources between two facades and the road + diffuse bursts + far facade', street='18 m wide, facades 20 m, shooter 6 m from the left facade firing along the street', facade_scattering=0.3, far_facade='T-junction building 150 m ahead'))
        return rc
    add('street_canyon', 'Urban street canyon', ['shooter', 'bystander', 'downrange'], urban)
    add('valley', 'Valley / canyon with distant echoes', ['shooter', 'bystander', 'downrange'], lambda p: outdoor(p, 6.0, [
        face([-180, 0, -100], [0, 0, 500], [0, 80, 0], 84, 13, 'rock', 'valleyL'),
        face([320, 0, 0], [0, 0, 600], [0, 120, 0], 100, 20, 'forest_slope', 'valleyR'),
        face([-200, 0, 750], [500, 0, 0], [0, 150, 0], 84, 25, 'rock', 'valleyH')],
        dict(kind='ground + Lambert scattering from three valley faces (first order only)', faces='rock wall 180 m left (500 x 80 m), forested slope 320 m right (600 x 120 m), rock head wall 750 m ahead (500 x 150 m)', ground=gdoc)))
    return out


def apply_action_timeline():
    """If the action simulation (../action/action.json) exists, take event times from it.
    Accepts {"events": [{"name": ..., "t_ms" | "t_s" | "t": ...}]} with times after the bullet leaves the muzzle
    (or after hammer strike if that is the earliest event). Returns the list of events it replaced."""
    path = os.path.join(HERE, '..', 'action', 'action.json')
    if not os.path.exists(path): return None
    try:
        ev = json.load(open(path)); ev = ev.get('events', ev) if isinstance(ev, dict) else ev
        keys = {'hammer': ['hammer'], 'piston': ['piston', 'rod', 'unlock'], 'deflector': ['deflector', 'eject'], 'buffer': ['buffer', 'rear', 'bottom'],
                'feed': ['feed', 'strip'], 'battery': ['battery', 'lock', 'closed']}
        got = {}
        for e in ev:
            nm = str(e.get('name', e.get('event', ''))).lower(); t = e.get('t_s', e['t_ms'] / 1e3 if 't_ms' in e else e.get('t'))
            if t is None: continue
            for k, words in keys.items():
                if k not in got and any(w in nm for w in words) and not ('unlock' in nm and k == 'battery'): got[k] = float(t)
        for row in CYCLE:
            if row[0] in got: row[1] = got[row[0]]
            if row[0] == 'spring' and 'buffer' in got: row[1] = got['buffer']
        return got
    except Exception as ex:
        print('action.json present but not understood (%s); using the built-in timeline' % ex); return None


def make_params():
    firs = []; action = apply_action_timeline()
    dec = signal.firwin(127, 0.9 / OS, window=('kaiser', 9.0))
    P = dict(version=1, fs=FS, os=OS, c=C0, rise=RISE, bands=BANDS, air_band=air_band(), mu=MU, fir_lat=LAT,
             atmosphere=dict(T_C=T_C, RH=RH, p_Pa=P_ATM), dec=b64(dec), shot_sd_db=SHOT_SD_DB,
             variants=VARIANTS, cycle=CYCLE, cycle_s=CYCLE_S, mech=mech_tables(), mech_clips=MECH_CLIPS,
             persp={n: make_persp(n, firs) for n in PERSP_LIS}, steel=steel_tables(), hpd=hpd_table(), overlays=make_overlays())
    P['firs'] = firs; P['action_timeline_from'] = 'action/action.json' if action else 'built-in (sim.py CYCLE)'
    return json.loads(json.dumps(P))        # exactly what the JS port reads


# ================================================================== stage B: tables -> waveforms (ported in hk416-sound.js)
def decimate_place(out, x, t_arr, gain, P, fir=None):
    """x is at FSO starting at source time 0; band-limit, decimate and add into out (48 kHz) at t_arr."""
    dec = P['_dec']; shift = rnd(t_arr * FSO); o = shift % OS; base = shift // OS
    xp = np.concatenate([np.zeros(o + 64), x, np.zeros(68)])
    y = np.convolve(xp, dec)[63::OS]
    add_at(out, y, base - 16, gain, P, fir)


def add_at(out, y, n0, gain, P, fir=None):
    if fir is not None and fir >= 0:
        y = np.convolve(y, P['_firs'][fir]); n0 -= P['fir_lat']
    a = max(0, -n0); b = min(len(y), len(out) - n0)
    if b > a: out[n0 + a:n0 + b] += gain * y[a:b]


def friedlander(Pk, T, rise):
    n = int((rise + 10 * T) * FSO) + 2; t = np.arange(n) / FSO - rise
    return np.where(t < 0, Pk * (1 + t / rise), Pk * (1 - t / T) * np.exp(-t / T))


def nwave(dp, T, rise):
    n = int((T + 2 * rise) * FSO) + 3; t = np.arange(n) / FSO
    return np.where(t < rise, dp * t / rise, np.where(t < rise + T, dp * (1 - 2 * (t - rise) / T), np.where(t < T + 2 * rise, -dp * (1 - (t - rise - T) / rise), 0.0)))


def mech_sig(ev, seed):
    T60max = max(m[1] for m in ev['modes']); n = int(FS * (min(0.45, 1.2 * T60max) + 0.005)); t = np.arange(n) / FS
    s = np.zeros(n)
    for f, T60, a in ev['modes']: s += a * np.exp(-6.9078 * t / T60) * np.sin(2 * np.pi * f * t)
    amp, tau = ev['click']
    if amp > 0:
        m = min(n, int(8 * tau * FS) + 1); s[:m] += amp * Rng(seed).g(m) * np.exp(-t[:m] / tau)
    return s / np.max(np.abs(s)) * P_REF * 10 ** (ev['p1m'] / 20)


def jet_sig(rms, tau, seed):
    n = int(8 * tau * FS); x = Rng(seed).g(n); a = 1 / (1 + 2 * np.pi * 800 / FS)
    y = signal.lfilter([a, -a], [1, -a], x); t = np.arange(n) / FS
    return rms * y * (1 - np.exp(-t / 1e-4)) * np.exp(-t / tau)


def prep(P):
    if '_dec' not in P:
        P['_dec'] = unb64(P['dec']); P['_firs'] = [unb64(s) for s in P['firs']]
    return P


def add_events(out, P, pp, events, ts, field, seed, jt=1.0, ja=None):
    for i, (name, te, pos) in enumerate(events):
        sig = mech_sig(P['mech'][name], '%s/%s' % (seed, name)) * (10 ** (ja[i] / 20) if ja is not None else 1.0)
        for path in pp['src'][pos]['field' if field else 'free']:
            add_at(out, sig, rnd((ts + te * jt + path['t'] + pp['t0']) * FS), path['g'], P, path['fir'])


def synth_dry(P, persp, variant, field=False, parts=('blast', 'nwave', 'mech')):
    """Pressure in Pa at 48 kHz for one perspective and fire variant."""
    prep(P); pp = P['persp'][persp]; var = P['variants'][variant]; v = 'field' if field else 'free'
    out = np.zeros(int(var['len'] * FS)); t0 = pp['t0']; rise = P['rise']
    for k, ts in enumerate(var['times']):
        j = Rng('shot%d' % k).g(16); jP = 10 ** (P['shot_sd_db'] * j[0] / 20); jt = 1 + 0.015 * j[1]
        if 'blast' in parts:
            for e in pp['blast'][v]: decimate_place(out, friedlander(e['P'] * jP, e['T'], rise), ts + e['t'] + t0, 1.0, P, e['fir'])
            for e in pp['sec'][v]: decimate_place(out, friedlander(e['P'] * jP, e['T'], rise), ts + e['t'] + t0, 1.0, P, e['fir'])
            for i, e in enumerate(pp['jet'][v]): add_at(out, jet_sig(e['rms'] * jP, e['tau'], 'jet%d/%d' % (k, i)), rnd((ts + e['t'] + t0) * FS), 1.0, P, e['fir'])
        if 'nwave' in parts:
            for e in pp['nwave'][v]: decimate_place(out, nwave(e['dp'], e['T'], rise), ts + e['t'] + t0, 1.0, P, e['fir'])
        if 'mech' in parts:
            ev = list(P['cycle'])
            if var['reset'] is not None: ev.append(['reset', var['reset'], 'recv'])
            add_events(out, P, pp, ev, ts, field, 'shot%d' % k, jt, 1.5 * j[2:2 + len(ev)])
    return out


def synth_mech(P, clip, persp='shooter', field=False):
    prep(P); pp = P['persp'][persp]; ev = P['mech_clips'][clip]
    out = np.zeros(int((max(e[1] for e in ev) + 0.5) * FS))
    add_events(out, P, pp, ev, 0.0 - pp['t0'] + 0.005 - min(0, min(e[1] for e in ev)), field, 'clip/' + clip)
    return out


def synth_steel(P, key, dist=None, seed=0):
    """AR500 plate ring heard at dist metres (free field, air absorption per mode). Pa at 48 kHz."""
    st = P['steel'][key]; d = st['dist'] if dist is None else dist
    n = int(1.6 * FS); t = np.arange(n) / FS; s = np.zeros(n)
    rg = Rng('steelhit/%s/%d' % (key, seed)); w = 0.6 + 0.8 * rg.u(len(st['modes']))      # hit-to-hit variation of modal weights
    for (f, T60, p1, al), wi in zip(st['modes'], w):
        s += wi * p1 * 10 ** (-al * d / 20) * np.exp(-6.9078 * t / T60) * np.sin(2 * np.pi * f * t)
    m = int(8 * st['splash']['tau'] * FS); s[:m] += st['splash']['p1m'] * rg.g(m) * np.exp(-t[:m] / st['splash']['tau'])
    return s / d


def band_weights(nf):
    f = np.fft.rfftfreq(nf, 1 / FS); u = np.log2(np.maximum(f, 1e-3) / 63.0); W = np.zeros((9, len(f)))
    for b in range(9):
        x = np.clip(u - b, -1, 1); w = np.cos(np.pi / 2 * x) ** 2
        if b == 0: w = np.where(u < 0, 1.0, w)
        if b == 8: w = np.where(u > 8, 1.0, w)
        W[b] = w
    return W


def el_shoebox(el, rc, P, taps, burst):
    L = el['L']; src = rc['src']; lis = rc['lis']; ax = rc['axis']; rmax = P['c'] * el['tmax'] + rc['rd']; s = el['scat']
    air = P['air_band']; gd = rc['Dd'] / rc['rd']; per = []
    for a in range(3):
        mm = el['mmax'][a] if el['mmax'] else int(math.ceil(rmax / (2 * L[a]))) + 1
        m = np.repeat(np.arange(-mm, mm + 1), 2); p = np.tile([0, 1], 2 * mm + 1)
        pos = (1 - 2 * p) * src[a] + 2 * m * L[a]; c0 = np.abs(m - p); c1 = np.abs(m)
        beta0 = np.sqrt(1 - np.array(el['alpha'][2 * a])); beta1 = np.sqrt(1 - np.array(el['alpha'][2 * a + 1]))
        gain = beta0[None, :] ** c0[:, None] * beta1[None, :] ** c1[:, None]
        per.append((lis[a] - pos, 1 - 2 * p, c0 + c1, gain))
    dx, dy, dz = np.meshgrid(per[0][0], per[1][0], per[2][0], indexing='ij')
    r = np.sqrt(dx * dx + dy * dy + dz * dz); mask = r < rmax
    fx, fy, fz = np.meshgrid(per[0][1], per[1][1], per[2][1], indexing='ij')
    cos = (dx * fx * ax[0] + dy * fy * ax[1] + dz * fz * ax[2]) / np.maximum(r, 1e-9)
    order = per[0][2][:, None, None] + per[1][2][None, :, None] + per[2][2][None, None, :]
    g0 = dirfac(cos) / np.maximum(r, 1e-9) / gd
    idx = np.floor((r - rc['rd']) / P['c'] * FS + 0.5).astype(int)
    for b in range(9):
        gb = g0 * per[0][3][:, None, None, b] * per[1][3][None, :, None, b] * per[2][3][None, None, :, b] * 10 ** (-air[b] * r / 20)
        sel = mask & (order > 0) & (gb != 0) & (idx >= 0) & (idx < taps.shape[1])
        np.add.at(taps[b], idx[sel], (gb * (1 - s) ** (order / 2.0))[sel])
        if el['bursts']: np.add.at(burst[b], idx[sel], (gb ** 2 * (1 - (1 - s) ** order))[sel])


def el_patches(el, rc, P, taps):
    rg = Rng(el['seed']); o = np.array(el['o'], float); eu = np.array(el['eu'], float); ev = np.array(el['ev'], float)
    nu, nv = el['nu'], el['nv']; nrm = np.cross(eu, ev); dA = np.linalg.norm(nrm) / (nu * nv); nrm = nrm / np.linalg.norm(nrm)
    u = rg.u(3 * nu * nv).reshape(-1, 3); i = np.repeat(np.arange(nu), nv); j = np.tile(np.arange(nv), nu)
    p = o[None] + ((i + u[:, 0]) / nu)[:, None] * eu[None] + ((j + u[:, 1]) / nv)[:, None] * ev[None]
    sign = np.where(u[:, 2] < 0.5, -1.0, 1.0)
    src = np.array(rc['src']); lis = np.array(rc['lis']); ax = np.array(rc['axis'])
    d1 = p - src; r1 = np.linalg.norm(d1, axis=1); d2 = lis - p; r2 = np.linalg.norm(d2, axis=1)
    ci = np.abs(d1 @ nrm) / r1; cs = np.abs(d2 @ nrm) / r2
    g = dirfac(d1 @ ax / r1) / r1 * np.sqrt(ci * cs * dA / np.pi) / r2 / (rc['Dd'] / rc['rd']) * sign
    idx = np.floor((r1 + r2 - rc['rd']) / P['c'] * FS + 0.5).astype(int); ok = (idx >= 0) & (idx < taps.shape[1])
    for b in range(9):
        np.add.at(taps[b], idx[ok], (g * math.sqrt(1 - el['alpha'][b]) * 10 ** (-P['air_band'][b] * (r1 + r2) / 20))[ok])


def el_trees(el, rc, P, taps):
    rg = Rng(el['seed']); n = int(el['density'] * (el['x1'] - el['x0']) * (el['z1'] - el['z0'])); u = rg.u(3 * n).reshape(-1, 3)
    x = el['x0'] + u[:, 0] * (el['x1'] - el['x0']); z = el['z0'] + u[:, 1] * (el['z1'] - el['z0']); sign = np.where(u[:, 2] < 0.5, -1.0, 1.0)
    src = np.array(rc['src']); lis = np.array(rc['lis']); ax = np.array(rc['axis'])
    p = np.stack([x, np.full(n, 1.6), z], 1); d1 = p - src; r1 = np.linalg.norm(d1, axis=1); d2 = lis - p; r2 = np.linalg.norm(d2, axis=1)
    inside = np.maximum(0, z - el['z0']) * (r1 / np.maximum(1e-6, np.abs(d1[:, 2]))) + np.where(lis[2] < el['z0'], np.maximum(0, z - el['z0']) * (r2 / np.maximum(1e-6, np.abs(d2[:, 2]))), np.minimum(r2, 60.0))
    g = dirfac(d1 @ ax / r1) / r1 / r2 / (rc['Dd'] / rc['rd']) * sign
    idx = np.floor((r1 + r2 - rc['rd']) / P['c'] * FS + 0.5).astype(int); ok = (idx >= 0) & (idx < taps.shape[1])
    for b in range(9):
        ka = 2 * np.pi * P['bands'][b] / P['c'] * el['radius']; sig = 2 * el['radius'] * el['heff'] * min(1.0, ka * ka)
        np.add.at(taps[b], idx[ok], (g * math.sqrt(sig / (4 * np.pi)) * 10 ** (-(P['air_band'][b] * (r1 + r2) + el['foliage'][b] * inside) / 20))[ok])


def build_ir(P, overlay, persp):
    """Impulse response at 48 kHz, direct path = unit impulse at t = 0. Returns (h, info)."""
    rc = P['overlays'][overlay]['persp'][persp]; N = int(rc['len'] * FS); NF = 1 << int(math.ceil(math.log2(N + 4096)))
    taps = np.zeros((9, N)); burst = np.zeros((9, N)); var = np.zeros((9, N)); firs = []; has_noise = False; t = np.arange(N) / FS
    taps[:, 0] += 1.0
    for el in rc['elements']:
        ty = el['type']
        if ty == 'shoebox':
            el_shoebox(el, rc, P, taps, burst)
            if el['bursts']:
                a = math.exp(-1 / (el['bursts'] * FS)); has_noise = True
                for b in range(9): var[b] += signal.lfilter([1 - a], [1, -a], burst[b])
        elif ty == 'stat':
            has_noise = True; te = t + el['te0']
            w = np.where(t >= el['tmix'], 1.0, 1 - (1 - el['scat']) ** (el['nrate'] * te))
            for b in range(9): var[b] += el['var0'] * np.exp(-13.8155 * te / el['T60'][b]) * w
        elif ty == 'taps':
            for delay, g in el['taps']:
                i = rnd(delay * FS)
                for b in range(9): taps[b, i] += g[b]
        elif ty == 'fir': firs.append(el)
        elif ty == 'patches': el_patches(el, rc, P, taps)
        elif ty == 'trees': el_trees(el, rc, P, taps)
    W = band_weights(NF); H = np.zeros(NF // 2 + 1, complex)
    for b in range(9): H += np.fft.rfft(taps[b], NF) * W[b]
    h = np.fft.irfft(H, NF)[:N]
    if has_noise:
        WF = np.fft.rfft(Rng('%s/%s/%s' % (rc['seed'], overlay, persp)).g(NF))
        for b in range(9): h += np.fft.irfft(WF * W[b], NF)[:N] * np.sqrt(var[b])
    for el in firs:
        add_at(h, unb64(el['fir']), rnd(el['delay'] * FS) - P['fir_lat'], el['gain'], P)
    assert np.isfinite(h).all()
    nfade = int(0.02 * FS); h[-nfade:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(nfade) / nfade)
    return h


# ================================================================== output
def true_peak(x):
    return float(np.max(np.abs(signal.resample_poly(x, 4, 1)))) if len(x) else 0.0


def a_weight(x):
    f = np.fft.rfftfreq(len(x), 1 / FS); f2 = f * f
    A = 12194 ** 2 * f2 * f2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2)) * 10 ** (2.0 / 20)
    return np.fft.irfft(np.fft.rfft(x) * A, len(x))


def levels(x):
    pk = float(np.max(np.abs(x)))
    return dict(peak_pa=round(pk, 4), peak_db_spl=round(20 * math.log10(pk / P_REF), 1),
                sel_db=round(10 * math.log10(np.sum(x ** 2) / FS / P_REF ** 2), 1), sel_a_db=round(10 * math.log10(np.sum(a_weight(x) ** 2) / FS / P_REF ** 2), 1))


def write_wav(path, x, bits=24):
    import wave
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(bits // 8); w.setframerate(FS)
        if bits == 16:
            w.writeframes((np.clip(x, -1, 1) * 32767).round().astype('<i2').tobytes())
        else:
            v = (np.clip(x, -1, 1) * 8388607).round().astype('<i4'); b = v.view(np.uint8).reshape(-1, 4)[:, :3]
            w.writeframes(b.tobytes())


def write_flac(path, x, bits=16, dither=True):
    tmp = path + '.tmp.wav'
    if dither and bits == 16:
        u = Rng('dither/' + os.path.basename(path)).u(2 * len(x)); x = x + (u[0::2] - u[1::2]) / 32768.0
    write_wav(tmp, x, 24 if bits == 24 else 16)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'flac', '-compression_level', '12', path], check=True)
    os.remove(tmp)


MANIFEST = []


def emit(name, x, what, kind, master=True, bits=16, norm_db=-1.0, extra=None):
    """Normalise to -1 dBTP, write the listening copy (FLAC) and optionally a 24-bit WAV master."""
    tp = true_peak(x); scale = 10 ** (norm_db / 20) / tp; y = x * scale
    rel = 'audio/%s.flac' % name; write_flac(os.path.join(HERE, rel), y, bits, dither=(bits == 16 and kind != 'ir'))
    if master: write_wav(os.path.join(MASTERS, name + '.wav'), y, 24)
    e = dict(id=name, file=rel, kind=kind, what=what, seconds=round(len(x) / FS, 3), normalised_dbtp=norm_db, units_per_fullscale=round(1 / scale, 6))
    e.update(extra or {}); MANIFEST.append(e)
    print('  %-34s %6.2fs  %s' % (name, len(x) / FS, {k: e[k] for k in e if k in ('peak_db_spl', 'energy_gain_db_vs_free')}))
    return e


def run_dry(P):
    print('dry shots')
    for persp in ['shooter', 'bystander', 'downrange']:
        for var in VARIANTS:
            for field in (False, True):
                x = synth_dry(P, persp, var, field); lv = levels(x)
                nm = 'dry_%s_%s_%s' % (persp, var, 'field' if field else 'free')
                emit(nm, x, ('%s, %s, %s. ' % (persp, var, 'open ground (ground reflection included): the Part 1 dry render' if field else 'free field (no reflections): convolve this with an overlay IR')) +
                     'Unit is pascals.', 'dry', extra=dict(perspective=persp, variant=var, ground=field, first_arrival_s=round(P['persp'][persp]['t_first'], 4), **lv))
    print('mechanical')
    for clip in MECH_CLIPS:
        x = synth_mech(P, clip); emit('mech_%s' % clip, x, 'mechanical action only, at the shooter ear: ' + ', '.join(e[0] for e in MECH_CLIPS[clip]), 'mech', extra=levels(x))
    print('steel')
    for key, st in P['steel'].items():
        for seed in (0, 1):
            x = synth_steel(P, key, seed=seed)
            emit('steel_%s_%dm_%d' % (key, st['dist'], seed), x, 'AR500 plate radius %.2f m hit by 5.56 at %d m, heard at the firing point (no delay baked in; add bullet flight + dist/343 s)' % (st['radius'], st['dist']),
                 'steel', extra=dict(radius_m=st['radius'], dist_m=st['dist'], lowest_mode_hz=st['modes'][0][0], modes=len(st['modes']), **levels(x)))


def run_overlays(P):
    print('overlays')
    dry = {p: synth_dry(P, p, 'single', False) for p in ['shooter', 'bystander', 'downrange']}
    for ov, o in P['overlays'].items():
        for persp in o['persp']:
            h = build_ir(P, ov, persp); wet = signal.fftconvolve(dry[persp], h)
            emit('ir_%s_%s' % (ov, persp), h, 'impulse response: %s, %s perspective. Direct path is the first sample; convolve a *_free dry render with it. Multiply by units_per_fullscale to restore the scale where the direct path = 1.' % (o['title'], persp),
                 'ir', master=False, bits=24, norm_db=-0.2, extra=dict(overlay=ov, perspective=persp, title=o['title'], doc=o['persp'][persp]['doc'],
                 peak_gain_db_vs_free=round(20 * math.log10(np.max(np.abs(wet)) / np.max(np.abs(dry[persp]))), 1),
                 energy_gain_db_vs_free=round(10 * math.log10(np.sum(wet ** 2) / np.sum(dry[persp] ** 2)), 1)))
    h = unb64(P['hpd']['fir'])
    emit('hpd_earmuff', h * 50, 'hearing protection: passive earmuff minimum-phase FIR (x50 so it survives 16-bit; divide by 50 = multiply by units_per_fullscale/50). Apply after the room.', 'hpd', master=False, bits=24, norm_db=-0.2,
         extra=dict(att_db=P['hpd']['att_db'], bands=BANDS, prescale=50))


def write_manifest():
    old = []
    mp = os.path.join(HERE, 'manifest.json')
    if os.path.exists(mp): old = json.load(open(mp)).get('outputs', [])
    ids = {e['id'] for e in MANIFEST}; outs = [e for e in old if e['id'] not in ids] + MANIFEST
    json.dump(dict(about='HK416 D14.5RS simulated sound. Everything here is synthesised by sound/sim.py from sound/params.json; nothing is a recording.',
                   sample_rate=FS, module='hk416-sound.js (synthesises the same sounds and IRs in the browser from params.json)',
                   chain='dry *_free -> convolve with ir_* (x units_per_fullscale) -> optional hpd_earmuff -> playback mapping (limiter/compressor, not physical)',
                   api={'S.shot(variant,{perspective,ground})': 'dry_<perspective>_<variant>_<free|field>', 'S.mech(clip)': 'mech_<clip>', 'S.steel(radius,{dist,seed})': 'steel_r<cm>_<dist>m_<seed>',
                        'S.ir(overlay,perspective)': 'ir_<overlay>_<perspective>', 'S.hpd()': 'hpd_earmuff'},
                   notes=['Fire dry_shooter_single_free once per round (it includes its own action and case sounds); semi3 and auto1s are fixed strings for listening.',
                          'IR files: ConvolverNode.normalize = false, then gain = units_per_fullscale so the direct path is 1.',
                          'Steel hits bypass the room IR (it is built for the muzzle). Delay them by bullet flight (dist/830 s) + dist/343 s.',
                          'Relative levels between files are in peak_db_spl; playback gain staging is a perceptual choice.'],
                   outputs=outs), open(mp, 'w'), indent=1)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for d in (AUDIO, MASTERS, COMPARE): os.makedirs(d, exist_ok=True)
    pj = os.path.join(HERE, 'params.json')
    if cmd in ('all', 'params') or not os.path.exists(pj):
        P = make_params(); json.dump(P, open(pj, 'w'), separators=(',', ':')); print('params.json', os.path.getsize(pj) // 1024, 'kB')
    P = prep(json.load(open(pj)))
    if cmd in ('all', 'dry'): run_dry(P)
    if cmd in ('all', 'overlays'): run_overlays(P)
    if MANIFEST: write_manifest()
    if cmd in ('all', 'compare'):
        sys.path.insert(0, HERE); import compare; compare.run(P)


if __name__ == '__main__':
    main()

"""HK416 D14.5RS muzzle flash and smoke: the physics (no rendering).

action/ interior ballistics (state of the bore at shot exit and its emptying) -> under-expanded jet through
the flash hider -> flash phases (thermal emission) -> photometry -> smoke puffs.

Nothing about the charge, the bore or the gas is set here: those numbers are read from ../action/action.json and
the bore's emptying is re-run from ../action/sim.py (ib_solve) with the calibrated constants stored in
action.json. Every other constant carries a source tag in PARAMS:
  'action'    read from ../action/action.json (which carries its own source for each)
  'model'     measured from ../model/build.py (the flash hider recipe)
  'published' a named publication, see README.md and REFERENCES.md
  'photo'     measured from a cited reference photo (REFERENCES.md); these are fits, not predictions
  'inferred'  an engineering estimate, not measured
SI units unless a name says otherwise. Flash time tau is seconds after the bullet base leaves the barrel crown.
"""
import importlib.util, json, math, os
import numpy as np
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
ACTION_DIR = os.path.join(os.path.dirname(HERE), 'action')
with open(os.path.join(ACTION_DIR, 'action.json')) as _f:
    ACTION = json.load(_f)
def _ap(k): return ACTION['params'][k]['value']

P_ATM, T_ATM, RHO_AIR, G = 101325.0, 293.0, 1.204, 9.81
R_UNIV = 8.314

# ---------------------------------------------------------------- parameters (value, unit, source, note)
PARAMS = {
    # the cartridge, bore and gas: action/'s numbers, not ours
    'charge_mass':     (_ap('m_charge'), 'kg', 'action', 'm_charge: ' + ACTION['params']['m_charge']['note']),
    'bore_area':       (_ap('bore_area'), 'm2', 'action', 'bore_area: ' + ACTION['params']['bore_area']['note']),
    'gamma':           (_ap('gamma'), '-', 'action', 'gamma: ' + ACTION['params']['gamma']['note']),
    'gas_constant':    (_ap('force_const') / _ap('flame_temp'), 'J/kg/K', 'action', 'force_const / flame_temp, as action/sim.py defines it'),
    'ignition_after_sear': (ACTION['events']['times']['ignition'], 's', 'action', 'events.ignition: sear release to the charge alight'),
    'exit_after_sear': (ACTION['events']['times']['bullet_exit'], 's', 'action', 'events.bullet_exit'),
    'socket_muzzle_z': (ACTION['meta']['nodes']['present']['socket_muzzle'][2], 'm', 'action', 'socket_muzzle in the gun frame (hider face, on the bore axis)'),
    # flash hider, from the modelled part (model/build.py build of flash_hider)
    'fh_len':          (42.9e-3, 'm', 'model', 'fh_l0 to fh_l1 in build.py; notes/NOTES.md: 42.9 mm long'),
    'fh_r':            (10.6e-3, 'm', 'model', 'fh_r: outer radius (21.2 mm diameter)'),
    'fh_chamber_r':    (7.8e-3, 'm', 'model', 'inner radius of the cage (15.6 mm open mouth)'),
    'fh_crown_back':   (34.9e-3, 'm', 'model', 'notes/NOTES.md: the barrel crown sits 8 mm inside the hider, so 34.9 mm behind its face'),
    'fh_slots':        (6, '-', 'model', 'six slots, 60 deg apart, first 30 deg from top (a real A2 has 5 and a closed bottom)'),
    'fh_slot_z':       ((-23.4e-3, -5.5e-3), 'm', 'model', 'slot ends from the hider face: build.py cuts a stadium from fh_l0 + 19.5 mm to fh_l1 - 5.5 mm'),
    'fh_slot_w':       (3.4e-3, 'm', 'model', 'slot width (stadium half-width 1.7 mm)'),
    'slot_cd':         (0.03, '-', 'photo', 'weight of the slot area against the open mouth in the MOMENTUM split. Fitted so the 16 in / 5-slot run puts the Mach disc where the TTAG A2 photo shows the upstream face of the glow (123 mm, +-12): nearly all the axial momentum stays in the mouth jet'),
    'slot_mass_cd':    (0.25, '-', 'inferred', 'discharge weight of the slot area against the open mouth for the MASS that leaves through the slots (the slots bleed the edge of the jet; its fast core goes straight on, so mass and momentum split differently)'),
    'slot_lean_deg':   (40.0, 'deg', 'photo', 'slot jets lean forward; angle from the bore, from the slot-jet blob in the TTAG A2 photo (+-10 deg)'),
    # jet
    'mach_disk_c':     (0.69, '-', 'published', 'x_M/D = 0.69 M_e sqrt(gamma p_e/p_inf): Lewis & Carlson (1964) form of the Mach disc distance of an under-expanded jet'),
    'slot_reach_cal':  (1.55, '-', 'photo', 'slot-jet glow sits about 50 mm from its slot in the TTAG A2 photo; the round-jet law scaled to the slot share gives less (sheet jets are not round jets)'),
    'disk_d_over_x':   (0.24, '-', 'photo', 'width of the glow behind the Mach disc / disc distance: fitted to the height of the glow in the TTAG A2 photo (30 mm at the photo\'s clip level). Steady-jet Mach discs are 0.4 to 0.5 of their distance across, so the bright core is narrower than the disc'),
    'establish_exp':   (20.0, '-', 'photo', 'while the shock still rides the bullet base it is only bullet-wide and faint; glow factor (x_disk / x_steady)^n. Fitted: the A2 photo is dark between the muzzle and the disc at its furthest'),
    'slot_glow_size':  (0.6, '-', 'photo', 'slot-jet glow is smaller than a round jet of the same flow would give (photo blob about 12 mm across)'),
    'slot_glow_factor':(0.2, '-', 'photo', 'slot-jet glow against the main glow per unit area, fitted to the blob above the hider in the TTAG A2 photo (thin sheet jets, oblique shocks)'),
    'front_speed_k':   (1.4, '-', 'inferred', 'gas front first outruns the bullet: initial front speed / muzzle velocity (the schlieren still shows the bullet inside the cloud)'),
    'front_t_decel':   (2.0e-4, 's', 'photo', 'front decelerates as x = a t / sqrt(1 + t/t_d); t_d fitted so the glow can reach as far down-range as the TTAG A2 photo shows (about 170 to 185 mm)'),
    'glow_len_over_x': (0.42, '-', 'photo', 'length of the luminous plume behind the disc / disc distance (TTAG A2 photo)'),
    # emission
    'soot_kappaY':     (50.0, 'm2/kg', 'inferred', 'grey absorption of particulates per kg of gas (about 1 % soot at 5 m2/g)'),
    'dT_chem':         (300.0, 'K', 'published', 'air burning into the shocked gas (intermediate flash): line reversal 1600 rising to 1940 K in a 7.62 mm rifle (Klingenberg & Mach 1976)'),
    'flush_k':         (0.2, '-', 'photo', 'the burning behind the Mach disc dies away once the disc has reached its furthest point, with time constant flush_k * x_max / v_muzzle (the air caught between the blast and the jet is used up). Fitted to the dark gap between muzzle and glow in the TTAG A2 photo'),
    'glow_floor':      (0.05, '-', 'photo', 'shocked gas that is not burning glows at this fraction of what its temperature and particulate load would give. Fitted to the dark gap in the TTAG A2 photo: the visible intermediate flash is mostly the burning'),
    'T_secondary':     (2400.0, 'K', 'published', 'Klingenberg & Mach 1976: secondary flash about 2500 K (7.62 mm rifle); taken a little lower for the smaller fireball'),
    'sec_rise':        (1.5e-3, 's', 'inferred', 'secondary flash pulse I ~ (t/tr) exp(1 - t/tr)'),
    'sec_delay':       (0.6e-3, 's', 'inferred', 'ignition delay after bullet exit'),
    'sec_hider_scale': (0.3, '-', 'inferred', 'a secondary flash that does light through the hider is a partial one (see the photo comparison: the two service photos bracket it)'),
    'T_ignite_sigma':  (60.0, 'K', 'inferred', 'shot-to-shot spread used to turn the margin into a probability'),
    # photometric anchors (16 in barrel, American Eagle 5.56, dark indoor range)
    'anchor_lux_a2':   (0.48 - 0.25, 'lx', 'published', 'TTAG flash hider shootout: A2 birdcage 0.48 lx with 0.25 lx ambient'),
    'anchor_lux_bare': (10760.0, 'lx', 'published', 'TTAG flash hider shootout: bare muzzle 10,760 lx'),
    'anchor_dist':     (0.61, 'm', 'inferred', 'the TTAG meter stood beside the muzzle; about two feet is read off their set-up photo, not stated to the centimetre'),
    'anchor_tau':      (10e-3, 's', 'inferred', 'peak-hold lux meter modelled as first order with a 10 ms response (typical of hand-held meters; TTAG does not give it)'),
    # smoke
    'smoke_mass_frac': (0.015, '-', 'inferred', 'particulate (soot, K salts, primer and jacket metal) / charge mass'),
    'smoke_kext':      (5.0e3, 'm2/kg', 'inferred', 'visible mass extinction coefficient of the particulate'),
    'smoke_albedo':    (0.6, '-', 'inferred', 'single-scatter albedo: grey-white, slightly blue in thin layers'),
    'entrain_alpha':   (0.28, '-', 'published', 'puff entrainment coefficient (turbulent puffs and thermals: 0.25 to 0.3, Turner 1973)'),
    'ambient_spread':  (0.06, 'm/s', 'inferred', 'slow growth of the puff radius by ambient turbulence'),
    'gas_block_frac':  (0.03, '-', 'inferred', 'share of gas vented at the piston gas block'),
    'eject_frac':      (0.015, '-', 'inferred', 'share of smoke leaving the ejection port (piston gun: small, manual p.11)'),
}
def P(k): return PARAMS[k][0]

# ---------------------------------------------------------------- the drive: action/'s interior ballistics
_ACTION_SIM = None
def action_sim():
    """../action/sim.py as a module, with the calibrated constants it stored in action.json (no re-calibration)."""
    global _ACTION_SIM
    if _ACTION_SIM is None:
        spec = importlib.util.spec_from_file_location('hk416_action_sim', os.path.join(ACTION_DIR, 'sim.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        for k in ('burn_coeff', 'form_theta', 'blowdown_scale'): m.setp(k, _ap(k))
        _ACTION_SIM = m
    return _ACTION_SIM

def drive(barrel_len=None):
    """State of the bore at shot exit and its emptying, from action/sim.py ib_solve.
    barrel_len (m) other than the HK416's is used only for the 16 in reference run behind the photo and
    light-meter comparisons: same cartridge, same calibrated burn law, a longer tube.
    Returns v (muzzle velocity), p_base, p_mean and T (reservoir pressure and temperature as the bullet leaves),
    Rg, t_exit (after ignition), and blow: tau, p0, T0 (the reservoir, taken as the stagnation state of the
    flow leaving the crown), mdot (choked or subsonic nozzle flow of that reservoir, the formula of
    action/sim.py) and thrust (action's bore force after exit, with its SAAMI momentum scale)."""
    m = action_sim(); keep = m.P['barrel_len']
    if barrel_len is not None: m.P['barrel_len'] = barrel_len
    try: tab, info = m.ib_solve(m.P['burn_coeff'], m.P['form_theta'])
    finally: m.P['barrel_len'] = keep
    g, Rg, A = P('gamma'), info['R'], P('bore_area')
    i = int(np.searchsorted(tab['t'], info['t_exit'] - 1e-12))
    tau = tab['t'][i:] - tab['t'][i]; p0 = tab['pm'][i:].copy(); T0 = tab['tg'][i:].copy(); th = tab['fg'][i:].copy()
    crit = (2 / (g + 1)) ** (g / (g - 1)); kflow = math.sqrt(g) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
    pr = np.maximum(P_ATM / p0, crit)
    sub = A * p0 * np.sqrt(np.maximum(2 * g / ((g - 1) * Rg * T0) * (pr ** (2 / g) - pr ** ((g + 1) / g)), 0.0))
    mdot = np.where(pr > crit, sub, A * p0 * kflow / np.sqrt(Rg * T0)) * (p0 > 1.05 * P_ATM)
    return dict(v=info['v_exit'], p_base=info['p_exit_base'], p_mean=info['p_exit_mean'], T=float(T0[0]), T_gas=float(tab['tg'][i - 1]), z=info['burnout_frac'],
                t_exit=info['t_exit'], p_max=info['p_max'], Rg=Rg, travel=info['travel'], barrel_len=barrel_len or keep,
                gas_eff_velocity=info['gas_eff_velocity'],
                blow=dict(t=tau, p0=p0, T0=T0, mdot=mdot, thrust=th))

# ---------------------------------------------------------------- jet
def area_mach(ar, g):
    f = lambda M: (1 / M) * ((2 / (g + 1)) * (1 + (g - 1) / 2 * M * M)) ** ((g + 1) / (2 * (g - 1))) - ar
    return brentq(f, 1.0001, 12)

class Shot:
    """Everything after the bullet leaves, for one configuration."""
    def __init__(self, ib, hider=True, slots=None):
        g = self.g = P('gamma'); self.ib = ib; self.hider = hider
        self.Rg = ib['Rg']; A = self.A = P('bore_area')
        self.Te = ib['T']; self.pe = ib['p_base']; self.ve = ib['v']
        self.ae = math.sqrt(g * self.Rg * self.Te)
        self.Me = self.ve / self.ae
        self.bd = ib['blow']
        self.T0 = float(np.mean(self.bd['T0'][1:6])); self.p00 = float(np.mean(self.bd['p0'][1:6]))   # first 25 microseconds
        self.n_slots = (P('fh_slots') if slots is None else slots) if hider else 0
        if hider:
            rc = P('fh_chamber_r'); self.Dm = 2 * rc
            self.Mm = area_mach(math.pi * rc * rc / A, g)
            a_m = math.pi * rc * rc
            z0, z1 = P('fh_slot_z'); w = P('fh_slot_w')
            a_s = self.n_slots * ((z1 - z0) * w + math.pi * (w / 2) ** 2)
            self.f_ax = a_m / (a_m + P('slot_cd') * a_s)                      # share of the MOMENTUM that stays in the mouth jet
            self.f_slot = (1 - a_m / (a_m + P('slot_mass_cd') * a_s)) / self.n_slots if self.n_slots else 0.0   # MASS share per slot
            self.a_slots = a_s
        else:
            self.Dm = math.sqrt(4 * A / math.pi); self.Mm = 1.0; self.f_ax = 1.0; self.f_slot = 0.0
        tt = np.linspace(0, 1.5e-3, 3001); xx = self.x_disk(tt)
        self.t_xmax = float(tt[int(np.argmax(xx))]); self.x_max = float(xx.max())      # the Mach disc at its furthest

    # exit stagnation state: the bore reservoir of action/sim.py
    def _i(self, t, key, right): return np.interp(np.asarray(t, float), self.bd['t'], self.bd[key], right=right)
    def p0(self, t): return self._i(t, 'p0', P_ATM)
    def T0t(self, t): return self._i(t, 'T0', T_ATM)
    def mdot(self, t): return self._i(t, 'mdot', 0.0)
    def thrust(self, t): return self._i(t, 'thrust', 0.0)
    def p_mouth(self, t):
        return self.p0(t) / (1 + (self.g - 1) / 2 * self.Mm ** 2) ** (self.g / (self.g - 1))
    # jet structure
    def x_full(self, t):
        """Steady Mach disc distance for the whole flow leaving the mouth."""
        return P('mach_disk_c') * self.Dm * self.Mm * np.sqrt(self.g * self.p_mouth(t) / P_ATM)
    def choked(self, t): return self.p0(t) > P_ATM * ((self.g + 1) / 2) ** (self.g / (self.g - 1))
    def x_front(self, t):
        t = np.asarray(t, float)
        return P('front_speed_k') * self.ve * t / np.sqrt(1 + t / P('front_t_decel'))
    def u_front(self, t):
        t = np.asarray(t, float); q = t / P('front_t_decel')
        return P('front_speed_k') * self.ve * (1 + q) ** -0.5 * (1 - 0.5 * q / (1 + q))
    def x_disk(self, t, share=None):
        """Mach disc distance: the steady value for the current exit state, but never ahead of the bullet's base
        while the bullet is still in the jet (smooth minimum). Slot jets: same law scaled to their share, times
        the photo calibration slot_reach_cal."""
        main = share is None
        share = self.f_ax if main else share
        xs = self.x_full(t) * math.sqrt(share) * self.choked(t) * (1.0 if main else P('slot_reach_cal'))
        xb = self.ve * np.asarray(t, float) * (1.0 if main else math.sqrt(share / self.f_ax) * P('slot_reach_cal'))
        return np.where((xs > 0) & (xb > 0), (np.maximum(xs, 1e-12) ** -4.0 + np.maximum(xb, 1e-12) ** -4.0) ** -0.25, 0.0)
    def blast_radius(self, t):
        """Spherical blast front, energy-fed: a fit to r = front early, then weak shock at the speed of sound."""
        t = np.asarray(t, float)
        return np.maximum(self.x_front(t), 0) + 343.0 * t * (1 - np.exp(-t / 3e-4))

# ---------------------------------------------------------------- photometry and colour
LAM = np.arange(380.0, 781.0, 5.0)      # nm
def _cmf(l):
    """CIE 1931 2-deg colour matching functions, Wyman-Sloan-Shirley (2013) multi-lobe fit."""
    def gs(x, mu, s1, s2): return np.exp(-0.5 * ((x - mu) / np.where(x < mu, s1, s2)) ** 2)
    x = 1.056 * gs(l, 599.8, 37.9, 31.0) + 0.362 * gs(l, 442.0, 16.0, 26.7) - 0.065 * gs(l, 501.1, 20.4, 26.2)
    y = 0.821 * gs(l, 568.8, 46.9, 40.5) + 0.286 * gs(l, 530.9, 16.3, 31.1)
    z = 1.217 * gs(l, 437.0, 11.8, 36.0) + 0.681 * gs(l, 459.0, 26.0, 13.8)
    return x, y, z
XB, YB, ZB = _cmf(LAM)
def planck(T, lam_nm=LAM):
    l = lam_nm * 1e-9
    return 1.191042e-16 / l ** 5 / np.expm1(np.minimum(1.438777e-2 / (l * T), 700.0))        # W m-2 sr-1 m-1
# emission features riding on the grey continuum: (centre nm, sigma nm, strength 0..1 of the blackbody ceiling)
LINES = {
    'Na D 589.0/589.6':  (589.3, 2.5, 1.0),
    'K 766.5/769.9':     (768.2, 3.0, 1.0),
    'CaOH 554':          (554.0, 6.0, 0.30),
    'CaOH 622':          (622.0, 8.0, 0.35),
    'CuOH/CuCl 525-555': (540.0, 12.0, 0.15),
}
def spectrum(T, eps, secondary=False):
    """Spectral radiance (W m-2 sr-1 nm-1): grey particulate continuum plus line/band features that fill
    toward the blackbody ceiling (thermal lines cannot exceed it). Secondary flash adds the CO+O continuum."""
    b = planck(T) * 1e-9
    f = sum(s * np.exp(-0.5 * ((LAM - c) / w) ** 2) for c, w, s in LINES.values())
    s = b * (eps + (1 - eps) * np.clip(f, 0, 1))
    if secondary:
        s = s + b[np.argmin(abs(LAM - 600))] * 0.05 * np.exp(-0.5 * ((LAM - 430.0) / 50.0) ** 2)
    return s
def luminance(spec): return 683.0 * np.trapezoid(spec * YB, LAM)              # cd/m2
M_XYZ2RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
def rgb_of(spec):
    """Linear sRGB with luminance 1 (out-of-gamut negatives clipped)."""
    xyz = np.array([np.trapezoid(spec * c, LAM) for c in (XB, YB, ZB)])
    rgb = np.clip(M_XYZ2RGB @ xyz, 0, None)
    return rgb / (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])
def bb_lum(T, eps=1.0, secondary=False): return luminance(spectrum(T, eps, secondary))

# ---------------------------------------------------------------- flash phases
def phases(shot, t, cal=1.0):
    """Instantaneous state of each luminous region at time t (s). Luminous intensity in cd (side-on)."""
    g, Rg = shot.g, shot.Rg
    kY = P('soot_kappaY')
    T0 = float(shot.T0t(t)); p0 = float(shot.p0(t))
    out = {}
    # primary: gas stagnating inside the cage, seen through the slots and the mouth
    if shot.hider:
        rho_h = 0.3 * p0 / (Rg * T0)
        eps_h = 1 - math.exp(-kY * rho_h * 4e-3)
        z0, z1 = P('fh_slot_z'); w = P('fh_slot_w')
        a_slot = (z1 - z0) * w
        Lh = bb_lum(T0, eps_h)
        # side-on: one slot square to the eye and two at 60 deg, bright over the front third
        out['primary'] = dict(T=T0, eps=eps_h, L=cal * Lh, I=cal * Lh * a_slot * (1 + 2 * 0.5) * 0.45,
                              I_front=cal * Lh * math.pi * P('fh_chamber_r') ** 2, slot_area=a_slot)
    else:
        rho_e = float(shot.p0(t)) * (2 / (g + 1)) ** (1 / (g - 1)) / (Rg * T0)
        eps = 1 - math.exp(-kY * rho_e * shot.Dm)
        Lh = bb_lum(T0 * 2 / (g + 1), eps)
        out['primary'] = dict(T=T0 * 2 / (g + 1), eps=eps, L=cal * Lh, I=cal * Lh * shot.Dm * 2 * shot.Dm,
                              I_front=cal * Lh * math.pi * shot.Dm ** 2 / 4, slot_area=0)
    # shocked gas behind a Mach disc: main jet and each slot jet
    burn = 1.0 if t <= shot.t_xmax else math.exp(-(t - shot.t_xmax) / (P('flush_k') * shot.x_max / shot.ve))
    Tg = T0 + P('dT_chem') * burn
    p_layer = max(P_ATM, 0.8 * RHO_AIR * float(shot.u_front(t)) ** 2)
    rho = p_layer / (Rg * Tg)
    def glow(share, origin_scale=1.0, factor=1.0, size=1.0):
        xM = float(shot.x_disk(t, None if share == shot.f_ax else share)); xF = float(shot.x_front(t)) * origin_scale
        W = size * max(P('disk_d_over_x') * xM, 0.4 * shot.Dm * math.sqrt(share / shot.f_ax))
        Ln = max(min(size * P('glow_len_over_x') * xM + 0.3 * W, xF - xM), 0.3 * W)
        eps = 1 - math.exp(-kY * rho * W)
        xs = float(shot.x_full(t)) * math.sqrt(share) * (1.0 if share == shot.f_ax else P('slot_reach_cal'))
        onset = (xM / xs) ** P('establish_exp') if xs > 0 else 0.0
        L = cal * bb_lum(Tg, eps) * onset * factor * (P('glow_floor') + (1 - P('glow_floor')) * burn)
        return dict(T=Tg, eps=eps, L=L, x_disk=xM, width=W, length=Ln, I=L * W * Ln * 0.6)
    out['intermediate'] = glow(shot.f_ax)
    if shot.n_slots:
        sj = glow(shot.f_slot, math.sqrt(shot.f_slot / shot.f_ax), P('slot_glow_factor'), P('slot_glow_size'))
        out['slot_jet'] = sj
    return out

def secondary_pulse(t, I_pk):
    tt = np.maximum(np.asarray(t, float) - P('sec_delay'), 0) / P('sec_rise')
    return I_pk * tt * np.exp(1 - tt)

def meter_reading(t, I, d, tau):
    """Peak of a first-order (time constant tau) illuminance meter at distance d."""
    y, pk = 0.0, 0.0
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        y += (I[i] / d ** 2 - y) * (1 - math.exp(-dt / tau)); pk = max(pk, y)
    return pk

def mix_temperature(shot, r):
    """Temperature of the burnt propellant gas mixed with r kg of air per kg of gas. The gas is taken at action/'s
    in-bore gas temperature as the bullet leaves (T_gas, the burnt fraction alone), cooled by the reservoir's
    expansion over the first 0.2 ms. T_gas rises as the barrel gets shorter, which is the observed trend."""
    cp_g, cp_a = shot.g * shot.Rg / (shot.g - 1), 1005.0
    Ts = shot.ib['T_gas'] * float(shot.T0t(2e-4)) / float(shot.T0t(0))
    return (Ts * cp_g + r * T_ATM * cp_a) / (cp_g + r * cp_a)

R_FLAMMABLE = 0.5      # kg air per kg gas for the fuel-rich gas to come inside its rich limit (inferred)
def ignition(shot, T_ign, r_hider):
    """Reduced-order secondary-flash criterion: is the gas still above the ignition temperature once it has
    entrained enough air to burn? A bare jet recompresses through one Mach disc with little air in it
    (r = R_FLAMMABLE); jets split by the hider entrain more air while still supersonic and cold (r = r_hider).
    T_ign and r_hider are FITTED to two observations (see sim.py), so this is a trend model, not a prediction."""
    r = r_hider if shot.hider else R_FLAMMABLE
    Tmix = mix_temperature(shot, r)
    margin = Tmix - T_ign
    prob = 0.5 * (1 + math.erf(margin / (math.sqrt(2) * P('T_ignite_sigma'))))
    return dict(T_mix_K=Tmix, air_per_gas=r, T_ignite_K=T_ign, margin_K=margin, probability=prob)

# ---------------------------------------------------------------- smoke puffs
def smoke_sources(shot):
    """Initial conditions of each smoke puff, in the muzzle frame (origin socket_muzzle, +Z down-range, +Y up,
    rifle's right side = -X; metres)."""
    C = P('charge_mass'); ms = C * P('smoke_mass_frac')
    tt = np.linspace(0, 8e-3, 4000)
    imp = float(np.trapezoid(shot.thrust(tt), tt))                    # gas impulse, N s
    heat = C * (shot.g * shot.Rg / (shot.g - 1)) * (shot.T0 - T_ATM)  # thermal energy above ambient, J
    gb, ej = P('gas_block_frac'), P('eject_frac')
    main = 1 - gb - ej - 0.02
    src = []
    def add(name, share, pos, direc, impulse, t0, r0, heat_share=None, note=''):
        d = np.array(direc, float); d /= np.linalg.norm(d)
        src.append(dict(name=name, t0=t0, pos=list(map(float, pos)), dir=d.round(4).tolist(), impulse=impulse,
                        gas_mass=C * share, smoke_mass=ms * share, heat=heat * (share if heat_share is None else heat_share),
                        r0=r0, note=note))
    if shot.hider:
        add('muzzle_forward', main * (1 - shot.n_slots * shot.f_slot), (0, 0, 0), (0, 0, 1), imp * shot.f_ax, 0.0, P('fh_chamber_r'),
            note='through the open mouth')
        lean = math.radians(P('slot_lean_deg')); zc = sum(P('fh_slot_z')) / 2
        for k in range(shot.n_slots):
            th = math.radians(30 + 60 * k)                          # from +Y (up) about the bore
            rx, ry = math.sin(th), math.cos(th)
            add(f'slot_{k + 1}', main * shot.f_slot, (rx * P('fh_r'), ry * P('fh_r'), zc),
                (rx * math.sin(lean), ry * math.sin(lean), math.cos(lean)), imp * (1 - shot.f_ax) / shot.n_slots, 0.0, 4e-3,
                note=f'slot at {30 + 60 * k} deg from top')
    else:
        add('muzzle_forward', main, (0, 0, 0), (0, 0, 1), imp, 0.0, 3e-3)
    add('muzzle_wisp', 0.02, (0, 0, 0), (0, 0.15, 1), C * 0.02 * 1.5, 0.03, 0.025, heat_share=0.01,
        note='inferred: slow hot gas left in the bore curls out after the jet')
    add('gas_block_vent', gb, (0, -0.012, -0.152), (0, -0.5, 1), C * gb * 300.0, 5e-4, 5e-3, heat_share=gb * 0.5,
        note='inferred: short-stroke piston vents at the gas block (152 mm behind the muzzle in the model)')
    add('ejection_port', ej, (-0.017, 0.002, -0.451), (-1, 0.35, -0.2), C * ej * 3.0, 0.012, 0.03, heat_share=0.002,
        note='inferred: chamber gas trailing the case; socket_eject. Piston gun, so small (manual p.11)')
    return src, imp, heat

WAKE = dict(head_share=0.6, fractions=[0.2, 0.4, 0.6, 0.8], share_each=0.1, radius_floor=0.35)
def puff_set(s, t, wind=(0.0, 0.0, 0.0)):
    """Head puff plus its stem: smoke left along the path (an inferred closure for the jet's shear layer).
    Returns a list of (pos, radius, tau_centre)."""
    p, R, _ = puff_track(s, [t], wind)
    if R[0] <= 0: return []
    o = np.array(s['pos'], float); out = []
    for f, sh in [(1.0, WAKE['head_share'])] + [(f, WAKE['share_each']) for f in WAKE['fractions']]:
        r = R[0] * (WAKE['radius_floor'] + (1 - WAKE['radius_floor']) * f)
        out.append((o + (p[0] - o) * f, r, P('smoke_kext') * s['smoke_mass'] * sh / (2 * math.pi * (r / 2) ** 2)))
    return out

def puff_track(s, times, wind=(0.0, 0.0, 0.0)):
    """Integrate one puff: entrainment dilutes its momentum (entrained air carries the wind), heat gives lift.
    Geometric time steps so the JS module can repeat exactly the same sums. Returns pos (n,3), radius, tau0."""
    a, ka = P('entrain_alpha'), P('ambient_spread')
    wind = np.array(wind, float)
    pos = np.array(s['pos'], float); R = s['r0']
    M = s['gas_mass'] + RHO_AIR * 4 / 3 * math.pi * R ** 3
    mom = np.array(s['dir'], float) * s['impulse']
    lift = G * s['heat'] / (1005.0 * T_ATM)                        # N, constant (heat conserved)
    t = 0.0; dt = 2e-6
    out_p, out_r = [], []
    times = np.asarray(times, float); i = 0
    while i < len(times):
        tgt = times[i] - s['t0']
        if tgt <= 0:
            out_p.append(pos.copy()); out_r.append(0.0); i += 1; continue
        while t < tgt:
            h = min(dt, tgt - t)
            u = mom / M
            urel = float(np.linalg.norm(u - wind))
            dM = RHO_AIR * 4 * math.pi * R * R * (a * urel + ka) * h
            mom = mom + wind * dM + np.array([0, lift, 0]) * h
            M += dM
            pos = pos + u * h
            R = (3 * (M - s['gas_mass']) / (4 * math.pi * RHO_AIR)) ** (1 / 3)
            t += h; dt = min(dt * 1.05, 5e-3)
        out_p.append(pos.copy()); out_r.append(R); i += 1
    R = np.array(out_r)
    tau0 = np.where(R > 0, P('smoke_kext') * s['smoke_mass'] / (2 * math.pi * np.maximum(R / 2, 1e-6) ** 2), 0)
    return np.array(out_p), R, tau0

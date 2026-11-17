#!/usr/bin/env python3
"""HK416 D14.5RS: lumped-parameter simulation of the firing train, internal ballistics, short-stroke gas
operating cycle, recoil into a shooter, and case ejection.

    python3 sim.py            # rebuilds action.json and plots/ (about a minute)
    python3 sim.py --no-plots # data only

Frame (same as hk416.glb): metres, +Z towards the muzzle, +Y up, +X to the shooter's left; origin on the bore
axis at the upper receiver's front face. Time zero is the sear releasing the hammer (the trigger break).
Every parameter carries its source in PARAMS: 'manual' (HK maintenance manual, see ../MANUAL_NOTES.md),
'published' (widely published figure, named), 'model' (measured from hk416.glb / build.py), 'inferred'
(engineering estimate, not measured) or 'calibrated' (solved so that a published figure is reproduced).
"""
import json, math, os, struct, sys, time

import numpy as np
from scipy.optimize import brentq, root

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(os.path.dirname(HERE), 'model')
GR = 6.479891e-5          # kg per grain
PATM = 101325.0

# ============================================================================ parameters
# key: (value, unit, source, note)
PARAMS = {
    # ---- cartridge and barrel
    'm_bullet':      (62 * GR, 'kg', 'published', 'M855 ball, 62 gr'),
    'm_charge':      (26.1 * GR, 'kg', 'published', 'M855: 26.1 gr WC844 (US Army TM 43-0001-27); varies by lot'),
    'm_case':        (6.2e-3, 'kg', 'inferred', 'fired 5.56 brass case with primer cup, about 95 gr'),
    'm_round':       (12.3e-3, 'kg', 'published', 'M855 cartridge, about 190 gr'),
    'barrel_len':    (0.3683, 'm', 'manual', '14.5 in, bolt face to muzzle'),
    'bullet_base0':  (0.0343, 'm', 'inferred', 'bullet base from the bolt face when chambered (57.4 mm overall, 23.1 mm bullet)'),
    'bore_area':     (2.48e-5, 'm^2', 'inferred', '5.56 mm lands / 5.69 mm grooves, mean'),
    'chamber_vol':   (1.76e-6, 'm^3', 'inferred', 'case capacity behind the seated bullet'),
    'port_to_muzzle': (0.1257, 'm', 'model', 'gas block centre to barrel crown in hk416.glb (photo-derived, not a published port position)'),
    'p_max_target':  (358.5e6, 'Pa', 'manual', 'chamber pressure 52,000 psi (p. 7)'),
    'v_muzzle_target': (850.0, 'm/s', 'manual', '2,790 ft/s for the 14.5 in barrel (p. 7)'),
    # ---- propellant (lumped)
    'force_const':   (1.00e6, 'J/kg', 'inferred', 'propellant force (impetus), typical double-base ball powder'),
    'gamma':         (1.24, '-', 'inferred', 'ratio of specific heats of propellant gas'),
    'covolume':      (0.95e-3, 'm^3/kg', 'inferred', 'Nobel-Abel covolume'),
    'rho_prop':      (1620.0, 'kg/m^3', 'inferred', 'solid propellant density'),
    'flame_temp':    (2850.0, 'K', 'inferred', 'adiabatic flame temperature; sets the gas constant R = F/T0'),
    'form_theta':    (None, '-', 'calibrated', 'form function psi = (1+th)Z - th Z^2; negative = progressive (deterred ball grain); solved for the manual muzzle velocity'),
    'burn_exp':      (0.90, '-', 'inferred', 'pressure exponent of the burn rate'),
    'burn_coeff':    (None, '1/s', 'calibrated', 'vivacity dZ/dt at 100 MPa; solved for the manual chamber pressure'),
    'loss_factor':   (0.20, '-', 'inferred', 'heat loss to the bore as a fraction of the work done on bullet and gas'),
    'gas_velocity_conv': (1219.2, 'm/s', 'published', 'SAAMI free-recoil convention: propellant gas leaves at 4,000 ft/s (high-power rifle)'),
    'blowdown_scale': (None, '-', 'calibrated', 'scale on the lumped blowdown thrust so total gas momentum equals the SAAMI convention (the raw lumped figure is kept in validation)'),
    'p_ign':         (5.0e6, 'Pa', 'inferred', 'primer/igniter pressure that starts the charge burning'),
    'p_shot_start':  (30.0e6, 'Pa', 'inferred', 'bullet pull and crimp release pressure'),
    'p_engrave':     (22.0e6, 'Pa', 'inferred', 'extra engraving resistance, decays over engrave_len'),
    'p_friction':    (8.0e6, 'Pa', 'inferred', 'bore friction as an equivalent pressure'),
    'engrave_len':   (0.004, 'm', 'inferred', ''),
    'muzzle_cf':     (None, '-', 'derived', 'sonic-exit thrust coefficient (g+1)(2/(g+1))^(g/(g-1)) during blowdown'),
    'brake_beta':    (0.0, '-', 'inferred', 'momentum recovered by the muzzle device; the HK "compensator" is a flash hider, taken as 0'),
    # ---- firing train
    'trigger_pull':  (23.6, 'N', 'manual', '4.6 to 6 lb (20.5 to 26.7 N), midpoint; not used in the dynamics'),
    'hammer_inertia': (1.6e-5, 'kg m^2', 'inferred', 'about 33 g hammer, 22 mm radius of gyration about its pin'),
    'hammer_torque_cocked': (0.62, 'N m', 'inferred', 'hammer spring torque on the sear'),
    'hammer_torque_fired': (0.40, 'N m', 'inferred', 'hammer spring torque resting on the firing pin'),
    'hammer_fall':   (60.0, 'deg', 'inferred', 'rotation from the sear to first contact with the firing pin'),
    'hammer_eff':    (0.90, '-', 'inferred', 'fraction of spring torque left after pivot friction'),
    'hammer_strike_r': (0.030, 'm', 'inferred', 'hammer pin to the face that strikes the firing pin'),
    'hammer_overcock': (6.0, 'deg', 'inferred', 'how far the carrier holds the hammer below the sear'),
    'fp_mass':       (8.3e-3, 'kg', 'inferred', 'AR-pattern firing pin, about 0.3 oz'),
    'fp_float':      (1.5e-3, 'm', 'inferred', 'free travel of the floating pin before its tip meets the primer'),
    'fp_protrusion': (1.0e-3, 'm', 'manual', 'firing pin protrusion 0.90 to 1.10 mm (p. 17): the hard stop on indentation'),
    'primer_f0':     (400.0, 'N', 'inferred', 'primer cup yield force'),
    'primer_k':      (1.0e6, 'N/m', 'inferred', 'primer cup hardening slope'),
    'primer_fire_indent': (0.30e-3, 'm', 'inferred', 'indent at which the priming mix initiates'),
    'primer_delay':  (0.15e-3, 's', 'inferred', 'primer initiation to flame in the charge (start of the ballistics model)'),
    # ---- gas system (short-stroke piston)
    'port_d':        (None, 'm', 'calibrated', 'barrel gas port diameter; solved for the target cyclic rate'),
    'cyclic_target': (800.0, 'rpm', 'manual', 'midpoint of the manual 700 to 900 rpm (p. 7)'),
    'piston_d':      (0.0100, 'm', 'inferred', 'piston diameter, from the 9.8 mm piston tube in the model'),
    'cyl_vol0':      (0.60e-6, 'm^3', 'inferred', 'gas cylinder dead volume'),
    'vent_open_x':   (0.003, 'm', 'inferred', 'piston travel at which the cylinder vents'),
    'vent_area':     (12.0e-6, 'm^2', 'inferred', 'vent area once open'),
    'leak_area':     (0.15e-6, 'm^2', 'inferred', 'leakage past the three piston rings'),
    'rod_stop_x':    (0.016, 'm', 'inferred', 'travel at which the piston rod stops and the carrier runs on alone'),
    'orifice_cd':    (0.80, '-', 'inferred', 'discharge coefficient'),
    'cyl_heat_eff':  (0.75, '-', 'inferred', 'fraction of inflow enthalpy kept (wall heat loss)'),
    'm_piston_rod':  (0.063, 'kg', 'inferred', 'piston plus piston rod'),
    'rod_spring':    (20.0, 'N', 'inferred', 'piston rod return spring'),
    # ---- carrier group, buffer, spring
    'm_carrier':     (0.300, 'kg', 'inferred', 'carrier with cam pin, firing pin and retaining pin (AR-pattern scale)'),
    'm_bolt':        (0.048, 'kg', 'inferred', 'bolt head with extractor and ejector'),
    'm_buffer':      (0.150, 'kg', 'inferred', 'HK buffer with tungsten granules (weight not in the manual)'),
    'm_spring_eff':  (0.020, 'kg', 'inferred', 'one third of the buffer spring'),
    'spring_preload': (30.0, 'N', 'inferred', 'buffer spring force in battery'),
    'spring_rate':   (330.0, 'N/m', 'inferred', 'buffer spring rate'),
    'stroke_contact': (0.094, 'm', 'inferred', 'carrier travel at which the buffer meets the tube end (AR pattern, about 3.75 in total)'),
    'buffer_k':      (1.5e6, 'N/m', 'inferred', 'buffer bumper stiffness'),
    'buffer_restitution': (0.25, '-', 'inferred', 'low because the tungsten granules deaden the rebound (manual p. 5 names them)'),
    'battery_k':     (1.0e7, 'N/m', 'inferred', 'carrier to barrel extension contact stiffness (overdamped, zeta 2: no bolt bounce)'),
    'rail_friction': (5.0, 'N', 'inferred', 'sliding friction of carrier, buffer and hammer drag'),
    'cam_dwell':     (0.0030, 'm', 'inferred', 'carrier free travel before the cam track starts turning the bolt'),
    'cam_len':       (0.0075, 'm', 'inferred', 'carrier travel over which the bolt turns'),
    'bolt_angle':    (22.5, 'deg', 'published', 'AR-pattern bolt rotation between locked and unlocked'),
    'lug_r':         (0.0080, 'm', 'inferred', 'mean radius of the locking lug faces'),
    'lug_mu':        (0.15, '-', 'inferred', 'steel on steel, lubricated'),
    'case_head_area': (7.2e-5, 'm^2', 'inferred', '9.6 mm case head: bolt thrust per unit chamber pressure'),
    'case_wall_area': (1.1e-3, 'm^2', 'inferred', 'case body wall bearing on the chamber'),
    'case_mu':       (0.20, '-', 'inferred', 'brass on steel during primary extraction'),
    'cock_x':        (0.032, 'm', 'inferred', 'carrier travel by which the hammer is fully cocked'),
    'bolt_face_z':   (-0.014, 'm', 'model', 'front of bolt_head in hk416.glb'),
    'case_len':      (0.0447, 'm', 'published', '5.56x45 case length 44.70 mm'),
    'case_r':        (0.0045, 'm', 'published', 'case body radius (9.6 mm head, 9.0 mm body)'),
    'port_front_z':  (-0.021, 'm', 'model', 'front edge of the ejection port in build.py'),
    'feed_pick_bolt_x': (0.065, 'm', 'inferred', 'bolt travel at which the bolt face meets the top round on the return'),
    'feed_free_x':   (0.045, 'm', 'inferred', 'carrier travel at which the round is clear of the feed lips'),
    'feed_friction': (15.0, 'N', 'inferred', 'drag of stripping the round from the lips'),
    'sear_trip_x':   (0.0015, 'm', 'inferred', 'carrier travel at which the auto sear is tripped on closing'),
    'hold_open_x':   (0.082, 'm', 'inferred', 'carrier travel at which the bolt catch holds the bolt after the last round'),
    # ---- ejection
    'ejector_energy': (0.049, 'J', 'inferred', 'ejector spring: 22 N compressed to 13 N over 2.8 mm'),
    'ejector_eff':   (0.80, '-', 'inferred', ''),
    'case_cm':       (0.0175, 'm', 'inferred', 'centre of mass from the case head'),
    'eject_release_deg': (35.0, 'deg', 'inferred', 'case rotation about the extractor claw at release'),
    'eject_elev_deg': (12.0, 'deg', 'inferred', 'upward tilt of the ejection plane'),
    'deflector_deg': (40.0, 'deg', 'inferred', 'deflector face normal, from straight out (-X) towards the muzzle (+Z)'),
    'deflector_e':   (0.50, '-', 'inferred', 'restitution of brass on the deflector'),
    'deflector_spin': (0.60, '-', 'inferred', 'spin kept after the deflector'),
    'brass_cd_area': (0.9 * 3.4e-4, 'm^2', 'inferred', 'drag coefficient times mean projected area of a tumbling case'),
    'eject_height':  (1.40, 'm', 'inferred', 'ejection port above the ground for a standing shooter (trajectory samples only)'),
    # ---- gun
    'm_gun':         (3.49, 'kg', 'manual', 'complete gun 7.7 lb (p. 7)'),
    'm_magazine':    (0.25 + 30 * 12.3e-3, 'kg', 'inferred', 'HK steel 30-round magazine (about 250 g) with 30 rounds'),
}
SURFACES = {   # inferred
    'concrete': dict(restitution=0.45, friction=0.35, spin_keep=0.5, roll=0.30),
    'dirt':     dict(restitution=0.12, friction=0.70, spin_keep=0.2, roll=0.60),
}
# Shooter models: all inferred, order of magnitude from published mass-spring-damper shoulder models.
STANCES = {
    'ads': dict(note='shouldered, aimed. Pitch pivot is the buttpad centre; bore axis 41 mm above it (model).',
                m_arm=2.0, k_s=30e3, c_s=400.0, m_t=25.0, k_t=6e3, c_t=700.0,
                h=0.041, I=1.10, K=250.0, zeta=0.50, e_yaw=0.012, K_yaw=250.0, pivot=[0.0, -0.041, -0.396]),
    'hip': dict(note='unshouldered, held by both hands. Pitch pivot is the firing hand (socket_hand_right).',
                m_arm=2.5, k_s=8e3, c_s=220.0, m_t=25.0, k_t=6e3, c_t=700.0,
                h=0.085, I=0.53, K=90.0, zeta=0.40, e_yaw=0.020, K_yaw=90.0, pivot=[0.0, -0.107, -0.178]),
}
P = {k: v[0] for k, v in PARAMS.items()}


def setp(key, value):
    P[key] = value
    PARAMS[key] = (value,) + PARAMS[key][1:]


def glb_nodes():
    """World translations of the sockets and parts we reference, read from hk416.glb."""
    with open(os.path.join(MODEL, 'hk416.glb'), 'rb') as f:
        f.read(12); n, _ = struct.unpack('<I4s', f.read(8)); g = json.loads(f.read(n))
    par = {}
    for i, nd in enumerate(g['nodes']):
        for c in nd.get('children', []): par[c] = i
    out = {}
    for i, nd in enumerate(g['nodes']):
        t = np.zeros(3); j = i
        while j is not None:
            t += np.array(g['nodes'][j].get('translation', [0, 0, 0])); j = par.get(j)
        out[nd.get('name', '')] = [round(float(v), 5) for v in t]
    return out


# ============================================================================ internal ballistics
def ib_solve(B, th, dt=5e-7, t_blow=9e-3):
    """Lumped (Resal energy balance, Nobel-Abel gas, Lagrange gradient) interior ballistics, then isentropic
    choked blowdown of the bore. Returns tables on a 1 us grid, t = 0 at charge ignition."""
    mb, mc, A, V0 = P['m_bullet'], P['m_charge'], P['bore_area'], P['chamber_vol']
    F, g, b, rho, n, chi = P['force_const'], P['gamma'], P['covolume'], P['rho_prop'], P['burn_exp'], P['loss_factor']
    R = F / P['flame_temp']
    L = P['barrel_len'] - P['bullet_base0']; xp = L - P['port_to_muzzle']
    l0 = V0 / A; Vi = V0 - mc / rho
    kb = 1 + mc / (3 * mb); kbr = (1 + mc / (2 * mb)) / kb

    def state(Z, x, v, W):
        psi = min(1.0, (1 + th) * Z - th * Z * Z)
        Vf = V0 + A * x - mc * (1 - psi) / rho - b * mc * psi
        Pm = (F * mc * psi + P['p_ign'] * Vi - (g - 1) * (1 + chi) * (0.5 * (mb + mc / 3) * v * v + W)) / Vf
        return psi, Vf, Pm

    def deriv(y):
        Z, x, v, W = y
        psi, Vf, Pm = state(Z, x, v, W)
        Pb = Pm / kb
        pres = P['p_friction'] + P['p_engrave'] * math.exp(-x / P['engrave_len'])
        a = A * (Pb - pres) / mb if (v > 0 or Pb > P['p_shot_start']) else 0.0
        dZ = B * (max(Pm, 0.0) / 1e8) ** n if Z < 1 else 0.0
        return (dZ, v, a, A * pres * v), a

    y = [0.0, 0.0, 0.0, 0.0]; t = 0.0
    T, PBR, PPORT, TG, FG, X, V, PM = [], [], [], [], [], [], [], []
    t_port = None
    while y[1] < L:
        d1, a = deriv(y)
        psi, Vf, Pm = state(*y)
        T.append(t); PM.append(Pm); PBR.append(Pm * kbr); X.append(y[1]); V.append(y[2])
        TG.append(Pm * Vf / (mc * max(psi, 1e-3) * R))
        FG.append((mb + mc / 2) * a)
        if y[1] >= xp:
            if t_port is None: t_port = t
            Pb = Pm / kb; sb = l0 + y[1]; sp = l0 + xp
            PPORT.append(Pm * kbr - (Pm * kbr - Pb) * (sp / sb) ** 2)
        else:
            PPORT.append(PATM)
        y2 = [y[i] + 0.5 * dt * d1[i] for i in range(4)]; d2, _ = deriv(y2)
        y3 = [y[i] + 0.5 * dt * d2[i] for i in range(4)]; d3, _ = deriv(y3)
        y4 = [y[i] + dt * d3[i] for i in range(4)]; d4, _ = deriv(y4)
        y = [y[i] + dt / 6 * (d1[i] + 2 * d2[i] + 2 * d3[i] + d4[i]) for i in range(4)]
        t += dt
        if t > 5e-3: raise RuntimeError('bullet did not exit')
    t_exit = t; v_exit = y[2]
    psi, Vf, Pm = state(*y)
    # blowdown of the bore volume through the muzzle
    m = mc; Vres = V0 + A * L; Tg = Pm * (Vres - b * m) / (m * R); Pr = Pm
    ratio = PPORT[-1] / Pm
    crit = (2 / (g + 1)) ** (g / (g - 1))
    cf = (g + 1) * crit
    kflow = math.sqrt(g) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
    while t < t_exit + t_blow:
        T.append(t); PM.append(Pr); PBR.append(Pr); PPORT.append(max(PATM, Pr * ratio)); TG.append(Tg)
        X.append(L + v_exit * (t - t_exit)); V.append(v_exit)
        FG.append(cf * max(Pr - PATM, 0.0) * A)
        if Pr > 1.05 * PATM:
            pr = max(PATM / Pr, crit)
            md = A * Pr * math.sqrt(2 * g / ((g - 1) * R * Tg) * (pr ** (2 / g) - pr ** ((g + 1) / g))) if pr > crit else A * Pr * kflow / math.sqrt(R * Tg)
            dm = min(md * dt, 0.5 * m)
            Tg *= (1 - dm / m) ** (g - 1); m -= dm
            Pr = m * R * Tg / (Vres - b * m)
        t += dt
    step = int(round(1e-6 / dt))
    tab = {k: np.array(v[::step]) for k, v in dict(t=T, pm=PM, pbr=PBR, pport=PPORT, tg=TG, fg=FG, x=X, v=V).items()}
    ie = int(round(t_exit * 1e6)); raw_blow = float(np.sum(tab['fg'][ie:]) * 1e-6); inbore = float(np.sum(tab['fg'][:ie]) * 1e-6)
    scale = P['blowdown_scale']
    if scale is None:                                             # calibrate: bullet + gas momentum = m_b v + m_c * convention
        scale = (mb * v_exit + mc * P['gas_velocity_conv'] - inbore) / raw_blow if raw_blow > 0 else 1.0
    tab['fg'][ie:] *= scale * (1 - P['brake_beta'])
    i_pk = int(np.argmax(tab['pbr']))
    info = dict(t_exit=t_exit, v_exit=v_exit, t_port=t_port, p_max=float(tab['pbr'][i_pk]), t_pmax=float(tab['t'][i_pk]),
                p_port_at_passage=float(PPORT[int(round(t_port / dt)) + 1]), p_exit_mean=float(Pm), p_exit_base=float(Pm / kb),
                burnout_frac=float(psi), R=R, cf=cf, travel=L, port_travel=xp,
                impulse_bullet=mb * v_exit, impulse_total=float(np.sum(tab['fg']) * 1e-6))
    info['blowdown_scale'] = scale; info['impulse_raw'] = inbore + raw_blow; info['gas_eff_velocity_raw'] = (inbore + raw_blow - mb * v_exit) / mc
    info['impulse_gas'] = info['impulse_total'] - info['impulse_bullet']
    info['gas_eff_velocity'] = info['impulse_gas'] / mc
    return tab, info


def ib_calibrate():
    def res(q):
        try:
            _, i = ib_solve(abs(q[0]) * 1e3, q[1], t_blow=0.0)
        except RuntimeError:
            return [1.0, 1.0]
        return [i['p_max'] / P['p_max_target'] - 1, i['v_exit'] / P['v_muzzle_target'] - 1]
    s = root(res, [0.6, -0.3], method='hybr', options=dict(xtol=1e-6))
    if not s.success or max(abs(v) for v in s.fun) > 1e-3: raise RuntimeError('ballistics calibration failed: %s' % s.message)
    setp('burn_coeff', abs(s.x[0]) * 1e3); setp('form_theta', float(s.x[1]))
    tab, info = ib_solve(P['burn_coeff'], P['form_theta'])
    setp('blowdown_scale', info['blowdown_scale'])
    return tab, info


# ============================================================================ firing train
def firing_train(dt=1e-6):
    """Sear release -> hammer fall -> firing pin -> primer indent. Returns 1 us tables of hammer angle (deg from the
    sear, positive towards the pin) and firing pin travel (m forward from its rearmost position)."""
    I, r, mp = P['hammer_inertia'], P['hammer_strike_r'], P['fp_mass']
    tc, tf, fall, eff = P['hammer_torque_cocked'], P['hammer_torque_fired'], math.radians(P['hammer_fall']), P['hammer_eff']
    tau = lambda ph: eff * (tc - (tc - tf) * ph / fall)
    ph = w = 0.0; t = 0.0; H = []; S = []
    while ph < fall:
        H.append(ph); S.append(0.0)
        w += tau(ph) / I * dt; ph += w * dt; t += dt
    ev = dict(hammer_strike=t, hammer_omega=w, hammer_energy=0.5 * I * w * w)
    Ic = I + mp * r * r; w *= I / Ic                      # hammer face stays on the pin after the blow
    s = 0.0; v = w * r; fl = P['fp_float']; dmax = P['fp_protrusion']; done = False
    ev['pin_velocity'] = v
    while t < ev['hammer_strike'] + 1.5e-3:
        H.append(fall + s / r); S.append(s)
        if not done:
            d = s - fl
            if d >= 0 and 'primer_contact' not in ev: ev['primer_contact'] = t
            if d >= P['primer_fire_indent'] and 'primer_fire' not in ev: ev['primer_fire'] = t
            f = tau(fall) / r - ((P['primer_f0'] + P['primer_k'] * d) if d >= 0 else 0.0)
            v += f / (Ic / (r * r)) * dt; s += v * dt
            if s - fl >= dmax: s = fl + dmax; done = True
            if v <= 0: done = True
            if done: ev['indent_done'] = t; ev['indent'] = s - fl
        t += dt
    if 'primer_fire' not in ev: raise RuntimeError('light strike: the primer does not fire with these parameters')
    ev['ignition'] = ev['primer_fire'] + P['primer_delay']
    ev['hammer_rest_deg'] = math.degrees(H[-1]); ev['pin_rest'] = S[-1]
    return np.degrees(np.array(H)), np.array(S), ev


# ============================================================================ coupled action + recoil
def smooth(u):
    u = 0.0 if u < 0 else (1.0 if u > 1 else u)
    return u * u * (3 - 2 * u)


def dsmooth(u):
    return 6 * u * (1 - u) if 0 < u < 1 else 0.0


def bolt_deg(x):
    return P['bolt_angle'] * smooth((x - P['cam_dwell']) / P['cam_len'])


def run(IB, FT, stance, n_shots=1, t_end=0.2, rec_dt=5e-5, stop_after_shots=False, over=None):
    """One coupled run: gas cylinder, carrier group, gun translation against the shooter, pitch and yaw.
    stance: 'ads', 'hip' or None (free recoil, gun floating). Returns recorded arrays and event lists."""
    q = dict(P); q.update(over or {})
    tab, info = IB; Hd, Sp, fev = FT
    g = q['gamma']; R = info['R']; cv = R / (g - 1); cp = g * cv
    crit = (2 / (g + 1)) ** (g / (g - 1))
    Ao = math.pi / 4 * q['port_d'] ** 2; Ap = math.pi / 4 * q['piston_d'] ** 2; Cd = q['orifice_cd']
    fg, pport, tg, pbr = tab['fg'], tab['pport'], tab['tg'], tab['pbr']; ntab = len(fg)
    S = STANCES.get(stance)
    M_all = q['m_gun'] + q['m_magazine'] + (S['m_arm'] if S else 0.0)
    x_d, x_u = q['cam_dwell'], q['cam_dwell'] + q['cam_len']
    x_ej = q['case_len'] + q['bolt_face_z'] - q['port_front_z'] + x_u       # case mouth clears the port's front edge
    x_pick = q['feed_pick_bolt_x'] + x_u
    kb, kc = q['buffer_k'], q['battery_k']
    e = q['buffer_restitution']; zb = -math.log(e) / math.sqrt(math.pi ** 2 + math.log(e) ** 2)
    m_cg = q['m_carrier'] + q['m_buffer'] + q['m_spring_eff']
    cb = 2 * zb * math.sqrt(kb * (m_cg + q['m_bolt'])); cc = 4 * math.sqrt(kc * m_cg)        # battery contact overdamped (zeta 2): the granule buffer kills bolt bounce
    tc_, tf_, fall = q['hammer_torque_cocked'], q['hammer_torque_fired'], math.radians(q['hammer_fall'])
    oc = q['hammer_overcock']; h_rest = fev['hammer_rest_deg']; t_ign_rel = fev['ignition']

    def flow(Pu, Tu, Pd, A):
        if Pu <= Pd: return 0.0
        pr = Pd / Pu
        if pr < crit: pr = crit
        return Cd * A * Pu * math.sqrt(2 * g / ((g - 1) * R * Tu) * (pr ** (2 / g) - pr ** ((g + 1) / g)))

    # state
    m = m_cg + q['m_piston_rod']                          # moving group: the rod pushes the carrier on the first 16 mm
    x = -q['spring_preload'] / kc; v = 0.0
    attached = True; xp = 0.0; first = True; bolt_with = False; cocked = False; have_case = True; round_on = False
    mc_ = PATM * q['cyl_vol0'] / (R * 300.0); Tc = 300.0; Pc = PATM
    zg = vg = zt = vt = 0.0; pit = pitv = yaw = yawv = 0.0
    if S:
        Cp = 2 * S['zeta'] * math.sqrt(S['K'] * S['I']); Cy = 2 * S['zeta'] * math.sqrt(S['K_yaw'] * S['I'])
    rel = [0.0]; ign = [t_ign_rel]; shot = 0; pending = True
    events = [[('sear_release', 0.0)]]; ev = events[0]
    for k in ('hammer_strike', 'primer_contact', 'primer_fire', 'ignition'): ev.append((k, fev[k]))
    for k, tk in (('peak_pressure', info['t_pmax']), ('bullet_passes_port', info['t_port']), ('bullet_exit', info['t_exit'])): ev.append((k, t_ign_rel + tk))
    flags = set(); v_eject = []; x_max = [0.0]; v_peak = [0.0]
    rec = {k: [] for k in ('t', 'x', 'v', 'bolt', 'hammer', 'pin', 'pc', 'zg', 'zt', 'pitch', 'yaw', 'fsh', 'frecv', 'vg')}
    J = 0.0; t = 0.0; next_rec = 0.0; settled_t = None
    while t < t_end:
        ti = t - ign[-1]
        fast = (-1e-4 < ti < 6e-3) or (v < 0 and x < 6e-4 and x > -1e-4 and abs(v) > 1e-3) or (x > q['stroke_contact'] - 3e-4)
        moving = fast or abs(v) > 1e-4 or x > 1e-4 or ti < 0
        dt = 2e-6 if fast else (2e-5 if moving else 5e-5)
        # ---- bore forcing from the current shot
        if 0 <= ti and ti * 1e6 < ntab - 1:
            j = int(ti * 1e6); Fb = fg[j]; Pp = pport[j]; Tp = tg[j]; Pb = pbr[j]
        else:
            Fb = 0.0; Pp = PATM; Tp = 300.0; Pb = PATM
        # ---- gas cylinder
        Vc = q['cyl_vol0'] + Ap * xp
        if Pp >= Pc:
            mdi = flow(Pp, Tp, Pc, Ao); hin = q['cyl_heat_eff'] * cp * Tp * mdi
        else:
            mdi = -flow(Pc, Tc, Pp, Ao); hin = cp * Tc * mdi
        mdo = flow(Pc, Tc, PATM, q['vent_area'] if xp >= q['vent_open_x'] else q['leak_area'])
        vxp = v if attached else 0.0
        U = mc_ * cv * Tc + dt * (hin - cp * Tc * mdo - Pc * Ap * vxp)
        mc_ = max(mc_ + dt * (mdi - mdo), 1e-9); Tc = max(U / (mc_ * cv), 250.0); Pc = mc_ * R * Tc / Vc
        if not attached and xp > 0 and Pc < 3e5: xp = 0.0          # rod spring has returned the piston
        # ---- forces on the moving group, positive rearward
        F = -(q['spring_preload'] + q['spring_rate'] * x) - q['rail_friction'] * math.tanh(v / 0.02)
        if attached: F += (Pc - PATM) * Ap - q['rod_spring']
        if x_d < x < x_u:                                          # lug friction through the cam, while pressure remains
            F -= math.copysign(1, v) * q['lug_mu'] * max(Pb - PATM, 0.0) * q['case_head_area'] * q['lug_r'] \
                 * math.radians(q['bolt_angle']) * dsmooth((x - x_d) / q['cam_len']) / q['cam_len']
        if first and v > 0:
            if x_u < x < x_u + 1e-3: F -= q['case_mu'] * max(Pb - PATM, 0.0) * q['case_wall_area']
            if 0 < x < q['cock_x'] and not cocked:                 # cocking the hammer
                u = x / q['cock_x']; ph = math.radians(h_rest - (h_rest + oc) * smooth(u))
                F -= (tc_ - (tc_ - tf_) * ph / fall) * math.radians(h_rest + oc) * dsmooth(u) / q['cock_x']
        if round_on and v < 0 and x > q['feed_free_x']: F += q['feed_friction']
        if x > q['stroke_contact']: F -= max(kb * (x - q['stroke_contact']) + cb * v, 0.0)
        if x < 0: F += max(-kc * x - cc * v, 0.0)
        # ---- gun and shooter (z positive towards the muzzle)
        Mr = M_all - m
        Fsh = (S['k_s'] * (zt - zg) + S['c_s'] * (vt - vg)) if S else 0.0
        ag = (-Fb + Fsh + F) / Mr
        a = F / m + ag
        Jg = 0.0                                                   # impulsive rearward kicks on the receiver this step
        v += a * dt; xo = x; x += v * dt
        vg += ag * dt; zg += vg * dt
        if S:
            at = (-Fsh - S['k_t'] * zt - S['c_t'] * vt) / S['m_t']; vt += at * dt; zt += vt * dt
        # ---- events (crossings)
        if first:
            if xo < 1e-3 <= x and 'cs' not in flags: flags.add('cs'); ev.append(('carrier_moves', t))
            if xo < x_d <= x and 'us' not in flags: flags.add('us'); ev.append(('unlock_start', t))
            if xo < x_u <= x and not bolt_with:
                bolt_with = True; mn = m + q['m_bolt'] + q['m_case']; v *= m / mn; m = mn
                ev.append(('unlock', t)); ev.append(('extract', t))
            if attached and x >= q['rod_stop_x']:
                attached = False; xp = q['rod_stop_x']; m -= q['m_piston_rod']; Jg += q['m_piston_rod'] * v
                ev.append(('piston_rod_stop', t)); v_peak[-1] = max(v_peak[-1], v)
            if not cocked and x >= q['cock_x']: cocked = True; ev.append(('hammer_cocked', t))
            if have_case and x >= x_ej:
                have_case = False; m -= q['m_case']; v_eject.append(v); ev.append(('eject', t))
            if xo <= q['stroke_contact'] < x: ev.append(('buffer_impact', t))
            if v < 0 and x > q['stroke_contact'] - 0.02:
                first = False; ev.append(('max_travel', t)); x_max[-1] = x
            if v > v_peak[-1]: v_peak[-1] = v
        else:
            if xo > x_pick >= x and not round_on and 'fp' not in flags:
                flags.add('fp'); round_on = True; mn = m + q['m_round']; v *= m / mn; m = mn; ev.append(('feed', t))
            if xo > x_u >= x and bolt_with:
                bolt_with = False; dm = q['m_bolt'] + (q['m_round'] if round_on else 0.0); m -= dm; Jg += dm * v   # v < 0: forward kick
                round_on = False; ev.append(('chambered', t))
            if xo > x_d >= x and 'lk' not in flags: flags.add('lk'); ev.append(('lock', t))
            if xo > q['sear_trip_x'] >= x and 'st' not in flags:
                flags.add('st'); ev.append(('auto_sear_trip', t))
                if shot + 1 < n_shots:
                    rel.append(t); ign.append(t + t_ign_rel)
            if x <= 5e-5 and 'ib' not in flags:
                flags.add('ib'); ev.append(('in_battery', t)); settled_t = t
                if len(rel) > shot + 1:                           # arm the next shot
                    shot += 1; ev = [('sear_release', rel[shot])]; events.append(ev)
                    for k in ('hammer_strike', 'primer_contact', 'primer_fire', 'ignition'): ev.append((k, rel[shot] + fev[k]))
                    for k, tk in (('peak_pressure', info['t_pmax']), ('bullet_passes_port', info['t_port']), ('bullet_exit', info['t_exit'])): ev.append((k, ign[shot] + tk))
                    first = True; cocked = False; have_case = True; flags = set(); attached = True; xp = 0.0
                    m = m_cg + q['m_piston_rod']; x_max.append(0.0); v_peak.append(0.0)
                elif stop_after_shots:
                    break
        if attached: xp = max(x, 0.0)
        if Jg:
            vg -= Jg / Mr
        # ---- pitch and yaw about the support
        Frear = Fb - F                                             # rearward axial force on the receiver
        J += Frear * dt + Jg
        if S:
            pitv += ((S['h'] * Frear - S['K'] * pit - Cp * pitv) * dt + S['h'] * Jg) / S['I']; pit += pitv * dt
            yawv += ((S['e_yaw'] * Frear - S['K_yaw'] * yaw - Cy * yawv) * dt + S['e_yaw'] * Jg) / S['I']; yaw += yawv * dt
        t += dt
        if t >= next_rec:
            tr = t - rel[shot] if t >= rel[shot] else -1.0        # time since this shot's sear release
            tr_new = t - rel[-1]
            if len(rel) > shot + 1 and tr_new >= 0:               # next hammer already falling (auto)
                k = int(tr_new * 1e6); hd = Hd[min(k, len(Hd) - 1)]; pn = Sp[min(k, len(Sp) - 1)]
            elif first and not cocked:
                k = int(tr * 1e6); hd = Hd[min(k, len(Hd) - 1)]; pn = Sp[min(k, len(Sp) - 1)]
                if x > 0:
                    hd = min(hd, h_rest - (h_rest + oc) * smooth(x / q['cock_x'])); pn *= max(0.0, 1 - x / 2e-3)
            else:
                hd = -oc * smooth(x / q['cock_x']) if x > 0 else 0.0; pn = 0.0
            rec['t'].append(t); rec['x'].append(x); rec['v'].append(v); rec['bolt'].append(bolt_deg(x)); rec['hammer'].append(hd)
            rec['pin'].append(pn); rec['pc'].append(Pc); rec['zg'].append(zg); rec['zt'].append(zt); rec['pitch'].append(pit)
            rec['yaw'].append(yaw); rec['fsh'].append(Fsh); rec['frecv'].append(J / rec_dt); rec['vg'].append(vg); J = 0.0
            next_rec += rec_dt
    out = {k: np.array(v) for k, v in rec.items()}
    out.update(events=events, rel=rel, ign=ign, v_eject=v_eject, x_max=x_max, v_peak=v_peak, x_eject=x_ej, x_pick=x_pick, M_all=M_all)
    return out


def cyclic_rate(IB, FT, stance='ads', over=None, shots=3):
    r = run(IB, FT, stance, n_shots=shots, t_end=0.2 * shots, stop_after_shots=True, over=over)
    if len(r['rel']) < shots: return 0.0, r
    return 60.0 / (r['rel'][-1] - r['rel'][-2]), r


# ============================================================================ brass
def mulberry32(seed):
    s = [seed & 0xFFFFFFFF]
    def rnd():
        s[0] = (s[0] + 0x6D2B79F5) & 0xFFFFFFFF
        z = s[0]
        z = ((z ^ (z >> 15)) * (z | 1)) & 0xFFFFFFFF
        z ^= (z + (((z ^ (z >> 7)) * (z | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd


def gauss(rng):
    return math.sqrt(-2 * math.log(max(rng(), 1e-12))) * math.cos(2 * math.pi * rng())


def eject_nominal(v_carrier):
    """Case state after the deflector, gun frame. See README: ejector spring energy -> rotation about the extractor
    claw -> release -> one impulsive bounce off the brass deflector."""
    m, L, d0 = P['m_case'], P['case_len'], P['case_cm']
    d = math.hypot(d0, P['case_r'] + 0.0003)
    Icm = 1.1 * m * L * L / 12; Ip = Icm + m * d * d
    w = math.sqrt(2 * P['ejector_energy'] * P['ejector_eff'] / Ip)
    ph = math.radians(P['eject_release_deg']); el = math.radians(P['eject_elev_deg'])
    lat = w * d * math.cos(ph)                                   # outwards, in the tilted ejection plane
    vel = np.array([-lat * math.cos(el), lat * math.sin(el), -v_carrier - w * d * math.sin(ph)])
    a = math.radians(P['deflector_deg']); n = np.array([-math.cos(a), 0.0, math.sin(a)])
    vn = float(vel @ n); hit = vn < 0
    pre = vel.copy()
    if hit: vel = vel - (1 + P['deflector_e']) * vn * n
    spin = -w * (P['deflector_spin'] if hit else 1.0)             # about +Y: the case mouth swings towards -X
    return dict(vel=vel, pre_deflector=pre, omega_bolt=w, spin_y=spin, hits_deflector=bool(hit), I_cm=Icm)


SCATTER = dict(speed_sigma=0.12, azimuth_sigma_deg=9.0, elevation_sigma_deg=6.0, spin_sigma=0.25, spin_tilt_sigma_deg=20.0,
               pos_sigma=0.002)   # inferred shot-to-shot spread


def eject_case(rng, nom, pos0):
    v = nom['vel']; sp = float(np.linalg.norm(v)); az = math.atan2(v[2], -v[0]); el = math.asin(v[1] / sp)
    sp *= max(0.3, 1 + SCATTER['speed_sigma'] * gauss(rng))
    az += math.radians(SCATTER['azimuth_sigma_deg']) * gauss(rng)
    el += math.radians(SCATTER['elevation_sigma_deg']) * gauss(rng)
    w = nom['spin_y'] * max(0.2, 1 + SCATTER['spin_sigma'] * gauss(rng))
    tx = math.radians(SCATTER['spin_tilt_sigma_deg']) * gauss(rng); tz = math.radians(SCATTER['spin_tilt_sigma_deg']) * gauss(rng)
    return dict(pos=[pos0[0], pos0[1] + SCATTER['pos_sigma'] * gauss(rng), pos0[2] + SCATTER['pos_sigma'] * gauss(rng)],
                vel=[-sp * math.cos(el) * math.cos(az), sp * math.sin(el), sp * math.cos(el) * math.sin(az)],
                angVel=[w * math.sin(tx), w * math.cos(tx) * math.cos(tz), w * math.sin(tz)], resting=False)


def step_case(s, dt, ground_y, surf, rng):
    """One step of flight (gravity, quadratic drag) with a randomised cylinder bounce. Mirrors hk416-action.js."""
    if s['resting'] == 2: return s
    p, v, w = s['pos'], s['vel'], s['angVel']; r = P['case_r']
    if s['resting'] == 1:                                         # sliding / rolling to a stop
        sp = math.hypot(v[0], v[2]); dec = surf['roll'] * 9.81 * dt
        if sp <= dec:
            v[0] = v[2] = 0.0; w[0] = w[1] = w[2] = 0.0; s['resting'] = 2
        else:
            k = (sp - dec) / sp; v[0] *= k; v[2] *= k; p[0] += v[0] * dt; p[2] += v[2] * dt
            for i in range(3): w[i] *= k
        return s
    sp = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    kd = 0.5 * 1.2 * P['brass_cd_area'] * sp / P['m_case']
    v[0] -= kd * v[0] * dt; v[1] -= (9.81 + kd * v[1]) * dt; v[2] -= kd * v[2] * dt
    for i in range(3): p[i] += v[i] * dt
    if p[1] - r < ground_y and v[1] < 0:
        p[1] = ground_y + r
        u1, u2, u3 = rng(), rng(), rng()
        e = surf['restitution'] * (0.55 + 0.45 * u1); vin = -v[1]; vn = vin * e
        st = math.hypot(v[0], v[2]); loss = surf['friction'] * (1 + e) * vin
        k = max(0.0, st - loss) / st if st > 1e-9 else 0.0
        wm = math.sqrt(w[0] ** 2 + w[1] ** 2 + w[2] ** 2)
        kick = 0.25 * wm * P['case_len'] * 0.5 * (2 * u2 - 1) * surf['spin_keep']; ang = 2 * math.pi * u3
        v[0] = v[0] * k + kick * math.cos(ang); v[2] = v[2] * k + kick * math.sin(ang)
        for i in range(3): w[i] *= surf['spin_keep']
        if vn < 0.25: v[1] = 0.0; s['resting'] = 1
        else: v[1] = vn
        s['bounces'] = s.get('bounces', 0) + 1
    return s


def brass_trajectory(seed, surface, nom, pos0, t_max=3.0, dt=1 / 240, every=4):
    rng = mulberry32(seed); s = eject_case(rng, nom, pos0); init = json.loads(json.dumps(s))
    gy = pos0[1] - P['eject_height']; pts = []; n = int(t_max / dt)
    for i in range(n + 1):
        if i % every == 0: pts.append([round(c, 4) for c in s['pos']])
        if s['resting'] == 2: break
        step_case(s, dt, gy, SURFACES[surface], rng)
    return dict(seed=seed, surface=surface, dt=dt * every, ground_y=round(gy, 4), init=init, pos=pts, rest=[round(c, 4) for c in s['pos']],
                bounces=s.get('bounces', 0))


# ============================================================================ build
def resample(t, y, dt, t_end, mean=False):
    n = int(round(t_end / dt)) + 1; tt = np.arange(n) * dt
    if not mean: return np.interp(tt, t, y)
    out = np.zeros(n); edges = np.concatenate([[-1e-9], tt + dt / 2]); idx = np.searchsorted(t, edges)
    for i in range(n):
        seg = y[idx[i]:idx[i + 1]]; out[i] = seg.mean() if len(seg) else 0.0
    return out


def evs_t(r, name, shot=0):
    return dict(r['events'][shot])[name]


def rl(a, nd=3):
    return [round(float(v), nd) for v in a]


def main():
    t0 = time.time(); plots = '--no-plots' not in sys.argv
    nodes = glb_nodes()
    print('calibrating internal ballistics ...')
    IB = ib_calibrate(); tab, info = IB
    setp('muzzle_cf', info['cf'])
    FT = firing_train(); Hd, Sp, fev = FT
    print('  p_max %.1f MPa, v %.1f m/s, exit %.3f ms, port %.1f MPa at %.3f ms; lock time %.2f ms'
          % (info['p_max'] / 1e6, info['v_exit'], info['t_exit'] * 1e3, info['p_port_at_passage'] / 1e6, info['t_port'] * 1e3, fev['primer_contact'] * 1e3))
    print('calibrating the gas port for %.0f rpm ...' % P['cyclic_target'])
    f = lambda d: cyclic_rate(IB, FT, 'ads', over=dict(port_d=d))[0] - P['cyclic_target']
    lo, hi = 0.9e-3, 2.6e-3
    scan = [(d, f(d) + P['cyclic_target']) for d in np.linspace(lo, hi, 9)]
    for d, rr in scan: print('    port %.2f mm -> %.0f rpm' % (d * 1e3, rr))
    ok = [(d, rr) for d, rr in scan if rr > 0]
    br = None
    for (d1, r1), (d2, r2) in zip(scan, scan[1:]):
        if r1 > 0 and r2 > 0 and (r1 - P['cyclic_target']) * (r2 - P['cyclic_target']) <= 0: br = (d1, d2); break
    if br is None: raise RuntimeError('target cyclic rate not bracketed')
    setp('port_d', float(brentq(f, br[0], br[1], xtol=2e-7)))
    print('  port diameter %.3f mm' % (P['port_d'] * 1e3))

    runs = {}
    for st in ('ads', 'hip'):
        runs['semi_' + st] = run(IB, FT, st, 1, 1.2)
        runs['auto_' + st] = run(IB, FT, st, 10, 2.0)
    runs['free'] = run(IB, FT, None, 1, 0.15)
    runs['free_auto'] = run(IB, FT, None, 4, 0.5, stop_after_shots=True)
    rates = {}
    for k in ('auto_ads', 'auto_hip', 'free_auto'):
        d = np.diff(runs[k]['rel']); rates[k] = dict(period_s=float(d[1:].mean()), rpm=float(60 / d[1:].mean()), first_period_s=float(d[0]),
                                                    rpm_min=float(60 / d.max()), rpm_max=float(60 / d.min()))
    print('  cyclic rate: ' + ', '.join('%s %.0f rpm' % (k, v['rpm']) for k, v in rates.items()))

    # ---- sensitivity of the cyclic rate (what drives it)
    sens = []
    for key, fac in (('port_d', 0.9), ('port_d', 1.1), ('spring_rate', 0.8), ('spring_rate', 1.2), ('spring_preload', 0.8), ('spring_preload', 1.2),
                     ('m_buffer', 0.8), ('m_buffer', 1.2), ('m_carrier', 0.9), ('m_carrier', 1.1), ('buffer_restitution', 0.5), ('buffer_restitution', 1.6),
                     ('stroke_contact', 0.95), ('rail_friction', 2.0), ('feed_friction', 2.0)):
        rr, r_ = cyclic_rate(IB, FT, 'ads', over={key: P[key] * fac})
        sens.append(dict(param=key, factor=fac, rpm=round(rr, 1), v_peak=round(r_['v_peak'][-1], 2), x_max_mm=round(max(r_['x_max']) * 1e3, 1)))
        print('    %-20s x%.2f -> %6.1f rpm' % (key, fac, rr))
    lt = dict(P)
    ft2 = None

    # ---- recoil figures
    semi = runs['semi_ads']; free = runs['free']
    M_gun_mag = P['m_gun'] + P['m_magazine']
    imp = info['impulse_total']
    saami = P['m_bullet'] * info['v_exit'] + P['m_charge'] * 1219.2
    valid = dict(
        muzzle_velocity=dict(sim=info['v_exit'], published=850.0, unit='m/s', source='HK manual p. 7 (calibration target)'),
        chamber_pressure=dict(sim=info['p_max'] / 1e6, published=358.5, unit='MPa', source='HK manual p. 7 (calibration target)'),
        cyclic_rate=dict(sim_ads=rates['auto_ads']['rpm'], sim_hip=rates['auto_hip']['rpm'], sim_free_gun=rates['free_auto']['rpm'],
                         published='700 to 900', unit='rpm', source='HK manual p. 7 (port diameter calibrated to the 800 rpm midpoint for the shouldered gun)'),
        lock_time=dict(sim_to_primer_contact=fev['primer_contact'] * 1e3, sim_to_ignition=fev['ignition'] * 1e3, published='about 10', unit='ms',
                       source='Wikipedia "Lock time": mil-spec AR-15 and HK416 fire control about 10 ms (likely a calculated figure)'),
        hammer_energy=dict(sim=fev['hammer_energy'], published='0.34 all-fire', unit='J', source='No. 41 primer all-fire about 48 in-oz (commonly quoted; inferred relevance)'),
        primer_indent=dict(sim=fev['indent'] * 1e3, published='limit 0.90 to 1.10', unit='mm', source='HK manual p. 17 firing pin protrusion'),
        barrel_time=dict(sim=info['t_exit'] * 1e3, unit='ms', published='about 1 (not pinned to a source)'),
        port_pressure=dict(sim=info['p_port_at_passage'] / 1e6, unit='MPa', published='no HK figure; AR carbine-port figures of 90 to 180 MPa are quoted for a port 45 mm nearer the breech'),
        recoil_impulse=dict(sim=imp, saami_formula=saami, unit='N s', source='SAAMI free-recoil formula with 4,000 ft/s gas velocity'),
        gas_effective_velocity=dict(sim=info['gas_eff_velocity'], published=1219.2, unit='m/s', source='SAAMI convention for high-power rifles'),
        free_recoil=dict(mass_kg=M_gun_mag, velocity=imp / M_gun_mag, energy=0.5 * imp ** 2 / M_gun_mag,
                         velocity_empty_gun=imp / P['m_gun'], energy_empty_gun=0.5 * imp ** 2 / P['m_gun'],
                         receiver_peak_velocity_in_cycle=float(-free['vg'].min()), unit='m/s, J',
                         published='about 4 to 5 J for 5.56 rifles of 3.2 to 3.6 kg (recoil tables, e.g. Chuck Hawks .223: 4.3 J at 3.6 kg)'),
        carrier=dict(peak_velocity=semi['v_peak'][0], velocity_at_eject=semi['v_eject'][0], max_travel_mm=semi['x_max'][0] * 1e3, unit='m/s',
                     published='no HK figure; AR carrier speeds of 4 to 6 m/s are commonly quoted'),
    )

    # superposition check: the 10-round burst rebuilt from shifted copies of the single-shot response
    sup = {}
    for st in ('ads', 'hip'):
        a = runs['auto_' + st]; s1 = runs['semi_' + st]; tt = np.arange(0, 2.0, 1e-3)
        for key, sc in (('zg', 1e3), ('pitch', 180 / math.pi)):
            ref = np.interp(tt, a['t'], a[key]) * sc
            est = sum(np.interp(tt - tr, s1['t'], s1[key], left=0.0, right=0.0) for tr in a['rel']) * sc
            sup['%s_%s' % (st, key)] = dict(max_abs_error=float(np.abs(ref - est).max()), peak=float(np.abs(ref).max()), unit='mm' if key == 'zg' else 'deg')
    valid['burst_superposition'] = sup
    j_un = int((evs_t(semi, 'unlock_start') - semi['ign'][0]) * 1e6); j_ex = int((evs_t(semi, 'unlock') - semi['ign'][0]) * 1e6)
    valid['chamber_pressure_at_unlock'] = dict(at_unlock_start=float(tab['pbr'][j_un] / 1e6), at_unlock_complete=float(tab['pbr'][j_ex] / 1e6), unit='MPa',
                                               note='residual bore pressure while the bolt turns and when extraction starts')
    # ---- brass
    pos0 = nodes['socket_eject']
    nom = eject_nominal(semi['v_eject'][0])
    nom['vel'] = np.round(nom['vel'], 3); nom['spin_y'] = round(nom['spin_y'], 1)      # as stored, so hk416-action.js reproduces the seeds
    trajs = [brass_trajectory(seed, surf, nom, pos0) for surf in ('concrete', 'dirt') for seed in (1, 2, 3, 4)]
    vn = nom['vel']; sp = float(np.linalg.norm(vn))
    clock = (math.degrees(math.atan2(-vn[0], vn[2])) / 30.0) % 12
    brass = dict(
        note='Gun frame. The case is released at socket_eject after it has bounced off the brass deflector; velocity is relative to the gun.',
        socket_eject=pos0, release_time_s=None,
        case=dict(mass_kg=P['m_case'], length_m=P['case_len'], radius_m=P['case_r'], I_transverse_kg_m2=nom['I_cm'], cd_area_m2=P['brass_cd_area']),
        nominal=dict(pos=pos0, vel=rl(vn, 3), angVel=[0.0, round(nom['spin_y'], 1), 0.0], speed=round(sp, 3),
                     clock_direction=round(clock, 2), elevation_deg=round(math.degrees(math.asin(vn[1] / sp)), 1),
                     before_deflector_vel=rl(nom['pre_deflector'], 3), spin_before_deflector=round(-nom['omega_bolt'], 1), hits_deflector=nom['hits_deflector'],
                     carrier_speed_at_eject=round(semi['v_eject'][0], 3)),
        scatter=SCATTER, surfaces=SURFACES, gravity=9.81, air_density=1.2, step_dt=1 / 240, eject_height_m=P['eject_height'], trajectories=trajs)

    # ---- sampled curves
    evs = {k: v for k, v in semi['events'][0]}
    brass['release_time_s'] = round(evs['eject'] + 0.004, 5)
    t_cyc = math.ceil((evs['in_battery'] + 0.01) / 0.005) * 0.005
    DT = 2.5e-4
    cyc = dict(dt=DT, t0=0.0, note='semi, shouldered. carrier_mm rearward travel; bolt_deg 0 locked, 22.5 unlocked; hammer_deg 0 on the sear, positive towards the firing pin, negative overcocked under the carrier; firing_pin_mm forward travel from its rearmost position (primer contact at fp_float); receiver_force_N rearward axial force on the gun body from bore and action, averaged over each sample (a rigid mount would feel this)',
               carrier_mm=rl(np.clip(resample(semi['t'], semi['x'] * 1e3, DT, t_cyc), 0, None), 3), carrier_mps=rl(resample(semi['t'], semi['v'], DT, t_cyc), 3),
               bolt_deg=rl(resample(semi['t'], semi['bolt'], DT, t_cyc), 2), hammer_deg=rl(resample(semi['t'], semi['hammer'], DT, t_cyc), 2),
               firing_pin_mm=rl(resample(semi['t'], semi['pin'] * 1e3, DT, t_cyc), 3),
               cylinder_MPa=rl(resample(semi['t'], semi['pc'] / 1e6, DT, t_cyc), 3),
               receiver_force_N=rl(resample(semi['t'], semi['frecv'], DT, t_cyc, mean=True), 1))
    n_f = int((fev['ignition'] + 1.0e-3) / 2e-5) + 1; ks = (np.arange(n_f) * 20).clip(max=len(Hd) - 1)
    firing = dict(dt=2e-5, t0=0.0, note='fine sampling of the firing train from sear release', hammer_deg=rl(Hd[ks], 2), firing_pin_mm=rl(Sp[ks] * 1e3, 3),
                  primer_indent_mm=rl(np.clip(Sp[ks] - P['fp_float'], 0, None) * 1e3, 3))
    nb = 400; kb_ = np.arange(nb) * 10
    ball = dict(dt=1e-5, t0=round(fev['ignition'], 6), note='t0 is charge ignition, seconds after sear release', chamber_MPa=rl(tab['pbr'][kb_] / 1e6, 2),
                port_MPa=rl(tab['pport'][kb_] / 1e6, 2), bullet_mm=rl(np.minimum(tab['x'][kb_], info['travel']) * 1e3, 2), bullet_mps=rl(tab['v'][kb_], 1),
                bore_force_N=rl(tab['fg'][kb_], 0), gas_temp_K=rl(tab['tg'][kb_], 0))
    RD = 1e-3
    def pose(r, t_end):
        return dict(z_mm=rl(resample(r['t'], r['zg'] * 1e3, RD, t_end), 3), pitch_up_deg=rl(resample(r['t'], np.degrees(r['pitch']), RD, t_end), 4),
                    yaw_right_deg=rl(resample(r['t'], np.degrees(r['yaw']), RD, t_end), 4),
                    support_force_N=rl(resample(r['t'], r['fsh'], RD, t_end, mean=True), 1), shot_times=rl(r['rel'], 5))
    recoil = dict(dt=RD, t0=0.0,
                  note='Gun pose offsets from rest in the gun frame. z_mm is translation along the bore (negative = rearward). pitch_up_deg and yaw_right_deg rotate the gun about `pivot` (muzzle up / muzzle to the shooter\'s right, right-handed shooter). support_force_N is the force the gun puts into the support (shoulder plus arms for ads, hands for hip; positive = pushing the shooter back, negative = the arms pulling the gun back as it rebounds), averaged per sample. Semi curves are the single-shot response; because the shooter model is linear, a burst is the sum of shifted copies.',
                  stances={k: dict(note=v['note'], pivot=v['pivot'], params={kk: vv for kk, vv in v.items() if kk not in ('note', 'pivot')}) for k, v in STANCES.items()},
                  semi={st: pose(runs['semi_' + st], 1.2) for st in ('ads', 'hip')}, auto={st: pose(runs['auto_' + st], 2.0) for st in ('ads', 'hip')})
    order = sorted(evs.items(), key=lambda kv: kv[1])
    data = dict(
        meta=dict(title='HK416 D14.5RS action and recoil simulation', credit='carpetshark', generator='assets/hk416/action/sim.py',
                  model='lumped-parameter; see README.md for the physics, sources and limits',
                  frame='metres, +Z muzzle, +Y up, +X shooter\'s left, origin on the bore axis at the upper receiver front face (as hk416.glb)',
                  time_zero='sear release (trigger break); ignition follows at events.ignition',
                  units='seconds, mm / deg / MPa / N / m/s as each key says',
                  nodes=dict(present={k: nodes[k] for k in ('bolt_carrier', 'bolt_head', 'charging_handle', 'dust_cover', 'trigger', 'socket_eject', 'socket_muzzle', 'socket_hand_right', 'socket_hand_left', 'socket_ads_eye', 'brass_deflector') if k in nodes},
                             absent=['hammer', 'firing_pin'], note='hammer and firing pin are not modelled (only hammer_pin_l/r); their curves are for timing and audio')),
        params={k: dict(value=v[0], unit=v[1], source=v[2], note=v[3]) for k, v in PARAMS.items()},
        validation=valid, sensitivity=sens,
        events=dict(note='seconds after sear release, one semi shot, shouldered', times={k: round(v, 6) for k, v in order}, order=[k for k, _ in order]),
        auto=dict(note='auto fire: the carrier trips the auto sear on closing; period is sear release to sear release',
                  period_s=round(rates['auto_ads']['period_s'], 5), rpm=round(rates['auto_ads']['rpm'], 1),
                  by_stance={k: {kk: round(vv, 5) for kk, vv in v.items()} for k, v in rates.items()}),
        firing=firing, ballistics=ball, cycle=cyc, recoil=recoil, brass=brass,
        mechanics=dict(full_stroke_mm=round(semi['x_max'][0] * 1e3, 2), hold_open_mm=P['hold_open_x'] * 1e3, eject_carrier_mm=round(semi['x_eject'] * 1e3, 2),
                       feed_pick_carrier_mm=round(semi['x_pick'] * 1e3, 2), unlock_carrier_mm=(P['cam_dwell'] + P['cam_len']) * 1e3,
                       charge_clip_travel_mm=75.0,
                       notes=['dust cover: opens on the first carrier movement of a closed-cover gun and stays open (as the charge clip does)',
                              'last round: the follower lifts the bolt catch and the carrier stops at hold_open_mm on its return instead of closing (manual p. 26); play cycle to max travel, then hold at hold_open_mm',
                              'reload from bolt-locked: no charging handle needed; the bolt_catch clip releases the carrier, which runs forward from hold_open_mm (use the cycle curve from where carrier_mm falls through hold_open_mm)',
                              'charge clip pulls the carrier 75 mm; the real stroke is to the buffer stop (about 95 mm) and the bolt face must pass the top round at feed_pick_carrier_mm to strip it']),
    )
    with open(os.path.join(HERE, 'action.json'), 'w') as fh:
        json.dump(data, fh, separators=(',', ':'))
    print('wrote action.json (%.0f kB) in %.0f s' % (os.path.getsize(os.path.join(HERE, 'action.json')) / 1e3, time.time() - t0))
    print('events (ms):'); [print('  %-20s %8.3f' % (k, v * 1e3)) for k, v in order]
    print(json.dumps(valid, indent=1, default=float))
    print('brass nominal', brass['nominal'])
    if plots:
        import plots as _pl
        _pl.make(data, runs, tab, info, FT, os.path.join(HERE, 'plots'))
    return data


if __name__ == '__main__':
    main()
